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
        name = rel.replace("__", "/")
        if name.endswith("_yml"):
            name = name[: -len("_yml")] + ".yml"
        target = pack_dir / name
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


# ---- US 15.2: keyed-catalog merging ----------------------------------------


def _activate(pack_dir: Path) -> None:
    activate_packs([Pack(path=pack_dir, manifest=load_manifest(pack_dir))])


def test_pack_overrides_and_extends_bestiary(tmp_path) -> None:
    from wyraj.content.bestiary import load_bestiary

    base = load_bestiary()
    pack = make_pack(
        tmp_path,
        bestiary__coastal_yml=yaml.safe_dump(
            {
                "wilk": {  # override whole entry: a coastal wolf is bigger
                    "name": "wilk morski",
                    "glyph": "w",
                    "ascii_glyph": "w",
                    "hp": 99,
                    "speed": 100,
                    "damage": 3,
                    "to_hit": 60,
                    "biomes": ["puszcza"],
                },
                "topielica": {
                    "name": "topielica",
                    "glyph": "t",
                    "ascii_glyph": "t",
                    "hp": 12,
                    "speed": 90,
                    "damage": 4,
                    "to_hit": 65,
                    "biomes": ["bagna"],
                },
            }
        ),
    )
    _activate(pack)
    merged = load_bestiary()
    assert merged["wilk"].hp == 99 and merged["wilk"].name == "wilk morski"
    assert "topielica" in merged
    assert set(merged) == set(base) | {"topielica"}
    activate_packs([])
    assert load_bestiary()["wilk"].hp == base["wilk"].hp  # base untouched


def test_pack_extends_items_hooks_loot_errands_epithets(tmp_path) -> None:
    from wyraj.content.epithets import load_epithets
    from wyraj.content.errands import load_errands
    from wyraj.content.hooks import load_hooks
    from wyraj.content.items import load_items
    from wyraj.content.loot import load_loot_tables

    pack = make_pack(
        tmp_path,
        items__extra_yml=yaml.safe_dump(
            {
                "bursztyn": {
                    "name": "amber lump",
                    "glyph": "*",
                    "ascii_glyph": "*",
                    "kind": "trophy",
                    "spawn_weight": 0,
                }
            }
        ),
        hooks__extra_yml=yaml.safe_dump(
            {
                "wrak": {
                    "name": "a rotted wreck",
                    "glyph": "&",
                    "ascii_glyph": "&",
                    "biomes": ["bagna"],
                }
            }
        ),
        loot__bagna_yml=yaml.safe_dump({"count": 9, "weights": {"odwar": 1}}),
        errands__extra_yml=yaml.safe_dump(
            {
                "bursztynowa_prosba": {
                    "giver": "trader",
                    "kind": "hunt",
                    "target": "wilk",
                    "proof": "wilczy_kiel",
                    "depth": 1,
                    "reward": {"denary": 50},
                }
            }
        ),
        epithets__epithets_yml=yaml.safe_dump(
            {"utopiec": {"en": "Drowner-bane", "pl": "Topielcza zguba"}}
        ),
    )
    _activate(pack)
    assert "bursztyn" in load_items()
    assert "wrak" in load_hooks()
    assert load_loot_tables()["bagna"].count == 9  # whole-file override by stem
    assert "bursztynowa_prosba" in load_errands()
    assert "utopiec" in load_epithets()


def test_later_pack_wins(tmp_path) -> None:
    from wyraj.content.items import load_items

    entry = {
        "name": "amber lump",
        "glyph": "*",
        "ascii_glyph": "*",
        "kind": "trophy",
        "spawn_weight": 0,
    }
    first = make_pack(tmp_path, "pierwszy", items__a_yml=yaml.safe_dump({"bursztyn": entry}))
    second = make_pack(
        tmp_path,
        "drugi",
        items__a_yml=yaml.safe_dump({"bursztyn": {**entry, "name": "sea amber"}}),
    )
    packs, notes = discover_packs([str(first), str(second)])
    assert notes == []
    activate_packs(packs)
    assert load_items()["bursztyn"].name == "sea amber"


# ---- US 15.3: narration, locale, audio, languages --------------------------


def test_pack_overrides_and_extends_narration(tmp_path) -> None:
    from wyraj.narration.templates import load_pack

    base_rules = load_pack("en").rules
    pack = make_pack(
        tmp_path,
        narration__en__extra_yml=yaml.safe_dump(
            {
                "talked_to": {"gossip": [{"weight": 1, "en": "The dziad only points at the sea."}]},
                "lore_discovered": {
                    "topielica": [{"weight": 1, "en": "A pale shape stands in the reeds."}]
                },
            }
        ),
    )
    _activate(pack)
    rules = load_pack("en").rules
    assert len(rules[("talked_to", "gossip")]) == 1  # whole-rule override: pack owns it
    assert ("lore_discovered", "topielica") in rules  # extension
    assert rules[("talked_to", "innkeeper")] == base_rules[("talked_to", "innkeeper")]


def test_language_pack_makes_a_new_lang_real(tmp_path) -> None:
    import random

    from wyraj.content.locale import available_languages, load_locale
    from wyraj.narration.templates import TemplateNarrator, load_pack
    from wyraj.ui import i18n

    pack = make_pack(
        tmp_path,
        locale__de_yml=yaml.safe_dump({"turn": "Zug {n}", "purse": "{n} Denare im Beutel"}),
        narration__de__combat_yml=yaml.safe_dump(
            {
                "attack_resolved": {
                    "player_hit": [{"weight": 1, "de": "Dein Hieb trifft {defender.name}."}]
                }
            }
        ),
    )
    _activate(pack)
    assert "de" in available_languages()
    assert load_locale("de")["turn"] == "Zug {n}"

    i18n.set_language("de")
    try:
        assert i18n.t("turn", n=7) == "Zug 7"
        assert i18n.t("codex_title")  # EN merged underneath fills the rest
    finally:
        i18n.set_language("en")

    from tests.test_narration_templates import REGISTRY, fixture_event

    narrator = TemplateNarrator(
        load_pack("de"), random.Random(1), REGISTRY, fallback_pack=load_pack("en")
    )
    hit = narrator.compose(fixture_event("attack_resolved", "player_hit"))
    assert hit and "Hieb" in hit[0].text
    fallback = narrator.compose(fixture_event("rested", None))
    assert fallback and fallback[0].text  # missing rule narrates in EN


def test_pack_audio_resolves_to_pack_files(tmp_path) -> None:
    from wyraj.content.audio import load_audio_catalog

    pack = make_pack(
        tmp_path,
        audio__sounds_yml=yaml.safe_dump(
            {"beds": {"wies": {"file": "beds/sea_wies.wav", "volume": 0.5}}}
        ),
    )
    (pack / "audio" / "beds").mkdir(parents=True)
    (pack / "audio" / "beds" / "sea_wies.wav").write_bytes(b"RIFF")
    _activate(pack)
    catalog = load_audio_catalog()
    wies = Path(catalog.beds["wies"].file)
    assert wies.is_absolute() and wies.is_relative_to(pack)
    dno = Path(catalog.beds["dno"].file)  # untouched base entry
    assert "pack" not in str(dno)


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
