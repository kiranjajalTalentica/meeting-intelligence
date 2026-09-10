"""
Tests for prompt loading.

Verifies that all required prompt files exist and can be loaded.
Also checks that prompts contain the expected {transcript} placeholder.
"""

import pytest

from app.prompts import load_prompt


REQUIRED_PROMPTS = [
    "topic_detection",
    "summarization",
    "decision_extraction",
    "action_extraction",
    "open_questions",
]


class TestPromptLoading:
    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_file_exists_and_loads(self, prompt_name):
        """Each required prompt file should exist and be non-empty."""
        text = load_prompt(prompt_name)
        assert len(text) > 0

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_has_transcript_placeholder(self, prompt_name):
        """Each prompt should have a {transcript} placeholder for formatting."""
        text = load_prompt(prompt_name)
        assert "{transcript}" in text

    @pytest.mark.parametrize("prompt_name", REQUIRED_PROMPTS)
    def test_prompt_can_be_formatted(self, prompt_name):
        """Each prompt should be formattable with a transcript string."""
        text = load_prompt(prompt_name)
        formatted = text.format(transcript="Hello, this is a test transcript.")
        assert "Hello, this is a test transcript." in formatted

    def test_nonexistent_prompt_raises(self):
        """Loading a prompt that doesn't exist should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")
