"""
Ollama local AI provider (free, no API key required).
Uses httpx for async HTTP to localhost:11434.
"""
from __future__ import annotations

import os

import httpx

from .base import AIProvider


class OllamaProvider(AIProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self._base_url = (base_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")

    @property
    def display_name(self) -> str:
        return f"Ollama ({self._model})"

    async def chat(self, messages: list[dict], system: str) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
            # Ask Ollama to return valid JSON (supported in llama3.1 and later)
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama no disponible en {self._base_url}. "
                "Instalá Ollama (https://ollama.ai) y ejecutá: ollama serve"
            )
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama devolvió error {exc.response.status_code}: {exc.response.text[:200]}"
            )


async def check_ollama_available(base_url: str = "http://localhost:11434") -> tuple[bool, list[str]]:
    """Check if Ollama is running and return (available, [model_names])."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return True, models
    except Exception:
        pass
    return False, []
