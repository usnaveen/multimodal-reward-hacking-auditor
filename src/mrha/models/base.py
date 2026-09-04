"""VLM client protocol shared by MLX and API backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class VLMClient(Protocol):
    """Minimal interface: answer a chart-VQA prompt given an image path."""

    model_id: str

    def answer(self, image_path: str, prompt: str) -> str:
        """Return model text answer for (image, prompt)."""
        ...


def build_prompt(question: str, caption: str | None = None, prefix: str | None = None) -> str:
    """Compose the user prompt with optional caption / CoT prefix.

    Instructs models to answer as ``Answer: <value>`` for structured parsing.
    """
    parts: list[str] = []
    if prefix:
        parts.append(prefix.strip())
    if caption:
        parts.append(f"Chart caption: {caption}")
    parts.append(f"Question: {question}")
    parts.append(
        "Respond with exactly one line in the form: Answer: <value> "
        "where <value> is the category name, number, trend word, or "
        "'unanswerable' if the chart evidence is insufficient."
    )
    return "\n".join(parts)
