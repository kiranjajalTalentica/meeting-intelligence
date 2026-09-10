"""
Input schemas for the Meeting Intelligence API.

These define the contract for what data enters the system.
"""

from pydantic import BaseModel, Field


class MeetingTranscriptInput(BaseModel):
    """
    The primary input to the Meeting Intelligence pipeline.

    Attributes:
        meeting_id: Unique identifier for the meeting.
        transcript: Full text transcript of the meeting.
    """

    meeting_id: str = Field(
        ..., description="Unique identifier for the meeting"
    )
    transcript: str = Field(
        ...,
        min_length=1,
        description="Full text transcript of the meeting",
    )
