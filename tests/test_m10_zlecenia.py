"""M10 "Zlecenia": errand assembly, the loop, reputation, fates."""

from wyraj.content.bestiary import load_bestiary
from wyraj.content.errands import load_errands
from wyraj.content.items import load_items
from wyraj.core.game import ERRANDS_MAX, ERRANDS_MIN, ROLE_FATES, Game
from wyraj.persistence.meta import MetaState

SEED = 42


# ---- US 13.1: model & assembly -------------------------------------------


def test_catalog_targets_and_proofs_exist() -> None:
    bestiary = load_bestiary()
    items = load_items()
    for errand in load_errands().values():
        if errand.kind == "hunt":
            assert errand.target in bestiary, errand.key
            assert errand.proof in items, errand.key
        else:
            assert errand.target in items, errand.key


def test_assembly_is_deterministic_per_seed_and_meta() -> None:
    first = Game(seed=SEED, meta_autosave=False)
    second = Game(seed=SEED, meta_autosave=False)
    assert first.errands == second.errands
    assert first.errands, "a run always carries at least one errand"


def test_assembly_count_and_one_per_giver() -> None:
    catalog = load_errands()
    for seed in range(20):
        game = Game(seed=seed, meta_autosave=False)
        assert ERRANDS_MIN <= len(game.errands) <= ERRANDS_MAX
        givers = [catalog[key].giver for key in game.errands]
        assert len(givers) == len(set(givers))
        assert all(status == "offered" for status in game.errands.values())


def test_resolved_fate_excludes_its_chain() -> None:
    catalog = load_errands()
    fated = next(d for d in catalog.values() if d.fate)
    meta = MetaState()
    meta.village.resolved.append(fated.fate)
    for seed in range(30):
        game = Game(seed=seed, meta=meta, meta_autosave=False)
        assert fated.key not in game.errands
        # The giver left with their chain (M10 §4).
        if fated.giver in ROLE_FATES:
            assert all(catalog[k].giver != fated.giver for k in game.errands)


# ---- US 13.2: the village grows two souls --------------------------------


def test_new_villagers_stand_in_the_wies() -> None:
    from wyraj.core.components import Lore, Villager

    game = Game(seed=SEED, meta_autosave=False)
    roles = {
        villager.role: game.world.expect(entity, Lore).name
        for entity, (villager,) in game.world.query(Villager)
    }
    assert roles["kowal"] == "Radzim the kowal"
    assert roles["mlynarz"] == "Bogusz the młynarz"


def test_bump_new_villagers_talks() -> None:
    from wyraj.core.actions import Move
    from wyraj.core.components import Position
    from wyraj.core.events import TalkedTo

    for role in ("kowal", "mlynarz"):
        game = Game(seed=SEED, meta_autosave=False)
        villager = _find_villager(game, role)
        ppos = game.world.expect(game.player, Position)
        game.world.add(villager, Position(ppos.x + 1, ppos.y))
        talks: list[TalkedTo] = []
        game.bus.subscribe(TalkedTo, talks.append)
        game.step(Move(1, 0))
        assert talks and talks[0].role == role


def _find_villager(game: Game, role: str) -> int:
    from wyraj.core.components import Villager

    for entity, (villager,) in game.world.query(Villager):
        if villager.role == role:
            return entity
    raise AssertionError(f"no {role} in the village")


# ---- US 13.3: the loop ----------------------------------------------------


def _bump(game: Game, villager: int) -> None:
    from wyraj.core.actions import Move
    from wyraj.core.components import Position

    ppos = game.world.expect(game.player, Position)
    game.world.add(villager, Position(ppos.x + 1, ppos.y))
    game.step(Move(1, 0))


