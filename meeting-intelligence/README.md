# Meeting Intelligence

AI-powered extraction of structured insights from meeting transcripts.
Part of the Meeting AI Agent learning project (Person 1's feature).

## Architecture

```
meeting-intelligence/
├── backend/          # Python — FastAPI + LangChain + LangGraph
│   ├── app/          # Application code
│   ├── prompts/      # Prompt templates as .txt files (editable without code changes)
│   ├── scripts/      # Utility scripts (verify LLM, run pipeline)
│   ├── tests/        # Unit tests
│   └── data/         # Sample transcripts
└── frontend/         # Vue 3 + TypeScript — UI
```

## LLM Providers

| Provider | Model | Use Case |
|----------|-------|----------|
| LM Studio (Local) | google/gemma-4-e4b | Offline, private, free |
| Google Gemini (Cloud) | gemini-2.5-flash | Fast, high quality |

Switch with one env var: `LLM_PROVIDER=lm_studio` or `LLM_PROVIDER=gemini`

## Quick Start

### Backend

```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env       # adjust settings if needed
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Scripts

```bash
# Verify LLM connection
python scripts/verify_llm.py

# Run full pipeline against sample transcript
python scripts/run_pipeline.py
```

## API

- `GET /health` — App health check
- `GET /api/health/llm` — LLM connection check
- `GET /api/sample-transcript` — Returns the bundled sample transcript
- `POST /api/analyze` — Analyze a meeting transcript
- `POST /api/transcribe` — Audio file → transcript (shared, see below)

## Transcription (Phase 8) — Shared Module

Speech-to-text using faster-whisper. This is a **standalone, shared**
capability — its output feeds BOTH Person 1 (Intelligence) and Person 2
(Q&A / RAG). Neither feature owns it.

### Contract

Request: `POST /api/transcribe` (multipart/form-data)
- `file`: audio file (wav/mp3/m4a/etc.)
- `meeting_id`: string

Response (`TranscriptionResult`):
```json
{
  "meeting_id": "mtg-001",
  "transcript": "Full transcript text...",   // Person 1 consumes this
  "language": "en",
  "duration": 123.4,
  "segments": [                                // Person 2 / RAG consumes this
    { "start": 0.0, "end": 2.5, "text": "..." }
  ]
}
```

- **Person 1** takes `transcript` and posts it to `/api/analyze`.
- **Person 2** can chunk `segments` (with timestamps) for RAG citations,
  or use `transcript` for full context.

### Config (in .env)

```env
WHISPER_MODEL_SIZE=base      # tiny | base | small | medium | large-v3
WHISPER_COMPUTE_TYPE=int8    # int8 is lightest on CPU
WHISPER_DEVICE=cpu           # cpu | cuda
```

Start with `base` on CPU (laptop-friendly). Scale up for better accuracy.

### Verify

```bash
# Smoke test (silent audio, proves it runs):
python scripts/verify_transcription.py

# With a real audio file:
python scripts/verify_transcription.py path/to/audio.wav
```

## Development Phases

1. ~~Phase 1 — Project setup~~
2. ~~Phase 2 — LLM connection + provider abstraction~~
3. ~~Phase 3 — Structured extraction with Pydantic~~
4. ~~Phase 4 — LangGraph workflow~~
5. ~~Phase 5 — Vue UI wired to backend~~

**Complete and verified end-to-end** with the Gemini provider — transcript
in, structured insights out, rendered in the Vue UI.

## Running the full app

Terminal 1 (backend):
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

Open http://localhost:5173, click "Load Sample", then "Process Meeting".

Note: on the Gemini free tier a full run takes ~60s because of the request
throttle (`LLM_CALL_DELAY` in .env). Set it to 0 for local LM Studio.

## Future work (other people / later phases, out of scope here)

Per the PRD, these build on top of this feature:
- Phase 8 — Audio → transcript (Faster-Whisper)
- Phase 9 — Real-time meeting capture
- Embeddings, RAG, Q&A, guardrails, agents, Confluence integration
