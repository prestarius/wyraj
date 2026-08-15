from pathlib import Path

import yaml

from wyraj.persistence.meta import MetaState, StashedItem, load_meta, save_meta


def test_missing_file_gives_fresh_default(tmp_path: Path) -> None:
    meta = load_meta(tmp_path / "meta.yml")
    assert meta.currency.denary == 0
    assert meta.stash.slots_total == 4
    assert meta.unlocks.origins == ["wygnaniec", "zielarka", "najemnik"]
    assert not meta.edited


def test_roundtrip_preserves_state(tmp_path: Path) -> None:
    path = tmp_path / "meta.yml"
    meta = MetaState()
    meta.currency.denary = 148
    meta.dziad.reputation = 3
    meta.codex.known["strzyga"] = "partial"
    meta.achievements["strzyga_deaths"] = 2
    meta.stash.items.append(StashedItem(item_id="toporek", instance={"memory_tag": "run-42"}))
    save_meta(meta, path)

    loaded = load_meta(path)
    assert loaded.currency.denary == 148
    assert loaded.dziad.reputation == 3
    assert loaded.codex.known["strzyga"] == "partial"
    assert loaded.stash.items[0].item_id == "toporek"
    assert loaded.stash.items[0].instance["memory_tag"] == "run-42"
    assert not loaded.edited, "clean save must not be flagged"


def test_hand_edit_flags_but_loads(tmp_path: Path) -> None:
    path = tmp_path / "meta.yml"
    meta = MetaState()
    meta.currency.denary = 10
    save_meta(meta, path)

    raw = yaml.safe_load(path.read_text())
    raw["currency"]["denary"] = 99999  # the classic
    path.write_text(yaml.safe_dump(raw))

    loaded = load_meta(path)
    assert loaded.currency.denary == 99999  # no punishment
    assert loaded.edited  # just honesty

    # The flag persists through the next legitimate save.
    save_meta(loaded, path)
    assert load_meta(path).edited


def test_unknown_fields_preserved(tmp_path: Path) -> None:
    path = tmp_path / "meta.yml"
    save_meta(MetaState(), path)
    raw = yaml.safe_load(path.read_text())
    raw["mod_extension"] = {"custom": True}
    path.write_text(yaml.safe_dump(raw))

    loaded = load_meta(path)  # flagged edited, fine
    save_meta(loaded, path)
    rewritten = yaml.safe_load(path.read_text())
    assert rewritten["mod_extension"] == {"custom": True}


def test_corrupt_file_backed_up_and_reset(tmp_path: Path) -> None:
    path = tmp_path / "meta.yml"
    path.write_text("[ this yaml never closes\nkey: [")
    meta = load_meta(path)
    assert meta.currency.denary == 0
    assert (tmp_path / "meta.yml.broken").exists()
    assert not path.exists()


def test_atomic_write_leaves_no_tmp(tmp_path: Path) -> None:
    path = tmp_path / "meta.yml"
    save_meta(MetaState(), path)
    assert not path.with_suffix(".yml.tmp").exists()
