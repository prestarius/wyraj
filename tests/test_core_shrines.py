from wyraj.core.actions import MakeOffering, Move
from wyraj.core.components import Position, Shrine
from wyraj.core.events import OfferingMade, ShrineVisited
from wyraj.core.game import Game
from wyraj.core.systems import status
from wyraj.persistence.meta import MetaState


def new_game() -> Game:
    return Game(seed=42, meta=MetaState(), meta_autosave=False)


def shrine_of(game: Game, god: str) -> int:
    for entity, (shrine,) in game.world.query(Shrine):
        if shrine.god == god:
            return entity
    raise AssertionError(f"no shrine of {god}")


def test_bump_shrine_publishes_visit() -> None:
    game = new_game()
    shrine = shrine_of(game, "weles")
    spos = game.world.expect(shrine, Position)
    game.world.add(game.player, Position(spos.x - 1, spos.y))
    visits: list[ShrineVisited] = []
    game.bus.subscribe(ShrineVisited, visits.append)
    game.step(Move(1, 0))
    assert visits and visits[0].god == "weles"
    # The player did not walk onto the shrine.
    assert game.world.expect(game.player, Position) == Position(spos.x - 1, spos.y)


def test_offering_applies_run_scoped_favor() -> None:
    game = new_game()
    game.meta.currency.denary = 100
    made: list[OfferingMade] = []
    game.bus.subscribe(OfferingMade, made.append)
    game.step(MakeOffering(god="perun"))
    assert made and made[0].god == "perun"
    assert game.meta.currency.denary == 100 - game.offerings["perun"].cost
    kinds = status.active_kinds(game.world, game.player)
    assert "perun_favor" in kinds
    assert status.to_hit_modifier(game.world, game.player) == game.offerings["perun"].power


def test_offering_refused_when_broke() -> None:
    game = new_game()
    game.meta.currency.denary = 1
    game.step(MakeOffering(god="weles"))
    assert game.meta.currency.denary == 1
    assert "weles_favor" not in status.active_kinds(game.world, game.player)


def test_weles_favor_boosts_drop_luck() -> None:
    game = new_game()
    game.meta.currency.denary = 100
    assert game._drop_luck(50) == 50
    game.step(MakeOffering(god="weles"))
    assert game._drop_luck(50) == 75  # +50%
    assert game._drop_luck(90) == 100  # capped
