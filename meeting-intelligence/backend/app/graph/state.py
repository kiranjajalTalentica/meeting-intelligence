"""
LangGraph State Definition.

The state is a TypedDict that flows through the graph.
Each node reads from and writes to this shared state.

Design principle: keep the state minimal — only what nodes need
to communicate with each other.
"""

from typing import TypedDict

from app.schemas.outputs import (
    ActionItem,
    Decision,
    OpenQuestion,
    Topic,
)


class MeetingState(TypedDict):
    """
    Shared state passed through the LangGraph workflow.

    Attributes:
        meeting_id: Unique identifier for the meeting.
        transcript: Raw transcript text (input).
        topics: Detected discussion topics.
        summary: Generated meeting summary.
        decisions: Extracted decisions.
        action_items: Extracted action items.
        open_questions: Extracted open questions.
    """

    meeting_id: str
    transcript: str
    topics: list[Topic]
    summary: str
    decisions: list[Decision]
    action_items: list[ActionItem]
    open_questions: list[OpenQuestion]
