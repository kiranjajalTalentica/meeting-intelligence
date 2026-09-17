"""
Tests for transcript preprocessing and chunking.
"""

from app.config import settings
from app.preprocessing import clean_transcript, chunk_transcript


class TestCleanTranscript:
    def test_collapses_blank_lines_and_spaces(self):
        raw = "Alice:   hello\n\n\nBob:\tworld  "
        cleaned = clean_transcript(raw)
        assert cleaned == "Alice: hello\nBob: world"

    def test_empty_input(self):
        assert clean_transcript("") == ""


class TestChunkTranscript:
    def test_short_transcript_single_chunk(self):
        text = "Alice: hi\nBob: hello"
        chunks = chunk_transcript(text)
        assert len(chunks) == 1

    def test_long_transcript_splits(self):
        # Build a transcript well over the threshold.
        line = "Speaker: " + ("word " * 20) + "\n"
        big = line * 200  # ~ tens of thousands of chars
        chunks = chunk_transcript(big)
        assert len(chunks) > 1
        # Every chunk should be within a reasonable bound of chunk size.
        for c in chunks:
            assert len(c) <= settings.chunk_size_chars + settings.chunk_overlap_chars + 50

    def test_always_returns_at_least_one_chunk(self):
        assert len(chunk_transcript("")) == 1
