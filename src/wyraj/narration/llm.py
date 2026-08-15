"""LLMNarrator — optional AI garnish over the template narrator (spec §5.3).

Hard contract:
- **Cosmetic only.** The LLM never touches game state and never sees anything
  but already-resolved facts. Gameplay determinism is untouched (the default
  TemplateNarrator remains the only narrator in tests and golden runs).
- **Grounded.** The prompt carries the mechanical facts and the deterministic
  template rendering as ground truth; the model may only rephrase, never
  invent entities, numbers, or outcomes.
- **Bounded.** One request per turn with a strict timeout; any error, timeout,
  or empty/oversized reply falls back to the template text. Output is capped.
- **Off by default.** Enabled via config (`narrator: llm`) or `--narrator llm`.
"""

import os
import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from wyraj.core.events import GameEvent
from wyraj.narration.engine import NarrationLine
from wyraj.narration.templates import NO_TAGS, TemplateNarrator

MAX_WORDS = 60
DEFAULT_TIMEOUT = 2.5
RECENT_LINES = 4


class LLMError(RuntimeError):
    pass


class LLMBackend(Protocol):
    name: str

    def complete(self, prompt: str, timeout: float) -> str: ...


class OllamaBackend:
    """Local Ollama, `/api/generate` (non-streaming)."""

    def __init__(
        self,
        model: str = "llama3.2",
        url: str = "http://localhost:11434",
        client: httpx.Client | None = None,
    ) -> None:
        self.name = f"ollama:{model}"
        self.model = model
        self.url = url.rstrip("/")
        self._client = client or httpx.Client()

    def complete(self, prompt: str, timeout: float) -> str:
        try:
            response = self._client.post(
                f"{self.url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 120, "temperature": 0.9},
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return str(response.json().get("response", ""))
        except httpx.HTTPError as error:
            raise LLMError(str(error)) from error


class OpenRouterBackend:
    """OpenRouter chat completions; key from OPENROUTER_API_KEY."""

    def __init__(
        self,
        model: str = "meta-llama/llama-3.2-3b-instruct",
        url: str = "https://openrouter.ai/api/v1",
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.name = f"openrouter:{model}"
        self.model = model
        self.url = url.rstrip("/")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._client = client or httpx.Client()

    def complete(self, prompt: str, timeout: float) -> str:
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not set")
        try:
            response = self._client.post(
                f"{self.url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError) as error:
            raise LLMError(str(error)) from error


STYLE_GUIDE = """You are the narrator of Wyraj, a roguelike set in Slavic folk horror.
Voice: a village elder telling it straight — concrete, unhurried, slightly too calm.
Short sentences land harder. No camp, no modern idiom, no exclamation marks.

REWRITE the DRAFT below into one short paragraph (at most 60 words), keeping every
fact exactly as given in FACTS. You may change phrasing and rhythm only.
NEVER invent creatures, names, items, numbers, or outcomes not present in FACTS.
Address the player as "you". Reply with the paragraph only — no preamble, no quotes."""


@dataclass
class LLMStats:
    requests: int = 0
    fallbacks: int = 0
    total_latency: float = 0.0
    prompt_chars: int = 0
    reply_chars: int = 0

    def summary(self) -> str:
        served = self.requests - self.fallbacks
        avg = self.total_latency / self.requests if self.requests else 0.0
        return (
            f"LLM narrator: {served}/{self.requests} turns narrated by the model "
            f"({self.fallbacks} template fallbacks), avg {avg * 1000:.0f} ms, "
            f"{self.prompt_chars + self.reply_chars} chars exchanged"
        )


def _facts_for(batch: list[tuple[GameEvent, frozenset[str]]]) -> str:
    lines = []
    for event, tags in batch:
        fact = repr(event)
        if tags:
            fact += f"  [context: {', '.join(sorted(tags))}]"
        lines.append(f"- {fact}")
    return "\n".join(lines)


def _sanitize(raw: str) -> str:
    text = " ".join(raw.strip().strip('"').split())
    words = text.split(" ")
    if len(words) > MAX_WORDS:
        clipped = " ".join(words[:MAX_WORDS])
        # Prefer ending on a sentence if one closed within the cap.
        match = re.match(r"^(.+[.!?…])", clipped)
        text = match.group(1) if match else clipped + "…"
    return text


class LLMNarrator:
    """Drop-in Narrator: same interface, template-grounded, template-guarded."""

    def __init__(
        self,
        template: TemplateNarrator,
        backend: LLMBackend,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.template = template
        self.backend = backend
        self.timeout = timeout
        self.stats = LLMStats()
        self._recent: deque[str] = deque(maxlen=RECENT_LINES)

    def compose(self, event: GameEvent, tags: frozenset[str] = NO_TAGS) -> list[NarrationLine]:
        return self.template.compose(event, tags)

    def compose_turn(self, batch: list[tuple[GameEvent, frozenset[str]]]) -> list[NarrationLine]:
        draft_lines = self.template.compose_turn(batch)
        if not draft_lines:
            return []
        draft = draft_lines[0]

        prompt = self._build_prompt(batch, draft.text)
        self.stats.requests += 1
        self.stats.prompt_chars += len(prompt)
        started = time.monotonic()
        try:
            raw = self.backend.complete(prompt, self.timeout)
        except LLMError:
            self.stats.fallbacks += 1
            self.stats.total_latency += time.monotonic() - started
            self._recent.append(draft.text)
            return draft_lines
        self.stats.total_latency += time.monotonic() - started

        text = _sanitize(raw)
        if not text:
            self.stats.fallbacks += 1
            self._recent.append(draft.text)
            return draft_lines
        self.stats.reply_chars += len(text)
        self._recent.append(text)
        return [NarrationLine(text=text, importance=draft.importance)]

    def _build_prompt(self, batch: list[tuple[GameEvent, frozenset[str]]], draft: str) -> str:
        parts = [STYLE_GUIDE, "", "FACTS:", _facts_for(batch)]
        if self._recent:
            parts += ["", "RECENT NARRATION (do not repeat wording):"]
            parts += [f"- {line}" for line in self._recent]
        parts += ["", "DRAFT:", draft]
        return "\n".join(parts)


def build_backend(config: dict[str, Any]) -> LLMBackend:
    """Build a backend from the `llm:` config mapping."""
    kind = str(config.get("backend", "ollama"))
    model = config.get("model")
    url = config.get("url")
    if kind == "openrouter":
        kwargs: dict[str, Any] = {}
        if model:
            kwargs["model"] = str(model)
        if url:
            kwargs["url"] = str(url)
        return OpenRouterBackend(**kwargs)
    kwargs = {}
    if model:
        kwargs["model"] = str(model)
    if url:
        kwargs["url"] = str(url)
    return OllamaBackend(**kwargs)
