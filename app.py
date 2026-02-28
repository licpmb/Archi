"""
ArchiMate AI Generator — FastAPI application.
"""
from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

load_dotenv()

from ai.base import SYSTEM_PROMPT, parse_ai_response, normalise_payload
from ai.claude_provider import ClaudeProvider
from ai.ollama_provider import OllamaProvider, check_ollama_available
from archimate.exchange_generator import generate_exchange_xml
from archimate.model import (
    ELEMENT_LAYER_MAP,
    RELATIONSHIP_ALIASES,
    VALID_RELATIONSHIP_TYPES,
    ArchiModel,
)
from archimate.xml_generator import generate_archimate_xml

# ---------------------------------------------------------------------------
# Provider initialisation
# ---------------------------------------------------------------------------

def _create_provider():
    # Priority 1: Anthropic Claude (best quality)
    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        return ClaudeProvider(api_key=os.getenv("ANTHROPIC_API_KEY").strip())
    # Priority 2: Ollama Cloud (OLLAMA_API_KEY set)
    ollama_key = os.getenv("OLLAMA_API_KEY", "").strip()
    # Priority 3: Ollama local (no key)
    return OllamaProvider(api_key=ollama_key if ollama_key else None)


AI_PROVIDER = _create_provider()

# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

MAX_HISTORY = 40  # messages to keep per session (20 turns)


@dataclass
class SessionData:
    model: ArchiModel = field(default_factory=ArchiModel)
    history: list[dict] = field(default_factory=list)


SESSIONS: dict[str, SessionData] = {}


def _get_session(session_id: Optional[str]) -> tuple[str, SessionData]:
    if session_id and session_id in SESSIONS:
        return session_id, SESSIONS[session_id]
    new_id = str(uuid.uuid4())
    SESSIONS[new_id] = SessionData()
    return new_id, SESSIONS[new_id]


def _require_session(session_id: str) -> SessionData:
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return SESSIONS[session_id]


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model_name: Optional[str] = None  # rename the ArchiMate model


class ChatResponse(BaseModel):
    session_id: str
    response: str
    added_elements: int
    added_relationships: int
    model_tree: dict
    element_count: int
    relationship_count: int
    provider: str


class RenameRequest(BaseModel):
    session_id: str
    name: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ArchiMate AI Generator",
    description="Generá modelos ArchiMate desde lenguaje natural.",
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.get("/api/status")
async def status():
    """Return current AI provider info and Ollama availability."""
    provider_name = AI_PROVIDER.display_name
    is_ollama = isinstance(AI_PROVIDER, OllamaProvider)
    ollama_available = False
    ollama_models: list[str] = []

    if is_ollama:
        ollama_available, ollama_models = await check_ollama_available(
            base_url=AI_PROVIDER._base_url,
            api_key=AI_PROVIDER._api_key,
        )

    return {
        "provider": provider_name,
        "is_ollama": is_ollama,
        "ollama_available": ollama_available,
        "ollama_models": ollama_models,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id, session = _get_session(req.session_id)

    # Optional model rename
    if req.model_name:
        session.model.name = req.model_name.strip() or session.model.name

    # Build system prompt with current model context
    system = SYSTEM_PROMPT.replace("{model_summary}", session.model.summary())

    # Append user message to history
    session.history.append({"role": "user", "content": req.message})

    # Call AI
    try:
        raw = await AI_PROVIDER.chat(messages=session.history, system=system)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error del proveedor de IA: {exc}")

    # Parse AI response
    payload = normalise_payload(parse_ai_response(raw))

    # Append assistant reply to history (use the response text for context)
    session.history.append({"role": "assistant", "content": payload["response"] or raw})

    # Prune history
    if len(session.history) > MAX_HISTORY:
        session.history = session.history[-MAX_HISTORY:]

    # Apply model changes
    added_elements = 0
    added_relationships = 0

    if payload["action"] == "add":
        # Build temp_id → real element mapping for this batch
        temp_to_elem: dict[str, object] = {}

        for el_data in payload["elements"]:
            name = str(el_data.get("name", "")).strip()
            el_type = str(el_data.get("type", "")).strip()
            temp_id = str(el_data.get("temp_id", "")).strip()
            doc = str(el_data.get("documentation", "")).strip()

            if not name or not el_type:
                continue

            # Normalise type (strip prefix if AI adds "archimate:")
            el_type = el_type.split(":")[-1]
            if el_type not in ELEMENT_LAYER_MAP:
                continue  # unknown type → skip silently

            elem, is_new = session.model.add_element(name, el_type, doc)
            if is_new:
                added_elements += 1
            if temp_id:
                temp_to_elem[temp_id] = elem

        for rel_data in payload["relationships"]:
            rel_type = str(rel_data.get("type", "")).strip()
            src_tmp = str(rel_data.get("source_temp_id", "")).strip()
            tgt_tmp = str(rel_data.get("target_temp_id", "")).strip()
            rel_name = str(rel_data.get("name", "")).strip()

            if not rel_type:
                continue

            # Normalise relationship type
            rel_type = RELATIONSHIP_ALIASES.get(rel_type, rel_type)
            rel_type = RELATIONSHIP_ALIASES.get(rel_type.replace("Relationship", ""), rel_type)
            if rel_type not in VALID_RELATIONSHIP_TYPES:
                rel_type = "AssociationRelationship"

            # Resolve source / target
            src_elem = temp_to_elem.get(src_tmp)
            tgt_elem = temp_to_elem.get(tgt_tmp)

            # Fall back to name-based lookup for cross-turn references
            if src_elem is None:
                src_name = str(rel_data.get("source_name", src_tmp)).strip()
                src_elem = session.model.find_element_by_name(src_name)
            if tgt_elem is None:
                tgt_name = str(rel_data.get("target_name", tgt_tmp)).strip()
                tgt_elem = session.model.find_element_by_name(tgt_name)

            if src_elem is None or tgt_elem is None:
                continue

            _, is_new = session.model.add_relationship(
                rel_type, src_elem.id, tgt_elem.id, rel_name
            )
            if is_new:
                added_relationships += 1

    return ChatResponse(
        session_id=session_id,
        response=payload["response"],
        added_elements=added_elements,
        added_relationships=added_relationships,
        model_tree=session.model.to_tree(),
        element_count=len(session.model.elements),
        relationship_count=len(session.model.relationships),
        provider=AI_PROVIDER.display_name,
    )


@app.get("/api/session/{session_id}/archimate")
async def download_archimate(session_id: str):
    """Download the Archi 4.x .archimate file."""
    session = _require_session(session_id)
    xml = generate_archimate_xml(session.model)
    filename = session.model.name.replace(" ", "_") + ".archimate"
    return Response(
        content=xml.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/session/{session_id}/exchange")
async def download_exchange(session_id: str):
    """Download the Open Exchange Format .xml file."""
    session = _require_session(session_id)
    xml = generate_exchange_xml(session.model)
    filename = session.model.name.replace(" ", "_") + "_exchange.xml"
    return Response(
        content=xml.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/session/{session_id}/model")
async def get_model(session_id: str):
    session = _require_session(session_id)
    return {
        "name": session.model.name,
        "tree": session.model.to_tree(),
        "element_count": len(session.model.elements),
        "relationship_count": len(session.model.relationships),
    }


@app.post("/api/session/{session_id}/rename")
async def rename_model(session_id: str, req: RenameRequest):
    session = _require_session(session_id)
    session.model.name = req.name.strip() or session.model.name
    return {"name": session.model.name}


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    SESSIONS.pop(session_id, None)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
