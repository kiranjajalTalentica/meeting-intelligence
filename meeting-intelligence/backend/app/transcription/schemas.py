"""
Transcription output schemas.

This is the SHARED CONTRACT for the transcription module.

Both features consume this output:
- Person 1 (Meeting Intelligence): uses `transcript` (the full text)
- Person 2 (Meeting Q&A / RAG): can use `segments` for timestamped
  chunking and source citations, plus `transcript` for full context

Keeping this contract stable means the transcription source (file upload,
mic recording, live stream) can change without breaking either feature.
"""

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    """
    A single timestamped chunk of transcribed speech.

    Useful for Person 2's RAG: each segment can become a retrievable
    chunk with a precise timestamp for citation.
    """

    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")


class TranscriptionResult(BaseModel):
    """
    The complete output of transcribing an audio file.

    This is what the transcription endpoint returns and what both
    features build on top of.

    Attributes:
        meeting_id: Identifier tying this transcript to a meeting.
        transcript: Full transcript as a single string (Person 1 input).
        language: Detected language code (e.g. "en").
        duration: Total audio duration in seconds.
        segments: Timestamped segments (Person 2 / RAG input).
    """

    meeting_id: str = Field(..., description="Meeting identifier")
    transcript: str = Field(..., description="Full transcript text")
    language: str = Field("", description="Detected language code")
    duration: float = Field(0.0, description="Audio duration in seconds")
    segments: list[TranscriptSegment] = Field(
        default_factory=list, description="Timestamped transcript segments"
    )
