"""M12 "Gusła": data packs — manifest, root chain, merging, validation."""

from pathlib import Path

import yaml

from wyraj.content.packs import (
    Pack,
    activate_packs,
    active_fingerprint,
    discover_packs,
    load_manifest,
)
from wyraj.core.game import Game

SEED = 42


def make_pack(root: Path, key: str = "testowy", **content_files: str) -> Path:
    """Write a minimal pack: manifest plus named YAML files ("bestiary/x.yml")."""
    pack_dir = root / key
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.yml").write_text(
        yaml.safe_dump(
            {"name": f"Pack {key}", "key": key, "version": "1.0", "license": "CC-BY-SA-4.0"}
        ),
        encoding="utf-8",
    )
    for rel, text in content_files.items():
        target = pack_dir / rel.replace("__", "/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return pack_dir


# ---- US 15.1: pack core ----------------------------------------------------


def test_manifest_loads_and_rejects_nc(tmp_path) -> None:
    import pytest

    from wyraj.content.packs import PackError

    pack = make_pack(tmp_path)
    manifest = load_manifest(pack)
    assert manifest.key == "testowy" and manifest.name == "Pack testowy"

    (pack / "pack.yml").write_text(
        yaml.safe_dump({"name": "X", "key": "x", "license": "CC-BY-NC-4.0"}), encoding="utf-8"
    )
    with pytest.raises(PackError):
        load_manifest(pack)


def test_discovery_skips_broken_and_duplicates(tmp_path) -> None:
    good = make_pack(tmp_path, "dobry")
    make_pack(tmp_path, "drugi")
    # A second pack claiming the same key, and a path with no manifest.
    twin = tmp_path / "twin"
    twin.mkdir()
    (twin / "pack.yml").write_text(
        yaml.safe_dump({"name": "Twin", "key": "dobry"}), encoding="utf-8"
    )
    empty = tmp_path / "empty"
    empty.mkdir()

    packs, notes = discover_packs([str(good), str(twin), str(tmp_path / "drugi"), str(empty)])
    assert [p.manifest.key for p in packs] == ["dobry", "drugi"]
    assert len(notes) == 2
    assert "duplicate" in notes[0] and "pack.yml" in notes[1]


def test_fingerprint_follows_activation(tmp_path) -> None:
    pack = Pack(path=make_pack(tmp_path), manifest=load_manifest(make_pack(tmp_path)))
    assert active_fingerprint() == []
    activate_packs([pack])
    assert active_fingerprint() == [["testowy", "1.0"]]
    activate_packs([])
    assert active_fingerprint() == []


def test_save_refuses_changed_pack_set(tmp_path) -> None:
    from wyraj.persistence.save import load_game, save_game

    game = Game(seed=SEED, meta_autosave=False)
    path = tmp_path / "save.json.gz"
    save_game(game, path)  # saved pack-free

    pack_dir = make_pack(tmp_path)
    activate_packs([Pack(path=pack_dir, manifest=load_manifest(pack_dir))])
    assert load_game(path) is None  # different world now

    # And the reverse: saved with a pack, loaded without.
    game2 = Game(seed=SEED, meta_autosave=False)
    save_game(game2, path)
    activate_packs([])
    assert load_game(path) is None
