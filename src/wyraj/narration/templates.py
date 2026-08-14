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
from wyraj.core.events import (
    AttackResolved,
    EntityDied,
    EntityRef,
    GameEvent,
    HungerChanged,
    ItemPickedUp,
    ItemUsed,
    ItemWielded,
    ItemWorn,
    LevelChanged,
    LightExtinguished,
    LoreDiscovered,
    MoveBlocked,
    StarvationHit,
    StatusApplied,
    StatusExpired,
    StatusTick,
)
from wyraj.narration.engine import NarrationLine
from wyraj.narration.forms import FormRegistry

_SLOT = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")


class Variant(BaseModel):
    en: str
    weight: int = Field(default=1, gt=0)
    importance: str = "normal"
    # Context tags required for this variant (all must be present).
    tags: list[str] = []


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
        case ItemPickedUp():
            return "item_picked_up", None
        case ItemUsed():
            return "item_used", event.effect
        case ItemWielded():
            return "item_wielded", None
        case ItemWorn():
            return "item_worn", None
        case HungerChanged():
            return "hunger_changed", event.band
        case StarvationHit():
            return "starvation_hit", None
        case LoreDiscovered():
            return "lore_discovered", event.entity.key
        case LevelChanged():
            return "level_changed", event.direction
        case StatusApplied():
            return "status_applied", event.kind
        case StatusTick():
            return "status_tick", event.kind
        case StatusExpired():
            return "status_expired", event.kind
        case LightExtinguished():
            return "light_extinguished", None
        case _:
            name = type(event).__name__
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
            return snake, None


def _resolve(event: GameEvent, path: str, registry: FormRegistry) -> str:
    parts = path.split(".")
    value: Any = event
    for i, part in enumerate(parts):
        if isinstance(value, EntityRef) and part in ("name", "pronoun"):
            forms = registry.forms_for(value)
            rest = parts[i + 1 :]
            if len(rest) > 1:
                raise KeyError(f"slot '{path}' goes too deep past '{part}'")
            if part == "name":
                return forms.resolve(rest[0] if rest else "base")
            return forms.pronoun(rest[0] if rest else "subj")
        if value is None or not hasattr(value, part):
            raise KeyError(f"unresolved slot '{path}' for {type(event).__name__}")
        value = getattr(value, part)
    return str(value)


def render(template: str, event: GameEvent, registry: FormRegistry) -> str:
    return _SLOT.sub(lambda m: _resolve(event, m.group(1), registry), template)


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


NO_TAGS: frozenset[str] = frozenset()


class TemplateNarrator:
    def __init__(self, pack: GrammarPack, rng: random.Random, registry: FormRegistry) -> None:
        self.pack = pack
        self.rng = rng
        self.registry = registry
        # Per-rule memory of the last template used (anti-repetition).
        self._last_template: dict[RuleKey, str] = {}

    def compose(self, event: GameEvent, tags: frozenset[str] = NO_TAGS) -> list[NarrationLine]:
        key = rule_key(event)
        # Fallback chain: exact subkey → "default" subkey → bare rule.
        variants = (
            self.pack.rules.get(key)
            or self.pack.rules.get((key[0], "default"))
            or self.pack.rules.get((key[0], None))
        )
        if not variants:
            return []  # no rule = deliberately silent (e.g. routine movement)
        chosen = self._pick(key, variants, tags)
        if chosen is None:
            return []
        text = render(chosen.en, event, self.registry)
        return [NarrationLine(text=text, importance=chosen.importance)]

    def _pick(self, key: RuleKey, variants: list[Variant], tags: frozenset[str]) -> Variant | None:
        eligible = [v for v in variants if set(v.tags) <= tags]
        if not eligible:
            eligible = [v for v in variants if not v.tags]
        if not eligible:
            return None
        # Prefer the most context-specific variants (tone modifiers win).
        max_specificity = max(len(v.tags) for v in eligible)
        pool = [v for v in eligible if len(v.tags) == max_specificity]
        # Avoid repeating the template chosen last time for this rule.
        fresh = [v for v in pool if v.en != self._last_template.get(key)]
        pool = fresh or pool
        chosen = self.rng.choices(pool, weights=[v.weight for v in pool])[0]
        self._last_template[key] = chosen.en
        return chosen

    def compose_turn(self, batch: list[tuple[GameEvent, frozenset[str]]]) -> list[NarrationLine]:
        """Coalesce one turn's events into a single composed paragraph."""
        sentences: list[str] = []
        importance = "normal"
        again_added = False
        for event, tags in batch:
            for line in self.compose(event, tags):
                if line.text in sentences:
                    if not again_added:
                        sentences.append("And again.")
                        again_added = True
                    continue
                sentences.append(line.text)
                if line.importance == "high":
                    importance = "high"
        if not sentences:
            return []
        return [NarrationLine(text=" ".join(sentences), importance=importance)]
