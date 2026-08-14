from wyraj.core.components import Actor
from wyraj.core.ecs import Entity, World
from wyraj.core.scheduler import TurnScheduler


def run_actions(scheduler: TurnScheduler, n: int) -> list[Entity]:
    order: list[Entity] = []
    for _ in range(n):
        entity = scheduler.next_actor()
        assert entity is not None
        order.append(entity)
        scheduler.spend(entity)
    return order


def test_equal_speeds_alternate_in_id_order() -> None:
    world = World()
    a = world.create(Actor(speed=100))
    b = world.create(Actor(speed=100))
    assert run_actions(TurnScheduler(world), 4) == [a, b, a, b]


def test_double_speed_acts_twice_as_often() -> None:
    world = World()
    fast = world.create(Actor(speed=100))
    slow = world.create(Actor(speed=50))
    order = run_actions(TurnScheduler(world), 9)
    assert order.count(fast) == 6
    assert order.count(slow) == 3


def test_no_actors_returns_none() -> None:
    world = World()
    assert TurnScheduler(world).next_actor() is None


def test_determinism_same_setup_same_order() -> None:
    def build() -> list[Entity]:
        world = World()
        world.create(Actor(speed=70))
        world.create(Actor(speed=130))
        world.create(Actor(speed=100))
        return run_actions(TurnScheduler(world), 20)

    assert build() == build()
