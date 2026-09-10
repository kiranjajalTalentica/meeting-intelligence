"""
Prompt Loading Utility.

Prompts are stored as separate .txt files in the /prompts directory
(at the project root). This keeps prompt engineering separate from
Python code — you can tweak prompts without touching any logic.

Reference: PRD Section 13 — Prompt Management
"""

from pathlib import Path

# Prompts directory is at the project root (backend/prompts/)
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """
    Load a prompt template from a .txt file.

    Args:
        name: Filename without extension (e.g., "summarization")

    Returns:
        The prompt text with {placeholders} ready for .format()

    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}. "
            f"Available prompts: {[f.stem for f in PROMPTS_DIR.glob('*.txt')]}"
        )
    return path.read_text(encoding="utf-8")
