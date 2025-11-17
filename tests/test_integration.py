"""Integration tests for full API workflows."""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from io import BytesIO


@pytest.fixture
def mock_llm_extract():
    """Mock LLM service to avoid OpenAI API calls."""
    with patch('app.services.llm_service.LLMService.extract_clauses') as mock:
        mock.return_value = [
            {
                "clause_type": "payment_terms",
                "title": "Payment Terms",
                "content": "Payment shall be made within 30 days.",
                "summary": "Net 30 payment terms"
            },
            {
                "clause_type": "termination",
                "title": "Termination Clause",
                "content": "Either party may terminate with 30 days notice.",
                "summary": "30 days termination notice required"
            }
        ]
        yield mock


@pytest.mark.asyncio
async def test_full_extraction_workflow_txt(mock_llm_extract):
    """Test complete workflow: register, login, upload TXT, extract clauses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]

        # 1. Register
        response = await client.post(
            "/api/auth/register",
            json={
                "email": f"integration_{unique_id}@test.com",
                "username": f"integration_{unique_id}",
                "password": "testpass123"
            }
        )
        assert response.status_code == 201

        # 2. Login
        response = await client.post(
            "/api/auth/login",
            json={
                "username": f"integration_{unique_id}",
                "password": "testpass123"
            }
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. Upload TXT file
        txt_content = b"This is a test contract with payment terms and termination clause."
        files = {"file": ("test_contract.txt", BytesIO(txt_content), "text/plain")}
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/extract",
            files=files,
            headers=headers
        )
        assert response.status_code == 201
        data = response.json()

        # Verify extraction
        assert data["status"] == "completed"
        assert data["filename"] == "test_contract.txt"
        assert data["file_type"] == "txt"
        assert len(data["clauses"]) == 2
        assert data["clauses"][0]["clause_type"] == "payment_terms"
        assert data["clauses"][1]["clause_type"] == "termination"

        extraction_id = data["id"]

        # 4. Get specific extraction
        response = await client.get(
            f"/api/extractions/{extraction_id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == extraction_id
        assert len(data["clauses"]) == 2

        # 5. List all extractions
        response = await client.get(
            "/api/extractions?skip=0&limit=10",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["extractions"]) >= 1


@pytest.mark.asyncio
async def test_extraction_with_invalid_file_type():
    """Test upload with unsupported file type."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]

        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "email": f"test_{unique_id}@test.com",
                "username": f"test_{unique_id}",
                "password": "testpass123"
            }
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": f"test_{unique_id}", "password": "testpass123"}
        )
        token = response.json()["access_token"]

        # Try to upload unsupported file type
        files = {"file": ("test.xlsx", BytesIO(b"fake excel content"), "application/xlsx")}
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/extract",
            files=files,
            headers=headers
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_extraction_with_no_filename():
    """Test upload with no filename."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]

        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "email": f"test_{unique_id}@test.com",
                "username": f"test_{unique_id}",
                "password": "testpass123"
            }
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": f"test_{unique_id}", "password": "testpass123"}
        )
        token = response.json()["access_token"]

        # Upload with no filename
        files = {"file": ("", BytesIO(b"content"), "text/plain")}
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/extract",
            files=files,
            headers=headers
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_nonexistent_extraction():
    """Test retrieving non-existent extraction."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())[:8]

        # Register and login
        await client.post(
            "/api/auth/register",
            json={
                "email": f"test_{unique_id}@test.com",
                "username": f"test_{unique_id}",
                "password": "testpass123"
            }
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": f"test_{unique_id}", "password": "testpass123"}
        )
        token = response.json()["access_token"]

        # Try to get non-existent extraction
        fake_id = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(
            f"/api/extractions/{fake_id}",
            headers=headers
        )
        assert response.status_code == 404
