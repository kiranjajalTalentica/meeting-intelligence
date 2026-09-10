"""
Structured extraction helpers.

This module provides utilities for calling the LLM and parsing
the response into Pydantic models. It handles the common patterns:
1. Plain text extraction (for summary)
2. JSON list extraction (for topics, decisions, action items, questions)

Why not use LangChain's `with_structured_output()` directly?
- Local models (LM Studio) often don't support OpenAI's function calling
- Instead we ask for JSON in the prompt and parse it ourselves
- This approach works with ANY model that can output JSON
"""

import json
import logging
import re
import time

from pydantic import BaseModel, ValidationError
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)


def _throttle() -> None:
    """
    Pause before an LLM call to respect rate limits.

    The Gemini free tier allows only 5 requests/minute. Since our
    pipeline makes 5 LLM calls, spacing them ~13s apart keeps us
    safely under the limit. Controlled by settings.llm_call_delay.
    """
    if settings.llm_call_delay > 0:
        time.sleep(settings.llm_call_delay)


def extract_text(llm: BaseChatModel, prompt: str) -> str:
    """
    Send a prompt to the LLM and return the raw text response.

    Used for free-form outputs like meeting summaries.
    """
    _throttle()
    response = llm.invoke(prompt)
    return response.content.strip()


def extract_json_list(
    llm: BaseChatModel,
    prompt: str,
    model_class: type[BaseModel],
) -> list[BaseModel]:
    """
    Send a prompt to the LLM, parse the response as a JSON array,
    and validate each item against the given Pydantic model.

    Steps:
    1. Call the LLM with the prompt
    2. Find a JSON array in the response (handles markdown code blocks)
    3. Parse each item in the array into the Pydantic model
    4. Skip items that fail validation (log a warning)

    Returns a list of validated Pydantic model instances.
    """
    _throttle()
    response = llm.invoke(prompt)
    raw_text = response.content.strip()

    # Try to extract JSON from the response
    json_array = _parse_json_array(raw_text)

    if json_array is None:
        logger.warning(
            "Could not parse JSON array from LLM response. "
            "Raw response: %s",
            raw_text[:500],
        )
        return []

    # Validate each item against the Pydantic model
    results = []
    for i, item in enumerate(json_array):
        try:
            validated = model_class.model_validate(item)
            results.append(validated)
        except ValidationError as e:
            logger.warning(
                "Item %d failed validation for %s: %s",
                i,
                model_class.__name__,
                e,
            )
            continue

    return results


def _parse_json_array(text: str) -> list[dict] | None:
    """
    Extract a JSON array from LLM output.

    Handles common patterns:
    - Raw JSON array: [...]
    - Markdown code block: ```json\n[...]\n```
    - Text before/after the JSON

    Returns None if no valid JSON array is found.
    """
    # First, try to find JSON inside markdown code blocks
    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL
    )
    if code_block_match:
        try:
            parsed = json.loads(code_block_match.group(1))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Try to find a raw JSON array in the text
    # Look for the first '[' and last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    # Last resort: try parsing the entire text as JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    return None
