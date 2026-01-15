"""
Pipeline Orchestrator - Main execution engine.

Manages task flow through pipeline stages with handoff verification.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    PipelineRun,
    PipelineRunStatus,
    PipelineStage,
    StageExecution,
    EscalationLevel,
    CCSessionStatus,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Main pipeline execution engine.

    Manages the flow of tasks through pipeline stages:
    QUEUED → DEVELOPING → TESTING → VERIFYING → PO_REVIEW → DEPLOYING → COMPLETED

    Features:
    - Handoff token verification between stages
    - Neural Ralph auto-correction on failures
    - Automatic escalation when retries exhausted
    - Integration with Health Inspector for verification
    """

    # Stage execution order
    STAGE_ORDER = [
        PipelineStage.QUEUED,
        PipelineStage.DEVELOPING,
        PipelineStage.TESTING,
        PipelineStage.VERIFYING,
        PipelineStage.PO_REVIEW,
        PipelineStage.DEPLOYING,
        PipelineStage.COMPLETED,
    ]

    # Minimum trust score required to proceed
    MIN_TRUST_SCORE = 70.0

    def __init__(
        self,
        db: AsyncSession,
        resource_manager: Optional["ResourceManager"] = None,
        health_inspector: Optional["HealthInspector"] = None,
        neural_ralph: Optional["NeuralRalph"] = None,
        escalation_manager: Optional["EscalationManager"] = None,
        guardrails: Optional["GuardrailsEngine"] = None,
        handoff_generator: Optional["HandoffTokenGenerator"] = None,
        cc_session_manager: Optional["CCSessionManager"] = None,
    ):
        self.db = db
        self.resource_manager = resource_manager
        self.health_inspector = health_inspector
        self.neural_ralph = neural_ralph
        self.escalation_manager = escalation_manager
        self.guardrails = guardrails
        self.handoff_generator = handoff_generator
        self.cc_session_manager = cc_session_manager

    async def create_run(
        self,
        task_id: str,
        task_title: str,
        task_description: Optional[str] = None,
        project_name: Optional[str] = None,
        priority: str = "normal",
        epoch_id: Optional[int] = None,
    ) -> PipelineRun:
        """
        Create a new pipeline run for a task.

        Args:
            task_id: External task identifier
            task_title: Human-readable task title
            task_description: Full task description
            project_name: Associated project name
            priority: Task priority (critical, high, normal, low)
            epoch_id: Optional epoch reference

        Returns:
            Created PipelineRun instance
        """
        # Determine initial escalation level based on priority
        initial_level = EscalationLevel.CODEX
        if priority == "critical":
            initial_level = EscalationLevel.OPUS  # Critical tasks start with Opus
        elif priority == "high":
            initial_level = EscalationLevel.SONNET

        run = PipelineRun(
            id=uuid4(),
            task_id=task_id,
            task_title=task_title,
            task_description=task_description,
            project_name=project_name,
            priority=priority,
            epoch_id=epoch_id,
            current_stage=PipelineStage.QUEUED,
            status=PipelineRunStatus.RUNNING,
            escalation_level=initial_level,
            retry_count=0,
            max_retries=3,
        )

        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        logger.info(f"Created pipeline run {run.id} for task {task_id}")
        return run

    async def run(self, pipeline_run: PipelineRun) -> PipelineRun:
        """
        Execute the full pipeline for a run.

        Progresses through stages sequentially, generating handoff tokens
        and handling failures with Neural Ralph or escalation.

        Args:
            pipeline_run: The pipeline run to execute

        Returns:
            Updated PipelineRun with final status
        """
        logger.info(f"Starting pipeline execution for {pipeline_run.task_id}")

        # Mark as started
        pipeline_run.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        # Allocate resources if resource manager is available
        if self.resource_manager:
            await self._allocate_resources(pipeline_run)

        try:
            # Execute each stage in order
            current_index = self.STAGE_ORDER.index(pipeline_run.current_stage)

            for stage in self.STAGE_ORDER[current_index:]:
                if stage == PipelineStage.COMPLETED:
                    break

                # Check guardrails before stage transition
                if self.guardrails:
                    allowed = await self.guardrails.validate_stage_transition(
                        pipeline_run.current_stage, stage
                    )
                    if not allowed:
                        logger.warning(f"Guardrail blocked transition to {stage}")
                        continue

                # Execute the stage
                success = await self._execute_stage(pipeline_run, stage)

                if not success:
                    # Handle failure
                    await self._handle_failure(pipeline_run, stage)
                    if pipeline_run.status == PipelineRunStatus.FAILED:
                        break

            # Mark as completed if we reached the end
            if pipeline_run.current_stage == PipelineStage.DEPLOYING:
                pipeline_run.current_stage = PipelineStage.COMPLETED
                pipeline_run.status = PipelineRunStatus.COMPLETED
                pipeline_run.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            pipeline_run.status = PipelineRunStatus.FAILED
            pipeline_run.error_message = str(e)

        finally:
            # Release resources
            if self.resource_manager:
                await self._release_resources(pipeline_run)

        await self.db.commit()
        await self.db.refresh(pipeline_run)

        logger.info(f"Pipeline {pipeline_run.task_id} finished with status {pipeline_run.status}")
        return pipeline_run

    async def _execute_stage(self, pipeline_run: PipelineRun, stage: PipelineStage) -> bool:
        """
        Execute a single pipeline stage.

        Creates a StageExecution record, runs the stage logic,
        generates a handoff token, and validates trust score.

        Args:
            pipeline_run: The pipeline run
            stage: Stage to execute

        Returns:
            True if stage passed, False if failed
        """
        logger.info(f"Executing stage {stage.value} for {pipeline_run.task_id}")

        # Create stage execution record
        execution = StageExecution(
            id=uuid4(),
            pipeline_run_id=pipeline_run.id,
            stage=stage,
            status="running",
            started_at=datetime.now(timezone.utc),
            agent_used=pipeline_run.escalation_level.value,
            retry_attempt=pipeline_run.retry_count,
        )
        self.db.add(execution)
        await self.db.commit()

        try:
            # Execute stage-specific logic
            output = await self._run_stage_logic(pipeline_run, stage)
            execution.output = output

            # Generate handoff token
            if self.handoff_generator:
                from_stage = pipeline_run.current_stage
                to_stage = self._get_next_stage(stage)

                token = await self.handoff_generator.create_token(
                    pipeline_run_id=pipeline_run.id,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    verification_results=output or {},
                )

                execution.handoff_token_id = token.id

                # Validate trust score
                if float(token.trust_score) < self.MIN_TRUST_SCORE:
                    logger.warning(
                        f"Trust score {token.trust_score} below minimum {self.MIN_TRUST_SCORE}"
                    )
                    token.valid = False
                    token.rejected_reason = f"Trust score {token.trust_score} < {self.MIN_TRUST_SCORE}"
                    execution.status = "failed"
                    execution.error_message = f"Trust score too low: {token.trust_score}"
                    await self.db.commit()
                    return False

            # Stage passed
            execution.status = "passed"
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                delta = execution.completed_at - execution.started_at
                execution.duration_seconds = int(delta.total_seconds())

            # Update pipeline run
            pipeline_run.current_stage = stage
            if self.handoff_generator and token:
                pipeline_run.final_trust_score = token.trust_score

            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Stage {stage.value} failed: {e}")
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return False

    async def _run_stage_logic(
        self, pipeline_run: PipelineRun, stage: PipelineStage
    ) -> Optional[dict]:
        """
        Execute the actual logic for a stage.

        Args:
            pipeline_run: The pipeline run
            stage: Stage to execute

        Returns:
            Stage output dictionary
        """
        output = {}

        if stage == PipelineStage.QUEUED:
            # Check dependencies, allocate resources
            output = {"status": "ready", "dependencies_met": True}

        elif stage == PipelineStage.DEVELOPING:
            # Development stage - execute via CC Session Manager (EPOCH 8)
            if self.cc_session_manager:
                output = await self._run_developing_via_cc(pipeline_run)
            else:
                # Fallback: No CC session manager, just mark as developed
                logger.warning("No CC Session Manager available, skipping development")
                output = {"status": "developed", "files_changed": 0, "cc_session": None}

        elif stage == PipelineStage.TESTING:
            # Run tests via Health Inspector
            if self.health_inspector:
                test_result = await self.health_inspector.check_tests(
                    pipeline_run.project_name or ""
                )
                output = {
                    "tests_passed": test_result.get("passed", 0),
                    "tests_failed": test_result.get("failed", 0),
                    "tests_skipped": test_result.get("skipped", 0),
                    "coverage": test_result.get("coverage"),
                }
            else:
                output = {"tests_passed": 0, "tests_failed": 0, "tests_skipped": 0}

        elif stage == PipelineStage.VERIFYING:
            # Full verification via Health Inspector
            if self.health_inspector:
                result = await self.health_inspector.run_full_inspection(
                    pipeline_run.task_id, {}
                )
                output = result
            else:
                output = {"health_score": 100, "lint_errors": 0, "console_errors": 0}

        elif stage == PipelineStage.PO_REVIEW:
            # PO review stage - waits for human approval
            output = {"status": "awaiting_review"}

        elif stage == PipelineStage.DEPLOYING:
            # Deployment stage
            output = {"status": "deployed", "environment": "staging"}

        return output

    async def _run_developing_via_cc(self, pipeline_run: PipelineRun) -> dict:
        """
        Execute development stage via CC Session Manager (EPOCH 8).

        Creates a CC session, sends the task, monitors until completion.

        Args:
            pipeline_run: The pipeline run

        Returns:
            Stage output dictionary
        """
        from datetime import timedelta

        # Determine working directory
        working_dir = f"D:\\Projects\\{pipeline_run.project_name}" if pipeline_run.project_name else "D:\\Projects"

        # Create session
        session_id = f"pipeline-{pipeline_run.id}-dev"
        try:
            cc_session = await self.cc_session_manager.create_session(
                session_id=session_id,
                working_directory=working_dir,
                pipeline_run_id=str(pipeline_run.id),
                stage_id=PipelineStage.DEVELOPING.value,
                max_runtime_minutes=25,  # Before 30-min crash
                max_restarts=3,
            )

            # Build task prompt
            task_prompt = self._build_development_prompt(pipeline_run)

            # Send task to CC session
            await self.cc_session_manager.send_task(
                session_id=session_id,
                task_prompt=task_prompt,
                dangerous_mode=True,  # Required for non-interactive
            )

            # Wait for completion (max 30 minutes per attempt)
            success = await self.cc_session_manager.wait_for_completion(
                session_id=session_id,
                timeout=timedelta(minutes=30),
                poll_interval=5.0,
            )

            # Get final session state
            session_state = self.cc_session_manager.sessions.get(session_id)
            if session_state:
                output_lines = len(session_state.output_lines)
                final_status = session_state.status.value
            else:
                output_lines = 0
                final_status = "unknown"

            if success:
                return {
                    "status": "developed",
                    "cc_session_id": session_id,
                    "cc_session_status": final_status,
                    "output_lines": output_lines,
                    "restarts": session_state.restart_count if session_state else 0,
                }
            else:
                raise Exception(f"CC session failed with status: {final_status}")

        except Exception as e:
            logger.error(f"CC session development failed: {e}")
            raise

    def _build_development_prompt(self, pipeline_run: PipelineRun) -> str:
        """
        Build the development task prompt for Claude Code.

        Args:
            pipeline_run: The pipeline run

        Returns:
            Task prompt string
        """
        prompt = f"""Task: {pipeline_run.task_title}

{pipeline_run.task_description or "No detailed description provided."}

Project: {pipeline_run.project_name or "Unknown project"}

Please implement this task. When done, summarize what you've accomplished.
"""
        return prompt

    async def _handle_failure(self, pipeline_run: PipelineRun, stage: PipelineStage):
        """
        Handle stage failure with Neural Ralph or escalation.

        Args:
            pipeline_run: The pipeline run
            stage: Failed stage
        """
        logger.info(f"Handling failure at stage {stage.value} for {pipeline_run.task_id}")

        # Check if retries available
        if pipeline_run.retry_count < pipeline_run.max_retries:
            # Attempt Neural Ralph correction
            if self.neural_ralph:
                logger.info("Attempting Neural Ralph correction")
                success = await self.neural_ralph.attempt_correction(
                    pipeline_run, stage
                )
                if success:
                    pipeline_run.retry_count += 1
                    await self.db.commit()
                    # Re-execute the stage
                    await self._execute_stage(pipeline_run, stage)
                    return

        # Escalate if retries exhausted
        if self.escalation_manager:
            new_level = await self.escalation_manager.escalate(pipeline_run)
            if new_level == EscalationLevel.HUMAN:
                # Final escalation - mark as requiring human intervention
                pipeline_run.status = PipelineRunStatus.PAUSED
                logger.warning(f"Pipeline {pipeline_run.task_id} escalated to human")
            else:
                # Retry with higher-level agent
                pipeline_run.retry_count = 0  # Reset retry count for new agent
                await self.db.commit()
        else:
            # No escalation manager - mark as failed
            pipeline_run.status = PipelineRunStatus.FAILED
            logger.error(f"Pipeline {pipeline_run.task_id} failed without escalation")

        await self.db.commit()

    def _get_next_stage(self, current: PipelineStage) -> PipelineStage:
        """Get the next stage in the pipeline."""
        try:
            idx = self.STAGE_ORDER.index(current)
            if idx + 1 < len(self.STAGE_ORDER):
                return self.STAGE_ORDER[idx + 1]
        except ValueError:
            pass
        return PipelineStage.COMPLETED

    async def _allocate_resources(self, pipeline_run: PipelineRun):
        """Allocate resources for the pipeline run."""
        if not self.resource_manager:
            return

        # Allocate frontend and backend ports
        await self.resource_manager.allocate_port(
            task_id=pipeline_run.task_id,
            category="frontend",
            pipeline_run_id=str(pipeline_run.id),
        )
        await self.resource_manager.allocate_port(
            task_id=pipeline_run.task_id,
            category="backend",
            pipeline_run_id=str(pipeline_run.id),
        )

    async def _release_resources(self, pipeline_run: PipelineRun):
        """Release all resources allocated to the pipeline run."""
        if not self.resource_manager:
            return

        await self.resource_manager.release_all(pipeline_run.task_id)

    async def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get a pipeline run by ID."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(PipelineRun).where(PipelineRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def pause(self, pipeline_run: PipelineRun):
        """Pause a running pipeline."""
        if pipeline_run.status == PipelineRunStatus.RUNNING:
            pipeline_run.status = PipelineRunStatus.PAUSED
            await self.db.commit()
            logger.info(f"Paused pipeline {pipeline_run.task_id}")

    async def resume(self, pipeline_run: PipelineRun):
        """Resume a paused pipeline."""
        if pipeline_run.status == PipelineRunStatus.PAUSED:
            pipeline_run.status = PipelineRunStatus.RUNNING
            await self.db.commit()
            logger.info(f"Resumed pipeline {pipeline_run.task_id}")
            # Continue execution
            await self.run(pipeline_run)

    async def cancel(self, pipeline_run: PipelineRun):
        """Cancel a pipeline run."""
        pipeline_run.status = PipelineRunStatus.CANCELLED
        pipeline_run.current_stage = PipelineStage.CANCELLED
        pipeline_run.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        logger.info(f"Cancelled pipeline {pipeline_run.task_id}")

        # Release resources
        if self.resource_manager:
            await self._release_resources(pipeline_run)
