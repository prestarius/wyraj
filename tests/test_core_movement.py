from wyraj.core.components import Health, Lore, Player, Position
from wyraj.core.ecs import World
from wyraj.core.events import EntityMoved, EventBus, GameEvent, MoveBlocked
from wyraj.core.map import GameMap, Tile
from wyraj.core.systems.movement import try_move


def open_map(width: int = 5, height: int = 5) -> GameMap:
    tiles = [[Tile.FLOOR] * width for _ in range(height)]
    tiles[0] = [Tile.WALL] * width
    return GameMap(tiles)


def test_move_onto_floor() -> None:
    world = World()
    bus = EventBus()
    log: list[GameEvent] = []
    bus.subscribe_all(log.append)
    e = world.create(Player(), Position(2, 2), Health(10, 10))
    assert try_move(world, open_map(), bus, e, 1, 0)
    assert world.expect(e, Position) == Position(3, 2)
    assert log == [
        EntityMoved(
            actor=log[0].actor,  # type: ignore[attr-defined]
            from_pos=(2, 2),
            to_pos=(3, 2),
        )
    ]


def test_move_into_wall_blocked() -> None:
    world = World()
    bus = EventBus()
    blocked: list[MoveBlocked] = []
    bus.subscribe(MoveBlocked, blocked.append)
    e = world.create(Player(), Position(2, 1), Health(10, 10))
    assert not try_move(world, open_map(), bus, e, 0, -1)
    assert world.expect(e, Position) == Position(2, 1)
    assert blocked[0].to_pos == (2, 0)


def test_move_into_creature_blocked() -> None:
    world = World()
    bus = EventBus()
    e = world.create(Player(), Position(1, 1), Health(10, 10))
    world.create(Lore(key="bies", name="bies"), Position(2, 1), Health(5, 5))
    assert not try_move(world, open_map(), bus, e, 1, 0)
    assert world.expect(e, Position) == Position(1, 1)
