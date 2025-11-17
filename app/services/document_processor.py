"""Document processing service for extracting text from PDFs and DOCX files."""
import fitz  # PyMuPDF
from docx import Document
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for extracting text from various document formats."""

    @staticmethod
    async def extract_text_from_pdf(file_content: bytes) -> str:
        """
        Extract text from PDF file content.

        Args:
            file_content: Binary content of the PDF file

        Returns:
            str: Extracted text from the PDF

        Raises:
            Exception: If PDF processing fails
        """
        try:
            # Open PDF from memory
            pdf_document = fitz.open(stream=file_content, filetype="pdf")

            # Extract text from all pages
            text_content = []
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text = page.get_text()
                text_content.append(text)

            pdf_document.close()

            # Join all pages with double newline
            full_text = "\n\n".join(text_content)

            logger.info(f"Successfully extracted {len(full_text)} characters from PDF with {len(text_content)} pages")

            return full_text

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    @staticmethod
    async def extract_text_from_docx(file_content: bytes) -> str:
        """
        Extract text from DOCX file content.

        Args:
            file_content: Binary content of the DOCX file

        Returns:
            str: Extracted text from the DOCX

        Raises:
            Exception: If DOCX processing fails
        """
        try:
            # Create a temporary file-like object
            from io import BytesIO
            docx_stream = BytesIO(file_content)

            # Open DOCX from memory
            document = Document(docx_stream)

            # Extract text from all paragraphs
            text_content = []
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)

            # Join all paragraphs with newline
            full_text = "\n".join(text_content)

            logger.info(f"Successfully extracted {len(full_text)} characters from DOCX with {len(text_content)} paragraphs")

            return full_text

        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")

    @staticmethod
    async def extract_text_from_txt(file_content: bytes) -> str:
        """
        Extract text from TXT file content.

        Args:
            file_content: Binary content of the TXT file

        Returns:
            str: Extracted text from the TXT

        Raises:
            Exception: If TXT processing fails
        """
        try:
            # Decode the text content
            text = file_content.decode('utf-8')
            logger.info(f"Successfully extracted {len(text)} characters from TXT file")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from TXT: {str(e)}")
            raise Exception(f"Failed to extract text from TXT: {str(e)}")

    @staticmethod
    async def extract_text(file_content: bytes, file_type: str) -> str:
        """
        Extract text from document based on file type.

        Args:
            file_content: Binary content of the file
            file_type: Type of file ('pdf', 'docx', 'txt')

        Returns:
            str: Extracted text

        Raises:
            ValueError: If file type is not supported
            Exception: If text extraction fails
        """
        file_type = file_type.lower()

        if file_type == "pdf":
            return await DocumentProcessor.extract_text_from_pdf(file_content)
        elif file_type in ["docx", "doc"]:
            return await DocumentProcessor.extract_text_from_docx(file_content)
        elif file_type == "txt":
            return await DocumentProcessor.extract_text_from_txt(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
