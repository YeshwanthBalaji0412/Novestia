"""Gemini AI client for generating explanations.

Uses google-genai SDK with gemini-2.5-flash model.
"""

from __future__ import annotations

import structlog
from google import genai
from google.genai.errors import ClientError

from novestia.config import settings
from novestia.core.errors import AppError

logger = structlog.stdlib.get_logger()

_client: genai.Client | None = None


class AIGenerationError(AppError):
    """Raised when AI generation fails."""

    def __init__(self, message: str = "AI explanation unavailable") -> None:
        super().__init__(code="AI_ERROR", message=message, status_code=502)


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not settings.gemini_api_key:
            raise AIGenerationError("Gemini API key not configured")
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def generate(prompt: str) -> str:
    """Generate text using Gemini 2.5 Flash.

    Returns the generated text or raises AIGenerationError.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text
        if not text:
            raise AIGenerationError("Gemini returned empty response")
        return text

    except ClientError as e:
        logger.error("gemini_error", error=str(e))
        raise AIGenerationError(f"Gemini API error: {e}") from e
    except AIGenerationError:
        raise
    except Exception as e:
        logger.error("gemini_unexpected_error", error=str(e))
        raise AIGenerationError("Unexpected AI generation error") from e
