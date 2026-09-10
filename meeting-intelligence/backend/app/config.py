"""
Application configuration.

Loads settings from environment variables with sensible defaults
for local development with LM Studio.
"""

from enum import Enum

from pydantic_settings import BaseSettings


class LLMProvider(str, Enum):
    """
    Supported LLM providers.

    LM_STUDIO: Local model via OpenAI-compatible API (default for dev).
    GEMINI: Google Gemini (for future use — requires langchain-google-genai).
    """

    LM_STUDIO = "lm_studio"
    GEMINI = "gemini"


class Settings(BaseSettings):
    """
    Central configuration for the Meeting Intelligence service.

    Values are read from environment variables or a .env file.
    This keeps secrets and environment-specific values out of code.
    """

    # Which LLM backend to use
    llm_provider: LLMProvider = LLMProvider.LM_STUDIO

    # LLM Provider settings
    # LM Studio exposes an OpenAI-compatible API on localhost
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model_name: str = "google/gemma-4-e4b"
    llm_temperature: float = 0.2

    # Gemini settings (used when llm_provider == "gemini")
    gemini_api_key: str = ""
    gemini_model_name: str = "gemini-flash-latest"

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Throttle between LLM calls (seconds). Helps stay under strict
    # rate limits like the Gemini free tier (5 requests/minute).
    # Set to 0 to disable (e.g. for local LM Studio which has no limit).
    llm_call_delay: float = 13.0

    # --- Transcription (Speech-to-Text) settings ---
    # Whisper model size: tiny, base, small, medium, large-v3.
    # "tiny" / "base" are CPU-friendly and low-memory (good for laptops).
    whisper_model_size: str = "base"
    # Compute type: int8 is fastest/lowest-memory on CPU.
    whisper_compute_type: str = "int8"
    # Device: "cpu" or "cuda". Keep "cpu" unless you have a capable GPU.
    whisper_device: str = "cpu"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton instance used throughout the app
settings = Settings()
