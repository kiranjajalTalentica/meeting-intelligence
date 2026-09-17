"""
Transcript preprocessing and chunking.

Why this exists:
- Sending a full 1-hour transcript to the LLM 5 times is slow and can
  blow past context limits. Instead we clean the text and split it into
  smaller, overlapping chunks that each process fast.
- Chunks are split on speaker-turn boundaries where possible so we never
  cut a sentence mid-way, which keeps extraction quality high.

The two public functions:
- clean_transcript(text): normalize whitespace, drop empty lines.
- chunk_transcript(text): return a list of overlapping text chunks.
"""

import re

from app.config import settings


def clean_transcript(text: str) -> str:
    """
    Normalize a raw transcript.

    - Strips leading/trailing whitespace.
    - Collapses runs of blank lines into a single newline.
    - Collapses runs of spaces/tabs into a single space per line.

    Keeps speaker turns (one per line) intact so downstream chunking
    can split on them.
    """
    if not text:
        return ""

    lines = []
    for raw_line in text.splitlines():
        # Collapse internal whitespace but keep the line's content
        collapsed = re.sub(r"[ \t]+", " ", raw_line).strip()
        if collapsed:
            lines.append(collapsed)

    return "\n".join(lines)


def _split_into_turns(text: str) -> list[str]:
    """
    Split cleaned transcript into speaker turns (one per line).

    Falls back to treating the whole text as a single unit if there
    are no line breaks.
    """
    turns = [line for line in text.split("\n") if line.strip()]
    return turns if turns else [text]


def chunk_transcript(text: str) -> list[str]:
    """
    Split a transcript into overlapping chunks sized by character count.

    Short transcripts (below the configured threshold) are returned as a
    single chunk — no need to split, avoids extra LLM calls.

    Longer transcripts are packed turn-by-turn into chunks up to
    `chunk_size_chars`, with `chunk_overlap_chars` of trailing context
    carried into the next chunk so nothing is lost at boundaries.

    Returns a list of chunk strings (always at least one).
    """
    cleaned = clean_transcript(text)
    if not cleaned:
        return [""]

    # Small transcript: no chunking needed.
    if len(cleaned) <= settings.chunk_threshold_chars:
        return [cleaned]

    size = settings.chunk_size_chars
    overlap = settings.chunk_overlap_chars

    turns = _split_into_turns(cleaned)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for turn in turns:
        turn_len = len(turn) + 1  # +1 for the newline join

        # If a single turn is larger than the chunk size, hard-split it.
        if turn_len > size:
            if current:
                chunks.append("\n".join(current))
                current, current_len = [], 0
            for i in range(0, len(turn), size):
                chunks.append(turn[i : i + size])
            continue

        # Would adding this turn overflow the chunk? Close it out first.
        if current_len + turn_len > size and current:
            chunks.append("\n".join(current))
            # Start the next chunk with an overlap tail of the previous one.
            tail = _overlap_tail(current, overlap)
            current = list(tail)
            current_len = sum(len(t) + 1 for t in current)

        current.append(turn)
        current_len += turn_len

    if current:
        chunks.append("\n".join(current))

    return chunks if chunks else [cleaned]


def _overlap_tail(turns: list[str], overlap_chars: int) -> list[str]:
    """
    Return the trailing turns of a chunk that fit within overlap_chars.

    Used to seed the next chunk with a bit of prior context so extraction
    doesn't lose meaning at a boundary.
    """
    tail: list[str] = []
    total = 0
    for turn in reversed(turns):
        total += len(turn) + 1
        if total > overlap_chars:
            break
        tail.insert(0, turn)
    return tail
