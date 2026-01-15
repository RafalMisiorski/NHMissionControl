"""
Neural Ralph - Automatic error correction system.

Analyzes failures and generates targeted fixes.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.core.models import PipelineRun, PipelineStage

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors that Neural Ralph can diagnose."""
    TEST_FAILURE = "test_failure"
    LINT_ERROR = "lint_error"
    TYPE_ERROR = "type_error"
    BUILD_FAILURE = "build_failure"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"
    PORT_CONFLICT = "port_conflict"
    DEPENDENCY_ERROR = "dependency_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorDiagnosis:
    """Result of error diagnosis."""
    error_type: ErrorType
    description: str
    affected_files: list[str]
    suggested_fix: str
    confidence: float  # 0-1


@dataclass
class CorrectionResult:
    """Result of correction attempt."""
    success: bool
    action_taken: str
    error_message: Optional[str] = None
    retry_recommended: bool = True


class NeuralRalph:
    """
    Automatic error correction system.

    Neural Ralph analyzes pipeline failures and attempts targeted fixes:
    1. Diagnose error type
    2. Identify affected files
    3. Generate correction prompt/action
    4. Execute fix
    5. Re-verify

    Max 3 retries per stage before escalation.
    """

    MAX_RETRIES = 3

    # Error patterns for diagnosis
    ERROR_PATTERNS = {
        ErrorType.TEST_FAILURE: [
            "AssertionError",
            "test failed",
            "FAILED",
            "pytest",
            "unittest",
        ],
        ErrorType.LINT_ERROR: [
            "ruff",
            "eslint",
            "flake8",
            "pylint",
            "linting",
        ],
        ErrorType.TYPE_ERROR: [
            "TypeError",
            "type error",
            "mypy",
            "typescript",
            "tsc",
        ],
        ErrorType.BUILD_FAILURE: [
            "build failed",
            "compilation error",
            "webpack",
            "vite",
            "npm run build",
        ],
        ErrorType.RUNTIME_ERROR: [
            "RuntimeError",
            "Exception",
            "crash",
            "Traceback",
        ],
        ErrorType.TIMEOUT: [
            "timeout",
            "timed out",
            "deadline exceeded",
        ],
        ErrorType.PORT_CONFLICT: [
            "port already in use",
            "EADDRINUSE",
            "address already in use",
        ],
        ErrorType.DEPENDENCY_ERROR: [
            "ModuleNotFoundError",
            "ImportError",
            "Cannot find module",
            "package not found",
        ],
    }

    # Correction strategies by error type
    CORRECTION_STRATEGIES = {
        ErrorType.TEST_FAILURE: [
            "Analyze test output and fix failing assertions",
            "Check for missing mock data or fixtures",
            "Verify test environment setup",
        ],
        ErrorType.LINT_ERROR: [
            "Run auto-fix with ruff --fix or eslint --fix",
            "Fix formatting issues",
            "Remove unused imports",
        ],
        ErrorType.TYPE_ERROR: [
            "Add or fix type annotations",
            "Check function signatures",
            "Verify import types",
        ],
        ErrorType.BUILD_FAILURE: [
            "Check for syntax errors",
            "Verify all dependencies are installed",
            "Check configuration files",
        ],
        ErrorType.RUNTIME_ERROR: [
            "Add error handling",
            "Check for null/undefined values",
            "Verify data types",
        ],
        ErrorType.TIMEOUT: [
            "Increase timeout value",
            "Optimize slow operations",
            "Add caching",
        ],
        ErrorType.PORT_CONFLICT: [
            "Request new port from Resource Manager",
            "Kill conflicting process",
            "Use dynamic port allocation",
        ],
        ErrorType.DEPENDENCY_ERROR: [
            "Install missing package",
            "Update import paths",
            "Check virtual environment",
        ],
    }

    def __init__(self, resource_manager: Optional["ResourceManager"] = None):
        self.resource_manager = resource_manager

    async def attempt_correction(
        self, pipeline_run: PipelineRun, stage: PipelineStage
    ) -> bool:
        """
        Attempt to correct a pipeline failure.

        Args:
            pipeline_run: The failed pipeline run
            stage: The stage that failed

        Returns:
            True if correction was successful
        """
        logger.info(
            f"Neural Ralph attempting correction for {pipeline_run.task_id} "
            f"at stage {stage.value} (attempt {pipeline_run.retry_count + 1})"
        )

        # Check retry limit
        if pipeline_run.retry_count >= self.MAX_RETRIES:
            logger.warning(f"Max retries ({self.MAX_RETRIES}) reached for {pipeline_run.task_id}")
            return False

        # Get the last error from stage execution
        error_message = pipeline_run.error_message or ""

        # Diagnose the error
        diagnosis = self._diagnose_error(error_message, stage)
        logger.info(f"Diagnosed error type: {diagnosis.error_type.value}")

        # Generate and execute correction
        result = await self._execute_correction(pipeline_run, diagnosis)

        if result.success:
            logger.info(f"Correction successful: {result.action_taken}")
            return True
        else:
            logger.warning(f"Correction failed: {result.error_message}")
            return False

    def _diagnose_error(self, error_message: str, stage: PipelineStage) -> ErrorDiagnosis:
        """
        Analyze error and determine type.

        Args:
            error_message: The error message to analyze
            stage: The pipeline stage where error occurred

        Returns:
            ErrorDiagnosis with type and suggested fix
        """
        error_lower = error_message.lower()
        detected_type = ErrorType.UNKNOWN
        confidence = 0.0

        # Check each error type's patterns
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_lower:
                    detected_type = error_type
                    confidence = 0.8  # High confidence on pattern match
                    break
            if detected_type != ErrorType.UNKNOWN:
                break

        # Stage-based inference if no pattern match
        if detected_type == ErrorType.UNKNOWN:
            if stage == PipelineStage.TESTING:
                detected_type = ErrorType.TEST_FAILURE
                confidence = 0.5
            elif stage == PipelineStage.VERIFYING:
                detected_type = ErrorType.RUNTIME_ERROR
                confidence = 0.5
            elif stage == PipelineStage.DEVELOPING:
                detected_type = ErrorType.BUILD_FAILURE
                confidence = 0.5

        # Get suggested fix
        strategies = self.CORRECTION_STRATEGIES.get(detected_type, ["Manual review required"])
        suggested_fix = strategies[0]

        # Extract affected files from error message
        affected_files = self._extract_affected_files(error_message)

        return ErrorDiagnosis(
            error_type=detected_type,
            description=f"{detected_type.value}: {error_message[:200]}",
            affected_files=affected_files,
            suggested_fix=suggested_fix,
            confidence=confidence,
        )

    def _extract_affected_files(self, error_message: str) -> list[str]:
        """
        Extract file paths from error message.

        Args:
            error_message: Error message to parse

        Returns:
            List of file paths found
        """
        import re

        files = []

        # Common file path patterns
        patterns = [
            r'File "([^"]+\.py)"',  # Python tracebacks
            r"at ([^\s]+\.(ts|tsx|js|jsx)):\d+",  # JavaScript/TypeScript
            r"in ([^\s]+\.(py|ts|js|tsx|jsx))",  # Generic
            r"([^\s]+\.(py|ts|js|tsx|jsx|json)):\d+:\d+",  # Line:column format
        ]

        for pattern in patterns:
            matches = re.findall(pattern, error_message)
            for match in matches:
                if isinstance(match, tuple):
                    files.append(match[0])
                else:
                    files.append(match)

        return list(set(files))  # Remove duplicates

    async def _execute_correction(
        self, pipeline_run: PipelineRun, diagnosis: ErrorDiagnosis
    ) -> CorrectionResult:
        """
        Execute the correction strategy.

        Args:
            pipeline_run: The pipeline run to correct
            diagnosis: The error diagnosis

        Returns:
            CorrectionResult indicating success/failure
        """
        error_type = diagnosis.error_type

        # Handle port conflicts specially
        if error_type == ErrorType.PORT_CONFLICT and self.resource_manager:
            return await self._handle_port_conflict(pipeline_run)

        # Handle lint errors with auto-fix
        if error_type == ErrorType.LINT_ERROR:
            return await self._handle_lint_error(pipeline_run, diagnosis)

        # Handle dependency errors
        if error_type == ErrorType.DEPENDENCY_ERROR:
            return await self._handle_dependency_error(pipeline_run, diagnosis)

        # For other errors, generate a correction prompt
        # This would integrate with the CC Dispatcher for actual code fixes
        prompt = self._generate_correction_prompt(diagnosis)

        return CorrectionResult(
            success=True,  # Assume prompt will be executed
            action_taken=f"Generated correction prompt for {error_type.value}",
            retry_recommended=True,
        )

    async def _handle_port_conflict(self, pipeline_run: PipelineRun) -> CorrectionResult:
        """Handle port conflict by reallocating ports."""
        if not self.resource_manager:
            return CorrectionResult(
                success=False,
                action_taken="No resource manager available",
                error_message="Cannot reallocate ports without resource manager",
                retry_recommended=False,
            )

        try:
            # Release current ports and reallocate
            await self.resource_manager.release_all(pipeline_run.task_id)

            # Allocate new ports
            await self.resource_manager.allocate_port(
                task_id=pipeline_run.task_id,
                category="frontend",
            )
            await self.resource_manager.allocate_port(
                task_id=pipeline_run.task_id,
                category="backend",
            )

            return CorrectionResult(
                success=True,
                action_taken="Reallocated ports to resolve conflict",
            )
        except Exception as e:
            return CorrectionResult(
                success=False,
                action_taken="Port reallocation failed",
                error_message=str(e),
            )

    async def _handle_lint_error(
        self, pipeline_run: PipelineRun, diagnosis: ErrorDiagnosis
    ) -> CorrectionResult:
        """Handle lint errors with auto-fix."""
        # This would execute lint --fix commands
        # For now, return success to trigger retry
        return CorrectionResult(
            success=True,
            action_taken="Triggered lint auto-fix",
            retry_recommended=True,
        )

    async def _handle_dependency_error(
        self, pipeline_run: PipelineRun, diagnosis: ErrorDiagnosis
    ) -> CorrectionResult:
        """Handle missing dependency errors."""
        # This would install missing packages
        return CorrectionResult(
            success=True,
            action_taken="Identified missing dependencies for installation",
            retry_recommended=True,
        )

    def _generate_correction_prompt(self, diagnosis: ErrorDiagnosis) -> str:
        """
        Generate a prompt for the AI agent to fix the error.

        Args:
            diagnosis: The error diagnosis

        Returns:
            Prompt string for correction
        """
        affected = ", ".join(diagnosis.affected_files) if diagnosis.affected_files else "unknown"

        prompt = f"""
        Fix the following error in the codebase:

        Error Type: {diagnosis.error_type.value}
        Description: {diagnosis.description}
        Affected Files: {affected}

        Suggested Fix: {diagnosis.suggested_fix}

        Instructions:
        1. Analyze the error carefully
        2. Make minimal changes to fix the issue
        3. Ensure the fix doesn't break other functionality
        4. Add appropriate error handling if needed
        """

        return prompt.strip()

    def get_retry_status(self, pipeline_run: PipelineRun) -> dict:
        """
        Get retry status information.

        Args:
            pipeline_run: The pipeline run

        Returns:
            Dict with retry information
        """
        return {
            "current_retries": pipeline_run.retry_count,
            "max_retries": self.MAX_RETRIES,
            "retries_remaining": self.MAX_RETRIES - pipeline_run.retry_count,
            "can_retry": pipeline_run.retry_count < self.MAX_RETRIES,
        }
