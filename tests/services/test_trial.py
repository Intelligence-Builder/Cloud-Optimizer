"""
Comprehensive tests for Trial Management System.

Tests cover:
- Trial creation and retrieval
- Usage tracking and limit enforcement
- Trial extensions
- Trial status reporting
- Trial conversion
- Error handling

Targets 80%+ coverage.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from cloud_optimizer.models.trial import Trial, TrialUsage
from cloud_optimizer.services.trial import (
    TRIAL_DURATION_DAYS,
    TRIAL_EXTENSION_DAYS,
    TRIAL_LIMITS,
    TrialError,
    TrialExpiredError,
    TrialExtensionError,
    TrialLimitExceededError,
    TrialService,
)


@pytest_asyncio.fixture
async def trial_service(db_session):
    """Create TrialService instance with test database session."""
    return TrialService(db_session)


@pytest_asyncio.fixture
async def test_trial(db_session, test_user):
    """Create a test trial for a user."""
    now = datetime.now(timezone.utc)
    trial = Trial(
        user_id=test_user.user_id,
        started_at=now,
        expires_at=now + timedelta(days=TRIAL_DURATION_DAYS),
        status="active",
    )
    db_session.add(trial)
    await db_session.commit()
    await db_session.refresh(trial)
    return trial


@pytest_asyncio.fixture
async def expired_trial(db_session, test_user):
    """Create an expired trial for testing expiration scenarios."""
    now = datetime.now(timezone.utc)
    trial = Trial(
        user_id=test_user.user_id,
        started_at=now - timedelta(days=TRIAL_DURATION_DAYS + 1),
        expires_at=now - timedelta(days=1),
        status="active",
    )
    db_session.add(trial)
    await db_session.commit()
    await db_session.refresh(trial)
    return trial


# Test: get_or_create_trial()


@pytest.mark.asyncio
async def test_get_or_create_trial_creates_new(trial_service, test_user, db_session):
    """Test that get_or_create_trial creates a new trial if none exists."""
    # Verify no trial exists
    result = await db_session.execute(
        select(Trial).where(Trial.user_id == test_user.user_id)
    )
    assert result.scalar_one_or_none() is None

    # Get or create trial
    trial = await trial_service.get_or_create_trial(test_user.user_id)

    # Verify trial was created
    assert trial is not None
    assert trial.user_id == test_user.user_id
    assert trial.status == "active"
    assert trial.started_at is not None
    assert trial.expires_at is not None

    # Verify expiration is correct (14 days from now)
    expected_expires = trial.started_at + timedelta(days=TRIAL_DURATION_DAYS)
    assert abs((trial.expires_at - expected_expires).total_seconds()) < 1


@pytest.mark.asyncio
async def test_get_or_create_trial_returns_existing(
    trial_service, test_user, test_trial
):
    """Test that get_or_create_trial returns existing trial."""
    # Get or create trial (should return existing)
    trial = await trial_service.get_or_create_trial(test_user.user_id)

    # Verify it's the same trial
    assert trial.trial_id == test_trial.trial_id
    assert trial.user_id == test_user.user_id
    assert trial.started_at == test_trial.started_at
    assert trial.expires_at == test_trial.expires_at


# Test: check_limit()


@pytest.mark.asyncio
async def test_check_limit_allows_within_limits(
    trial_service, test_user, test_trial, db_session
):
    """Test that check_limit allows actions within limits."""
    # No usage recorded yet, should be allowed
    result = await trial_service.check_limit(test_user.user_id, "scans")
    assert result is True


@pytest.mark.asyncio
async def test_check_limit_blocks_when_exceeded(
    trial_service, test_user, test_trial, db_session
):
    """Test that check_limit blocks when limit is exceeded."""
    # Create usage record at the limit
    usage = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="scans",
        count=TRIAL_LIMITS["scans"],
    )
    db_session.add(usage)
    await db_session.commit()

    # Should raise exception
    with pytest.raises(TrialLimitExceededError) as exc_info:
        await trial_service.check_limit(test_user.user_id, "scans")

    assert "Trial limit exceeded" in str(exc_info.value)
    assert "scans" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_limit_blocks_expired_trial(
    trial_service, test_user, expired_trial
):
    """Test that check_limit blocks when trial has expired."""
    with pytest.raises(TrialExpiredError) as exc_info:
        await trial_service.check_limit(test_user.user_id, "scans")

    assert "Trial period has expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_check_limit_allows_converted_users(
    trial_service, test_user, test_trial, db_session
):
    """Test that check_limit allows unlimited access for converted users."""
    # Mark trial as converted with "converted" status
    # Converted users should bypass ALL limits regardless of trial status
    test_trial.converted_at = datetime.now(timezone.utc)
    test_trial.status = "converted"
    await db_session.commit()

    # Create usage WAY over the limit
    usage = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="scans",
        count=TRIAL_LIMITS["scans"] + 100,  # Way over limit
    )
    db_session.add(usage)
    await db_session.commit()

    # Should still be allowed (no limits for converted/paid users)
    result = await trial_service.check_limit(test_user.user_id, "scans")
    assert result is True


@pytest.mark.asyncio
async def test_check_limit_with_unknown_dimension(trial_service, test_user, test_trial):
    """Test that check_limit handles unknown dimensions (defaults to 0 limit)."""
    # Unknown dimension should have 0 limit, so should immediately fail
    with pytest.raises(TrialLimitExceededError):
        await trial_service.check_limit(test_user.user_id, "unknown_dimension")


# Test: record_usage()


@pytest.mark.asyncio
async def test_record_usage_creates_new_record(
    trial_service, test_user, test_trial, db_session
):
    """Test that record_usage creates a new usage record."""
    usage = await trial_service.record_usage(test_user.user_id, "scans", count=1)

    # Verify usage was created
    assert usage is not None
    assert usage.trial_id == test_trial.trial_id
    assert usage.dimension == "scans"
    assert usage.count == 1

    # Verify it's in the database
    result = await db_session.execute(
        select(TrialUsage).where(
            TrialUsage.trial_id == test_trial.trial_id,
            TrialUsage.dimension == "scans",
        )
    )
    db_usage = result.scalar_one()
    assert db_usage.count == 1


@pytest.mark.asyncio
async def test_record_usage_increments_existing(
    trial_service, test_user, test_trial, db_session
):
    """Test that record_usage increments existing usage record."""
    # Create initial usage
    usage = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="questions",
        count=5,
    )
    db_session.add(usage)
    await db_session.commit()

    # Record additional usage
    updated_usage = await trial_service.record_usage(
        test_user.user_id, "questions", count=3
    )

    # Verify count was incremented
    assert updated_usage.count == 8

    # Verify in database
    result = await db_session.execute(
        select(TrialUsage).where(
            TrialUsage.trial_id == test_trial.trial_id,
            TrialUsage.dimension == "questions",
        )
    )
    db_usage = result.scalar_one()
    assert db_usage.count == 8


@pytest.mark.asyncio
async def test_record_usage_with_custom_count(
    trial_service, test_user, test_trial, db_session
):
    """Test that record_usage correctly handles custom count values."""
    usage = await trial_service.record_usage(test_user.user_id, "documents", count=5)

    assert usage.count == 5


@pytest.mark.asyncio
async def test_record_usage_updates_timestamp(
    trial_service, test_user, test_trial, db_session
):
    """Test that record_usage updates the updated_at timestamp."""
    # Create initial usage
    usage = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="scans",
        count=1,
    )
    db_session.add(usage)
    await db_session.commit()
    original_updated_at = usage.updated_at

    # Wait a moment to ensure timestamp changes
    import asyncio

    await asyncio.sleep(0.1)

    # Record additional usage
    updated_usage = await trial_service.record_usage(
        test_user.user_id, "scans", count=1
    )

    # Verify timestamp was updated
    assert updated_usage.updated_at > original_updated_at


# Test: extend_trial()


@pytest.mark.asyncio
async def test_extend_trial_success(trial_service, test_user, test_trial, db_session):
    """Test that extend_trial successfully extends the trial."""
    original_expires = test_trial.expires_at

    # Extend trial
    extended_trial = await trial_service.extend_trial(test_user.user_id)

    # Verify extension
    assert extended_trial.extended_at is not None
    expected_new_expires = original_expires + timedelta(days=TRIAL_EXTENSION_DAYS)
    assert abs((extended_trial.expires_at - expected_new_expires).total_seconds()) < 1


@pytest.mark.asyncio
async def test_extend_trial_fails_on_second_attempt(
    trial_service, test_user, test_trial, db_session
):
    """Test that extend_trial fails on second extension attempt."""
    # First extension should succeed
    await trial_service.extend_trial(test_user.user_id)

    # Second extension should fail
    with pytest.raises(TrialExtensionError) as exc_info:
        await trial_service.extend_trial(test_user.user_id)

    assert "already been extended" in str(exc_info.value)


@pytest.mark.asyncio
async def test_extend_trial_fails_for_converted(
    trial_service, test_user, test_trial, db_session
):
    """Test that extend_trial fails for converted trials."""
    # Mark trial as converted
    test_trial.converted_at = datetime.now(timezone.utc)
    test_trial.status = "converted"
    await db_session.commit()

    # Extension should fail
    with pytest.raises(TrialExtensionError) as exc_info:
        await trial_service.extend_trial(test_user.user_id)

    assert "converted to paid account" in str(exc_info.value)


# Test: get_trial_status()


@pytest.mark.asyncio
async def test_get_trial_status_returns_correct_structure(
    trial_service, test_user, test_trial
):
    """Test that get_trial_status returns correctly structured data."""
    status = await trial_service.get_trial_status(test_user.user_id)

    # Verify structure
    assert "trial_id" in status
    assert "status" in status
    assert "is_active" in status
    assert "started_at" in status
    assert "expires_at" in status
    assert "days_remaining" in status
    assert "extended" in status
    assert "can_extend" in status
    assert "converted" in status
    assert "usage" in status

    # Verify types
    assert isinstance(status["trial_id"], str)
    assert isinstance(status["status"], str)
    assert isinstance(status["is_active"], bool)
    assert isinstance(status["days_remaining"], int)
    assert isinstance(status["extended"], bool)
    assert isinstance(status["can_extend"], bool)
    assert isinstance(status["converted"], bool)
    assert isinstance(status["usage"], dict)


@pytest.mark.asyncio
async def test_get_trial_status_with_usage(
    trial_service, test_user, test_trial, db_session
):
    """Test that get_trial_status correctly includes usage information."""
    # Create usage records
    usage_scans = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="scans",
        count=10,
    )
    usage_questions = TrialUsage(
        trial_id=test_trial.trial_id,
        dimension="questions",
        count=50,
    )
    db_session.add_all([usage_scans, usage_questions])
    await db_session.commit()

    # Get status
    status = await trial_service.get_trial_status(test_user.user_id)

    # Verify usage information
    assert status["usage"]["scans"]["current"] == 10
    assert status["usage"]["scans"]["limit"] == TRIAL_LIMITS["scans"]
    assert status["usage"]["scans"]["remaining"] == TRIAL_LIMITS["scans"] - 10

    assert status["usage"]["questions"]["current"] == 50
    assert status["usage"]["questions"]["limit"] == TRIAL_LIMITS["questions"]
    assert status["usage"]["questions"]["remaining"] == TRIAL_LIMITS["questions"] - 50


@pytest.mark.asyncio
async def test_get_trial_status_active_trial(trial_service, test_user, test_trial):
    """Test that get_trial_status correctly identifies active trial."""
    status = await trial_service.get_trial_status(test_user.user_id)

    assert status["is_active"] is True
    assert status["status"] == "active"
    assert status["days_remaining"] > 0


@pytest.mark.asyncio
async def test_get_trial_status_expired_trial(trial_service, test_user, expired_trial):
    """Test that get_trial_status correctly identifies expired trial."""
    status = await trial_service.get_trial_status(test_user.user_id)

    assert status["is_active"] is False
    assert status["days_remaining"] == 0


@pytest.mark.asyncio
async def test_get_trial_status_extension_flags(
    trial_service, test_user, test_trial, db_session
):
    """Test that get_trial_status correctly sets extension flags."""
    # Before extension
    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["extended"] is False
    assert status["can_extend"] is True

    # After extension
    await trial_service.extend_trial(test_user.user_id)
    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["extended"] is True
    assert status["can_extend"] is False


@pytest.mark.asyncio
async def test_get_trial_status_conversion_flag(
    trial_service, test_user, test_trial, db_session
):
    """Test that get_trial_status correctly sets conversion flag."""
    # Before conversion
    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["converted"] is False
    assert status["can_extend"] is True

    # After conversion
    test_trial.converted_at = datetime.now(timezone.utc)
    test_trial.status = "converted"
    await db_session.commit()

    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["converted"] is True
    assert status["can_extend"] is False


# Test: convert_trial()


@pytest.mark.asyncio
async def test_convert_trial_success(trial_service, test_user, test_trial, db_session):
    """Test that convert_trial successfully converts a trial."""
    # Convert trial
    converted_trial = await trial_service.convert_trial(test_user.user_id)

    # Verify conversion
    assert converted_trial.converted_at is not None
    assert converted_trial.status == "converted"

    # Verify in database
    result = await db_session.execute(
        select(Trial).where(Trial.trial_id == test_trial.trial_id)
    )
    db_trial = result.scalar_one()
    assert db_trial.converted_at is not None
    assert db_trial.status == "converted"


@pytest.mark.asyncio
async def test_convert_trial_idempotent(
    trial_service, test_user, test_trial, db_session
):
    """Test that convert_trial is idempotent (can be called multiple times)."""
    # First conversion
    first_conversion = await trial_service.convert_trial(test_user.user_id)
    first_converted_at = first_conversion.converted_at

    # Second conversion should not change timestamp
    second_conversion = await trial_service.convert_trial(test_user.user_id)

    # Timestamps should be the same
    assert second_conversion.converted_at == first_converted_at


# Integration Tests


@pytest.mark.asyncio
async def test_trial_lifecycle(trial_service, test_user, db_session):
    """
    Integration test: Complete trial lifecycle.

    Tests the full flow:
    1. Trial creation
    2. Usage recording
    3. Limit checking
    4. Extension
    5. Conversion
    6. Converted users bypass all limits
    """
    # 1. Create trial
    trial = await trial_service.get_or_create_trial(test_user.user_id)
    assert trial.status == "active"

    # 2. Record usage
    await trial_service.record_usage(test_user.user_id, "scans", count=5)
    await trial_service.record_usage(test_user.user_id, "questions", count=25)

    # 3. Check limits (should pass)
    assert await trial_service.check_limit(test_user.user_id, "scans") is True
    assert await trial_service.check_limit(test_user.user_id, "questions") is True

    # 4. Get status
    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["usage"]["scans"]["current"] == 5
    assert status["usage"]["questions"]["current"] == 25

    # 5. Extend trial
    extended_trial = await trial_service.extend_trial(test_user.user_id)
    assert extended_trial.extended_at is not None

    # 6. Convert trial
    converted_trial = await trial_service.convert_trial(test_user.user_id)
    assert converted_trial.status == "converted"

    # 7. Verify converted (paid) users bypass ALL limits
    # Record usage WAY over the limit
    await trial_service.record_usage(test_user.user_id, "scans", count=1000)

    # Converted users should have unlimited access regardless of trial status
    result = await trial_service.check_limit(test_user.user_id, "scans")
    assert result is True


@pytest.mark.asyncio
async def test_concurrent_usage_tracking(
    trial_service, test_user, test_trial, db_session
):
    """
    Integration test: Verify usage tracking handles concurrent updates.

    Tests that multiple usage recordings for the same dimension
    correctly accumulate the count.
    """
    # Record usage multiple times
    await trial_service.record_usage(test_user.user_id, "questions", count=10)
    await trial_service.record_usage(test_user.user_id, "questions", count=15)
    await trial_service.record_usage(test_user.user_id, "questions", count=20)

    # Verify total count
    status = await trial_service.get_trial_status(test_user.user_id)
    assert status["usage"]["questions"]["current"] == 45


@pytest.mark.asyncio
async def test_limit_enforcement_at_boundary(
    trial_service, test_user, test_trial, db_session
):
    """
    Integration test: Verify limit enforcement at the exact boundary.

    Tests that usage at limit-1 is allowed, but at limit is blocked.
    """
    limit = TRIAL_LIMITS["documents"]

    # Record usage up to limit - 1
    await trial_service.record_usage(test_user.user_id, "documents", count=limit - 1)

    # Should be allowed
    assert await trial_service.check_limit(test_user.user_id, "documents") is True

    # Record one more to reach the limit
    await trial_service.record_usage(test_user.user_id, "documents", count=1)

    # Should now be blocked
    with pytest.raises(TrialLimitExceededError):
        await trial_service.check_limit(test_user.user_id, "documents")


# Error Handling Tests


def test_trial_error_hierarchy():
    """Test that exception hierarchy is correct."""
    assert issubclass(TrialExpiredError, TrialError)
    assert issubclass(TrialLimitExceededError, TrialError)
    assert issubclass(TrialExtensionError, TrialError)


@pytest.mark.asyncio
async def test_check_limit_with_nonexistent_user(trial_service, db_session):
    """Test that check_limit handles non-existent users with foreign key constraint."""
    from sqlalchemy.exc import IntegrityError

    fake_user_id = uuid4()

    # Since Trial has a foreign key to User, trying to create a trial for
    # a non-existent user should raise IntegrityError when flushed to DB
    with pytest.raises(IntegrityError):
        await trial_service.check_limit(fake_user_id, "scans")


@pytest.mark.asyncio
async def test_service_initialization(db_session):
    """Test that TrialService can be initialized with a real session."""
    service = TrialService(db_session)

    assert service.db is db_session


# TRL-006: Analytics Tests


@pytest.mark.asyncio
async def test_get_trial_analytics_empty(trial_service, db_session):
    """Test analytics with no trials."""
    analytics = await trial_service.get_trial_analytics()

    assert analytics["total_trials"] == 0
    assert analytics["active_trials"] == 0
    assert analytics["expired_trials"] == 0
    assert analytics["converted_trials"] == 0
    assert analytics["conversion_rate"] == 0.0
    assert analytics["average_days_to_conversion"] is None
    assert analytics["extension_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_trial_analytics_with_trials(
    trial_service, test_user, test_trial, db_session
):
    """Test analytics with existing trials."""
    analytics = await trial_service.get_trial_analytics()

    assert analytics["total_trials"] == 1
    assert analytics["active_trials"] == 1
    assert analytics["expired_trials"] == 0
    assert analytics["converted_trials"] == 0
    assert analytics["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_trial_analytics_with_converted_trial(
    trial_service, test_user, test_trial, db_session
):
    """Test analytics correctly counts converted trials."""
    # Convert the trial
    test_trial.converted_at = datetime.now(timezone.utc)
    test_trial.status = "converted"
    await db_session.commit()

    analytics = await trial_service.get_trial_analytics()

    assert analytics["total_trials"] == 1
    assert analytics["converted_trials"] == 1
    assert analytics["conversion_rate"] == 100.0


@pytest.mark.asyncio
async def test_get_trial_analytics_with_extended_trial(
    trial_service, test_user, test_trial, db_session
):
    """Test analytics correctly counts extended trials."""
    # Extend the trial
    await trial_service.extend_trial(test_user.user_id)

    analytics = await trial_service.get_trial_analytics()

    assert analytics["extension_rate"] == 100.0


@pytest.mark.asyncio
async def test_get_usage_analytics_empty(trial_service, db_session):
    """Test usage analytics with no usage data."""
    analytics = await trial_service.get_usage_analytics()

    assert analytics["dimensions"] == []
    assert analytics["most_used_dimension"] is None
    assert analytics["least_used_dimension"] is None


@pytest.mark.asyncio
async def test_get_usage_analytics_with_usage(
    trial_service, test_user, test_trial, db_session
):
    """Test usage analytics with usage data."""
    # Record some usage
    await trial_service.record_usage(test_user.user_id, "scans", count=10)
    await trial_service.record_usage(test_user.user_id, "questions", count=50)
    await trial_service.record_usage(test_user.user_id, "documents", count=5)

    analytics = await trial_service.get_usage_analytics()

    assert len(analytics["dimensions"]) == 3

    # Questions should be most used, documents least
    assert analytics["most_used_dimension"] == "questions"
    assert analytics["least_used_dimension"] == "documents"

    # Verify dimension data
    scans_data = next(d for d in analytics["dimensions"] if d["dimension"] == "scans")
    assert scans_data["total_usage"] == 10
    assert scans_data["average_usage"] == 10.0


@pytest.mark.asyncio
async def test_get_usage_analytics_limit_reached(
    trial_service, test_user, test_trial, db_session
):
    """Test usage analytics tracks limit reached count."""
    # Record usage at the limit
    await trial_service.record_usage(
        test_user.user_id, "scans", count=TRIAL_LIMITS["scans"]
    )

    analytics = await trial_service.get_usage_analytics()

    scans_data = next(d for d in analytics["dimensions"] if d["dimension"] == "scans")
    assert scans_data["limit_reached_count"] == 1
