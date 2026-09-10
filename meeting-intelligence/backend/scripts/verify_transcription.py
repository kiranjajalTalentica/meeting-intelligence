"""
Transcription Verification Script.

Verifies the faster-whisper transcription module loads and runs.

Usage:
    # With your own audio file:
    python scripts/verify_transcription.py path/to/audio.wav

    # Without an argument, it generates a short silent WAV just to
    # confirm the model loads and runs end-to-end (output will be empty).

Note: The first run downloads the Whisper model weights (base ~140MB).
This is a one-time download, cached by huggingface for future runs.
"""

import sys
import wave
import struct
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.transcription.transcriber import transcribe_audio


def make_silent_wav(seconds: float = 1.0) -> bytes:
    """Generate a short silent WAV file as bytes (for a smoke test)."""
    frames = int(16000 * seconds)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        path = tmp.name
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        for _ in range(frames):
            w.writeframes(struct.pack("<h", 0))
    data = Path(path).read_bytes()
    Path(path).unlink(missing_ok=True)
    return data


def main():
    print("=" * 60)
    print("Transcription Verification")
    print("=" * 60)

    if len(sys.argv) > 1:
        audio_path = Path(sys.argv[1])
        if not audio_path.exists():
            print(f"File not found: {audio_path}")
            sys.exit(1)
        print(f"Transcribing: {audio_path}")
        audio_bytes = audio_path.read_bytes()
        suffix = audio_path.suffix or ".wav"
    else:
        print("No audio file given — generating a 1s silent WAV smoke test.")
        print("(Expect an empty transcript; this just proves it runs.)")
        audio_bytes = make_silent_wav()
        suffix = ".wav"

    print("\nLoading model + transcribing (first run downloads weights)...")
    result = transcribe_audio(
        audio_bytes=audio_bytes,
        meeting_id="verify-001",
        filename_suffix=suffix,
    )

    print("\n--- Result ---")
    print(f"Language:  {result.language}")
    print(f"Duration:  {result.duration}s")
    print(f"Segments:  {len(result.segments)}")
    print(f"Transcript: {result.transcript!r}")
    print("\nOK — transcription module works.")


if __name__ == "__main__":
    main()
