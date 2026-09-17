"""
Meeting analysis pipeline (async, no LangGraph).

Replaces the previous LangGraph workflow. The pipeline is a simple
fan-out + merge:

1. Preprocess: clean and chunk the transcript.
2. Fan out: run summary (map-reduce) and the four extractors concurrently,
   each processing all chunks.
3. Merge: collect results into a MeetingInsights object.

Why plain async instead of LangGraph:
- The workflow has no loops, branching, or evolving shared state — it's
  just "run N independent extractors and combine". asyncio.gather expresses
  that directly, is easier to debug, and drops a dependency.
"""

import asyncio
import logging

from app.llm.provider import get_llm
from app.llm.extraction import (
    extract_json_list_from_chunks,
    summarize_chunks,
)
from app.preprocessing import chunk_transcript
from app.prompts import load_prompt
from app.schemas.outputs import (
    ActionItem,
    Decision,
    MeetingInsights,
    OpenQuestion,
    Topic,
)

logger = logging.getLogger(__name__)


async def analyze_transcript(meeting_id: str, transcript: str) -> MeetingInsights:
    """
    Run the full analysis pipeline on a transcript.

    Returns a MeetingInsights object. Individual sections degrade
    gracefully to empty results if their extraction fails, but the
    overall call still returns the sections that succeeded.
    """
    llm = get_llm()

    # 1. Preprocess: clean + chunk once, reused by every extractor.
    chunks = chunk_transcript(transcript)
    logger.info(
        "Analyzing meeting %s: %d chars -> %d chunk(s)",
        meeting_id,
        len(transcript),
        len(chunks),
    )

    # Load prompts once.
    topic_prompt = load_prompt("topic_detection")
    summary_map_prompt = load_prompt("summarization")
    summary_reduce_prompt = load_prompt("summary_combine")
    decision_prompt = load_prompt("decision_extraction")
    action_prompt = load_prompt("action_extraction")
    question_prompt = load_prompt("open_questions")

    # 2. Fan out: all sections run concurrently.
    summary_task = summarize_chunks(
        llm, summary_map_prompt, summary_reduce_prompt, chunks
    )
    topics_task = extract_json_list_from_chunks(
        llm, topic_prompt, chunks, Topic
    )
    decisions_task = extract_json_list_from_chunks(
        llm, decision_prompt, chunks, Decision
    )
    actions_task = extract_json_list_from_chunks(
        llm, action_prompt, chunks, ActionItem
    )
    questions_task = extract_json_list_from_chunks(
        llm, question_prompt, chunks, OpenQuestion
    )

    summary, topics, decisions, action_items, open_questions = (
        await asyncio.gather(
            summary_task,
            topics_task,
            decisions_task,
            actions_task,
            questions_task,
            return_exceptions=True,
        )
    )

    # 3. Merge, tolerating per-section failures.
    return MeetingInsights(
        meeting_id=meeting_id,
        summary=_ok(summary, "", "summary"),
        topics=_ok(topics, [], "topics"),
        decisions=_ok(decisions, [], "decisions"),
        action_items=_ok(action_items, [], "action_items"),
        open_questions=_ok(open_questions, [], "open_questions"),
    )


def _ok(result, default, label):
    """Return the result unless it's an exception, then log and default."""
    if isinstance(result, Exception):
        logger.error("Section '%s' failed: %s", label, result)
        return default
    return result
