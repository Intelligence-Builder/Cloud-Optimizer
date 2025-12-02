"""Fixtures for API tests.

Uses PostgreSQL for testing to support JSONB columns.
Requires: docker-compose -f docker/docker-compose.test.yml up -d
"""
import os
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cloud_optimizer.database import Base, get_db
from cloud_optimizer.main import app
from cloud_optimizer.models.aws_account import AWSAccount, ConnectionStatus, ConnectionType
from cloud_optimizer.models.user import User

# PostgreSQL test configuration
POSTGRES_TEST_CONFIG = {
    "host": os.getenv("TEST_POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("TEST_POSTGRES_PORT", "5434")),
    "user": os.getenv("TEST_POSTGRES_USER", "test"),
    "password": os.getenv("TEST_POSTGRES_PASSWORD", "test"),
    "database": os.getenv("TEST_POSTGRES_DB", "test_intelligence"),
}


def get_test_database_url() -> str:
    """Get the test database URL."""
    return (
        f"postgresql+asyncpg://{POSTGRES_TEST_CONFIG['user']}:"
        f"{POSTGRES_TEST_CONFIG['password']}@{POSTGRES_TEST_CONFIG['host']}:"
        f"{POSTGRES_TEST_CONFIG['port']}/{POSTGRES_TEST_CONFIG['database']}"
    )


@pytest_asyncio.fixture
async def db_engine():
    """Create PostgreSQL database engine for testing."""
    try:
        engine = create_async_engine(
            get_test_database_url(),
            echo=False,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        # Clean up tables after tests
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    except Exception as e:
        pytest.skip(f"PostgreSQL test database not available: {e}")


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create database session for testing."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_session):
    """Create async test client with database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user for tests that need user foreign key."""
    user = User(
        email="test@example.com",
        password_hash="$2b$12$test_hash_for_testing_only",
        name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_aws_account(db_session, test_user):
    """Create a test AWS account for tests that need aws_account foreign key."""
    account = AWSAccount(
        user_id=test_user.user_id,
        aws_account_id="123456789012",
        friendly_name="test-account",
        connection_type=ConnectionType.IAM_ROLE,
        role_arn="arn:aws:iam::123456789012:role/CloudOptimizerRole",
        external_id=str(uuid4()),
        status=ConnectionStatus.ACTIVE,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account
