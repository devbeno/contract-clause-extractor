"""Tests for API endpoints."""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_user():
    """Test user registration endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Generate unique email and username for each test run
        unique_id = str(uuid.uuid4())[:8]

        # Register new user
        response = await client.post(
            "/api/auth/register",
            json={
                "email": f"test_{unique_id}@example.com",
                "username": f"testuser_{unique_id}",
                "password": "testpass123"
            }
        )

        # Should return 201 Created
        assert response.status_code == 201
        data = response.json()

        # Should return user data (not token - must login separately)
        assert "id" in data
        assert "email" in data
        assert data["email"] == f"test_{unique_id}@example.com"
        assert data["username"] == f"testuser_{unique_id}"
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_extract_requires_auth():
    """Test that extraction endpoint requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to access without token
        response = await client.post("/api/extract")

        # FastAPI HTTPBearer returns 403 Forbidden when no credentials provided
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_extractions_requires_auth():
    """Test that list extractions endpoint requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Try to access without token
        response = await client.get("/api/extractions")

        # FastAPI HTTPBearer returns 403 Forbidden when no credentials provided
        assert response.status_code == 403
