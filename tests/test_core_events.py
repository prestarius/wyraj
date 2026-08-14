from wyraj.core.events import (
    EntityDied,
    EntityMoved,
    EntityRef,
    EventBus,
    GameEvent,
)

PLAYER = EntityRef(entity=1, key="player", name="you", is_player=True)
BIES = EntityRef(entity=2, key="bies", name="bies")


def test_typed_subscription_only_matching_events() -> None:
    bus = EventBus()
    moves: list[EntityMoved] = []
    bus.subscribe(EntityMoved, moves.append)
    bus.publish(EntityMoved(actor=PLAYER, from_pos=(0, 0), to_pos=(1, 0)))
    bus.publish(EntityDied(entity=BIES))
    assert len(moves) == 1
    assert moves[0].to_pos == (1, 0)


def test_catch_all_receives_everything_in_order() -> None:
    bus = EventBus()
    log: list[GameEvent] = []
    bus.subscribe_all(log.append)
    e1 = EntityMoved(actor=PLAYER, from_pos=(0, 0), to_pos=(1, 0))
    e2 = EntityDied(entity=BIES)
    bus.publish(e1)
    bus.publish(e2)
    assert log == [e1, e2]


def test_typed_handlers_run_before_catch_all() -> None:
    bus = EventBus()
    order: list[str] = []
    bus.subscribe(EntityDied, lambda e: order.append("typed"))
    bus.subscribe_all(lambda e: order.append("all"))
    bus.publish(EntityDied(entity=BIES))
    assert order == ["typed", "all"]
