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
