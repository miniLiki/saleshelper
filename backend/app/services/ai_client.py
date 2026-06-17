import hashlib
import json
import math
from typing import Any

import httpx

from app.core.config import settings


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.openai_api_key:
        headers["Authorization"] = f"Bearer {settings.openai_api_key}"
    return headers


def deterministic_embedding(text: str, dimensions: int | None = None) -> list[float]:
    dims = dimensions or settings.embedding_dimension
    vector = [0.0] * dims
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dims
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def embed_text(text: str) -> list[float]:
    if not settings.enable_external_ai or not settings.openai_api_key:
        return deterministic_embedding(text)
    url = f"{settings.openai_base_url.rstrip('/')}/embeddings"
    try:
        response = httpx.post(
            url,
            headers=_headers(),
            json={"model": settings.embedding_model, "input": text[:8000]},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload["data"][0]["embedding"]
        return [float(value) for value in embedding]
    except Exception:
        return deterministic_embedding(text)


def chat_json(system_prompt: str, user_prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
    if not settings.enable_external_ai or not settings.openai_api_key:
        return fallback
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    model = settings.llm_model or settings.chat_model
    try:
        response = httpx.post(
            url,
            headers=_headers(),
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return fallback


def chat_text(system_prompt: str, user_prompt: str, fallback: str) -> str:
    if not settings.enable_external_ai or not settings.openai_api_key:
        return fallback
    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    model = settings.llm_model or settings.chat_model
    try:
        response = httpx.post(
            url,
            headers=_headers(),
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return fallback
