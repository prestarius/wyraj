from wyraj.core.components import Health, Position
from wyraj.core.ecs import World


def test_create_and_get() -> None:
    world = World()
    e = world.create(Position(1, 2), Health(10, 10))
    assert world.get(e, Position) == Position(1, 2)
    assert world.expect(e, Health).hp == 10
    assert world.get(e, Health) is not None
    assert world.is_alive(e)


def test_add_overwrites_same_type() -> None:
    world = World()
    e = world.create(Health(10, 10))
    world.add(e, Health(3, 10))
    assert world.expect(e, Health).hp == 3


def test_remove_and_destroy() -> None:
    world = World()
    e = world.create(Position(0, 0), Health(5, 5))
    world.remove(e, Position)
    assert world.get(e, Position) is None
    world.destroy(e)
    assert not world.is_alive(e)
    assert world.get(e, Health) is None
    assert world.entities_with(Health) == []


def test_query_requires_all_components_in_id_order() -> None:
    world = World()
    a = world.create(Position(0, 0), Health(1, 1))
    world.create(Position(1, 1))  # no Health — excluded
    c = world.create(Position(2, 2), Health(2, 2))
    results = list(world.query(Position, Health))
    assert [e for e, _ in results] == [a, c]
    assert results[0][1] == (Position(0, 0), Health(1, 1))


def test_query_skips_destroyed() -> None:
    world = World()
    a = world.create(Position(0, 0))
    world.destroy(a)
    assert list(world.query(Position)) == []
