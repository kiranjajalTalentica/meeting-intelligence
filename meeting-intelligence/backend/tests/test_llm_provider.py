"""
Tests for the LLM provider abstraction.

These tests verify the provider factory without requiring a live LLM server.
They test configuration and instantiation — NOT actual LLM calls.
"""

from unittest.mock import patch

from langchain_openai import ChatOpenAI

from app.config import LLMProvider, Settings
from app.llm.provider import get_llm


class TestProviderFactory:
    @patch("app.llm.provider.settings")
    def test_lm_studio_creates_chatopenai_instance(self, mock_settings):
        """The LM Studio provider should create a ChatOpenAI instance."""
        mock_settings.llm_provider = LLMProvider.LM_STUDIO
        mock_settings.llm_base_url = "http://localhost:1234/v1"
        mock_settings.llm_model_name = "test-model"
        mock_settings.llm_temperature = 0.2
        llm = get_llm()
        assert isinstance(llm, ChatOpenAI)

    @patch("app.llm.provider.settings")
    def test_lm_studio_uses_configured_base_url(self, mock_settings):
        """The ChatOpenAI instance should use the configured base_url."""
        mock_settings.llm_provider = LLMProvider.LM_STUDIO
        mock_settings.llm_base_url = "http://localhost:1234/v1"
        mock_settings.llm_model_name = "test-model"
        mock_settings.llm_temperature = 0.2
        llm = get_llm()
        assert llm.openai_api_base == "http://localhost:1234/v1"

    @patch("app.llm.provider.settings")
    def test_groq_without_key_raises(self, mock_settings):
        """Requesting Groq without an API key should raise ValueError."""
        mock_settings.llm_provider = LLMProvider.GROQ
        mock_settings.groq_api_key = ""
        mock_settings.groq_model_name = "llama-3.3-70b-versatile"
        mock_settings.llm_temperature = 0.2
        try:
            get_llm()
            assert False, "Should have raised"
        except (ValueError, ImportError):
            pass

    @patch("app.llm.provider.settings")
    def test_custom_temperature(self, mock_settings):
        """Provider should respect temperature from settings."""
        mock_settings.llm_provider = LLMProvider.LM_STUDIO
        mock_settings.llm_base_url = "http://localhost:1234/v1"
        mock_settings.llm_model_name = "test-model"
        mock_settings.llm_temperature = 0.7
        llm = get_llm()
        assert llm.temperature == 0.7

    @patch("app.llm.provider.settings")
    def test_gemini_without_key_raises(self, mock_settings):
        """Requesting Gemini without an API key should raise ValueError."""
        mock_settings.llm_provider = LLMProvider.GEMINI
        mock_settings.gemini_api_key = ""
        mock_settings.gemini_model_name = "gemini-2.5-flash"
        mock_settings.llm_temperature = 0.2

        try:
            get_llm()
            assert False, "Should have raised"
        except (ValueError, ImportError):
            pass  # Either is acceptable depending on installed packages


class TestProviderConfig:
    def test_default_provider(self):
        """Groq is the default provider in code (no .env)."""
        s = Settings(
            _env_file=None  # don't read .env in tests
        )
        assert s.llm_provider == LLMProvider.GROQ

    def test_provider_enum_values(self):
        """Verify enum string values match expected .env values."""
        assert LLMProvider.LM_STUDIO.value == "lm_studio"
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.GROQ.value == "groq"
