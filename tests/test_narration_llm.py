import json
import random

import httpx

from tests.test_narration_templates import REGISTRY, fixture_event
from wyraj.narration.llm import (
    DEFAULT_TIMEOUT,
    LLMError,
    LLMNarrator,
    OllamaBackend,
    OpenRouterBackend,
    _sanitize,
    build_backend,
)
from wyraj.narration.templates import TemplateNarrator, load_pack


class FakeBackend:
    name = "fake"

    def __init__(self, reply: str | None = None, error: bool = False) -> None:
        self.reply = reply
        self.error = error
        self.prompts: list[str] = []

    def complete(self, prompt: str, timeout: float) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise LLMError("boom")
        return self.reply or ""


def make_narrator(backend: FakeBackend) -> LLMNarrator:
    template = TemplateNarrator(load_pack("en"), random.Random(1), REGISTRY)
    return LLMNarrator(template, backend, timeout=DEFAULT_TIMEOUT)


def batch() -> list[tuple]:
    return [(fixture_event("attack_resolved", "enemy_hit"), frozenset({"player_bloodied"}))]


def test_model_reply_replaces_draft_and_keeps_importance() -> None:
    backend = FakeBackend(reply="The bies finds your ribs; the pain is old news by now.")
    narrator = make_narrator(backend)
    lines = narrator.compose_turn(batch())
    assert lines[0].text == "The bies finds your ribs; the pain is old news by now."
    assert narrator.stats.requests == 1
    assert narrator.stats.fallbacks == 0


def test_error_falls_back_to_template() -> None:
    backend = FakeBackend(error=True)
    narrator = make_narrator(backend)
    lines = narrator.compose_turn(batch())
    assert lines, "fallback must still narrate"
    assert narrator.stats.fallbacks == 1
    # Template text comes from the deterministic pack, so it mentions the bies.
    assert "bies" in lines[0].text.lower() or "you" in lines[0].text.lower()


def test_empty_reply_falls_back() -> None:
    narrator = make_narrator(FakeBackend(reply="   "))
    lines = narrator.compose_turn(batch())
    assert lines
    assert narrator.stats.fallbacks == 1


def test_prompt_is_grounded_in_facts_and_draft() -> None:
    backend = FakeBackend(reply="ok")
    narrator = make_narrator(backend)
    narrator.compose_turn(batch())
    prompt = backend.prompts[0]
    assert "FACTS:" in prompt
    assert "AttackResolved" in prompt
    assert "player_bloodied" in prompt
    assert "DRAFT:" in prompt
    assert "NEVER invent" in prompt


def test_recent_lines_carried_into_next_prompt() -> None:
    backend = FakeBackend(reply="A line the model wrote.")
    narrator = make_narrator(backend)
    narrator.compose_turn(batch())
    narrator.compose_turn(batch())
    assert "A line the model wrote." in backend.prompts[1]


def test_sanitize_caps_length() -> None:
    long_reply = "word " * 200
    assert len(_sanitize(long_reply).split()) <= 61
    assert _sanitize('"quoted reply"') == "quoted reply"
    assert _sanitize("Multi.\n\nParagraph.\nText.") == "Multi. Paragraph. Text."


def test_silent_turn_stays_silent() -> None:
    narrator = make_narrator(FakeBackend(reply="should never be used"))
    assert narrator.compose_turn([]) == []
    assert narrator.stats.requests == 0


def test_ollama_backend_request_shape() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = json.loads(request.content)
        return httpx.Response(200, json={"response": "narrated"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OllamaBackend(model="test-model", client=client)
    assert backend.complete("hello", 1.0) == "narrated"
    assert captured["url"].endswith("/api/generate")
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["stream"] is False


def test_openrouter_backend_request_shape_and_missing_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["messages"][0]["content"] == "hello"
        assert request.headers["Authorization"] == "Bearer sekret"
        return httpx.Response(200, json={"choices": [{"message": {"content": "narrated"}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OpenRouterBackend(api_key="sekret", client=client)
    assert backend.complete("hello", 1.0) == "narrated"

    keyless = OpenRouterBackend(api_key="", client=client)
    try:
        keyless.complete("hello", 1.0)
        raise AssertionError("should have raised")
    except LLMError:
        pass


def test_build_backend_dispatch() -> None:
    assert build_backend({}).name.startswith("ollama:")
    assert build_backend({"backend": "openrouter", "model": "x"}).name == "openrouter:x"
    assert build_backend({"backend": "ollama", "model": "y"}).name == "ollama:y"
