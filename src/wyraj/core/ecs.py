"""Minimal hand-rolled ECS: entities are ints, components are frozen dataclasses.

Components are immutable; "changing" one means replacing it via `add()`
(which overwrites any existing component of the same type).
"""

from collections.abc import Iterator
from typing import Any, TypeVar

Entity = int

C = TypeVar("C")


class World:
    def __init__(self) -> None:
        self._next_id: Entity = 1
        self._alive: set[Entity] = set()
        self._components: dict[type[Any], dict[Entity, Any]] = {}

    def create(self, *components: Any) -> Entity:
        entity = self._next_id
        self._next_id += 1
        self._alive.add(entity)
        for component in components:
            self.add(entity, component)
        return entity

    def destroy(self, entity: Entity) -> None:
        self._alive.discard(entity)
        for store in self._components.values():
            store.pop(entity, None)

    def is_alive(self, entity: Entity) -> bool:
        return entity in self._alive

    def add(self, entity: Entity, component: Any) -> None:
        if entity not in self._alive:
            raise KeyError(f"entity {entity} does not exist")
        self._components.setdefault(type(component), {})[entity] = component

    def remove(self, entity: Entity, component_type: type[Any]) -> None:
        self._components.get(component_type, {}).pop(entity, None)

    def get(self, entity: Entity, component_type: type[C]) -> C | None:
        component: C | None = self._components.get(component_type, {}).get(entity)
        return component

    def expect(self, entity: Entity, component_type: type[C]) -> C:
        component = self.get(entity, component_type)
        if component is None:
            raise KeyError(f"entity {entity} has no {component_type.__name__}")
        return component

    def has(self, entity: Entity, component_type: type[Any]) -> bool:
        return entity in self._components.get(component_type, {})

    def query(self, *component_types: type[Any]) -> Iterator[tuple[Entity, tuple[Any, ...]]]:
        """Yield (entity, components) for every live entity having all given types.

        Iteration order is entity-id order, so systems are deterministic.
        """
        if not component_types:
            return
        stores = [self._components.get(t, {}) for t in component_types]
        candidates = min(stores, key=len)
        for entity in sorted(candidates):
            if entity in self._alive and all(entity in s for s in stores):
                yield entity, tuple(s[entity] for s in stores)

    def entities_with(self, *component_types: type[Any]) -> list[Entity]:
        return [entity for entity, _ in self.query(*component_types)]
