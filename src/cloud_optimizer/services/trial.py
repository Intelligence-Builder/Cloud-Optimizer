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
    "scans": 50,  # per month
    "questions": 500,  # per month
    "documents": 20,  # total
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

        # Check if trial is converted FIRST - converted users have no limits
        # regardless of trial status or expiration
        if trial.converted_at:
            return True  # No limits for converted (paid) users

        # Check if trial is expired (only for non-converted users)
        now = datetime.now(timezone.utc)
        if trial.status != "active" or now > trial.expires_at:
            raise TrialExpiredError("Trial period has expired")

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

    # TRL-006: Analytics methods

    async def get_trial_analytics(self) -> dict[str, Any]:
        """
        Get aggregate trial analytics for admin dashboard.

        Returns:
            Dictionary containing trial metrics.
        """
        from sqlalchemy import case, func

        # Get trial counts by status
        result = await self.db.execute(
            select(
                func.count(Trial.trial_id).label("total"),
                func.count(case((Trial.status == "active", 1))).label("active"),
                func.count(case((Trial.status == "converted", 1))).label("converted"),
                func.count(case((Trial.extended_at.isnot(None), 1))).label("extended"),
            )
        )
        counts = result.one()
        total = counts.total or 0
        active = counts.active or 0
        converted = counts.converted or 0
        extended = counts.extended or 0

        # Calculate expired (not active and not converted)
        now = datetime.now(timezone.utc)
        expired_result = await self.db.execute(
            select(func.count(Trial.trial_id)).where(
                Trial.status == "active",
                Trial.expires_at < now,
            )
        )
        expired = expired_result.scalar() or 0

        # Calculate conversion rate
        conversion_rate = (converted / total * 100) if total > 0 else 0.0
        extension_rate = (extended / total * 100) if total > 0 else 0.0

        # Calculate average days to conversion
        avg_days_result = await self.db.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch", Trial.converted_at - Trial.started_at
                    ) / 86400  # seconds to days
                )
            ).where(Trial.converted_at.isnot(None))
        )
        avg_days = avg_days_result.scalar()

        return {
            "total_trials": total,
            "active_trials": active - expired,  # Active minus expired
            "expired_trials": expired,
            "converted_trials": converted,
            "conversion_rate": round(conversion_rate, 2),
            "average_days_to_conversion": round(avg_days, 1) if avg_days else None,
            "extension_rate": round(extension_rate, 2),
        }

    async def get_usage_analytics(self) -> dict[str, Any]:
        """
        Get usage analytics by dimension.

        Returns:
            Dictionary containing usage breakdown.
        """
        from sqlalchemy import func

        # Get usage stats per dimension
        result = await self.db.execute(
            select(
                TrialUsage.dimension,
                func.sum(TrialUsage.count).label("total_usage"),
                func.avg(TrialUsage.count).label("avg_usage"),
                func.count(TrialUsage.usage_id).label("trial_count"),
            ).group_by(TrialUsage.dimension)
        )
        usage_rows = result.all()

        dimensions = []
        max_usage = 0
        max_dimension = None
        min_usage = float("inf")
        min_dimension = None

        for row in usage_rows:
            dimension = row.dimension
            total = int(row.total_usage or 0)
            avg = float(row.avg_usage or 0)
            trial_count = int(row.trial_count or 0)

            # Get limit for this dimension
            limit = TRIAL_LIMITS.get(dimension, 0)

            # Count how many reached the limit
            limit_result = await self.db.execute(
                select(func.count(TrialUsage.usage_id)).where(
                    TrialUsage.dimension == dimension,
                    TrialUsage.count >= limit,
                )
            )
            limit_reached = limit_result.scalar() or 0

            # Calculate utilization rate
            utilization = (avg / limit * 100) if limit > 0 else 0.0

            dimensions.append({
                "dimension": dimension,
                "total_usage": total,
                "average_usage": round(avg, 1),
                "limit_reached_count": limit_reached,
                "utilization_rate": round(utilization, 1),
            })

            # Track most/least used
            if total > max_usage:
                max_usage = total
                max_dimension = dimension
            if total < min_usage:
                min_usage = total
                min_dimension = dimension

        return {
            "dimensions": dimensions,
            "most_used_dimension": max_dimension,
            "least_used_dimension": min_dimension,
        }
