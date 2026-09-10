"""
FastAPI Application Entry Point.

Run with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.transcription_routes import router as transcription_router
from app.config import settings

app = FastAPI(
    title="Meeting Intelligence API",
    description="Extracts structured insights from meeting transcripts",
    version="0.1.0",
)

# Allow the Vue frontend (typically on port 5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(transcription_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
