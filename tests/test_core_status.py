import random

from tests.conftest import goto_depth
from wyraj.core.actions import Get, UseItem, Wait
from wyraj.core.components import (
    AttackStatus,
    Health,
    LightSource,
    Melee,
    Position,
    StatusEffect,
    StatusEffects,
)
from wyraj.core.ecs import World
from wyraj.core.events import (
    EventBus,
    LightExtinguished,
    StatusApplied,
    StatusExpired,
    StatusTick,
)
from wyraj.core.game import CRYPT_FOV_RADIUS, FOV_RADIUS, Game
from wyraj.core.systems import status
from wyraj.core.systems.combat import attack


def test_apply_tick_expire_cycle() -> None:
    world = World()
    bus = EventBus()
    applied: list[StatusApplied] = []
    ticked: list[StatusTick] = []
    expired: list[StatusExpired] = []
    bus.subscribe(StatusApplied, applied.append)
    bus.subscribe(StatusTick, ticked.append)
    bus.subscribe(StatusExpired, expired.append)

    actor = world.create(Health(10, 10))
    status.apply_status(world, bus, actor, StatusEffect(kind="bleeding", duration=2, power=1))
    assert applied[0].kind == "bleeding"

    status.tick(world, bus, actor)
    assert world.expect(actor, Health).hp == 9
    assert ticked[0].damage == 1
    status.tick(world, bus, actor)
    assert world.expect(actor, Health).hp == 8
    assert expired and expired[0].kind == "bleeding"
    assert world.expect(actor, StatusEffects).effects == ()


def test_reapply_refreshes_no_duplicate_event() -> None:
    world = World()
    bus = EventBus()
    applied: list[StatusApplied] = []
    bus.subscribe(StatusApplied, applied.append)
    actor = world.create(Health(10, 10))
    status.apply_status(world, bus, actor, StatusEffect(kind="poison", duration=3, power=1))
    status.apply_status(world, bus, actor, StatusEffect(kind="poison", duration=5, power=1))
    assert len(applied) == 1
    effects = world.expect(actor, StatusEffects).effects
    assert len(effects) == 1
    assert effects[0].duration == 5


def test_fear_and_blessing_modify_to_hit() -> None:
    world = World()
    bus = EventBus()
    actor = world.create(Health(10, 10), Melee(damage=1, to_hit=50))
    status.apply_status(world, bus, actor, StatusEffect(kind="fear", duration=3, power=15))
    assert status.to_hit_modifier(world, actor) == -15
    status.apply_status(world, bus, actor, StatusEffect(kind="blessing", duration=3, power=15))
    assert status.to_hit_modifier(world, actor) == 0


def test_attack_can_inflict_status() -> None:
    world = World()
    bus = EventBus()
    attacker = world.create(
        Melee(damage=1, to_hit=100),
        AttackStatus(kind="bleeding", chance=100, duration=3, power=1),
        Health(5, 5),
    )
    defender = world.create(Health(10, 10))
    attack(world, bus, random.Random(1), attacker, defender)
    kinds = status.active_kinds(world, defender)
    assert "bleeding" in kinds


def test_dot_can_kill_player_in_game() -> None:
    game = Game(seed=42)
    game.world.add(game.player, Health(2, 20))
    status.apply_status(
        game.world, game.bus, game.player, StatusEffect(kind="bleeding", duration=10, power=1)
    )
    for _ in range(5):
        if game.game_over:
            break
        game.step(Wait())
    assert game.game_over


def test_crypt_darkness_and_gromnica() -> None:
    game = Game(seed=42)
    assert game.fov_radius == FOV_RADIUS
    goto_depth(game, 3)
    assert game.fov_radius == CRYPT_FOV_RADIUS

    ppos = game.world.expect(game.player, Position)
    gromnica = game.spawn_item(game.items_catalog["gromnica"], ppos.x, ppos.y, game.depth)
    game.step(Get())
    game.step(UseItem(gromnica))
    assert game.world.get(game.player, LightSource) is not None
    assert game.fov_radius == FOV_RADIUS


def test_light_burns_down_and_goes_out() -> None:
    game = Game(seed=42)
    out: list[LightExtinguished] = []
    game.bus.subscribe(LightExtinguished, out.append)
    game.world.add(game.player, LightSource(turns=3))
    for _ in range(4):
        game.step(Wait())
    assert game.world.get(game.player, LightSource) is None
    assert out and out[0].actor.is_player


def test_darkness_tag_in_crypt() -> None:
    from wyraj.core.events import EntityDied, EntityRef
    from wyraj.narration.context import ContextEnricher

    game = Game(seed=42)
    enricher = ContextEnricher(game)
    event = EntityDied(entity=EntityRef(entity=99, key="bies", name="bies"))
    assert "darkness" not in enricher.enrich(event)
    goto_depth(game, 3)
    assert "darkness" in enricher.enrich(event)
    game.world.add(game.player, LightSource(turns=10))
    assert "darkness" not in enricher.enrich(event)