def test_hunt_errand_end_to_end() -> None:
    from wyraj.core.actions import Get
    from wyraj.core.components import Inventory, Item, Position
    from wyraj.core.events import EntityDied, EntityRef, ErrandCompleted, ErrandHeard

    game = Game(seed=SEED, meta_autosave=False)
    game.errands = {"syn_mlynarza": "offered"}
    mlynarz = _find_villager(game, "mlynarz")

    heard: list[ErrandHeard] = []
    game.bus.subscribe(ErrandHeard, heard.append)
    _bump(game, mlynarz)
    assert heard and heard[0].errand == "syn_mlynarza"
    assert game.errands["syn_mlynarza"] == "heard"

    # The kill guarantees the proof at the corpse (M10 §2).
    ppos = game.world.expect(game.player, Position)
    game.bus.publish(
        EntityDied(
            entity=EntityRef(entity=999, key="utopiec", name="utopiec"),
            position=(ppos.x, ppos.y),
            depth=0,
        )
    )
    assert game.errands["syn_mlynarza"] == "proof"
    game.step(Get())
    carried = [
        game.world.expect(e, Item).key
        for e in game.world.expect(game.player, Inventory).items
        if game.world.get(e, Item) is not None
    ]
    assert "utopcowa_luska" in carried

    done: list[ErrandCompleted] = []
    game.bus.subscribe(ErrandCompleted, done.append)
    wallet_before = game.meta.currency.denary
    _bump(game, mlynarz)
    assert done and done[0].reward == 70
    assert game.errands["syn_mlynarza"] == "done"
    assert game.meta.currency.denary == wallet_before + 70
    assert game.meta.villagers["mlynarz"].reputation == 1
    assert game.meta.villagers["mlynarz"].errands_done == 1
    # The proof stays with the giver.
    carried = [
        game.world.expect(e, Item).key
        for e in game.world.expect(game.player, Inventory).items
        if game.world.get(e, Item) is not None
    ]
    assert "utopcowa_luska" not in carried


def test_fetch_errand_stamped_and_completed() -> None:
    from wyraj.core.components import Inventory, Item, OnLevel
    from wyraj.core.events import ErrandCompleted

    game = Game(seed=SEED, meta_autosave=False)
    game.errands = {"kadzielnica_kaplicznika": "heard"}
    game._ensure_level(1)
    game._ensure_level(2)
    game._ensure_level(3)
    game._ensure_level(4)
    stamped = [
        entity
        for entity, (item, on_level) in game.world.query(Item, OnLevel)
        if item.key == "kadzielnica" and on_level.depth == 4
    ]
    assert len(stamped) == 1, "the censer waits in the second crypt, once"

    # Carry it home and hand it over.
    censer = stamped[0]
    game.world.remove(censer, OnLevel)
    inv = game.world.get(game.player, Inventory) or Inventory()
    game.world.add(game.player, Inventory(items=(*inv.items, censer)))
    done: list[ErrandCompleted] = []
    game.bus.subscribe(ErrandCompleted, done.append)
    _bump(game, _find_villager(game, "gossip"))
    assert done and done[0].errand == "kadzielnica_kaplicznika"
    assert game.meta.villagers["gossip"].reputation == 1


def test_fetch_stamp_is_deterministic() -> None:
    from wyraj.core.components import Item, OnLevel, Position

    def censer_pos(game: Game) -> tuple[int, int]:
        game.errands = {"kadzielnica_kaplicznika": "offered"}
        for d in range(1, 5):
            game._ensure_level(d)
        for entity, (item, on_level) in game.world.query(Item, OnLevel):
            if item.key == "kadzielnica" and on_level.depth == 4:
                pos = game.world.expect(entity, Position)
                return (pos.x, pos.y)
        raise AssertionError("no censer stamped")

    assert censer_pos(Game(seed=7, meta_autosave=False)) == censer_pos(
        Game(seed=7, meta_autosave=False)
    )


def test_unheard_errand_grants_no_proof() -> None:
    from wyraj.core.components import Position
    from wyraj.core.events import EntityDied, EntityRef

    game = Game(seed=SEED, meta_autosave=False)
    game.errands = {"syn_mlynarza": "offered"}
    ppos = game.world.expect(game.player, Position)
    game.bus.publish(
        EntityDied(
            entity=EntityRef(entity=999, key="utopiec", name="utopiec"),
            position=(ppos.x, ppos.y),
            depth=0,
        )
    )
    assert game.errands["syn_mlynarza"] == "offered"


def test_errand_state_survives_save(tmp_path) -> None:
    from wyraj.persistence.save import load_game, save_game

    game = Game(seed=SEED, meta_autosave=False)
    key = next(iter(game.errands))
    game.errands[key] = "heard"
    path = tmp_path / "save.json.gz"
    save_game(game, path)
    loaded = load_game(path)
    assert loaded is not None
    assert loaded.errands == game.errands
