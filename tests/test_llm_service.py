"""Tests for LLM service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.llm_service import LLMService


def _create_service_without_openai_call():
    """Helper to instantiate service without real OpenAI client."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        mock_openai.return_value = MagicMock()
        return LLMService()


@pytest.mark.asyncio
async def test_extract_clauses_success():
    """Test successful clause extraction."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        # Mock the OpenAI response
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '''
        [
            {
                "clause_type": "payment_terms",
                "title": "Payment Terms",
                "content": "Payment within 30 days",
                "summary": "Net 30 payment"
            }
        ]
        '''
        # Use AsyncMock for async method
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client

        service = LLMService()
        result = await service.extract_clauses("Test contract text")

        assert len(result) == 1
        assert result[0]["clause_type"] == "payment_terms"
        assert result[0]["title"] == "Payment Terms"


@pytest.mark.asyncio
async def test_extract_clauses_empty_response():
    """Test extraction with empty LLM response."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '[]'
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client

        service = LLMService()
        result = await service.extract_clauses("Test contract text")

        assert result == []


@pytest.mark.asyncio
async def test_extract_clauses_invalid_json():
    """Test extraction with invalid JSON response."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = 'Invalid JSON'
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client

        service = LLMService()

        with pytest.raises(Exception):
            await service.extract_clauses("Test contract text")


@pytest.mark.asyncio
async def test_extract_clauses_api_error():
    """Test extraction with API error."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))
        mock_openai.return_value = mock_client

        service = LLMService()

        with pytest.raises(Exception) as exc_info:
            await service.extract_clauses("Test contract text")

        assert "API Error" in str(exc_info.value) or "Failed to extract clauses" in str(exc_info.value)


@pytest.mark.asyncio
async def test_extract_clauses_multiple_clauses():
    """Test extraction with multiple clauses."""
    with patch('app.services.llm_service.AsyncOpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '''
        [
            {
                "clause_type": "payment_terms",
                "title": "Payment",
                "content": "Pay within 30 days",
                "summary": "Net 30"
            },
            {
                "clause_type": "termination",
                "title": "Termination",
                "content": "30 days notice required",
                "summary": "30 day notice"
            },
            {
                "clause_type": "confidentiality",
                "title": "NDA",
                "content": "All information is confidential",
                "summary": "Standard NDA"
            }
        ]
        '''
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client

        service = LLMService()
        result = await service.extract_clauses("Test contract text")

        assert len(result) == 3
        assert result[0]["clause_type"] == "payment_terms"
        assert result[1]["clause_type"] == "termination"
        assert result[2]["clause_type"] == "confidentiality"


def test_parse_llm_response_missing_fields():
    """Ensure missing optional fields are populated with defaults."""
    service = _create_service_without_openai_call()
    response = '''
    [
        {
            "clause_type": "payment_terms",
            "content": "Payment within 30 days"
        }
    ]
    '''

    clauses = service._parse_llm_response(response)

    assert clauses[0]["title"] == "Clause 1"
    assert clauses[0]["summary"] == ""


def test_parse_llm_response_skips_non_dict_entries():
    """Ensure non-dictionary entries are ignored."""
    service = _create_service_without_openai_call()
    response = '''
    [
        "invalid entry",
        {
            "clause_type": "termination",
            "title": "Termination",
            "content": "30 days notice"
        }
    ]
    '''

    clauses = service._parse_llm_response(response)

    assert len(clauses) == 1
    assert clauses[0]["clause_type"] == "termination"


def test_parse_llm_response_json_decode_error():
    """Ensure JSON decoding errors surface with clear message."""
    service = _create_service_without_openai_call()
    response = '[{"clause_type": "payment_terms", ]'  # malformed JSON

    with pytest.raises(Exception) as exc:
        service._parse_llm_response(response)

    assert "Invalid JSON" in str(exc.value)


def test_parse_llm_response_requires_array(monkeypatch):
    """Ensure non-list responses raise a parsing error."""
    service = _create_service_without_openai_call()

    def _fake_loads(_):
        return {"not": "a list"}

    monkeypatch.setattr("app.services.llm_service.json.loads", _fake_loads)

    with pytest.raises(Exception) as exc:
        service._parse_llm_response('[{"clause_type": "payment_terms"}]')

    assert "Failed to parse LLM response" in str(exc.value)
