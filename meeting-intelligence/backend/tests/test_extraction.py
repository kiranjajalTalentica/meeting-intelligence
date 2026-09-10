"""
Tests for the structured extraction helpers.

These tests mock the LLM so they can run without a live server.
They verify that our JSON parsing and validation logic works
with various response formats that LLMs typically produce.
"""

from unittest.mock import MagicMock

from app.llm.extraction import extract_text, extract_json_list, _parse_json_array
from app.schemas.outputs import Topic, Decision, ActionItem, OpenQuestion


class TestParseJsonArray:
    """Test the JSON array parser with various LLM output formats."""

    def test_clean_json_array(self):
        text = '[{"title": "Budget", "summary": "Discussed budget."}]'
        result = _parse_json_array(text)
        assert result == [{"title": "Budget", "summary": "Discussed budget."}]

    def test_json_in_markdown_code_block(self):
        text = '```json\n[{"title": "Budget", "summary": "Discussed."}]\n```'
        result = _parse_json_array(text)
        assert result == [{"title": "Budget", "summary": "Discussed."}]

    def test_json_with_surrounding_text(self):
        text = 'Here are the topics:\n[{"title": "X", "summary": "Y"}]\nDone.'
        result = _parse_json_array(text)
        assert result == [{"title": "X", "summary": "Y"}]

    def test_empty_array(self):
        text = "[]"
        result = _parse_json_array(text)
        assert result == []

    def test_invalid_json_returns_none(self):
        text = "This is not JSON at all."
        result = _parse_json_array(text)
        assert result is None

    def test_json_object_not_array_returns_none(self):
        text = '{"key": "value"}'
        result = _parse_json_array(text)
        assert result is None

    def test_code_block_without_json_tag(self):
        text = '```\n[{"title": "A", "summary": "B"}]\n```'
        result = _parse_json_array(text)
        assert result == [{"title": "A", "summary": "B"}]


class TestExtractText:
    def test_returns_stripped_content(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="  This is a summary.  \n"
        )
        result = extract_text(mock_llm, "some prompt")
        assert result == "This is a summary."


class TestExtractJsonList:
    def test_valid_topics(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"title": "API Design", "summary": "Discussed REST vs GraphQL"}]'
        )
        result = extract_json_list(mock_llm, "prompt", Topic)
        assert len(result) == 1
        assert result[0].title == "API Design"
        assert result[0].summary == "Discussed REST vs GraphQL"

    def test_valid_decisions(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"decision": "Use Redis", "reason": "Better perf", "source_reference": "Alice said so"}]'
        )
        result = extract_json_list(mock_llm, "prompt", Decision)
        assert len(result) == 1
        assert result[0].decision == "Use Redis"
        assert result[0].reason == "Better perf"

    def test_valid_action_items(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"task": "Write tests", "owner": "Bob", "deadline": "Friday", "source_reference": "Bob agreed"}]'
        )
        result = extract_json_list(mock_llm, "prompt", ActionItem)
        assert len(result) == 1
        assert result[0].owner == "Bob"
        assert result[0].deadline == "Friday"

    def test_valid_open_questions(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"question": "Who owns deploy?", "context": "Not resolved"}]'
        )
        result = extract_json_list(mock_llm, "prompt", OpenQuestion)
        assert len(result) == 1
        assert result[0].question == "Who owns deploy?"

    def test_partial_valid_items_skips_invalid(self):
        """If one item is invalid, others should still be returned."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"title": "Good", "summary": "Valid"}, {"bad_field": "no title"}]'
        )
        result = extract_json_list(mock_llm, "prompt", Topic)
        # First item is valid, second is missing required 'title'
        assert len(result) == 1
        assert result[0].title == "Good"

    def test_empty_response_returns_empty_list(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="[]")
        result = extract_json_list(mock_llm, "prompt", Topic)
        assert result == []

    def test_garbage_response_returns_empty_list(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="I don't understand the question."
        )
        result = extract_json_list(mock_llm, "prompt", Topic)
        assert result == []

    def test_optional_fields_default_to_empty(self):
        """Decision with only required field should still parse."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='[{"decision": "Use Python"}]'
        )
        result = extract_json_list(mock_llm, "prompt", Decision)
        assert len(result) == 1
        assert result[0].decision == "Use Python"
        assert result[0].reason == ""
        assert result[0].source_reference == ""
