"""ContextEnricher: attaches situational tags the raw event lacks (spec §5.1).

Tags produced in M1:
- `player_healthy` / `player_bloodied` / `player_dying` — HP bands
- `unseen_attacker` — the attacker is outside the player's FOV
- `again` — this rule fired within the last few turns (recency callback)
- `darkness` — supported by the selection machinery and exercised in tests;
  emitted for real once light sources land in M2.

Enrichment happens at event-capture time, so tags reflect the state in which
the event actually occurred, not the state at end-of-turn flush.
"""

from dataclasses import dataclass, field

from wyraj.core.components import Health, Position
from wyraj.core.events import AttackResolved, GameEvent, OfferingMade, ShrineVisited, TalkedTo
from wyraj.core.game import Game
from wyraj.narration.templates import RuleKey, rule_key

BLOODIED_AT = 0.5
DYING_AT = 0.25
AGAIN_WINDOW_TURNS = 3
KNOWN_FACE_REP = 3  # M10 §3: the villager remembers this soul


@dataclass
class ContextEnricher:
    game: Game
    _last_seen: dict[RuleKey, int] = field(default_factory=dict)

    def enrich(self, event: GameEvent) -> frozenset[str]:
        tags = set(self._player_tags())
        tags.update(self._event_tags(event))
        tags.update(self._recency_tags(event))
        return frozenset(tags)

    def _player_tags(self) -> set[str]:
        tags: set[str] = set()
        health = self.game.world.get(self.game.player, Health)
        if health is not None:
            if health.fraction <= DYING_AT:
                tags.add("player_dying")
            elif health.fraction <= BLOODIED_AT:
                tags.add("player_bloodied")
            else:
                tags.add("player_healthy")
        if self.game.in_darkness:
            tags.add("darkness")
        return tags

    def _event_tags(self, event: GameEvent) -> set[str]:
        tags: set[str] = set()
        if isinstance(event, AttackResolved) and not event.attacker.is_player:
            pos = self.game.world.get(event.attacker.entity, Position)
            if pos is not None and (pos.x, pos.y) not in self.game.map.visible:
                tags.add("unseen_attacker")
        if isinstance(event, TalkedTo):
            # M10: village talk knows about unfinished business and old faces.
            for key, state in sorted(self.game.errands.items()):
                if state in ("heard", "proof"):
                    tags.add(f"errand_{key}")
            memory = self.game.meta.villagers.get(event.role)
            if memory is not None and memory.reputation >= KNOWN_FACE_REP:
                tags.add("known_face")
        if isinstance(event, TalkedTo | ShrineVisited | OfferingMade):
            # Resolved fates tint what the wieś and its shrines say (M10 §4).
            for fate in self.game.meta.village.resolved:
                tags.add(f"fate_{fate}")
        return tags

    def _recency_tags(self, event: GameEvent) -> set[str]:
        key = rule_key(event)
        last = self._last_seen.get(key)
        self._last_seen[key] = self.game.turn
        if last is not None and self.game.turn - last <= AGAIN_WINDOW_TURNS:
            return {"again"}
        return set()
