"""Local vision-language inference through Ollama's native chat API."""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path


class OllamaVLMClient:
    """Vision-capable local model served by Ollama."""

    def __init__(
        self,
        model_id: str,
        base_url: str = "http://127.0.0.1:11434",
        max_tokens: int = 128,
        temperature: float = 0.0,
        timeout: int = 300,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    def answer(self, image_path: str, prompt: str) -> str:
        """Send one image and prompt, retrying one length-exhausted blank."""
        image = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
        last_data: dict = {}
        for attempt in range(2):
            payload = {
                "model": self.model_id,
                "stream": False,
                "think": False,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image],
                    }
                ],
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens * (2**attempt),
                },
            }
            request = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Ollama API error {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"Ollama request failed: {exc}") from exc

            last_data = data
            content = data.get("message", {}).get("content")
            if (
                isinstance(content, str)
                and content.strip()
                and data.get("done_reason") != "length"
            ):
                return content.strip()
            if data.get("done_reason") != "length":
                break

        content = last_data.get("message", {}).get("content", "")
        if last_data.get("done_reason") == "length":
            detail = "length-exhausted response"
        elif last_data.get("message", {}).get("thinking", ""):
            detail = "thinking-only response"
        else:
            detail = "empty response"
        raise RuntimeError(f"Unexpected Ollama {detail}: {content!r}")
