"""Tests for document processing service."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test DocumentProcessor service."""

    @pytest.mark.asyncio
    async def test_extract_text_from_txt(self):
        """Test TXT file extraction."""
        content = b"This is a test contract.\nPayment terms: Net 30 days."
        result = await DocumentProcessor.extract_text_from_txt(content)

        assert "test contract" in result
        assert "Payment terms" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_extract_text_from_txt_empty(self):
        """Test empty TXT file."""
        content = b""
        result = await DocumentProcessor.extract_text_from_txt(content)

        assert result == ""

    @pytest.mark.asyncio
    async def test_extract_text_from_txt_unicode(self):
        """Test TXT with unicode characters."""
        content = "Contract with unicode: €100, ©2024".encode('utf-8')
        result = await DocumentProcessor.extract_text_from_txt(content)

        assert "€100" in result
        assert "©2024" in result

    @pytest.mark.asyncio
    async def test_extract_text_from_txt_error(self):
        """Test TXT extraction error handling."""
        # Invalid UTF-8 bytes
        content = b"\xff\xfe"

        with pytest.raises(Exception, match="Failed to extract text from TXT"):
            await DocumentProcessor.extract_text_from_txt(content)

    @pytest.mark.asyncio
    async def test_extract_text_dispatcher_txt(self):
        """Test extract_text dispatcher for TXT files."""
        content = b"Sample contract text"
        result = await DocumentProcessor.extract_text(content, "txt")

        assert "Sample contract text" in result

    @pytest.mark.asyncio
    async def test_extract_text_dispatcher_pdf(self):
        """Test extract_text dispatcher for PDF files."""
        with patch('app.services.document_processor.fitz.open') as mock_fitz:
            # Mock PDF document
            mock_doc = MagicMock()
            mock_doc.page_count = 1
            mock_page = MagicMock()
            mock_page.get_text.return_value = "PDF contract text"
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value = mock_doc

            content = b"fake pdf content"
            result = await DocumentProcessor.extract_text(content, "pdf")

            assert "PDF contract text" in result
            mock_doc.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_text_dispatcher_docx(self):
        """Test extract_text dispatcher for DOCX files."""
        with patch('app.services.document_processor.Document') as mock_doc:
            # Mock DOCX document
            mock_paragraph1 = MagicMock()
            mock_paragraph1.text = "Paragraph 1"
            mock_paragraph2 = MagicMock()
            mock_paragraph2.text = "Paragraph 2"

            mock_doc_instance = MagicMock()
            mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]
            mock_doc.return_value = mock_doc_instance

            content = b"fake docx content"
            result = await DocumentProcessor.extract_text(content, "docx")

            assert "Paragraph 1" in result
            assert "Paragraph 2" in result

    @pytest.mark.asyncio
    async def test_extract_text_dispatcher_doc(self):
        """Test extract_text dispatcher for DOC files."""
        with patch('app.services.document_processor.Document') as mock_doc:
            mock_paragraph = MagicMock()
            mock_paragraph.text = "DOC content"

            mock_doc_instance = MagicMock()
            mock_doc_instance.paragraphs = [mock_paragraph]
            mock_doc.return_value = mock_doc_instance

            content = b"fake doc content"
            result = await DocumentProcessor.extract_text(content, "doc")

            assert "DOC content" in result

    @pytest.mark.asyncio
    async def test_extract_text_unsupported_format(self):
        """Test unsupported file format raises error."""
        content = b"test"

        with pytest.raises(ValueError, match="Unsupported file type"):
            await DocumentProcessor.extract_text(content, "xlsx")

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_multipage(self):
        """Test PDF extraction with multiple pages."""
        with patch('app.services.document_processor.fitz.open') as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.page_count = 3

            mock_page1 = MagicMock()
            mock_page1.get_text.return_value = "Page 1 content"
            mock_page2 = MagicMock()
            mock_page2.get_text.return_value = "Page 2 content"
            mock_page3 = MagicMock()
            mock_page3.get_text.return_value = "Page 3 content"

            mock_doc.__getitem__.side_effect = [mock_page1, mock_page2, mock_page3]
            mock_fitz.return_value = mock_doc

            content = b"fake pdf"
            result = await DocumentProcessor.extract_text_from_pdf(content)

            assert "Page 1 content" in result
            assert "Page 2 content" in result
            assert "Page 3 content" in result

    @pytest.mark.asyncio
    async def test_extract_text_from_pdf_error(self):
        """Test PDF extraction error handling."""
        with patch('app.services.document_processor.fitz.open') as mock_fitz:
            mock_fitz.side_effect = Exception("PDF parsing error")

            content = b"corrupt pdf"

            with pytest.raises(Exception, match="Failed to extract text from PDF"):
                await DocumentProcessor.extract_text_from_pdf(content)

    @pytest.mark.asyncio
    async def test_extract_text_from_docx_empty_paragraphs(self):
        """Test DOCX extraction with empty paragraphs."""
        with patch('app.services.document_processor.Document') as mock_doc:
            mock_p1 = MagicMock()
            mock_p1.text = "Content"
            mock_p2 = MagicMock()
            mock_p2.text = "   "  # Empty paragraph (whitespace only)
            mock_p3 = MagicMock()
            mock_p3.text = "More content"

            mock_doc_instance = MagicMock()
            mock_doc_instance.paragraphs = [mock_p1, mock_p2, mock_p3]
            mock_doc.return_value = mock_doc_instance

            content = b"fake docx"
            result = await DocumentProcessor.extract_text_from_docx(content)

            assert "Content" in result
            assert "More content" in result
            # Empty paragraph should not be included

    @pytest.mark.asyncio
    async def test_extract_text_from_docx_error(self):
        """Test DOCX extraction error handling."""
        with patch('app.services.document_processor.Document') as mock_doc:
            mock_doc.side_effect = Exception("DOCX parsing error")

            content = b"corrupt docx"

            with pytest.raises(Exception, match="Failed to extract text from DOCX"):
                await DocumentProcessor.extract_text_from_docx(content)
