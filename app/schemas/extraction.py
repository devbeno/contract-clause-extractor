"""Pydantic schemas for extraction API."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class ClauseCreate(BaseModel):
    """Schema for creating a clause."""

    clause_type: str = Field(..., description="Type of clause (e.g., payment_terms, termination)")
    title: Optional[str] = Field(None, description="Title of the clause")
    content: str = Field(..., description="Full text content of the clause")
    order: int = Field(..., description="Order/position of clause in document")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ClauseSchema(ClauseCreate):
    """Schema for clause response."""

    id: str = Field(..., description="Unique identifier for the clause")
    extraction_id: str = Field(..., description="ID of the parent extraction")
    created_at: datetime = Field(..., description="Timestamp when clause was created")

    model_config = ConfigDict(from_attributes=True)


class ExtractionCreate(BaseModel):
    """Schema for creating an extraction."""

    filename: str = Field(..., description="Name of the uploaded file")
    file_type: str = Field(..., description="Type of file (pdf, docx, etc.)")
    file_size: int = Field(..., description="Size of file in bytes")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ExtractionSchema(ExtractionCreate):
    """Schema for extraction response."""

    id: str = Field(..., description="Unique identifier for the extraction")
    status: str = Field(..., description="Status of extraction (completed, failed, processing)")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")
    created_at: datetime = Field(..., description="Timestamp when extraction was created")
    updated_at: datetime = Field(..., description="Timestamp when extraction was last updated")

    model_config = ConfigDict(from_attributes=True)


class ExtractionResponse(ExtractionSchema):
    """Schema for detailed extraction response with clauses."""

    clauses: List[ClauseSchema] = Field(default_factory=list, description="List of extracted clauses")

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of records to return")


class ExtractionListResponse(BaseModel):
    """Schema for paginated list of extractions."""

    total: int = Field(..., description="Total number of extractions")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Maximum number of records returned")
    extractions: List[ExtractionResponse] = Field(..., description="List of extractions")
