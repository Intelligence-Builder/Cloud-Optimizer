"""
Trial management service for Cloud Optimizer.

Implements trial period management, usage tracking, and limit enforcement.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloud_optimizer.models.trial import Trial, TrialUsage


class TrialError(Exception):
    """Base exception for trial-related errors."""

    pass


class TrialExpiredError(TrialError):
    """Trial period has expired."""

    pass


class TrialLimitExceededError(TrialError):
    """Trial usage limit has been exceeded."""

    pass


class TrialExtensionError(TrialError):
    """Trial extension is not allowed."""

    pass


# Trial limits configuration
TRIAL_LIMITS = {
    "scans": 10,  # per month
    "questions": 50,  # per month
    "documents": 5,  # total
}

TRIAL_DURATION_DAYS = 14
TRIAL_EXTENSION_DAYS = 7


class TrialService:
    """
    Trial management service.

    Handles:
    - Trial creation and expiration
    - Usage tracking and limit enforcement
    - Trial extensions
    - Trial status reporting
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize trial service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def get_or_create_trial(self, user_id: UUID) -> Trial:
        """
        Get or create trial for user.

        Auto-creates a 14-day trial if user doesn't have one.

        Args:
            user_id: User's UUID.

        Returns:
            Trial instance.
        """
        # Check for existing trial
        result = await self.db.execute(select(Trial).where(Trial.user_id == user_id))
        trial = result.scalar_one_or_none()

        if trial:
            return trial

        # Create new trial
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=TRIAL_DURATION_DAYS)

        trial = Trial(
            user_id=user_id,
            started_at=now,
            expires_at=expires_at,
            status="active",
        )
        self.db.add(trial)
        await self.db.flush()

        return trial

    async def check_limit(
        self,
        user_id: UUID,
        dimension: str,
    ) -> bool:
        """
        Check if user can perform action within trial limits.

        Args:
            user_id: User's UUID.
            dimension: Usage dimension (scans, questions, documents).

        Returns:
            True if action is allowed, False otherwise.

        Raises:
            TrialExpiredError: If trial has expired.
            TrialLimitExceededError: If limit has been exceeded.
        """
        trial = await self.get_or_create_trial(user_id)

        # Check if trial is expired
        now = datetime.now(timezone.utc)
        if trial.status != "active" or now > trial.expires_at:
            raise TrialExpiredError("Trial period has expired")

        # Check if trial is converted
        if trial.converted_at:
            return True  # No limits for converted users

        # Get current usage
        result = await self.db.execute(
            select(TrialUsage).where(
                TrialUsage.trial_id == trial.trial_id,
                TrialUsage.dimension == dimension,
            )
        )
        usage = result.scalar_one_or_none()

        # Check limit
        limit = TRIAL_LIMITS.get(dimension, 0)
        current_count = usage.count if usage else 0

        if current_count >= limit:
            raise TrialLimitExceededError(
                f"Trial limit exceeded for {dimension}: {current_count}/{limit}"
            )

        return True

    async def record_usage(
        self,
        user_id: UUID,
        dimension: str,
        count: int = 1,
    ) -> TrialUsage:
        """
        Record usage for a dimension.

        Increments the usage counter for the specified dimension.

        Args:
            user_id: User's UUID.
            dimension: Usage dimension (scans, questions, documents).
            count: Amount to increment (default: 1).

        Returns:
            Updated TrialUsage instance.
        """
        trial = await self.get_or_create_trial(user_id)

        # Get or create usage record
        result = await self.db.execute(
            select(TrialUsage).where(
                TrialUsage.trial_id == trial.trial_id,
                TrialUsage.dimension == dimension,
            )
        )
        usage = result.scalar_one_or_none()

        if usage:
            usage.count += count
            usage.updated_at = datetime.now(timezone.utc)
        else:
            usage = TrialUsage(
                trial_id=trial.trial_id,
                dimension=dimension,
                count=count,
            )
            self.db.add(usage)

        await self.db.flush()
        return usage

    async def extend_trial(self, user_id: UUID) -> Trial:
        """
        Extend trial by 7 days (one-time only).

        Args:
            user_id: User's UUID.

        Returns:
            Updated Trial instance.

        Raises:
            TrialExtensionError: If trial cannot be extended.
        """
        trial = await self.get_or_create_trial(user_id)

        # Check if already extended
        if trial.extended_at:
            raise TrialExtensionError("Trial has already been extended")

        # Check if converted
        if trial.converted_at:
            raise TrialExtensionError("Trial has been converted to paid account")

        # Extend trial
        now = datetime.now(timezone.utc)
        trial.expires_at = trial.expires_at + timedelta(days=TRIAL_EXTENSION_DAYS)
        trial.extended_at = now

        await self.db.flush()
        return trial

    async def get_trial_status(self, user_id: UUID) -> dict[str, Any]:
        """
        Get comprehensive trial status for UI display.

        Args:
            user_id: User's UUID.

        Returns:
            Dictionary containing trial status information.
        """
        trial = await self.get_or_create_trial(user_id)

        # Get all usage records
        result = await self.db.execute(
            select(TrialUsage).where(TrialUsage.trial_id == trial.trial_id)
        )
        usage_records = result.scalars().all()

        # Build usage dict
        usage = {
            dimension: {
                "current": 0,
                "limit": limit,
                "remaining": limit,
            }
            for dimension, limit in TRIAL_LIMITS.items()
        }

        for record in usage_records:
            if record.dimension in usage:
                usage[record.dimension]["current"] = record.count
                usage[record.dimension]["remaining"] = max(
                    0, TRIAL_LIMITS[record.dimension] - record.count
                )

        # Calculate days remaining
        now = datetime.now(timezone.utc)
        days_remaining = (trial.expires_at - now).days
        is_active = trial.status == "active" and now <= trial.expires_at

        return {
            "trial_id": str(trial.trial_id),
            "status": trial.status,
            "is_active": is_active,
            "started_at": trial.started_at.isoformat(),
            "expires_at": trial.expires_at.isoformat(),
            "days_remaining": max(0, days_remaining),
            "extended": trial.extended_at is not None,
            "can_extend": trial.extended_at is None and not trial.converted_at,
            "converted": trial.converted_at is not None,
            "usage": usage,
        }

    async def convert_trial(self, user_id: UUID) -> Trial:
        """
        Convert trial to paid account.

        Args:
            user_id: User's UUID.

        Returns:
            Updated Trial instance.
        """
        trial = await self.get_or_create_trial(user_id)

        if not trial.converted_at:
            trial.converted_at = datetime.now(timezone.utc)
            trial.status = "converted"
            await self.db.flush()

        return trial
