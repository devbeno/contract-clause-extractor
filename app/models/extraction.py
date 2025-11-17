"""Database models for contract extractions."""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid


class Extraction(Base):
    """Model for storing contract extraction results."""

    __tablename__ = "extractions"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Document metadata
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # pdf, docx, etc.
    file_size = Column(Integer, nullable=False)  # in bytes

    # Extraction status
    status = Column(String, default="completed")  # completed, failed, processing
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Additional metadata (flexible JSON field)
    extra_data = Column(JSON, default=dict)

    # Relationships
    clauses = relationship("Clause", back_populates="extraction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Extraction(id={self.id}, filename={self.filename}, status={self.status})>"


class Clause(Base):
    """Model for storing individual clauses extracted from contracts."""

    __tablename__ = "clauses"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to extraction
    extraction_id = Column(String, ForeignKey("extractions.id"), nullable=False)

    # Clause information
    clause_type = Column(String, nullable=False)  # e.g., "payment_terms", "termination", etc.
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)

    # Position in document
    order = Column(Integer, nullable=False)  # Order of clause in document

    # Additional clause metadata (flexible JSON field)
    extra_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    extraction = relationship("Extraction", back_populates="clauses")

    def __repr__(self):
        return f"<Clause(id={self.id}, type={self.clause_type}, extraction_id={self.extraction_id})>"
