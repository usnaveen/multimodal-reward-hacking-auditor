"""Anthropic Claude backend using the Messages API (no external deps)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


class AnthropicVLMClient:
    """Vision-capable Claude client via Anthropic Messages API.

    Works with Walmart's Anthropic gateway (ANTHROPIC_BASE_URL) or
    direct Anthropic (api.anthropic.com). Uses ANTHROPIC_AUTH_TOKEN
    or ANTHROPIC_API_KEY for auth. Zero extra pip installs — pure stdlib.

    Example:
        client = AnthropicVLMClient(model_id="claude-haiku-4-5")
        ans = client.answer("/path/chart.png", "Which bar is tallest?")
    """

    DEFAULT_BASE_URL = "https://api.anthropic.com"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(
        self,
        model_id: str = "claude-haiku-4-5",
        api_key: str | None = None,
        base_url: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.0,
    ) -> None:
        self.model_id = model_id
        self.api_key = (
            api_key
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("MRHA_API_KEY")
        )
        raw_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or self.DEFAULT_BASE_URL
        self.base_url = raw_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_key:
            raise RuntimeError(
                "AnthropicVLMClient requires ANTHROPIC_AUTH_TOKEN, "
                "ANTHROPIC_API_KEY, or MRHA_API_KEY."
            )

    def answer(self, image_path: str, prompt: str) -> str:
        """Send a chart image + prompt to Claude; return the text reply."""
        raw = Path(image_path).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"

        payload = {
            "model": self.model_id,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": b64,
                            },
                        },
                    ],
                }
            ],
        }
        if self.temperature != 0.0:
            payload["temperature"] = self.temperature

        req = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Anthropic API request failed: {e}") from e

        # Extract text from first content block
        content = data.get("content", [])
        if content and content[0].get("type") == "text":
            return content[0]["text"].strip()
        return str(content).strip()
