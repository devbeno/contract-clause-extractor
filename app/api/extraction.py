"""API routes for contract clause extraction."""
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Extraction, Clause
from app.schemas import (
    ExtractionResponse,
    ExtractionListResponse,
    ClauseCreate,
)
from app.services.document_processor import DocumentProcessor
from app.services.llm_service import LLMService
from app.services.auth_service import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["extractions"])


@router.post("/extract", response_model=ExtractionResponse, status_code=201)
async def extract_clauses(
    file: UploadFile = File(..., description="Contract document (PDF or DOCX)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Extract clauses from a contract document.

    This endpoint:
    1. Accepts a PDF or DOCX file
    2. Extracts text from the document
    3. Uses LLM to identify and structure legal clauses
    4. Stores results in database
    5. Returns structured JSON with all extracted clauses

    Args:
        file: Uploaded contract document
        db: Database session

    Returns:
        ExtractionResponse: Extraction result with all clauses

    Raises:
        HTTPException: If file processing or extraction fails
    """
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ["pdf", "docx", "doc", "txt"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Only PDF, DOCX, and TXT files are supported."
            )

        logger.info(f"Processing file: {file.filename} ({file_extension})")

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        logger.info(f"File size: {file_size} bytes")

        # Create extraction record
        extraction = Extraction(
            filename=file.filename,
            file_type=file_extension,
            file_size=file_size,
            status="processing",
        )

        db.add(extraction)
        await db.commit()
        await db.refresh(extraction)

        logger.info(f"Created extraction record: {extraction.id}")

        try:
            # Extract text from document
            document_text = await DocumentProcessor.extract_text(file_content, file_extension)

            if not document_text.strip():
                raise Exception("No text could be extracted from the document")

            logger.info(f"Extracted {len(document_text)} characters from document")

            # Use LLM to extract clauses
            llm_service = LLMService()
            extracted_clauses = await llm_service.extract_clauses(document_text)

            logger.info(f"LLM extracted {len(extracted_clauses)} clauses")

            # Save clauses to database
            for idx, clause_data in enumerate(extracted_clauses):
                clause = Clause(
                    extraction_id=extraction.id,
                    clause_type=clause_data.get("clause_type", "unknown"),
                    title=clause_data.get("title", f"Clause {idx + 1}"),
                    content=clause_data.get("content", ""),
                    order=idx,
                    extra_data={
                        "summary": clause_data.get("summary", ""),
                    }
                )
                db.add(clause)

            # Update extraction status
            extraction.status = "completed"
            extraction.extra_data = {
                "total_clauses": len(extracted_clauses),
                "text_length": len(document_text),
            }

            await db.commit()
            await db.refresh(extraction)

            logger.info(f"Successfully completed extraction {extraction.id}")

        except Exception as e:
            # Update extraction status to failed
            extraction.status = "failed"
            extraction.error_message = str(e)
            await db.commit()
            await db.refresh(extraction)

            logger.error(f"Extraction failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

        # Fetch extraction with clauses (eagerly load clauses to avoid lazy loading issues)
        result = await db.execute(
            select(Extraction)
            .options(selectinload(Extraction.clauses))
            .where(Extraction.id == extraction.id)
        )
        extraction_with_clauses = result.scalar_one()

        return extraction_with_clauses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in extract_clauses: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/extractions/{document_id}", response_model=ExtractionResponse)
async def get_extraction(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a specific extraction result by ID.

    Args:
        document_id: Unique identifier of the extraction
        db: Database session

    Returns:
        ExtractionResponse: Extraction result with all clauses

    Raises:
        HTTPException: If extraction not found
    """
    try:
        # Query extraction with clauses (eagerly load clauses)
        result = await db.execute(
            select(Extraction)
            .options(selectinload(Extraction.clauses))
            .where(Extraction.id == document_id)
        )
        extraction = result.scalar_one_or_none()

        if not extraction:
            raise HTTPException(status_code=404, detail=f"Extraction not found: {document_id}")

        return extraction

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving extraction {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/extractions", response_model=ExtractionListResponse)
async def list_extractions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all extractions with pagination.

    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        db: Database session

    Returns:
        ExtractionListResponse: Paginated list of extractions

    Raises:
        HTTPException: If database query fails
    """
    try:
        # Get total count
        count_result = await db.execute(select(func.count(Extraction.id)))
        total = count_result.scalar_one()

        # Get paginated extractions (eagerly load clauses)
        result = await db.execute(
            select(Extraction)
            .options(selectinload(Extraction.clauses))
            .order_by(Extraction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        extractions = result.scalars().all()

        return ExtractionListResponse(
            total=total,
            skip=skip,
            limit=limit,
            extractions=extractions,
        )

    except Exception as e:
        logger.error(f"Error listing extractions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
