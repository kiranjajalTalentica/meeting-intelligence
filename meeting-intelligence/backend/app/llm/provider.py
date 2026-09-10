"""
LLM Provider Abstraction.

This module is the ONLY place that knows which LLM backend is in use.
All other code calls `get_llm()` and receives a LangChain BaseChatModel.

To switch providers:
- Set LLM_PROVIDER=lm_studio or LLM_PROVIDER=gemini in your .env
- For Gemini, also set GEMINI_API_KEY

No other files need to change.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.config import LLMProvider, settings


def _create_lm_studio() -> ChatOpenAI:
    """Create a ChatOpenAI instance pointed at LM Studio's local server."""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        model=settings.llm_model_name,
        temperature=settings.llm_temperature,
        # LM Studio doesn't require a real API key,
        # but the OpenAI client requires the field to be non-empty.
        api_key="lm-studio",
    )


def _create_gemini() -> BaseChatModel:
    """
    Create a Gemini chat model.

    Requires: pip install langchain-google-genai
    And GEMINI_API_KEY set in environment.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "To use Gemini, install: pip install langchain-google-genai"
        )

    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY must be set when using the Gemini provider"
        )

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model_name,
        google_api_key=settings.gemini_api_key,
        temperature=settings.llm_temperature,
    )


def get_llm() -> BaseChatModel:
    """
    Returns a LangChain ChatModel for the configured provider.

    The provider is selected via the LLM_PROVIDER environment variable.
    Defaults to LM Studio for local development.
    """
    if settings.llm_provider == LLMProvider.GEMINI:
        return _create_gemini()
    return _create_lm_studio()
