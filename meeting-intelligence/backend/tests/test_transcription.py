"""
Tests for the transcription module.

These test the shared output contract (schemas) without needing to
load the heavy Whisper model. Actual transcription is verified via
scripts/verify_transcription.py with real audio.
"""

from app.transcription.schemas import (
    TranscriptSegment,
    TranscriptionResult,
)


class TestTranscriptSegment:
    def test_valid_segment(self):
        seg = TranscriptSegment(start=0.0, end=2.5, text="Hello world")
        assert seg.start == 0.0
        assert seg.end == 2.5
        assert seg.text == "Hello world"


class TestTranscriptionResult:
    def test_minimal_result(self):
        """A result needs only meeting_id and transcript."""
        result = TranscriptionResult(
            meeting_id="mtg-001",
            transcript="Alice will finish the report by Friday.",
        )
        assert result.meeting_id == "mtg-001"
        assert result.language == ""
        assert result.duration == 0.0
        assert result.segments == []

    def test_full_result_with_segments(self):
        result = TranscriptionResult(
            meeting_id="mtg-002",
            transcript="Hello. Goodbye.",
            language="en",
            duration=4.2,
            segments=[
                TranscriptSegment(start=0.0, end=2.0, text="Hello."),
                TranscriptSegment(start=2.0, end=4.2, text="Goodbye."),
            ],
        )
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.segments[1].text == "Goodbye."

    def test_transcript_feeds_intelligence_contract(self):
        """
        The transcript field is what Person 1's pipeline consumes —
        it must be a plain string usable as MeetingTranscriptInput.
        """
        result = TranscriptionResult(
            meeting_id="mtg-003",
            transcript="Some meeting text.",
        )
        # Simulate handing off to the intelligence feature
        from app.schemas.inputs import MeetingTranscriptInput

        handoff = MeetingTranscriptInput(
            meeting_id=result.meeting_id,
            transcript=result.transcript,
        )
        assert handoff.transcript == "Some meeting text."
