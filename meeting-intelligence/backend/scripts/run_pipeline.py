"""
End-to-End Pipeline Test.

Runs the full LangGraph workflow against the sample transcript.
Use this to verify the entire pipeline works after LM Studio is running.

Usage:
    cd backend
    python scripts/run_pipeline.py

This will:
1. Load the sample transcript
2. Run the full LangGraph workflow
3. Print all extracted insights
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.workflow import build_workflow
from app.schemas.outputs import MeetingInsights


def main():
    # Load sample transcript
    transcript_path = Path(__file__).parent.parent / "data" / "sample_transcript.txt"
    transcript = transcript_path.read_text(encoding="utf-8")

    print("=" * 60)
    print("Meeting Intelligence — Full Pipeline Run")
    print("=" * 60)
    print(f"\nTranscript: {len(transcript)} chars")
    print(f"First 100 chars: {transcript[:100]}...")
    print()

    # Build and run workflow
    print("Building workflow...")
    workflow = build_workflow()

    print("Running pipeline (this may take a minute with a local model)...")
    print()

    initial_state = {
        "meeting_id": "demo-001",
        "transcript": transcript,
        "topics": [],
        "summary": "",
        "decisions": [],
        "action_items": [],
        "open_questions": [],
    }

    result = workflow.invoke(initial_state)

    # Build structured output
    insights = MeetingInsights(
        meeting_id=result["meeting_id"],
        summary=result["summary"],
        topics=result["topics"],
        decisions=result["decisions"],
        action_items=result["action_items"],
        open_questions=result["open_questions"],
    )

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
    main()
