"""Energy/speed-based turn scheduler (ADOM-style).

Actors accumulate `speed` energy per tick; an actor may act once it has at
least ACTION_COST energy. Ties resolve in entity-id order, which keeps runs
deterministic.
"""

from dataclasses import replace

from wyraj.core.components import Actor, OnLevel
from wyraj.core.ecs import Entity, World

ACTION_COST = 100


class TurnScheduler:
    def __init__(self, world: World) -> None:
        self.world = world

    def _on_level(self, entity: Entity, depth: int | None) -> bool:
        if depth is None:
            return True
        on_level = self.world.get(entity, OnLevel)
        return (on_level.depth if on_level is not None else 0) == depth

    def next_actor(self, depth: int | None = None) -> Entity | None:
        """Return the next entity due to act, ticking energy forward as needed.

        Actors on other levels are frozen: with `depth` given, only actors on
        that level accumulate energy or act. Returns None if no actors exist.
        Does not deduct energy — the caller performs the action and then
        calls `spend()`.
        """
        while True:
            actors = [
                (entity, actor)
                for entity, (actor,) in self.world.query(Actor)
                if self._on_level(entity, depth)
            ]
            if not actors:
                return None
            for entity, actor in actors:
                if actor.energy >= ACTION_COST:
                    return entity
            for entity, actor in actors:
                self.world.add(entity, replace(actor, energy=actor.energy + actor.speed))

    def spend(self, entity: Entity, cost: int = ACTION_COST) -> None:
        actor = self.world.expect(entity, Actor)
        self.world.add(entity, replace(actor, energy=actor.energy - cost))
