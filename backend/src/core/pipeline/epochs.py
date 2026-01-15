"""
Epoch Manager - System versioning and feature gating.

Manages system evolution through major phases.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import Epoch, EpochStatus

logger = logging.getLogger(__name__)


class EpochManager:
    """
    System epoch management.

    Epochs represent major phases of system evolution:
    - EPOCH_1_MVP: Basic pipeline, manual review
    - EPOCH_2_INTEGRATION: Auto-correction, health inspector
    - EPOCH_3_ADVANCED: Full automation, predictive escalation

    Each epoch enables/disables specific features.
    """

    # Epoch definitions
    EPOCH_DEFINITIONS = {
        "EPOCH_1_MVP": {
            "version": "0.1.0",
            "description": "Basic pipeline with manual review",
            "features": [
                "basic_pipeline",
                "manual_review",
                "port_allocation",
            ],
            "guardrails_mode": "strict",
        },
        "EPOCH_2_INTEGRATION": {
            "version": "0.2.0",
            "description": "Auto-correction and health inspection",
            "features": [
                "basic_pipeline",
                "manual_review",
                "port_allocation",
                "neural_ralph",
                "health_inspector",
                "auto_lint_fix",
            ],
            "guardrails_mode": "standard",
        },
        "EPOCH_3_ADVANCED": {
            "version": "0.3.0",
            "description": "Full automation with predictive escalation",
            "features": [
                "basic_pipeline",
                "manual_review",
                "port_allocation",
                "neural_ralph",
                "health_inspector",
                "auto_lint_fix",
                "auto_approve",
                "predictive_escalation",
                "self_healing",
            ],
            "guardrails_mode": "adaptive",
        },
    }

    # Feature descriptions
    FEATURE_DESCRIPTIONS = {
        "basic_pipeline": "Core pipeline stages (queued → completed)",
        "manual_review": "PO review required for all tasks",
        "port_allocation": "Dynamic port allocation from pools",
        "neural_ralph": "Automatic error correction (3 retries)",
        "health_inspector": "Full verification (tests, lint, UI)",
        "auto_lint_fix": "Automatic lint fixes with ruff/eslint",
        "auto_approve": "Auto-approve if health > 90%",
        "predictive_escalation": "AI predicts when to escalate early",
        "self_healing": "Automatic recovery from failures",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self._current_epoch: Optional[Epoch] = None

    async def get_current_epoch(self) -> Optional[Epoch]:
        """Get the currently active epoch."""
        if self._current_epoch:
            return self._current_epoch

        result = await self.db.execute(
            select(Epoch)
            .where(Epoch.status == EpochStatus.ACTIVE)
            .order_by(Epoch.started_at.desc())
        )
        self._current_epoch = result.scalar_one_or_none()
        return self._current_epoch

    async def initialize_epoch(self, epoch_name: str) -> Epoch:
        """
        Initialize an epoch if not already exists.

        Args:
            epoch_name: Name of epoch to initialize

        Returns:
            Created or existing Epoch
        """
        if epoch_name not in self.EPOCH_DEFINITIONS:
            raise ValueError(f"Unknown epoch: {epoch_name}")

        # Check if already exists
        result = await self.db.execute(
            select(Epoch).where(Epoch.name == epoch_name)
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        # Create new epoch
        definition = self.EPOCH_DEFINITIONS[epoch_name]
        epoch = Epoch(
            name=epoch_name,
            version=definition["version"],
            description=definition["description"],
            features=definition["features"],
            status=EpochStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )

        self.db.add(epoch)
        await self.db.commit()
        await self.db.refresh(epoch)

        logger.info(f"Initialized epoch {epoch_name} v{definition['version']}")
        self._current_epoch = epoch

        return epoch

    async def transition_epoch(self, new_epoch_name: str) -> Epoch:
        """
        Transition to a new epoch.

        Args:
            new_epoch_name: Target epoch name

        Returns:
            New active Epoch
        """
        if new_epoch_name not in self.EPOCH_DEFINITIONS:
            raise ValueError(f"Unknown epoch: {new_epoch_name}")

        # Mark current epoch as completed
        current = await self.get_current_epoch()
        if current:
            current.status = EpochStatus.COMPLETED
            current.completed_at = datetime.now(timezone.utc)

        # Create or activate new epoch
        result = await self.db.execute(
            select(Epoch).where(Epoch.name == new_epoch_name)
        )
        new_epoch = result.scalar_one_or_none()

        if new_epoch:
            new_epoch.status = EpochStatus.ACTIVE
            new_epoch.started_at = datetime.now(timezone.utc)
            new_epoch.completed_at = None
        else:
            definition = self.EPOCH_DEFINITIONS[new_epoch_name]
            new_epoch = Epoch(
                name=new_epoch_name,
                version=definition["version"],
                description=definition["description"],
                features=definition["features"],
                status=EpochStatus.ACTIVE,
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(new_epoch)

        await self.db.commit()
        await self.db.refresh(new_epoch)

        logger.info(f"Transitioned to epoch {new_epoch_name}")
        self._current_epoch = new_epoch

        return new_epoch

    async def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature is enabled in the current epoch.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is enabled
        """
        epoch = await self.get_current_epoch()

        if not epoch:
            # Default to MVP features if no epoch set
            mvp_features = self.EPOCH_DEFINITIONS["EPOCH_1_MVP"]["features"]
            return feature in mvp_features

        return feature in epoch.features

    async def get_enabled_features(self) -> list[str]:
        """Get list of all enabled features in current epoch."""
        epoch = await self.get_current_epoch()

        if not epoch:
            return self.EPOCH_DEFINITIONS["EPOCH_1_MVP"]["features"]

        return epoch.features

    def get_feature_info(self, feature: str) -> dict:
        """
        Get information about a feature.

        Args:
            feature: Feature name

        Returns:
            Dict with feature information
        """
        return {
            "name": feature,
            "description": self.FEATURE_DESCRIPTIONS.get(feature, "No description"),
            "available_in": [
                name for name, defn in self.EPOCH_DEFINITIONS.items()
                if feature in defn["features"]
            ],
        }

    def get_all_features(self) -> list[dict]:
        """Get information about all features."""
        return [
            self.get_feature_info(feature)
            for feature in self.FEATURE_DESCRIPTIONS.keys()
        ]

    async def get_epoch_history(self) -> list[Epoch]:
        """Get all epochs ordered by start date."""
        result = await self.db.execute(
            select(Epoch).order_by(Epoch.started_at.desc())
        )
        return list(result.scalars().all())

    def get_epoch_definition(self, epoch_name: str) -> Optional[dict]:
        """Get definition for an epoch."""
        return self.EPOCH_DEFINITIONS.get(epoch_name)

    def get_all_epoch_definitions(self) -> dict:
        """Get all epoch definitions."""
        return self.EPOCH_DEFINITIONS

    async def get_guardrails_mode(self) -> str:
        """Get the guardrails mode for current epoch."""
        epoch = await self.get_current_epoch()

        if not epoch:
            return "strict"

        definition = self.EPOCH_DEFINITIONS.get(epoch.name, {})
        return definition.get("guardrails_mode", "standard")
