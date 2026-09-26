"""FastAPI server: serves the chat UI and the /api/chat endpoint."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .agent import run_agent
from .config import GEMINI_API_KEY
from . import state

app = FastAPI(title="The Loop — Commerce Copilot")

_INDEX = Path(__file__).with_name("index.html")

SESSION_TTL = 60 * 60 * 2  # seconds


class ChatMessage(BaseModel):
    role: str  # 'user' | 'model'
    text: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ProfileRequest(BaseModel):
    email: str


def _history(session_id: str) -> list[dict[str, str]]:
    return state.SESSIONS.get(session_id, [])


def _save(session_id: str, history: list[dict[str, str]]) -> None:
    state.SESSIONS[session_id] = history[-40:]


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _INDEX.read_text(encoding="utf-8")


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=400,
            detail=(
                "GEMINI_API_KEY is not set. Edit the .env file in the project root "
                "(same folder as app/) and set GEMINI_API_KEY=<your key from "
                "aistudio.google.com/api-keys>, then restart uvicorn."
            ),
        )
    history = _history(req.session_id)
    history.append({"role": "user", "text": req.message})
    try:
        result = run_agent(history)
        reply, events = result["reply"], result["tool_events"]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"agent error: {exc}")
    finally:
        # Keep the user turn even if the agent failed, so retries have context
        _save(req.session_id, history)

    history.append({"role": "model", "text": reply})
    _save(req.session_id, history)

    return {"reply": reply, "tool_events": events}


@app.post("/api/profile")
def profile(req: ProfileRequest) -> dict:
    """Unified customer profile for the side panel (bypasses the agent)."""
    from .profile_tool import resolve_customer

    return resolve_customer(req.email)
