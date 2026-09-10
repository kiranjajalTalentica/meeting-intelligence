"""
LangGraph Node Functions.

Each function here is a single node in the processing graph.
Every node has ONE responsibility:
- Read the transcript from state
- Load its prompt from a .txt file
- Call the LLM with the formatted prompt
- Parse the result into Pydantic models
- Return updated state fields

Key design decisions:
- Each node gets its own LLM instance (cheap — it's just config)
- Prompts live in /prompts/*.txt — editable without code changes
- Errors are caught per-node so one failure doesn't crash the pipeline
- Nodes return partial state updates (only the fields they own)

Reference: PRD Section 7 — Graph 1, Node Responsibilities
"""

import logging

from app.graph.state import MeetingState
from app.llm.provider import get_llm
from app.llm.extraction import extract_text, extract_json_list
from app.prompts import load_prompt
from app.schemas.outputs import (
    ActionItem,
    Decision,
    OpenQuestion,
    Topic,
)

logger = logging.getLogger(__name__)


def detect_topics(state: MeetingState) -> dict:
    """
    Detect discussion topics from the transcript.

    This runs FIRST in the pipeline. Other nodes can use
    the detected topics for context if needed.
    """
    try:
        llm = get_llm()
        prompt = load_prompt("topic_detection").format(
            transcript=state["transcript"]
        )
        topics = extract_json_list(llm, prompt, Topic)
        logger.info("Detected %d topics", len(topics))
        return {"topics": topics}
    except Exception as e:
        logger.error("Topic detection failed: %s", e)
        return {"topics": []}


def generate_summary(state: MeetingState) -> dict:
    """
    Generate a concise meeting summary.

    Uses plain text extraction since the output is a paragraph,
    not structured JSON.
    """
    try:
        llm = get_llm()
        prompt = load_prompt("summarization").format(
            transcript=state["transcript"]
        )
        summary = extract_text(llm, prompt)
        logger.info("Generated summary (%d chars)", len(summary))
        return {"summary": summary}
    except Exception as e:
        logger.error("Summary generation failed: %s", e)
        return {"summary": ""}


def extract_decisions(state: MeetingState) -> dict:
    """Extract decisions made during the meeting."""
    try:
        llm = get_llm()
        prompt = load_prompt("decision_extraction").format(
            transcript=state["transcript"]
        )
        decisions = extract_json_list(llm, prompt, Decision)
        logger.info("Extracted %d decisions", len(decisions))
        return {"decisions": decisions}
    except Exception as e:
        logger.error("Decision extraction failed: %s", e)
        return {"decisions": []}


def extract_action_items(state: MeetingState) -> dict:
    """Extract action items assigned during the meeting."""
    try:
        llm = get_llm()
        prompt = load_prompt("action_extraction").format(
            transcript=state["transcript"]
        )
        action_items = extract_json_list(llm, prompt, ActionItem)
        logger.info("Extracted %d action items", len(action_items))
        return {"action_items": action_items}
    except Exception as e:
        logger.error("Action item extraction failed: %s", e)
        return {"action_items": []}


def extract_open_questions(state: MeetingState) -> dict:
    """Extract questions that remain unresolved."""
    try:
        llm = get_llm()
        prompt = load_prompt("open_questions").format(
            transcript=state["transcript"]
        )
        open_questions = extract_json_list(llm, prompt, OpenQuestion)
        logger.info("Extracted %d open questions", len(open_questions))
        return {"open_questions": open_questions}
    except Exception as e:
        logger.error("Open question extraction failed: %s", e)
        return {"open_questions": []}
