"""Additional tests for application setup and models."""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app, lifespan
from app.database import init_db
from app.models.extraction import Extraction, Clause
from app.models.user import User


@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_lifespan_initializes_database():
    with patch("app.main.init_db", new_callable=AsyncMock) as mock_init:
        async with lifespan(app):
            mock_init.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_handles_init_failure():
    with patch(
        "app.main.init_db",
        new=AsyncMock(side_effect=RuntimeError("startup fail")),
    ):
        with pytest.raises(RuntimeError):
            async with lifespan(app):
                pass  # pragma: no cover


@pytest.mark.asyncio
async def test_init_db_executes_without_error():
    # Ensure init_db runs to completion to cover table creation branch
    await init_db()


def test_model_reprs():
    extraction = Extraction(
        id=str(uuid.uuid4()),
        filename="sample.txt",
        file_type="txt",
        file_size=123,
        status="completed",
    )
    clause = Clause(
        id=str(uuid.uuid4()),
        extraction_id=extraction.id,
        clause_type="payment_terms",
        title="Payment Terms",
        content="Payment within 30 days",
        order=1,
    )
    user = User(
        id=str(uuid.uuid4()),
        email="repr@example.com",
        username="repr-user",
        hashed_password="hashed",
    )

    assert "Extraction" in repr(extraction)
    assert "Clause" in repr(clause)
    assert "User" in repr(user)

