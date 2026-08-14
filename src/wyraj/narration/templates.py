"""TemplateNarrator: deterministic grammar-pack narration.

Packs are YAML keyed by event rule, each rule holding weighted variants:

    attack_resolved:
      player_hit:
        - weight: 3
          en: "Your blow bites into the {defender.name}."

Slots like `{defender.name}` resolve as dotted attribute paths on the event.
An unresolvable slot is a content bug and raises immediately (CI catches it).
Variant choice draws from the `narration` RNG stream — never from gameplay
streams, so flavor variety cannot perturb the simulation (spec pillar 3).
"""

import random
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir
from wyraj.core.events import AttackResolved, EntityDied, GameEvent, MoveBlocked
from wyraj.narration.engine import NarrationLine

_SLOT = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")


class Variant(BaseModel):
    en: str
    weight: int = Field(default=1, gt=0)
    importance: str = "normal"


RuleKey = tuple[str, str | None]


def rule_key(event: GameEvent) -> RuleKey:
    """Map an event to its pack rule. Perspective (player vs enemy) is part
    of the key in M0; proper context tags arrive with the M1 enricher."""
    match event:
        case AttackResolved():
            side = "player" if event.attacker.is_player else "enemy"
            return "attack_resolved", f"{side}_{event.outcome.value}"
        case EntityDied():
            return "entity_died", "player" if event.entity.is_player else "enemy"
        case MoveBlocked():
            return "move_blocked", "player" if event.actor.is_player else "enemy"
        case _:
            name = type(event).__name__
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            return snake, None


def _resolve(event: GameEvent, path: str) -> str:
    value: Any = event
    for part in path.split("."):
        if value is None or not hasattr(value, part):
            raise KeyError(f"unresolved slot '{path}' for {type(event).__name__}")
        value = getattr(value, part)
    return str(value)


def render(template: str, event: GameEvent) -> str:
    return _SLOT.sub(lambda m: _resolve(event, m.group(1)), template)


class GrammarPack:
    def __init__(self, rules: dict[RuleKey, list[Variant]]) -> None:
        self.rules = rules

    @classmethod
    def load_dir(cls, directory: Path) -> "GrammarPack":
        rules: dict[RuleKey, list[Variant]] = {}
        for path in sorted(directory.glob("*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for event_key, body in raw.items():
                if isinstance(body, list):
                    rules[(event_key, None)] = [Variant(**v) for v in body]
                else:
                    for subkey, variants in body.items():
                        rules[(event_key, subkey)] = [Variant(**v) for v in variants]
        return cls(rules)


def load_pack(lang: str = "en") -> GrammarPack:
    return GrammarPack.load_dir(data_dir() / "narration" / lang)


class TemplateNarrator:
    def __init__(self, pack: GrammarPack, rng: random.Random) -> None:
        self.pack = pack
        self.rng = rng

    def compose(self, event: GameEvent) -> list[NarrationLine]:
        variants = self.pack.rules.get(rule_key(event))
        if not variants:
            return []  # no rule = deliberately silent (e.g. routine movement)
        chosen = self.rng.choices(variants, weights=[v.weight for v in variants])[0]
        return [NarrationLine(text=render(chosen.en, event), importance=chosen.importance)]
