# 6.4 Basic Authentication

## Parent Epic
Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Implement simplified authentication for MVP single-tenant deployment. This provides email/password login with JWT tokens for a single admin user per container deployment.

## Background

MVP uses **Basic Auth** (email/password) because:
- Trial customers don't need complex multi-user management
- Reduces onboarding friction (no SSO setup required)
- Single admin user simplifies container deployment
- Full multi-user support deferred to Phase 4

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| USR-001 | User registration | Email/password registration, email validation format |
| USR-004 | Profile management | View/update name, email; change password |
| USR-007 | Password policies | Min 8 chars, 1 uppercase, 1 number; bcrypt hashing |

## Technical Specification

### Database Schema

```sql
-- Single user table (simplified for MVP)
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    is_admin BOOLEAN NOT NULL DEFAULT true,  -- MVP: all users are admin
    email_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Sessions table
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,  -- Hashed refresh token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token_hash);
```

### Password Policy

```python
# src/cloud_optimizer/auth/password.py
from passlib.context import CryptContext
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordPolicy:
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_NUMBER = True
    REQUIRE_SPECIAL = False  # MVP: simplified

    @classmethod
    def validate(cls, password: str) -> List[str]:
        """Validate password against policy. Returns list of errors."""
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")

        if cls.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if cls.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if cls.REQUIRE_NUMBER and not re.search(r"\d", password):
            errors.append("Password must contain at least one number")

        return errors

    @classmethod
    def hash(cls, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    @classmethod
    def verify(cls, password: str, hash: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, hash)
```

### JWT Token Service

```python
# src/cloud_optimizer/auth/jwt.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic import BaseModel

class TokenService:
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def create_access_token(self, user_id: str, email: str) -> str:
        """Create short-lived access token."""
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)

    def create_refresh_token(self, user_id: str) -> str:
        """Create long-lived refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.ALGORITHM)

    def decode_token(self, token: str) -> dict:
        """Decode and validate token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.ALGORITHM])
            return payload
        except JWTError as e:
            raise InvalidTokenException(str(e))
```

### Auth Service

```python
# src/cloud_optimizer/services/auth.py
class AuthService:
    def __init__(self, db: AsyncSession, token_service: TokenService):
        self.db = db
        self.token_service = token_service

    async def register(self, email: str, password: str, name: str = None) -> User:
        """Register new user."""
        # Check if user exists
        existing = await self.db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise UserAlreadyExistsException()

        # Validate password
        errors = PasswordPolicy.validate(password)
        if errors:
            raise PasswordValidationException(errors)

        # Create user
        user = User(
            email=email,
            password_hash=PasswordPolicy.hash(password),
            name=name,
            is_admin=True,  # MVP: all users are admin
        )
        self.db.add(user)
        await self.db.commit()

        return user

    async def login(self, email: str, password: str) -> TokenPair:
        """Authenticate user and return tokens."""
        user = await self._get_user_by_email(email)
        if not user:
            raise InvalidCredentialsException()

        if not PasswordPolicy.verify(password, user.password_hash):
            raise InvalidCredentialsException()

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.commit()

        # Generate tokens
        access_token = self.token_service.create_access_token(
            str(user.user_id), user.email
        )
        refresh_token = self.token_service.create_refresh_token(str(user.user_id))

        # Store refresh token hash
        session = Session(
            user_id=user.user_id,
            token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        self.db.add(session)
        await self.db.commit()

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.token_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Refresh access token using refresh token."""
        payload = self.token_service.decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise InvalidTokenException("Not a refresh token")

        # Verify session exists and not revoked
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = await self._get_session(token_hash)

        if not session or session.revoked_at:
            raise InvalidTokenException("Session revoked or expired")

        user = await self._get_user_by_id(session.user_id)

        # Generate new access token
        access_token = self.token_service.create_access_token(
            str(user.user_id), user.email
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,  # Reuse refresh token
            token_type="bearer",
            expires_in=self.token_service.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str):
        """Revoke refresh token."""
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        await self.db.execute(
            update(Session)
            .where(Session.token_hash == token_hash)
            .values(revoked_at=datetime.utcnow())
        )
        await self.db.commit()
```

### Auth Middleware

```python
# src/cloud_optimizer/middleware/auth.py
class AuthMiddleware:
    """Validate JWT tokens on protected routes."""

    PUBLIC_PATHS = [
        "/health",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]

        # Skip auth for public paths
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            await self.app(scope, receive, send)
            return

        # Extract token from header
        headers = dict(scope["headers"])
        auth_header = headers.get(b"authorization", b"").decode()

        if not auth_header.startswith("Bearer "):
            return await self._unauthorized(scope, receive, send)

        token = auth_header[7:]

        try:
            payload = self.token_service.decode_token(token)
            scope["state"]["user_id"] = payload["sub"]
            scope["state"]["email"] = payload["email"]
        except InvalidTokenException:
            return await self._unauthorized(scope, receive, send)

        await self.app(scope, receive, send)
```

## API Endpoints

```
POST /api/v1/auth/register     # Register new user
POST /api/v1/auth/login        # Login, returns tokens
POST /api/v1/auth/refresh      # Refresh access token
POST /api/v1/auth/logout       # Revoke refresh token
GET  /api/v1/auth/me           # Get current user profile
PUT  /api/v1/auth/me           # Update profile
PUT  /api/v1/auth/password     # Change password
```

## Files to Create

```
src/cloud_optimizer/auth/
├── __init__.py
├── password.py              # Password policy and hashing
├── jwt.py                   # JWT token service
└── exceptions.py            # Auth exceptions

src/cloud_optimizer/services/
└── auth.py                  # Auth service

src/cloud_optimizer/models/
├── user.py                  # User model
└── session.py               # Session model

src/cloud_optimizer/middleware/
└── auth.py                  # Auth middleware

src/cloud_optimizer/api/routers/
└── auth.py                  # Auth API endpoints

alembic/versions/
└── xxx_create_user_tables.py

tests/auth/
├── test_password.py
├── test_jwt.py
├── test_auth_service.py
└── test_auth_api.py
```

## Testing Requirements

### Unit Tests
- [ ] `test_password_policy.py` - Password validation rules
- [ ] `test_password_hashing.py` - Bcrypt hash/verify
- [ ] `test_jwt_tokens.py` - Token creation/validation
- [ ] `test_auth_service.py` - Register/login/refresh/logout

### Integration Tests
- [ ] `test_auth_api.py` - Full API flow

## Acceptance Criteria Checklist

- [ ] User can register with email/password
- [ ] Password policy enforced (8+ chars, uppercase, number)
- [ ] Passwords stored with bcrypt
- [ ] Login returns access + refresh tokens
- [ ] Access token expires in 15 minutes
- [ ] Refresh token expires in 7 days
- [ ] Token refresh works correctly
- [ ] Logout revokes refresh token
- [ ] Protected endpoints return 401 without valid token
- [ ] User can view/update profile
- [ ] User can change password
- [ ] 80%+ test coverage

## Dependencies

- 6.1 Container Packaging (database schema)

## Blocked By

- 6.1 Container Packaging

## Blocks

- 6.5 Chat Interface UI (needs auth endpoints)

## Estimated Effort

0.5 weeks

## Labels

`auth`, `security`, `mvp`, `phase-1`, `P0`
