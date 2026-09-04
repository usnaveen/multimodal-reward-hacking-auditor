"""MLX / mlx-vlm backend for Apple Silicon (optional dependency)."""

from __future__ import annotations

from typing import Any


class MLXVLMClient:
    """Local VLM via mlx-vlm. Raises ImportError with install hints if missing.

    Intended for 48GB Apple Silicon machines. Example model ids:
      - mlx-community/Qwen2-VL-7B-Instruct-4bit
      - mlx-community/Qwen2.5-VL-7B-Instruct-4bit
    """

    def __init__(
        self,
        model_id: str = "mlx-community/Qwen2-VL-7B-Instruct-4bit",
        max_tokens: int = 128,
        temperature: float = 0.0,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._model: Any = None
        self._processor: Any = None
        self._config: Any = None
        self._load()

    def _load(self) -> None:
        try:
            from mlx_vlm import load  # type: ignore
            from mlx_vlm.utils import load_config  # type: ignore
        except ImportError as e:  # pragma: no cover - exercised on Linux CI
            raise ImportError(
                "mlx-vlm is required for MLXVLMClient.\n"
                "Install on Apple Silicon (Python 3.11+):\n"
                "  pip install mlx mlx-vlm\n"
                "Then download a model, e.g.:\n"
                "  python -c \"from mlx_vlm import load; load("
                "'mlx-community/Qwen2-VL-7B-Instruct-4bit')\"\n"
                "Note: 8GB M1 is insufficient for 7B; use a 48GB machine."
            ) from e
        self._model, self._processor = load(self.model_id)
        try:
            self._config = load_config(self.model_id)
        except Exception:
            self._config = None

    def answer(self, image_path: str, prompt: str) -> str:
        """Generate an answer with mlx-vlm."""
        from mlx_vlm import generate  # type: ignore
        from mlx_vlm.prompt_utils import apply_chat_template  # type: ignore
        from mlx_vlm.utils import load_image  # type: ignore

        image = load_image(image_path)
        formatted = apply_chat_template(
            self._processor, self._config, prompt, num_images=1
        )
        result = generate(
            self._model,
            self._processor,
            formatted,
            image,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            verbose=False,
        )
        # mlx-vlm may return str or object with .text
        if isinstance(result, str):
            return result.strip()
        text = getattr(result, "text", None) or getattr(result, "output", None)
        return str(text or result).strip()
