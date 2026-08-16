"""Szept — the first-encounter whisper system ("Próg" spec §5).

A thin bus subscriber: the first time a situation occurs *per profile*, one
dim-italic aside follows the normal narration. Fired-once flags persist in
meta (`szept_seen`). Never blocks, never modal, never repeats; when every
core whisper has been heard, a single farewell line closes the mouth.
"""

from collections.abc import Callable

from wyraj.core.events import (
    AttackResolved,
    DeepDescended,
    EntityDied,
    EntityMoved,
    HungerChanged,
    LoreDiscovered,
    StatusApplied,
    TurnEnded,
    WijStirred,
)
from wyraj.core.game import Game
from wyraj.core.map import Tile

CORE_TRIGGERS = (
    "first_move",
    "first_hostile",
    "hp_low",
    "first_hunger",
    "first_darkness",
    "item_on_floor",
    "forest_edge",
    "first_status",
    "first_kill",
)


class SzeptSystem:
    def __init__(
        self,
        game: Game,
        table: dict[str, str],
        sink: Callable[[str], None],
        enabled: bool = True,
    ) -> None:
        self.game = game
        self.table = table
        self.sink = sink
        self.enabled = enabled
        bus = game.bus
        bus.subscribe(EntityMoved, self._on_moved)
        bus.subscribe(LoreDiscovered, self._on_discovered)
        bus.subscribe(AttackResolved, self._on_attack)
        bus.subscribe(HungerChanged, self._on_hunger)
        bus.subscribe(StatusApplied, self._on_status)
        bus.subscribe(EntityDied, self._on_died)
        bus.subscribe(TurnEnded, self._on_turn_end)
        # M8 §1: past the last sky shaft the szept changes sides — it stops
        # helping and starts noticing. Not in CORE_TRIGGERS: the farewell
        # must not wait on whispers most souls will never live to hear.
        bus.subscribe(DeepDescended, self._on_deep_descended)
        bus.subscribe(WijStirred, self._on_wij_stirred)

    # -- firing ----------------------------------------------------------

    def _fire(self, key: str) -> None:
        if not self.enabled or key in self.game.meta.szept_seen or key not in self.table:
            return
        self.game.meta.szept_seen.append(key)
        self.game._save_meta()
        self.sink(self.table[key])
        if all(k in self.game.meta.szept_seen for k in CORE_TRIGGERS):
            self._farewell()

    def _farewell(self) -> None:
        if "farewell" in self.game.meta.szept_seen or "farewell" not in self.table:
            return
        self.game.meta.szept_seen.append("farewell")
        self.game._save_meta()
        self.sink(self.table["farewell"])

    # -- triggers --------------------------------------------------------

    def _on_moved(self, event: EntityMoved) -> None:
        if event.actor.is_player:
            self._fire("first_move")

    def _on_discovered(self, event: LoreDiscovered) -> None:
        if event.entity.key in self.game.bestiary:
            self._fire("first_hostile")

    def _on_attack(self, event: AttackResolved) -> None:
        if event.defender.is_player and event.damage > 0 and event.defender_hp_frac < 0.5:
            self._fire("hp_low")

    def _on_hunger(self, event: HungerChanged) -> None:
        if event.actor.is_player and event.band == "hungry":
            self._fire("first_hunger")

    def _on_status(self, event: StatusApplied) -> None:
        if event.actor.is_player and event.kind in ("bleeding", "poison", "fear"):
            self._fire("first_status")

    def _on_died(self, event: EntityDied) -> None:
        if not event.entity.is_player and event.entity.key in self.game.bestiary:
            self._fire("first_kill")

    def _on_deep_descended(self, event: DeepDescended) -> None:
        self._fire("deep_descended")

    def _on_wij_stirred(self, event: WijStirred) -> None:
        self._fire("wij_watching")

    def _on_turn_end(self, event: TurnEnded) -> None:
        game = self.game
        if game.in_darkness:
            self._fire("first_darkness")
        from wyraj.core.components import Item, Position
        from wyraj.core.systems.movement import level_of

        ppos = game.world.get(game.player, Position)
        if ppos is None:
            return
        if game.depth == 0 and game.map.tiles[ppos.y][ppos.x] is Tile.STAIRS_DOWN:
            self._fire("forest_edge")
        for entity, (_item, pos) in game.world.query(Item, Position):
            if level_of(game.world, entity) == game.depth and (pos.x, pos.y) in game.map.visible:
                self._fire("item_on_floor")
                break
