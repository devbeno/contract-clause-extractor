"""Direct tests for API-layer validation branches."""
import uuid
from io import BytesIO

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.api.auth import register, login
from app.api.extraction import extract_clauses, get_extraction, list_extractions
from app.database import AsyncSessionLocal
from app.models import Extraction
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin
from app.services.auth_service import get_password_hash


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_http_exception():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:8]
        email = f"user_{unique}@example.com"

        await register(
            UserCreate(email=email, username=f"user_{unique}", password="secret123"),
            db=session,
        )

        with pytest.raises(HTTPException) as exc:
            await register(
                UserCreate(email=email, username=f"other_{unique}", password="secret123"),
                db=session,
            )

        assert exc.value.status_code == 400
        assert "Email already registered" in exc.value.detail


@pytest.mark.asyncio
async def test_register_duplicate_username_raises_http_exception():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:8]
        username = f"user_{unique}"

        await register(
            UserCreate(email=f"{username}@example.com", username=username, password="secret123"),
            db=session,
        )

        with pytest.raises(HTTPException) as exc:
            await register(
                UserCreate(
                    email=f"other_{username}@example.com",
                    username=username,
                    password="secret123",
                ),
                db=session,
            )

        assert exc.value.status_code == 400
        assert "Username already taken" in exc.value.detail


