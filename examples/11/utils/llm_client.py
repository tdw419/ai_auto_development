#!/usr/bin/env python3
"""
Lightweight LM client used by remediation and judges.
Falls back to deterministic responses when LM Studio is unavailable.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests

from utils.intelligent_cache import get_cache

LM_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
DEFAULT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5-7b-instruct")


class LLMClient:
    """Simple wrapper around LM Studio HTTP API with graceful fallbacks."""

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_MODEL
        self.cache = get_cache()

    def generate_text_response(
        self,
        prompt: str,
        *,
        system_message: str = "You are a helpful assistant.",
        temperature: float = 0.2,
    ) -> str:
        """Return raw text response (no automatic JSON parsing)."""
        cache_prompt = self._compose_cache_prompt(system_message, prompt, "text")
        cached = self.cache.get_llm_response(cache_prompt, self.model, temperature)
        if cached is not None:
            return cached if isinstance(cached, str) else cached.get("content", "")

        try:
            content = self._invoke_model(prompt, system_message, temperature, response_format=None)
            self.cache.store_llm_response(cache_prompt, self.model, temperature, content)
            return content
        except Exception:
            # Propagate to structured fallback for consistency with prior behaviour.
            return "LLM unavailable. Please try again later."

    def generate_structured_response(
        self,
        prompt: str,
        system_message: str = "You are a helpful assistant.",
        response_format: str = "json",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Invoke LM Studio and return parsed JSON; fallback to template."""
        cache_prompt = self._compose_cache_prompt(system_message, prompt, response_format)
        cached = self.cache.get_llm_response(cache_prompt, self.model, temperature)
        if cached is not None:
            return cached if isinstance(cached, dict) else cached

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"} if response_format == "json" else None,
        }

        try:
            response = requests.post(LM_URL, json=payload, timeout=120)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            self.cache.store_llm_response(cache_prompt, self.model, temperature, parsed)
            return parsed
        except Exception:
            # Provide deterministic fallback so pipeline keeps running.
            return {
                "fallback": True,
                "summary": "LLM unavailable, generated fallback response.",
                "confidence": 0.3,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _compose_cache_prompt(self, system_message: str, user_prompt: str, response_format: str | None) -> str:
        payload = {
            "system": system_message,
            "user": user_prompt,
            "response_format": response_format or "text",
        }
        return json.dumps(payload, sort_keys=True)

    def _invoke_model(
        self,
        prompt: str,
        system_message: str,
        temperature: float,
        *,
        response_format: str | None,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = requests.post(LM_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
