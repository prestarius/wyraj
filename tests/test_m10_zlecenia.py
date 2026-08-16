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


# ---- US 13.4: reputation & the good shelf --------------------------------


def _trader_stock_keys(game: Game) -> list[str]:
    from wyraj.core.components import Inventory, Item

    trader = _find_villager(game, "trader")
    return [game.world.expect(e, Item).key for e in game.world.expect(trader, Inventory).items]


def test_reputation_unlocks_the_good_shelf() -> None:
    from wyraj.persistence.meta import VillagerMemory

    plain = _trader_stock_keys(Game(seed=SEED, meta_autosave=False))
    assert "szkaplerz" not in plain and "baranica" not in plain

    meta = MetaState()
    meta.villagers["kowal"] = VillagerMemory(reputation=2)
    meta.villagers["mlynarz"] = VillagerMemory(reputation=1)
    trusted = _trader_stock_keys(Game(seed=SEED, meta=meta, meta_autosave=False))
    assert "szkaplerz" in trusted and "baranica" not in trusted
    # Rolled stock is untouched by the meta gate (no extra RNG draws).
    assert trusted[: len(plain)] == plain

    meta.villagers["gossip"] = VillagerMemory(reputation=3)
    best = _trader_stock_keys(Game(seed=SEED, meta=meta, meta_autosave=False))
    assert "szkaplerz" in best and "baranica" in best


def test_known_face_tag_from_reputation() -> None:
    from wyraj.core.events import EntityRef, TalkedTo
    from wyraj.narration.context import ContextEnricher
    from wyraj.persistence.meta import VillagerMemory

    game = Game(seed=SEED, meta_autosave=False)
    game.errands = {"syn_mlynarza": "heard"}
    game.meta.villagers["kowal"] = VillagerMemory(reputation=3)
    enricher = ContextEnricher(game)
    villager = EntityRef(entity=5, key="kowal", name="Radzim the kowal")
    tags = enricher.enrich(TalkedTo(villager=villager, role="kowal"))
    assert "known_face" in tags
    assert "errand_syn_mlynarza" in tags
    stranger = enricher.enrich(TalkedTo(villager=villager, role="mlynarz"))
    assert "known_face" not in stranger


# ---- US 13.5: fates -------------------------------------------------------


def test_ignored_chain_resolves_after_patience_runs() -> None:
    meta = MetaState()
    for run in range(3):
        game = Game(seed=run, meta=meta, meta_autosave=False)
        game.errands = {"syn_mlynarza": "heard"}
        game.apply_death_to_meta()
    assert meta.village.fates["mlyn_pusty"] == 3
    assert meta.village.resolved == ["mlyn_pusty"]
    assert meta.villagers["mlynarz"].errands_failed == 3

    # A fourth ignored run cannot resolve it twice — and the miller is gone.
    game = Game(seed=99, meta=meta, meta_autosave=False)
    from wyraj.core.components import Villager

    roles = {v.role for _e, (v,) in game.world.query(Villager)}
    assert "mlynarz" not in roles
    game.apply_death_to_meta()
    assert meta.village.resolved == ["mlyn_pusty"]
    assert meta.village.fates["mlyn_pusty"] == 3


def test_unheard_errands_do_not_count_against_you() -> None:
    meta = MetaState()
    game = Game(seed=SEED, meta=meta, meta_autosave=False)
    game.errands = {"syn_mlynarza": "offered"}
    game.apply_death_to_meta()
    assert "mlynarz" not in meta.villagers
    assert meta.village.fates == {}


def test_fate_announced_once_ever() -> None:
    from wyraj.core.actions import Wait
    from wyraj.core.events import VillageFateResolved

    meta = MetaState()
    meta.village.resolved.append("zimna_kuznia")

    game = Game(seed=SEED, meta=meta, meta_autosave=False)
    told: list[VillageFateResolved] = []
    game.bus.subscribe(VillageFateResolved, told.append)
    game.step(Wait())
    game.step(Wait())
    assert [event.fate for event in told] == ["zimna_kuznia"]
    assert meta.village.announced == ["zimna_kuznia"]

    later = Game(seed=SEED + 1, meta=meta, meta_autosave=False)
    told_again: list[VillageFateResolved] = []
    later.bus.subscribe(VillageFateResolved, told_again.append)
    later.step(Wait())
    assert told_again == []


def test_resolved_fate_thins_the_shelves() -> None:
    meta = MetaState()
    meta.village.resolved.extend(["mlyn_pusty", "zimna_kuznia"])
    stock = _trader_stock_keys(Game(seed=SEED, meta=meta, meta_autosave=False))
    assert "chleb" not in stock
    assert "toporek" not in stock and "ciupaga" not in stock


def test_morgue_records_the_changed_wies(tmp_path) -> None:
    from datetime import datetime

    from wyraj.persistence.morgue import write_morgue

    meta = MetaState()
    meta.village.resolved.append("mlyn_pusty")
    game = Game(seed=SEED, meta=meta, meta_autosave=False)
    game.errands = {"czwarta_noc": "heard"}
    path = write_morgue(game, datetime(2026, 8, 16, 12, 0, 0), directory=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert "Words given and not kept: czwarta_noc" in text
    assert "The wieś, changed: mlyn_pusty" in text


# ---- US 13.6: the Zlecenia tab --------------------------------------------


def test_errands_tab_renders_in_run_view() -> None:
    from wyraj.persistence.meta import VillagerMemory
    from wyraj.ui.codex_view import build_errands_text

    game = Game(seed=SEED, meta_autosave=False)
    game.errands = {"syn_mlynarza": "heard", "czwarta_noc": "offered", "wosk_na_handel": "done"}
    game.meta.villagers["mlynarz"] = VillagerMemory(reputation=2, errands_done=2)
    game.meta.village.resolved.append("zimna_kuznia")
    text = build_errands_text(
        catalog=game.errands_catalog,
        run_errands=game.errands,
        meta=game.meta,
        bestiary=game.bestiary,
        items_catalog=game.items_catalog,
    ).plain
    assert "utopiec" in text and "heard" in text
    assert "done" in text
    # Unheard asks stay unheard — no journal spoilers.
    assert "strzyga" not in text
    assert "Bogusz the młynarz" in text
    assert "The forge is cold" in text


def test_errands_tab_renders_from_meta_alone() -> None:
    from wyraj.content.errands import load_errands as load_catalog
    from wyraj.ui.codex_view import build_errands_text

    meta = MetaState()
    text = build_errands_text(
        catalog=load_catalog(),
        run_errands=None,
        meta=meta,
        bestiary=load_bestiary(),
        items_catalog=load_items(),
    ).plain
    assert "This journey" not in text
    assert "No one here knows your name yet." in text


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