@pytest.mark.asyncio
async def test_login_inactive_user_forbidden():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:8]
        user = User(
            email=f"inactive_{unique}@example.com",
            username=f"inactive_{unique}",
            hashed_password=get_password_hash("secret123"),
            is_active=False,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(HTTPException) as exc:
            await login(
                UserLogin(username=user.username, password="secret123"),
                db=session,
            )

        assert exc.value.status_code == 403
        assert "inactive" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_extract_clauses_requires_filename():
    async with AsyncSessionLocal() as session:
        dummy_user = User(
            email="dummy@example.com",
            username="dummy-user",
            hashed_password="hashed",
        )
        upload = UploadFile(filename="", file=BytesIO(b"content"))

        with pytest.raises(HTTPException) as exc:
            await extract_clauses(
                file=upload,
                current_user=dummy_user,
                db=session,
            )

        assert exc.value.status_code == 400
        assert "No filename" in exc.value.detail


@pytest.mark.asyncio
async def test_extract_clauses_rejects_unsupported_types():
    async with AsyncSessionLocal() as session:
        dummy_user = User(
            email="dummy2@example.com",
            username="dummy-user-2",
            hashed_password="hashed",
        )
        upload = UploadFile(filename="contract.xlsx", file=BytesIO(b"fake"))

        with pytest.raises(HTTPException) as exc:
            await extract_clauses(
                file=upload,
                current_user=dummy_user,
                db=session,
            )

        assert exc.value.status_code == 400
        assert "Unsupported file type" in exc.value.detail


@pytest.mark.asyncio
@patch("app.api.extraction.DocumentProcessor.extract_text", new_callable=AsyncMock)
async def test_extract_clauses_success_flow(mock_extract_text):
    mock_extract_text.return_value = "Important contract text."

    async with AsyncSessionLocal() as session:
        user = User(
            email="flow@example.com",
            username="flow-user",
            hashed_password="hashed",
            is_active=True,
        )
        upload = UploadFile(filename="contract.txt", file=BytesIO(b"dummy"))

        with patch("app.api.extraction.LLMService") as mock_llm_cls:
            llm_instance = AsyncMock()
            llm_instance.extract_clauses.return_value = [
                {
                    "clause_type": "payment_terms",
                    "title": "Payment Terms",
                    "content": "Payment within 30 days",
                    "summary": "Net 30 terms",
                },
                {
                    "clause_type": "termination",
                    "title": "Termination",
                    "content": "30 days notice",
                    "summary": "Termination clause",
                },
            ]
            mock_llm_cls.return_value = llm_instance

            extraction = await extract_clauses(
                file=upload,
                current_user=user,
                db=session,
            )

        assert extraction.status == "completed"
        assert extraction.filename == "contract.txt"
        assert extraction.extra_data["total_clauses"] == 2
        assert len(extraction.clauses) == 2
        assert extraction.clauses[0].clause_type == "payment_terms"


@pytest.mark.asyncio
@patch("app.api.extraction.DocumentProcessor.extract_text", new_callable=AsyncMock)
async def test_extract_clauses_records_failure_on_empty_text(mock_extract_text):
    mock_extract_text.return_value = "   "

    async with AsyncSessionLocal() as session:
        user = User(
            email="fail@example.com",
            username="fail-user",
            hashed_password="hashed",
            is_active=True,
        )
        upload = UploadFile(filename="empty.txt", file=BytesIO(b"content"))

        with pytest.raises(HTTPException) as exc:
            await extract_clauses(
                file=upload,
                current_user=user,
                db=session,
            )

        assert exc.value.status_code == 500
    async with AsyncSessionLocal() as verify_session:
        latest = await verify_session.execute(
            select(Extraction).order_by(Extraction.created_at.desc())
        )
        extraction = latest.scalars().first()
        assert extraction.status == "failed"
        assert "No text could be extracted" in extraction.error_message


@pytest.mark.asyncio
async def test_get_extraction_not_found_raises():
    async with AsyncSessionLocal() as session:
        user = User(
            email="get@example.com",
            username="get-user",
            hashed_password="hashed",
            is_active=True,
        )
        with pytest.raises(HTTPException) as exc:
            await get_extraction(
                document_id="missing-id",
                current_user=user,
                db=session,
            )

        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_extractions_returns_pagination():
    async with AsyncSessionLocal() as session:
        extraction_one = Extraction(
            filename="doc1.txt",
            file_type="txt",
            file_size=10,
            status="completed",
        )
        extraction_two = Extraction(
            filename="doc2.txt",
            file_type="txt",
            file_size=20,
            status="completed",
        )
        session.add_all([extraction_one, extraction_two])
        await session.commit()

        user = User(
            email="list@example.com",
            username="list-user",
            hashed_password="hashed",
            is_active=True,
        )

        result = await list_extractions(
            skip=0,
            limit=5,
            current_user=user,
            db=session,
        )

        assert result.total >= 2
        assert len(result.extractions) >= 2


@pytest.mark.asyncio
async def test_register_unexpected_error_returns_500():
    async with AsyncSessionLocal() as session:
        failing_execute = AsyncMock(side_effect=RuntimeError("boom"))
        session.execute = failing_execute

        with pytest.raises(HTTPException) as exc:
            await register(
                UserCreate(
                    email="err@example.com",
                    username="erruser",
                    password="secret123",
                ),
                db=session,
            )

        assert exc.value.status_code == 500
        assert "Registration failed" in exc.value.detail


@pytest.mark.asyncio
async def test_login_success_returns_token():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        user = User(
            email=f"login_success_{unique}@example.com",
            username=f"login-success-{unique}",
            hashed_password=get_password_hash("secret123"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

        token = await login(
            UserLogin(username=f"login-success-{unique}", password="secret123"),
            db=session,
        )

        assert token.token_type == "bearer"
        assert isinstance(token.access_token, str)
        assert len(token.access_token) > 10


@pytest.mark.asyncio
async def test_login_unexpected_error_returns_500():
    async with AsyncSessionLocal() as session:
        session.execute = AsyncMock(side_effect=RuntimeError("explode"))

        with pytest.raises(HTTPException) as exc:
            await login(
                UserLogin(username="whoever", password="password"),
                db=session,
            )

        assert exc.value.status_code == 500
        assert "Login failed" in exc.value.detail


@pytest.mark.asyncio
async def test_login_invalid_credentials_branch():
    async with AsyncSessionLocal() as session:
        unique = uuid.uuid4().hex[:6]
        user = User(
            email=f"invalid_{unique}@example.com",
            username=f"invalid-{unique}",
            hashed_password=get_password_hash("correctpass"),
            is_active=True,
        )
        session.add(user)
        await session.commit()

        with pytest.raises(HTTPException) as exc:
            await login(
                UserLogin(username=f"invalid-{unique}", password="wrongpass"),
                db=session,
            )

        assert exc.value.status_code == 401
        assert "Incorrect username or password" in exc.value.detail


@pytest.mark.asyncio
@patch("app.api.extraction.DocumentProcessor.extract_text", new_callable=AsyncMock)
async def test_extract_clauses_unexpected_error_handles_outer(mock_extract_text):
    mock_extract_text.return_value = "Some text here."

    async with AsyncSessionLocal() as session:
        user = User(
            email="outer@example.com",
            username="outer-user",
            hashed_password="hashed",
            is_active=True,
        )
        upload = UploadFile(filename="contract.txt", file=BytesIO(b"abc"))

        with patch("app.api.extraction.LLMService") as mock_llm_cls:
            llm_instance = AsyncMock()
            llm_instance.extract_clauses.return_value = []
            mock_llm_cls.return_value = llm_instance

            session.execute = AsyncMock(side_effect=RuntimeError("fetch failed"))

            with pytest.raises(HTTPException) as exc:
                await extract_clauses(
                    file=upload,
                    current_user=user,
                    db=session,
                )

        assert exc.value.status_code == 500
        assert "Internal server error" in exc.value.detail

    async with AsyncSessionLocal() as verify_session:
        latest = await verify_session.execute(
            select(Extraction).order_by(Extraction.created_at.desc())
        )
        extraction = latest.scalars().first()
        assert extraction is not None


@pytest.mark.asyncio
async def test_get_extraction_handles_db_error():
    async with AsyncSessionLocal() as session:
        session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        user = User(
            email="err2@example.com",
            username="err2",
            hashed_password="hashed",
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc:
            await get_extraction(
                document_id="whatever",
                current_user=user,
                db=session,
            )

        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_extraction_success_returns_record():
    async with AsyncSessionLocal() as session:
        extraction = Extraction(
            filename="success.txt",
            file_type="txt",
            file_size=42,
            status="completed",
        )
        session.add(extraction)
        await session.commit()
        await session.refresh(extraction)

        user = User(
            email="getsuccess@example.com",
            username="getsuccess",
            hashed_password="hashed",
            is_active=True,
        )

        result = await get_extraction(
            document_id=extraction.id,
            current_user=user,
            db=session,
        )

        assert result.id == extraction.id
        assert result.filename == "success.txt"


@pytest.mark.asyncio
async def test_list_extractions_handles_db_error():
    async with AsyncSessionLocal() as session:
        session.execute = AsyncMock(side_effect=RuntimeError("count failed"))
        user = User(
            email="err3@example.com",
            username="err3",
            hashed_password="hashed",
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc:
            await list_extractions(
                skip=0,
                limit=10,
                current_user=user,
                db=session,
            )

        assert exc.value.status_code == 500

