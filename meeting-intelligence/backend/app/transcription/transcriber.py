"""
Speech-to-Text transcription using faster-whisper.

This is a STANDALONE module — it does not import from the meeting
intelligence pipeline. Its only job is: audio bytes -> transcript.

Design notes:
- The Whisper model is LAZY-LOADED and cached. It's only loaded into
  memory the first time transcription is requested, then reused. This
  keeps idle memory low (important on modest hardware).
- Model size / device / compute type are configurable via settings so
  you can start tiny (CPU-friendly) and scale up later.
- faster-whisper (CTranslate2) is much lighter than the original Whisper.
"""

import logging
import tempfile
from pathlib import Path

from app.config import settings
from app.transcription.schemas import (
    TranscriptSegment,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)

# Module-level cache for the loaded model (loaded once, reused).
_model = None


def _get_model():
    """
    Lazily load and cache the Whisper model.

    The first call downloads the model weights (if not cached by
    huggingface) and loads them into memory. Subsequent calls reuse it.
    """
    global _model
    if _model is None:
        # Import here so the heavy dependency only loads when needed
        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model: size=%s device=%s compute=%s",
            settings.whisper_model_size,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe_audio(
    audio_bytes: bytes,
    meeting_id: str,
    filename_suffix: str = ".wav",
) -> TranscriptionResult:
    """
    Transcribe audio bytes into a structured TranscriptionResult.

    Args:
        audio_bytes: Raw audio file content (wav/mp3/m4a/etc.).
        meeting_id: Identifier to attach to the result.
        filename_suffix: File extension hint for the temp file.

    Returns:
        A TranscriptionResult with the full transcript and segments.

    This writes the audio to a temp file (faster-whisper reads from a
    path), runs transcription, then cleans up the temp file.
    """
    model = _get_model()

    # faster-whisper reads from a file path, so write bytes to a temp file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=filename_suffix
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Run transcription. `segments` is a generator — iterating it
        # is what actually performs the work.
        segments_gen, info = model.transcribe(tmp_path, beam_size=1)

        segments: list[TranscriptSegment] = []
        text_parts: list[str] = []
        for seg in segments_gen:
            segments.append(
                TranscriptSegment(
                    start=round(seg.start, 2),
                    end=round(seg.end, 2),
                    text=seg.text.strip(),
                )
            )
            text_parts.append(seg.text.strip())

        transcript = " ".join(text_parts).strip()

        logger.info(
            "Transcribed %.1fs of audio into %d segments",
            info.duration,
            len(segments),
        )

        return TranscriptionResult(
            meeting_id=meeting_id,
            transcript=transcript,
            language=info.language or "",
            duration=round(info.duration, 2),
            segments=segments,
        )
    finally:
        # Always clean up the temp file
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
