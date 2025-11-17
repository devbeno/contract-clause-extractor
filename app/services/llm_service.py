"""LLM service for extracting clauses from legal contracts using OpenAI."""
import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI API to extract contract clauses."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Cost-effective model for contract analysis

    async def extract_clauses(self, document_text: str) -> List[Dict[str, Any]]:
        """
        Extract structured clauses from legal contract text using LLM.

        This method uses a carefully crafted prompt to ensure the LLM:
        1. Identifies all major legal clauses
        2. Categorizes them by type
        3. Returns structured JSON output

        Args:
            document_text: Full text content of the legal contract

        Returns:
            List[Dict[str, Any]]: List of extracted clauses with metadata

        Raises:
            Exception: If LLM extraction fails
        """
        try:
            # Craft the system prompt for legal clause extraction
            system_prompt = """You are an expert legal document analyzer specializing in contract clause extraction.

Your task is to analyze legal contracts and extract all significant clauses into a structured format.

For each clause you identify, provide:
1. clause_type: The category of the clause (e.g., "payment_terms", "termination", "confidentiality", "liability", "governing_law", "dispute_resolution", "warranties", "indemnification", "term_duration", "renewal", "intellectual_property", etc.)
2. title: A brief, descriptive title for the clause
3. content: The full text of the clause exactly as it appears in the document
4. summary: A 1-2 sentence summary of what the clause means

Return your response as a valid JSON array of objects. Each object should have these exact keys: clause_type, title, content, summary.

Important guidelines:
- Extract ALL significant legal clauses, not just major ones
- Keep the original wording in the "content" field
- Be thorough but avoid duplicates
- If multiple clauses of the same type exist, number them (e.g., "payment_terms_1", "payment_terms_2")
- Return ONLY the JSON array, no additional text"""

            user_prompt = f"""Analyze the following legal contract and extract all significant clauses.

Contract text:
{document_text}

Return a JSON array of all extracted clauses following the schema provided in the system message."""

            logger.info(f"Sending contract to LLM for clause extraction (text length: {len(document_text)} chars)")

            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent, factual extraction
                max_tokens=4000,  # Allow for detailed extraction
            )

            # Extract response content
            response_text = response.choices[0].message.content.strip()

            logger.info(f"Received LLM response: {len(response_text)} characters")

            # Parse JSON response
            clauses = self._parse_llm_response(response_text)

            logger.info(f"Successfully extracted {len(clauses)} clauses from contract")

            return clauses

        except Exception as e:
            logger.error(f"Error extracting clauses with LLM: {str(e)}")
            raise Exception(f"Failed to extract clauses: {str(e)}")

    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse and validate LLM JSON response.

        Args:
            response_text: Raw text response from LLM

        Returns:
            List[Dict[str, Any]]: Parsed and validated clauses

        Raises:
            Exception: If parsing fails or response is invalid
        """
        try:
            # Try to extract JSON if there's extra text
            start_idx = response_text.find('[')
            end_idx = response_text.rfind(']') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")

            json_str = response_text[start_idx:end_idx]
            clauses = json.loads(json_str)

            if not isinstance(clauses, list):
                raise ValueError("Response is not a JSON array")

            # Validate each clause has required fields
            required_fields = {"clause_type", "title", "content", "summary"}
            validated_clauses = []

            for idx, clause in enumerate(clauses):
                if not isinstance(clause, dict):
                    logger.warning(f"Skipping clause {idx}: not a dictionary")
                    continue

                # Check for required fields
                missing_fields = required_fields - set(clause.keys())
                if missing_fields:
                    logger.warning(f"Clause {idx} missing fields: {missing_fields}")
                    # Add default values for missing fields
                    for field in missing_fields:
                        if field == "summary":
                            clause["summary"] = ""
                        elif field == "title":
                            clause["title"] = f"Clause {idx + 1}"

                validated_clauses.append(clause)

            return validated_clauses

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            logger.error(f"Response text: {response_text[:500]}...")
            raise Exception(f"Invalid JSON in LLM response: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise Exception(f"Failed to parse LLM response: {str(e)}")
