"""
Tests for Pydantic schemas.

Validates that our data models accept valid data and reject invalid data.
"""

import pytest
from pydantic import ValidationError

from app.schemas.inputs import MeetingTranscriptInput
from app.schemas.outputs import (
    ActionItem,
    Decision,
    MeetingInsights,
    OpenQuestion,
    Topic,
)


class TestMeetingTranscriptInput:
    def test_valid_input(self):
        data = MeetingTranscriptInput(
            meeting_id="mtg-001",
            transcript="Alice: Let's start the meeting.",
        )
        assert data.meeting_id == "mtg-001"
        assert data.transcript == "Alice: Let's start the meeting."

    def test_empty_transcript_rejected(self):
        with pytest.raises(ValidationError):
            MeetingTranscriptInput(
                meeting_id="mtg-001", transcript=""
            )


class TestOutputModels:
    def test_topic(self):
        topic = Topic(title="Budget", summary="Discussed Q3 budget.")
        assert topic.title == "Budget"

    def test_decision_minimal(self):
        decision = Decision(decision="Use Python 3.13")
        assert decision.reason == ""
        assert decision.source_reference == ""

    def test_action_item_full(self):
        item = ActionItem(
            task="Write tests",
            owner="Alice",
            deadline="Friday",
            source_reference="Alice said she'd handle tests",
        )
        assert item.owner == "Alice"

    def test_open_question(self):
        q = OpenQuestion(question="Who owns the deploy?")
        assert q.context == ""

    def test_meeting_insights_assembles(self):
        insights = MeetingInsights(
            meeting_id="mtg-001",
            summary="A productive meeting.",
            topics=[Topic(title="Roadmap", summary="Q4 plans")],
            decisions=[],
            action_items=[],
            open_questions=[],
        )
        assert insights.meeting_id == "mtg-001"
        assert len(insights.topics) == 1
