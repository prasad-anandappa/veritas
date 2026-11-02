"""FastAPI app for Veritas: REST API + one self-contained web UI page."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import ResearchAgent
from .config import load_settings
from .models import ResearchReport

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

EXAMPLE_QUESTIONS = [
    "What is the current state of solid-state batteries for electric vehicles?",
    "How close is fusion energy to powering the grid?",
    "What are the benefits and risks of GLP-1 drugs for weight loss?",
    "Why do research agents need verification passes?",
]

app = FastAPI(title="Veritas — Sourced Research Agent", version="1.0.0")


def get_agent() -> ResearchAgent:
    return ResearchAgent(load_settings())


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=600)


@app.get("/api/health")
def health() -> dict:
    settings = load_settings()
    return {"ok": True, **settings.mode_detail()}


@app.get("/api/examples")
def examples() -> dict:
    return {"examples": EXAMPLE_QUESTIONS}


@app.post("/api/research", response_model=ResearchReport)
def research(req: ResearchRequest) -> ResearchReport:
    return get_agent().run(req.question.strip())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
