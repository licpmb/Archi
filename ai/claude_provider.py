"""
Anthropic Claude AI provider.
"""
from __future__ import annotations

import asyncio
import os

import anthropic

from .base import AIProvider


class ClaudeProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        model: str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    @property
    def display_name(self) -> str:
        return f"Claude ({self._model})"

    async def chat(self, messages: list[dict], system: str) -> str:
        # Run the synchronous Anthropic client in a thread so we don't block
        def _call() -> str:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=messages,
            )
            return response.content[0].text

        return await asyncio.to_thread(_call)
