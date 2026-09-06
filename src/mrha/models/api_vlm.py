"""Optional OpenAI / Gemini-compatible API stub behind VLMClient."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


class APIVLMClient:
    """Minimal HTTP client for OpenAI-compatible multimodal chat APIs.

    Set MRHA_API_KEY (or pass api_key). Defaults to OpenAI-compatible
    /v1/chat/completions. This is a stub for Phase A — prefer MLX locally.
    """

    def __init__(
        self,
        model_id: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        max_tokens: int = 128,
        temperature: float = 0.0,
    ) -> None:
        self.model_id = model_id
        self.api_key = api_key or os.environ.get("MRHA_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

    def answer(self, image_path: str, prompt: str) -> str:
        """Call chat completions with a data-URL image."""
        if not self.api_key:
            raise RuntimeError(
                "APIVLMClient requires MRHA_API_KEY or OPENAI_API_KEY."
            )
        raw = Path(image_path).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        payload = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{b64}"
                            },
                        },
                    ],
                }
            ],
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"API VLM request failed: {e}") from e
        return data["choices"][0]["message"]["content"].strip()
