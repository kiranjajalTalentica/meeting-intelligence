"""
End-to-End Pipeline Test.

Runs the full async pipeline (preprocess -> chunk -> extract) against the
sample transcript. Use this to verify the entire pipeline works.

Usage:
    cd backend
    python scripts/run_pipeline.py

This will:
1. Load the sample transcript
2. Run the full async analysis pipeline
3. Print all extracted insights
"""

import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Force UTF-8 stdout so summaries containing non-ASCII characters
# (e.g. narrow no-break spaces from the LLM) print on Windows consoles.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.pipeline import analyze_transcript


async def main():
    # Load sample transcript
    transcript_path = Path(__file__).parent.parent / "data" / "sample_transcript.txt"
    transcript = transcript_path.read_text(encoding="utf-8")

    print("=" * 60)
    print("Meeting Intelligence — Full Pipeline Run")
    print("=" * 60)
    print(f"\nTranscript: {len(transcript)} chars")
    print(f"First 100 chars: {transcript[:100]}...")
    print()

    print("Running pipeline...")
    print()

    insights = await analyze_transcript("demo-001", transcript)

    # Print results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n--- Summary ---")
    print(insights.summary or "(empty)")

    print(f"\n--- Topics ({len(insights.topics)}) ---")
    for t in insights.topics:
        print(f"  * {t.title}: {t.summary}")

    print(f"\n--- Decisions ({len(insights.decisions)}) ---")
    for d in insights.decisions:
        print(f"  * {d.decision}")
        if d.reason:
            print(f"    Reason: {d.reason}")

    print(f"\n--- Action Items ({len(insights.action_items)}) ---")
    for a in insights.action_items:
        owner = f" [{a.owner}]" if a.owner else ""
        deadline = f" (due: {a.deadline})" if a.deadline else ""
        print(f"  * {a.task}{owner}{deadline}")

    print(f"\n--- Open Questions ({len(insights.open_questions)}) ---")
    for q in insights.open_questions:
        print(f"  * {q.question}")
        if q.context:
            print(f"    Context: {q.context}")

    # Also dump as JSON for inspection
    print(f"\n--- Raw JSON ---")
    print(json.dumps(insights.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
