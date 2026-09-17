"""
API Routes for Meeting Intelligence.

Exposes endpoints to analyze transcripts, load a sample,
and check the LLM connection.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.llm.provider import get_llm
from app.pipeline import analyze_transcript
from app.schemas.inputs import MeetingTranscriptInput
from app.schemas.outputs import MeetingInsights

router = APIRouter()

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
    2. Preprocesses (cleans + chunks) the transcript.
    3. Runs summary (map-reduce) and the four extractors concurrently,
       each over all chunks, then merges the results.
    4. Returns structured MeetingInsights.
    """
    return await analyze_transcript(
        input_data.meeting_id, input_data.transcript
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
