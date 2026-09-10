"""
Transcription API Routes.

Exposes the shared speech-to-text capability. Kept separate from the
meeting intelligence routes so the transcription feature is independent
and reusable by any consumer (Person 1's Intelligence, Person 2's Q&A).

Endpoints:
- POST /api/transcribe        -> audio file -> TranscriptionResult
- POST /api/transcribe-analyze -> audio file -> transcribe THEN run
                                  the intelligence pipeline (convenience)
"""

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.transcription.transcriber import transcribe_audio
from app.transcription.schemas import TranscriptionResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe(
    file: UploadFile = File(...),
    meeting_id: str = Form(...),
):
    """
    Transcribe an uploaded audio file into text + timestamped segments.

    This is the SHARED endpoint. Its output (TranscriptionResult) is
    designed to feed both the Meeting Intelligence and Meeting Q&A
    features — the transcript string for both, and segments for RAG.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Preserve the original extension so faster-whisper/av can decode it
    suffix = ""
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1]

    try:
        result = transcribe_audio(
            audio_bytes=audio_bytes,
            meeting_id=meeting_id,
            filename_suffix=suffix or ".wav",
        )
        return result
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {type(e).__name__}: {e}",
        )
