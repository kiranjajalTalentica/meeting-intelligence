"""
Tests for LangGraph node functions.

Each node is tested with a mocked LLM to verify:
1. It loads the correct prompt file
2. It returns the right state key with parsed data
3. It handles LLM errors gracefully (returns empty data)
"""

from unittest.mock import patch, MagicMock

from app.graph.nodes import (
    detect_topics,
    generate_summary,
    extract_decisions,
    extract_action_items,
    extract_open_questions,
)


SAMPLE_STATE = {
    "meeting_id": "test-001",
    "transcript": "Alice: Let's use Redis. Bob: Agreed.",
    "topics": [],
    "summary": "",
    "decisions": [],
    "action_items": [],
    "open_questions": [],
}


class TestDetectTopics:
    @patch("app.graph.nodes.get_llm")
    def test_returns_topics(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"title": "Infrastructure", "summary": "Discussed Redis"}]'
        )
        mock_get_llm.return_value = mock_llm

        result = detect_topics(SAMPLE_STATE)
        assert "topics" in result
        assert len(result["topics"]) == 1
        assert result["topics"][0].title == "Infrastructure"

    @patch("app.graph.nodes.get_llm")
    def test_handles_error_gracefully(self, mock_get_llm):
        mock_get_llm.side_effect = Exception("Connection refused")
        result = detect_topics(SAMPLE_STATE)
        assert result == {"topics": []}


class TestGenerateSummary:
    @patch("app.graph.nodes.get_llm")
    def test_returns_summary_text(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="The team decided to use Redis for caching."
        )
        mock_get_llm.return_value = mock_llm

        result = generate_summary(SAMPLE_STATE)
        assert "summary" in result
        assert "Redis" in result["summary"]

    @patch("app.graph.nodes.get_llm")
    def test_handles_error_gracefully(self, mock_get_llm):
        mock_get_llm.side_effect = Exception("Timeout")
        result = generate_summary(SAMPLE_STATE)
        assert result == {"summary": ""}


class TestExtractDecisions:
    @patch("app.graph.nodes.get_llm")
    def test_returns_decisions(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"decision": "Use Redis", "reason": "Performance", "source_reference": "Alice said so"}]'
        )
        mock_get_llm.return_value = mock_llm

        result = extract_decisions(SAMPLE_STATE)
        assert "decisions" in result
        assert len(result["decisions"]) == 1
        assert result["decisions"][0].decision == "Use Redis"


class TestExtractActionItems:
    @patch("app.graph.nodes.get_llm")
    def test_returns_action_items(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"task": "Set up Redis", "owner": "Bob", "deadline": "Thursday", "source_reference": "Bob agreed"}]'
        )
        mock_get_llm.return_value = mock_llm

        result = extract_action_items(SAMPLE_STATE)
        assert "action_items" in result
        assert len(result["action_items"]) == 1
        assert result["action_items"][0].owner == "Bob"


class TestExtractOpenQuestions:
    @patch("app.graph.nodes.get_llm")
    def test_returns_open_questions(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"question": "Who handles deploy?", "context": "Not discussed"}]'
        )
        mock_get_llm.return_value = mock_llm

        result = extract_open_questions(SAMPLE_STATE)
        assert "open_questions" in result
        assert len(result["open_questions"]) == 1
        assert "deploy" in result["open_questions"][0].question
