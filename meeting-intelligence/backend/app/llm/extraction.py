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

import asyncio
import json
import logging
import re
import time

from pydantic import BaseModel, ValidationError
from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings

logger = logging.getLogger(__name__)

# Tracks whether we've made at least one LLM call yet. The rate limit
# only cares about calls within a rolling minute, so the very first call
# doesn't need to wait — skipping that leading delay saves ~one delay
# per pipeline run with no risk of tripping the limit.
_first_call_done = False


def reset_throttle() -> None:
    """
    Reset the throttle so the next LLM call skips its leading delay.

    Call this at the start of each pipeline run so the first call of
    every run avoids the unnecessary up-front wait.
    """
    global _first_call_done
    _first_call_done = False


def _throttle() -> None:
    """
    Pause before an LLM call to respect rate limits.

    The Gemini free tier allows only 5 requests/minute. Since our
    pipeline makes 5 LLM calls, spacing them ~13s apart keeps us
    safely under the limit. Controlled by settings.llm_call_delay.

    The first call in a pipeline run skips the delay: there's nothing
    to space it from, so waiting up front just wastes time.
    """
    global _first_call_done
    if not _first_call_done:
        _first_call_done = True
        return
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


# ---------------------------------------------------------------------------
# Async, chunk-aware extraction
# ---------------------------------------------------------------------------
#
# These helpers run one LLM call per transcript chunk concurrently, then
# merge the results. This keeps each call small and fast regardless of how
# long the meeting is. Used by the async pipeline that replaced LangGraph.


async def extract_json_list_from_chunks(
    llm: BaseChatModel,
    prompt_template: str,
    chunks: list[str],
    model_class: type[BaseModel],
) -> list[BaseModel]:
    """
    Run a JSON-list extraction prompt over every chunk concurrently and
    return the merged, de-duplicated list of validated models.

    Args:
        llm: The chat model to call.
        prompt_template: A template containing a `{transcript}` placeholder.
        chunks: Transcript chunks to process.
        model_class: Pydantic model to validate each item against.
    """
    tasks = [
        _invoke_json_list(llm, prompt_template.format(transcript=chunk), model_class)
        for chunk in chunks
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: list[BaseModel] = []
    for res in results:
        if isinstance(res, Exception):
            logger.error("Chunk extraction failed: %s", res)
            continue
        merged.extend(res)

    return _dedupe_models(merged)


async def _invoke_json_list(
    llm: BaseChatModel,
    prompt: str,
    model_class: type[BaseModel],
) -> list[BaseModel]:
    """Call the LLM once (async) and parse a JSON array into models."""
    response = await llm.ainvoke(prompt)
    raw_text = response.content.strip()

    json_array = _parse_json_array(raw_text)
    if json_array is None:
        logger.warning(
            "Could not parse JSON array from chunk response: %s",
            raw_text[:300],
        )
        return []

    results: list[BaseModel] = []
    for item in json_array:
        try:
            results.append(model_class.model_validate(item))
        except ValidationError as e:
            logger.warning(
                "Item failed validation for %s: %s", model_class.__name__, e
            )
    return results


def _dedupe_models(items: list[BaseModel]) -> list[BaseModel]:
    """
    Remove duplicate models that arise from overlapping chunks.

    Two items are considered duplicates if their serialized field values
    (excluding source_reference) match. Keeps the first occurrence.
    """
    seen: set = set()
    unique: list[BaseModel] = []
    for item in items:
        data = item.model_dump()
        data.pop("source_reference", None)
        key = json.dumps(data, sort_keys=True).lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


async def summarize_chunks(
    llm: BaseChatModel,
    map_template: str,
    reduce_template: str,
    chunks: list[str],
) -> str:
    """
    Map-reduce summarization.

    1. MAP: summarize each chunk concurrently.
    2. REDUCE: combine the per-chunk summaries into one final summary.

    For a single chunk, skips the reduce step and returns the map result.
    """
    map_tasks = [
        _invoke_text(llm, map_template.format(transcript=chunk))
        for chunk in chunks
    ]
    map_results = await asyncio.gather(*map_tasks, return_exceptions=True)

    partial_summaries = [
        r for r in map_results if not isinstance(r, Exception) and r
    ]
    for r in map_results:
        if isinstance(r, Exception):
            logger.error("Chunk summary failed: %s", r)

    if not partial_summaries:
        return ""
    if len(partial_summaries) == 1:
        return partial_summaries[0]

    combined = "\n".join(f"- {s}" for s in partial_summaries)
    return await _invoke_text(llm, reduce_template.format(summaries=combined))


async def _invoke_text(llm: BaseChatModel, prompt: str) -> str:
    """Call the LLM once (async) and return stripped text."""
    response = await llm.ainvoke(prompt)
    return response.content.strip()
