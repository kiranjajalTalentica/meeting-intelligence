"""
LLM Connection Verification Script.

Run this to verify that your LLM provider (LM Studio or Gemini)
is reachable and responding correctly.

Usage:
    cd backend
    python scripts/verify_llm.py

Prerequisites:
    - LM Studio: must be running with google/gemma-4-e4b loaded, server started on port 1234
    - Gemini: must have GEMINI_API_KEY set in .env, pip install ".[gemini]"
"""

import sys
from pathlib import Path

# Add the backend directory to Python path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.llm.provider import get_llm


def main():
    print("=" * 60)
    print("Meeting Intelligence — LLM Connection Verification")
    print("=" * 60)
    print()
    print(f"Provider:    {settings.llm_provider.value}")

    if settings.llm_provider.value == "lm_studio":
        print(f"Base URL:    {settings.llm_base_url}")
        print(f"Model:       {settings.llm_model_name}")
    else:
        print(f"Model:       {settings.gemini_model_name}")

    print(f"Temperature: {settings.llm_temperature}")
    print()

    # Step 1: Create the LLM instance
    print("[1/3] Creating LLM instance...")
    try:
        llm = get_llm()
        print(f"      OK - Created {llm.__class__.__name__}")
    except Exception as e:
        print(f"      FAILED - {e}")
        sys.exit(1)

    # Step 2: Simple connectivity test
    print("[2/3] Sending simple prompt: 'Say hello in one word.'")
    try:
        response = llm.invoke("Say hello in one word.")
        reply = response.content.strip()
        print(f"      OK - Response: {reply[:100]}")
    except Exception as e:
        print(f"      FAILED - {e}")
        print()
        if settings.llm_provider.value == "lm_studio":
            print("Troubleshooting:")
            print("  - Is LM Studio running?")
            print("  - Is google/gemma-4-e4b loaded?")
            print("  - Is the server started (Developer tab)?")
            print(f"  - Is it accessible at {settings.llm_base_url}?")
        else:
            print("Troubleshooting:")
            print("  - Is GEMINI_API_KEY set in .env?")
            print("  - Did you install: pip install '.[gemini]'?")
        sys.exit(1)

    # Step 3: JSON extraction test (simulates what the pipeline does)
    print("[3/3] Testing JSON extraction capability...")
    test_prompt = (
        "From the following text, extract action items as a JSON array. "
        "Each item should have 'task' and 'owner' fields.\n\n"
        "Text: Alice will write the report by Friday. "
        "Bob needs to review the API design.\n\n"
        "Return ONLY a valid JSON array:\n"
    )
    try:
        response = llm.invoke(test_prompt)
        reply = response.content.strip()
        print(f"      OK - Response ({len(reply)} chars):")
        for line in reply.split("\n")[:8]:
            print(f"        {line}")
    except Exception as e:
        print(f"      FAILED - {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("All checks passed! LLM connection is working.")
    print("=" * 60)


if __name__ == "__main__":
    main()
