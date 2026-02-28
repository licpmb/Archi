"""
Ollama AI provider — soporta tanto Ollama local como Ollama Cloud.

Local (gratis, sin internet):
    - URL: http://localhost:11434
    - Sin API key
    - Instalar desde https://ollama.ai, luego: ollama pull llama3.1 && ollama serve

Cloud (ollama.com, sin instalar nada):
    - URL: https://api.ollama.com
    - Requiere OLLAMA_API_KEY
    - Crear clave en https://ollama.com/settings/keys
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
        api_key: str | None = None,
    ) -> None:
        self._model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self._api_key = (api_key or os.getenv("OLLAMA_API_KEY", "")).strip()

        # Si hay API key → usar cloud por defecto; si no → localhost
        if self._api_key:
            default_url = "https://api.ollama.com"
        else:
            default_url = "http://localhost:11434"

        self._base_url = (
            base_url or os.getenv("OLLAMA_URL", default_url)
        ).rstrip("/")

    @property
    def display_name(self) -> str:
        suffix = "Cloud" if self._api_key else "local"
        return f"Ollama {suffix} ({self._model})"

    @property
    def is_cloud(self) -> bool:
        return bool(self._api_key)

    async def chat(self, messages: list[dict], system: str) -> str:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                *messages,
            ],
        }

        # Opciones específicas de Ollama local (el cloud las ignora o da error)
        if not self._api_key:
            payload["format"] = "json"
            payload["options"] = {
                "temperature": 0.2,
                "num_ctx": 8192,
            }

        endpoint = f"{self._base_url}/api/chat"
        timeout = 120.0

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]

        except httpx.ConnectError:
            if self.is_cloud:
                raise RuntimeError(
                    f"No se pudo conectar a Ollama Cloud ({self._base_url}). "
                    "Verificá tu conexión a internet y que la URL sea correcta."
                )
            raise RuntimeError(
                f"Ollama local no disponible en {self._base_url}. "
                "Instalá Ollama (https://ollama.ai) y ejecutá: ollama serve"
            )

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            body = exc.response.text[:300]
            if code == 401:
                raise RuntimeError(
                    "API key de Ollama inválida o expirada. "
                    "Verificá OLLAMA_API_KEY en tu archivo .env"
                )
            if code == 404:
                raise RuntimeError(
                    f"Modelo '{self._model}' no encontrado en Ollama. "
                    "Probá con llama3.1, mistral o qwen2.5"
                )
            raise RuntimeError(f"Ollama devolvió error {code}: {body}")


async def check_ollama_available(
    base_url: str = "http://localhost:11434",
    api_key: str = "",
) -> tuple[bool, list[str]]:
    """Check if Ollama is reachable and return (available, [model_names])."""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return True, models
    except Exception:
        pass
    return False, []
