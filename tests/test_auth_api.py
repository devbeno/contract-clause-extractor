"""Comprehensive tests for authentication API."""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """Test registration with duplicate email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]
        email = f"duplicate_{unique_id}@test.com"

        # First registration
        response = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": f"user1_{unique_id}",
                "password": "testpass123"
            }
        )
        assert response.status_code == 201

        # Try to register with same email
        response = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": f"user2_{unique_id}",
                "password": "testpass123"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username():
    """Test registration with duplicate username."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]
        username = f"duplicateuser_{unique_id}"

        # First registration
        response = await client.post(
            "/api/auth/register",
            json={
                "email": f"email1_{unique_id}@test.com",
                "username": username,
                "password": "testpass123"
            }
        )
        assert response.status_code == 201

        # Try to register with same username
        response = await client.post(
            "/api/auth/register",
            json={
                "email": f"email2_{unique_id}@test.com",
                "username": username,
                "password": "testpass123"
            }
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]

        # Register user
        await client.post(
            "/api/auth/register",
            json={
                "email": f"test_{unique_id}@test.com",
                "username": f"test_{unique_id}",
                "password": "correctpass"
            }
        )

        # Try to login with wrong password
        response = await client.post(
            "/api/auth/login",
            json={
                "username": f"test_{unique_id}",
                "password": "wrongpass"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    """Test login with non-existent user."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent_user_12345",
                "password": "somepass"
            }
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_email():
    """Test login using email instead of username."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]
        email = f"test_{unique_id}@test.com"

        # Register user
        await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": f"test_{unique_id}",
                "password": "testpass123"
            }
        )

        # Login with email
        response = await client.post(
            "/api/auth/login",
            json={
                "username": email,  # Using email as username
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user info."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]
        email = f"test_{unique_id}@test.com"
        username = f"test_{unique_id}"

        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": username,
                "password": "testpass123"
            }
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": username, "password": "testpass123"}
        )
        token = response.json()["access_token"]

        # Get current user info
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["username"] == username
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test getting user info with invalid token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = await client.get("/api/auth/me", headers=headers)

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_no_token():
    """Test getting user info without token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/auth/me")

        assert response.status_code == 403
