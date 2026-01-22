"""Shared LLM utilities."""

from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from ..config import settings


def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """Get configured LLM instance.

    Args:
        temperature: LLM temperature setting (default 0.3)

    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
    )


def parse_llm_response(content: Any) -> str:
    """Parse LLM response content, handling Gemini's structured format.

    Args:
        content: Raw response content from LLM

    Returns:
        Parsed string content
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        # Gemini 3 returns [{'type': 'text', 'text': '...'}]
        text_parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif isinstance(item, str):
                text_parts.append(item)
        return "".join(text_parts) if text_parts else str(content)
    return str(content)
