"""
API Routes for Meeting Intelligence.

Exposes endpoints to analyze transcripts, load a sample,
and check the LLM connection.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.llm.provider import get_llm
from app.schemas.inputs import MeetingTranscriptInput
from app.schemas.outputs import MeetingInsights
from app.graph.workflow import build_workflow

router = APIRouter()

# Compile the workflow once at module level for reuse
workflow = build_workflow()

# Path to the bundled sample transcript
SAMPLE_TRANSCRIPT_PATH = (
    Path(__file__).parent.parent.parent / "data" / "sample_transcript.txt"
)


@router.post("/analyze", response_model=MeetingInsights)
async def analyze_meeting(input_data: MeetingTranscriptInput):
    """
    Analyze a meeting transcript and return structured insights.

    This endpoint:
    1. Accepts a meeting_id and transcript text.
    2. Runs the LangGraph workflow (topic detection → parallel extraction).
    3. Returns structured MeetingInsights.
    """
    # Prepare initial state for the graph
    initial_state = {
        "meeting_id": input_data.meeting_id,
        "transcript": input_data.transcript,
        "topics": [],
        "summary": "",
        "decisions": [],
        "action_items": [],
        "open_questions": [],
    }

    # Invoke the compiled workflow
    result = workflow.invoke(initial_state)

    # Build and return the response
    return MeetingInsights(
        meeting_id=result["meeting_id"],
        summary=result["summary"],
        topics=result["topics"],
        decisions=result["decisions"],
        action_items=result["action_items"],
        open_questions=result["open_questions"],
    )


@router.get("/sample-transcript")
async def get_sample_transcript():
    """
    Return the bundled sample meeting transcript.

    Lets the UI offer a "Load Sample" button so users can try
    the pipeline without pasting their own transcript.
    """
    if not SAMPLE_TRANSCRIPT_PATH.exists():
        raise HTTPException(
            status_code=404, detail="Sample transcript not found"
        )
    return {"transcript": SAMPLE_TRANSCRIPT_PATH.read_text(encoding="utf-8")}


@router.get("/health/llm")
async def check_llm_connection():
    """
    Verify that the LLM provider is reachable and responding.

    Sends a simple prompt and checks that a non-empty response is returned.
    Useful for debugging connection issues with LM Studio or other providers.
    """
    try:
        llm = get_llm()
        response = llm.invoke("Say 'hello' in one word.")
        reply = response.content.strip()

        if not reply:
            raise HTTPException(
                status_code=503,
                detail="LLM returned an empty response",
            )

        return {
            "status": "connected",
            "provider": str(llm.__class__.__name__),
            "sample_response": reply[:200],  # truncate for safety
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"LLM connection failed: {type(e).__name__}: {str(e)}",
        )
