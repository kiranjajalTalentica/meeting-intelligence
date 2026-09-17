# Meeting Intelligence — Backend

AI-powered extraction of structured insights from meeting transcripts.

You give it a meeting transcript (typed, pasted, or produced from audio) and it
returns a **structured summary**: an overall summary, discussion topics,
decisions made, action items, and open questions — as clean, validated JSON.

This document explains the **entire backend implementation** so anyone can
understand how it works, run it, and extend it, without reading the source
first.

---

## Table of Contents

1. [What it does](#1-what-it-does)
2. [Tech stack](#2-tech-stack)
3. [High-level architecture](#3-high-level-architecture)
4. [Project layout](#4-project-layout)
5. [Request flow, end to end](#5-request-flow-end-to-end)
6. [Module-by-module walkthrough](#6-module-by-module-walkthrough)
7. [Data contracts (schemas)](#7-data-contracts-schemas)
8. [Prompts](#8-prompts)
9. [Configuration](#9-configuration)
10. [API reference](#10-api-reference)
11. [Setup & running](#11-setup--running)
12. [Verification scripts & tests](#12-verification-scripts--tests)
13. [Design decisions & rationale](#13-design-decisions--rationale)
14. [Extending the system](#14-extending-the-system)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. What it does

Meetings produce lots of talk but little structured output. Action items get
forgotten, decisions get lost, and unanswered questions slip away. This service
uses an LLM to read a transcript and pull out five things automatically:

| Output | Meaning |
|--------|---------|
| **Summary** | A 3–6 sentence overview of the whole meeting |
| **Topics** | The main things discussed (title + short summary each) |
| **Decisions** | What was decided, why, and a supporting quote |
| **Action items** | Tasks assigned, with owner and deadline if mentioned |
| **Open questions** | Questions raised but never resolved |

There is also a **standalone transcription module** that turns audio files into
text, so you can go from a recording straight to insights.

---

## 2. Tech stack

- **Python 3.12+**
- **FastAPI** — the web framework / API layer
- **Uvicorn** — the ASGI server that runs the app
- **LangChain** — a thin, uniform interface over different LLM providers
- **Pydantic v2** + **pydantic-settings** — data validation and config
- **faster-whisper** — speech-to-text (optional, for audio)
- **pytest** — tests

LLM providers supported (pick one via config):

| Provider | Where it runs | Notes |
|----------|---------------|-------|
| **Groq** (default) | Cloud | Fast LPU inference, generous free tier |
| **Gemini** | Cloud | Google's model, high quality |
| **LM Studio** | Local | Fully offline & private; OpenAI-compatible API |

---

## 3. High-level architecture

The core idea: **preprocess the transcript, then run several independent
extractors in parallel, then merge their results.**

```
                 POST /api/analyze  { meeting_id, transcript }
                                │
                                ▼
                   ┌───────────────────────────┐
                   │  Preprocess                │
                   │  clean + chunk transcript  │
                   └───────────────────────────┘
                                │  (list of chunks)
        ┌───────────────┬───────┼───────┬───────────────┐
        ▼               ▼       ▼       ▼               ▼
    Summary          Topics  Decisions Actions   Open Questions
  (map-reduce)     (extract) (extract) (extract)    (extract)
        │               │       │       │               │
        └───────────────┴───────┼───────┴───────────────┘
                                │  (all run concurrently via asyncio.gather)
                                ▼
                    ┌───────────────────────┐
                    │  Merge into            │
                    │  MeetingInsights (JSON)│
                    └───────────────────────┘
                                │
                                ▼
                         Response to client
```

The **LLM provider is abstracted** — only one file knows which backend is in
use. Everything else just asks for "the LLM" and gets a standard LangChain chat
model back.

---

## 4. Project layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app + CORS + router wiring
│   ├── config.py               # All settings (env-driven) + provider enum
│   ├── pipeline.py             # Orchestrates the analysis (fan-out + merge)
│   │
│   ├── api/
│   │   ├── routes.py               # /analyze, /sample-transcript, /health/llm
│   │   └── transcription_routes.py # /transcribe (audio -> text)
│   │
│   ├── llm/
│   │   ├── provider.py         # get_llm(): the ONLY provider-aware file
│   │   └── extraction.py       # LLM calls + JSON parsing + throttling
│   │
│   ├── preprocessing/
│   │   └── chunker.py          # clean_transcript(), chunk_transcript()
│   │
│   ├── prompts/
│   │   └── __init__.py         # load_prompt(): reads prompts/*.txt
│   │
│   ├── schemas/
│   │   ├── inputs.py           # MeetingTranscriptInput
│   │   └── outputs.py          # Topic, Decision, ActionItem, ... MeetingInsights
│   │
│   └── transcription/
│       ├── transcriber.py      # faster-whisper wrapper (audio -> text)
│       └── schemas.py          # TranscriptionResult, TranscriptSegment
│
├── prompts/                    # Prompt templates as editable .txt files
│   ├── summarization.txt
│   ├── summary_combine.txt
│   ├── topic_detection.txt
│   ├── decision_extraction.txt
│   ├── action_extraction.txt
│   └── open_questions.txt
│
├── data/
│   └── sample_transcript.txt   # Bundled demo transcript
│
├── scripts/
│   ├── verify_llm.py           # Check the LLM connection works
│   ├── run_pipeline.py         # Run the full pipeline on the sample
│   └── verify_transcription.py # Check transcription works
│
├── tests/                      # Unit tests
├── pyproject.toml              # Dependencies & packaging
├── .env.example                # Template for your .env
└── .env                        # Your local config (not committed)
```

---

## 5. Request flow, end to end

Here's exactly what happens when a client calls `POST /api/analyze`:

1. **`main.py`** receives the request and routes it to `analyze_meeting` in
   `api/routes.py`.
2. The request body is validated against **`MeetingTranscriptInput`**
   (`meeting_id` + non-empty `transcript`). Invalid input → 422 automatically.
3. The route calls **`analyze_transcript(meeting_id, transcript)`** in
   `pipeline.py`.
4. **`pipeline.py`**:
   - Gets the configured LLM via `get_llm()`.
   - **Cleans and chunks** the transcript with `chunk_transcript()`.
   - **Loads all six prompt templates** with `load_prompt()`.
   - Kicks off **five tasks concurrently** with `asyncio.gather`:
     - `summarize_chunks(...)` — map-reduce summary
     - four `extract_json_list_from_chunks(...)` calls (topics, decisions,
       actions, questions)
   - Each task runs one LLM call per chunk (also concurrently).
5. **`extraction.py`** handles each LLM call: sends the prompt, gets text back,
   finds and parses a JSON array, validates each item against its Pydantic
   model, and drops anything malformed.
6. **`pipeline.py`** merges everything into a **`MeetingInsights`** object. If
   any single section failed, it logs the error and substitutes an empty result
   (the rest still return).
7. FastAPI serializes `MeetingInsights` to JSON and returns it.

---

## 6. Module-by-module walkthrough

### `app/main.py` — application entry point
Creates the FastAPI app, enables CORS for the Vue frontend (ports 5173/3000),
and mounts two routers under `/api`. Also exposes a plain `GET /health`.

Run it with: `uvicorn app.main:app --reload`

### `app/config.py` — configuration
Defines a Pydantic `Settings` class whose values come from environment
variables or a `.env` file. A module-level singleton `settings` is imported
everywhere. Also defines the `LLMProvider` enum (`lm_studio`, `gemini`,
`groq`). See [Configuration](#9-configuration) for every setting.

### `app/llm/provider.py` — provider abstraction
**The only file that knows which LLM backend is used.** It exposes a single
function:

```python
def get_llm() -> BaseChatModel:
    # returns a LangChain chat model for the configured provider
```

Internally it has `_create_lm_studio()`, `_create_gemini()`, and
`_create_groq()`. To switch providers you change **one env var** —
no other code changes. (For Groq, it also sends a browser-like `User-Agent`
so Cloudflare in front of Groq doesn't block the request.)

### `app/llm/extraction.py` — LLM calls, parsing, throttling
The workhorse for talking to the model. Key pieces:

- **`extract_json_list_from_chunks(llm, prompt, chunks, Model)`** — runs the
  prompt over every chunk concurrently, parses each response as a JSON array,
  validates items against `Model`, merges and de-duplicates them.
- **`summarize_chunks(llm, map_prompt, reduce_prompt, chunks)`** — **map-reduce
  summary**: summarize each chunk, then combine the partial summaries into one.
  For a single chunk it skips the reduce step.
- **`_parse_json_array(text)`** — robustly extracts a JSON array from messy LLM
  output. Handles raw arrays, markdown ```json fences, and surrounding text.
- **`_dedupe_models(items)`** — removes duplicates that come from overlapping
  chunks (compares field values, ignoring `source_reference`).
- **`_throttle()` / `reset_throttle()`** — optional pause between calls to
  respect rate limits. The first call of each run skips the delay (nothing to
  space it from).

> **Why parse JSON ourselves instead of LangChain's `with_structured_output()`?**
> Local models often don't support OpenAI-style function calling. Asking for
> JSON in the prompt and parsing it works with *any* model that can emit JSON.

### `app/preprocessing/chunker.py` — cleaning & chunking
- **`clean_transcript(text)`** — normalizes whitespace and drops blank lines,
  while keeping one speaker turn per line.
- **`chunk_transcript(text)`** — splits long transcripts into overlapping
  chunks (default ~6000 chars, ~400 char overlap), splitting on speaker turns
  so sentences aren't cut mid-way. **Short transcripts skip chunking entirely**
  (a single call). Oversized single turns are hard-split as a fallback.

> **Why chunk?** Sending a full 1-hour transcript to the LLM five times is slow
> and can exceed context limits. Small chunks stay fast; the overlap preserves
> meaning at boundaries.

### `app/prompts/__init__.py` — prompt loading
`load_prompt("summarization")` reads `prompts/summarization.txt` and returns
the template string (with `{placeholders}` ready for `.format()`). Prompts live
as text files so they can be tuned without touching code.

### `app/pipeline.py` — orchestration
`analyze_transcript(meeting_id, transcript)` ties it all together: preprocess →
fan out five concurrent extractors → merge into `MeetingInsights`. Uses
`asyncio.gather(..., return_exceptions=True)` plus an `_ok()` helper so one
failing section doesn't sink the whole response (**graceful degradation**).

> **Why plain async instead of LangGraph?** The workflow has no loops or
> branching — it's just "run N independent extractors and combine." `asyncio`
> expresses that directly, is easier to debug, and drops a dependency.

### `app/api/routes.py` — intelligence endpoints
- `POST /analyze` → runs the pipeline, returns `MeetingInsights`.
- `GET /sample-transcript` → returns the bundled demo transcript (powers the
  UI's "Load Sample" button).
- `GET /health/llm` → sends a tiny prompt to confirm the LLM is reachable;
  reports provider name and a sample reply.

### `app/transcription/` — speech-to-text (standalone & shared)
- **`transcriber.py`** wraps **faster-whisper**. The model is **lazy-loaded and
  cached** (loaded on first use, reused after) to keep idle memory low. It
  writes the uploaded audio to a temp file, transcribes, and cleans up.
- **`schemas.py`** defines the output contract (`TranscriptionResult` with a
  full `transcript` string plus timestamped `segments`).
- **`api/transcription_routes.py`** exposes `POST /transcribe`.

> This module **does not import from the intelligence pipeline** on purpose.
> Its output is designed to feed both this feature (via `transcript`) and a
> future Q&A/RAG feature (via timestamped `segments`). Neither owns it.

---

## 7. Data contracts (schemas)

### Input — `app/schemas/inputs.py`

```python
class MeetingTranscriptInput(BaseModel):
    meeting_id: str          # unique id for the meeting
    transcript: str          # full transcript text (min_length=1)
```

### Output — `app/schemas/outputs.py`

```python
class Topic(BaseModel):
    title: str
    summary: str

class Decision(BaseModel):
    decision: str
    reason: str = ""
    source_reference: str = ""      # supporting quote from the transcript

class ActionItem(BaseModel):
    task: str
    owner: str = ""
    deadline: str = ""
    source_reference: str = ""

class OpenQuestion(BaseModel):
    question: str
    context: str = ""

class MeetingInsights(BaseModel):        # top-level API response
    meeting_id: str
    summary: str
    topics: list[Topic]
    decisions: list[Decision]
    action_items: list[ActionItem]
    open_questions: list[OpenQuestion]
```

### Transcription — `app/transcription/schemas.py`

```python
class TranscriptSegment(BaseModel):
    start: float             # seconds
    end: float               # seconds
    text: str

class TranscriptionResult(BaseModel):
    meeting_id: str
    transcript: str          # full text (Intelligence consumes this)
    language: str = ""
    duration: float = 0.0
    segments: list[TranscriptSegment]    # timestamped (RAG consumes this)
```

### Example `MeetingInsights` response

```json
{
  "meeting_id": "mtg-001",
  "summary": "The team reviewed Q3 progress and agreed on the caching approach...",
  "topics": [
    { "title": "Caching Strategy", "summary": "Discussed Redis vs in-memory." }
  ],
  "decisions": [
    { "decision": "Use Redis for caching", "reason": "Better at scale",
      "source_reference": "Alice: let's go with Redis" }
  ],
  "action_items": [
    { "task": "Write auth unit tests", "owner": "Bob", "deadline": "Friday",
      "source_reference": "Bob will handle tests by Friday" }
  ],
  "open_questions": [
    { "question": "Who owns the deploy pipeline?", "context": "Deferred to next meeting" }
  ]
}
```

---

## 8. Prompts

Prompts are plain `.txt` files in `backend/prompts/`, loaded by name. Each
extraction prompt contains a `{transcript}` placeholder (the summary-combine
prompt uses `{summaries}`), filled in at runtime with `.format()`.

| File | Used for | Output |
|------|----------|--------|
| `summarization.txt` | Summarize one chunk (map step) | Plain text (2–4 sentences) |
| `summary_combine.txt` | Combine chunk summaries (reduce step) | Plain text (3–6 sentences) |
| `topic_detection.txt` | Find discussion topics | JSON array of `{title, summary}` |
| `decision_extraction.txt` | Extract decisions | JSON array of `{decision, reason, source_reference}` |
| `action_extraction.txt` | Extract tasks | JSON array of `{task, owner, deadline, source_reference}` |
| `open_questions.txt` | Find unresolved questions | JSON array of `{question, context}` |

Each JSON prompt instructs the model to return **only** a valid JSON array (no
markdown, no prose) and gives a worked example. To change behavior, edit the
text file — no code change or redeploy needed.

---

## 9. Configuration

All settings are read from environment variables or a `.env` file (see
`.env.example`). Names below are the env var; the code uses the lowercase form.

### LLM selection
| Env var | Default | Purpose |
|---------|---------|---------|
| `LLM_PROVIDER` | `groq` | `groq` \| `gemini` \| `lm_studio` |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature (lower = more deterministic) |

### LM Studio (local)
| Env var | Default | Purpose |
|---------|---------|---------|
| `LLM_BASE_URL` | `http://localhost:1234/v1` | LM Studio's OpenAI-compatible endpoint |
| `LLM_MODEL_NAME` | `google/gemma-4-e4b` | Model loaded in LM Studio |

### Groq (cloud, default)
| Env var | Default | Purpose |
|---------|---------|---------|
| `GROQ_API_KEY` | *(empty)* | Required when using Groq — get one at console.groq.com/keys |
| `GROQ_MODEL_NAME` | `openai/gpt-oss-20b` | Groq model id |

### Gemini (cloud)
| Env var | Default | Purpose |
|---------|---------|---------|
| `GEMINI_API_KEY` | *(empty)* | Required when using Gemini |
| `GEMINI_MODEL_NAME` | `gemini-flash-latest` | Gemini model id |

### Chunking
| Env var | Default | Purpose |
|---------|---------|---------|
| `CHUNK_SIZE_CHARS` | `6000` | Target chunk size (~1500 tokens) |
| `CHUNK_OVERLAP_CHARS` | `400` | Overlap carried between chunks |
| `CHUNK_THRESHOLD_CHARS` | `6000` | Below this, skip chunking (single call) |

### Rate limiting
| Env var | Default | Purpose |
|---------|---------|---------|
| `LLM_CALL_DELAY` | `0` | Seconds to wait between calls. Raise this (e.g. `13`) for strict free tiers like Gemini; `0` is fine for Groq/local |

### Transcription
| Env var | Default | Purpose |
|---------|---------|---------|
| `WHISPER_MODEL_SIZE` | `base` | `tiny`\|`base`\|`small`\|`medium`\|`large-v3` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` is fastest/lowest-memory on CPU |
| `WHISPER_DEVICE` | `cpu` | `cpu` or `cuda` |

### API
| Env var | Default | Purpose |
|---------|---------|---------|
| `API_HOST` | `0.0.0.0` | Bind host |
| `API_PORT` | `8000` | Bind port |

---

## 10. API reference

Base prefix for feature routes: `/api`

### `GET /health`
Liveness check for the app itself.
```json
{ "status": "ok" }
```

### `GET /api/health/llm`
Confirms the configured LLM is reachable and responding.
```json
{ "status": "connected", "provider": "ChatGroq", "sample_response": "Hello" }
```
Returns **503** if the provider is unreachable or returns nothing.

### `GET /api/sample-transcript`
Returns the bundled demo transcript.
```json
{ "transcript": "..." }
```

### `POST /api/analyze`
**Request:**
```json
{ "meeting_id": "mtg-001", "transcript": "Full meeting text..." }
```
**Response:** a `MeetingInsights` object (see [schemas](#7-data-contracts-schemas)).

### `POST /api/transcribe`
`multipart/form-data`:
- `file` — audio file (wav/mp3/m4a/webm/…)
- `meeting_id` — string

**Response:** a `TranscriptionResult` object. Returns **400** on empty file,
**500** on transcription error.

### Example: curl

```bash
# Analyze a transcript
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"meeting_id":"mtg-001","transcript":"Alice: Let'\''s use Redis..."}'

# Transcribe an audio file
curl -X POST http://localhost:8000/api/transcribe \
  -F "file=@meeting.wav" \
  -F "meeting_id=mtg-001"
```

Interactive docs are available at `http://localhost:8000/docs` (Swagger UI)
once the server is running.

---

## 11. Setup & running

### Prerequisites
- Python 3.12+
- One LLM backend ready:
  - **Groq/Gemini:** an API key, or
  - **LM Studio:** the app running with a model loaded and its server started

### Install

```bash
cd backend
pip install -e ".[dev]"          # core + test deps
# optional extras:
pip install -e ".[gemini]"       # for the Gemini provider
pip install -e ".[transcription]"# for audio transcription (faster-whisper)
```

### Configure

```bash
cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key
```

### Run

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` to try the endpoints, or point the Vue
frontend (port 5173) at it.

---

## 12. Verification scripts & tests

### Scripts (`backend/scripts/`)

```bash
# 1. Confirm the LLM connection works (creates model, sends a prompt,
#    tests JSON extraction)
python scripts/verify_llm.py

# 2. Run the FULL pipeline against the sample transcript and print results
python scripts/run_pipeline.py

# 3. Confirm transcription works (silent-audio smoke test, or a real file)
python scripts/verify_transcription.py [path/to/audio.wav]
```

### Tests (`backend/tests/`)

```bash
pytest            # run everything
pytest -v         # verbose
```

Covered areas: `test_chunker.py`, `test_extraction.py`,
`test_llm_provider.py`, `test_prompts.py`, `test_schemas.py`,
`test_transcription.py`.

---

## 13. Design decisions & rationale

| Decision | Why |
|----------|-----|
| **Provider abstraction** (`get_llm()`) | Swap Groq / Gemini / local with one env var; no vendor lock-in; demo works offline |
| **Prompts as `.txt` files** | Tune AI behavior without code changes or redeploys |
| **Chunking with overlap** | Keeps each LLM call small/fast and under context limits; overlap preserves meaning at boundaries |
| **Hand-rolled JSON parsing** | Works with any model that emits JSON, including local models without function-calling |
| **Parallel fan-out (`asyncio.gather`)** | The workflow is independent extractors + merge; plain async is simpler than LangGraph and drops a dependency |
| **Graceful degradation** (`_ok()`) | A partial result beats a total failure; one broken section doesn't sink the response |
| **First-call throttle skip** | Saves ~one delay per run while still respecting rate limits |
| **De-duplication after merge** | Overlapping chunks can surface the same item twice |
| **Lazy-loaded Whisper model** | Low idle memory; the heavy model loads only when audio is actually transcribed |
| **Transcription kept standalone** | Reusable by both Intelligence and a future Q&A/RAG feature; stable contract |

---

## 14. Extending the system

**Add a new extractor (e.g. "risks"):**
1. Add a `Risk` model to `app/schemas/outputs.py` and a `risks` field on
   `MeetingInsights`.
2. Create `prompts/risk_extraction.txt` returning a JSON array of risks.
3. In `pipeline.py`, load the prompt and add a
   `extract_json_list_from_chunks(...)` task to the `asyncio.gather` call.
4. Add it to the `MeetingInsights(...)` merge at the end.

**Add a new LLM provider:**
1. Add the enum value in `config.py`.
2. Add a `_create_yourprovider()` function in `llm/provider.py` and wire it
   into `get_llm()`.
3. Add any needed settings to `config.py` and `.env.example`.

**Change AI behavior:** edit the relevant file in `prompts/` — no code change.

---

## 15. Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `GET /api/health/llm` returns 503 | Provider unreachable. Groq/Gemini: check API key. LM Studio: is it running with a model loaded and the server started? |
| Empty topics/decisions/etc. | The model didn't return valid JSON for that section — check server logs (parse warnings). Try a stronger model or edit the prompt |
| `GROQ_API_KEY must be set` | Set `GROQ_API_KEY` in `.env` (or switch `LLM_PROVIDER`) |
| `ImportError: langchain-google-genai` | `pip install -e ".[gemini]"` |
| Transcription fails / import error | `pip install -e ".[transcription]"` |
| Very slow runs | On Gemini free tier, `LLM_CALL_DELAY` spaces calls (~60s total). Use Groq or local and set `LLM_CALL_DELAY=0` |
| 422 on `/api/analyze` | Request body missing `meeting_id` or `transcript`, or transcript is empty |
| Non-ASCII characters break console output | `run_pipeline.py` forces UTF-8 stdout; ensure your terminal uses UTF-8 |

---

*This backend is the "Meeting Intelligence" feature. Transcription is a shared
capability; downstream features (embeddings, RAG, Q&A) build on top of the
transcript and segment contracts described above.*
