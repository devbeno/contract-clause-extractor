"""Tests for authentication service."""
import pytest
import uuid
from datetime import timedelta
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException
from app.services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_active_user,
)
from app.database import AsyncSessionLocal
from app.models.user import User


class TestAuthService:
    """Test authentication service functions."""

    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "securepassword123"
        hashed = get_password_hash(password)

        # Hash should be different from password
        assert hashed != password
        # Should verify correctly
        assert verify_password(password, hashed) is True
        # Wrong password should not verify
        assert verify_password("wrongpassword", hashed) is False

    def test_password_hashing_long_password(self):
        """Test hashing works with long passwords (bcrypt 72-byte limit)."""
        # Create a password longer than 72 bytes
        password = "a" * 100
        hashed = get_password_hash(password)

        # Should still hash and verify
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        # Token should have 3 parts (header.payload.signature)
        assert token.count(".") == 2

    def test_create_access_token_with_expiry(self):
        """Test JWT token creation with custom expiration."""
        data = {"sub": "test@example.com"}
        token = create_access_token(data, expires_delta=timedelta(minutes=15))

        assert isinstance(token, str)
        assert len(token) > 0


async def _create_test_user(session, *, is_active: bool = True) -> User:
    """Helper to insert a test user."""
    user = User(
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        username=f"user_{uuid.uuid4().hex[:8]}",
        hashed_password="hashed",
        is_active=is_active,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_current_user_success():
    async with AsyncSessionLocal() as session:
        user = await _create_test_user(session)
        token = create_access_token({"sub": user.id, "username": user.username})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        result = await get_current_user(credentials=credentials, db=session)

        assert result.id == user.id
        assert result.username == user.username


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    async with AsyncSessionLocal() as session:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=session)

        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_user_record():
    async with AsyncSessionLocal() as session:
        token = create_access_token({"sub": str(uuid.uuid4()), "username": "ghost"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=session)

        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_claim():
    async with AsyncSessionLocal() as session:
        token = create_access_token({})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=session)

        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_inactive_user():
    async with AsyncSessionLocal() as session:
        user = await _create_test_user(session, is_active=False)
        token = create_access_token({"sub": user.id, "username": user.username})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc:
            await get_current_user(credentials=credentials, db=session)

        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_active_user_checks_status():
    inactive_user = User(
        email="inactive@example.com",
        username="inactive_user",
        hashed_password="hashed",
        is_active=False,
        is_superuser=False,
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_active_user(current_user=inactive_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_active_user_returns_active_user():
    active_user = User(
        email="active@example.com",
        username="active_user",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
    )

    result = await get_current_active_user(current_user=active_user)

    assert result is active_user
