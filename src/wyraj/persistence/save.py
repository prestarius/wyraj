"""Single-slot save/load: gzip-compressed JSON.

Permadeath contract: the save is deleted the moment it is loaded and on
death; quitting with save re-writes it. Narration session state (variant
memory, recency) is not persisted — narration is cosmetic; gameplay RNG
streams are restored bit-exactly.
"""

import gzip
import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from wyraj.core import components as components_module
from wyraj.core.components import StatusEffect, StatusEffects
from wyraj.core.ecs import Entity
from wyraj.core.events import AttackResolved, StarvationHit, StatusTick
from wyraj.core.game import Game
from wyraj.core.map import GameMap, Tile
from wyraj.core.rng import STREAM_NAMES, RngStreams
from wyraj.core.scheduler import TurnScheduler
from wyraj.persistence.paths import wyraj_home

SAVE_VERSION = 2

_TILE_TO_CHAR = {
    Tile.WALL: "#",
    Tile.FLOOR: ".",
    Tile.WATER: "~",
    Tile.SHAFT: "o",
    Tile.STAIRS_DOWN: ">",
    Tile.STAIRS_UP: "<",
}
_CHAR_TO_TILE = {c: t for t, c in _TILE_TO_CHAR.items()}

_COMPONENT_TYPES: dict[str, type[Any]] = {
    name: obj
    for name, obj in vars(components_module).items()
    if isinstance(obj, type) and hasattr(obj, "__dataclass_fields__")
}


def save_path() -> Path:
    return wyraj_home() / "save.json.gz"


def has_save(path: Path | None = None) -> bool:
    return (path or save_path()).exists()


def delete_save(path: Path | None = None) -> None:
    target = path or save_path()
    target.unlink(missing_ok=True)


def _encode_component(component: Any) -> dict[str, Any]:
    data = asdict(component)
    data["__type__"] = type(component).__name__
    return data


def _decode_component(data: dict[str, Any]) -> Any:
    type_name = data.pop("__type__")
    cls = _COMPONENT_TYPES[type_name]
    if cls is StatusEffects:
        effects = tuple(StatusEffect(**e) for e in data.get("effects", []))
        return StatusEffects(effects=effects)
    kwargs = {
        f.name: tuple(data[f.name]) if isinstance(data.get(f.name), list) else data.get(f.name)
        for f in fields(cls)
    }
    return cls(**kwargs)


def _encode_map(game_map: GameMap) -> dict[str, Any]:
    return {
        "biome": game_map.biome,
        "tiles": ["".join(_TILE_TO_CHAR[t] for t in row) for row in game_map.tiles],
        "explored": sorted(game_map.explored),
    }


def _decode_map(data: dict[str, Any]) -> GameMap:
    tiles = [[_CHAR_TO_TILE[c] for c in row] for row in data["tiles"]]
    game_map = GameMap(tiles, biome=data["biome"])
    game_map.explored = {(x, y) for x, y in data["explored"]}
    return game_map


def save_game(game: Game, path: Path | None = None) -> Path:
    target = path or save_path()
    payload = {
        "version": SAVE_VERSION,
        "seed": game.seed,
        "turn": game.turn,
        "depth": game.depth,
        "game_over": game.game_over,
        "codex_seen": sorted(game.codex_seen),
        "origin": game.origin.key,
        "max_depth_reached": game.max_depth_reached,
        "dziad_traded_this_run": getattr(game, "dziad_traded_this_run", False),
        "dziad_seen_this_run": getattr(game, "dziad_seen_this_run", False),
        "dziad_met_this_run": getattr(game, "dziad_met_this_run", False),
        "dziad_last_depth": getattr(game, "dziad_last_depth", 0),
        "blizny": getattr(game, "blizny", 0),
        "was_dying": getattr(game, "_was_dying", False),
        "weapon_kills": getattr(game, "weapon_kills", {}),
        "dziad_greeted_weapon": getattr(game, "_dziad_greeted_weapon", False),
        "glebiej": getattr(game, "glebiej", False),
        "kupala_bloomed": getattr(game, "kupala_bloomed", False),
        "wij_phase": getattr(game, "wij_phase", "buried"),
        "wij_lift": getattr(game, "wij_lift", 0),
        "wij_respawn": getattr(game, "_wij_respawn", 12),
        "errands": getattr(game, "errands", {}),
        "fates_announced": getattr(game, "_fates_announced", False),
        "player": game.player,
        "rng": game.rng.get_states(),
        "levels": {str(depth): _encode_map(m) for depth, m in game.levels.items()},
        "entities": {
            str(entity): [_encode_component(c) for c in game.world.components_of(entity)]
            for entity in game.world.all_entities()
        },
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(payload).encode("utf-8")))
    return target


def load_game(path: Path | None = None) -> Game | None:
    """Load and DELETE the save (permadeath: one life, one file)."""
    target = path or save_path()
    if not target.exists():
        return None
    payload = json.loads(gzip.decompress(target.read_bytes()).decode("utf-8"))
    delete_save(target)
    if payload.get("version") != SAVE_VERSION:
        return None

    game = Game.__new__(Game)
    game.seed = payload["seed"]
    game.turn = payload["turn"]
    game.depth = payload["depth"]
    game.game_over = payload["game_over"]
    game.codex_seen = set(payload["codex_seen"])
    game.max_depth_reached = payload.get("max_depth_reached", game.depth)
    game.death_cause = None
    game.death_by_key = None
    game.player = payload["player"]

    game.rng = RngStreams(game.seed)
    for name in STREAM_NAMES:
        version, internal, gauss = payload["rng"][name]
        game.rng.set_state(name, (version, tuple(internal), gauss))

    from wyraj.content.bestiary import load_bestiary
    from wyraj.content.economy import load_drops, load_dziad_shop, load_prices, load_village_shop
    from wyraj.content.epithets import load_epithets
    from wyraj.content.hooks import load_hooks
    from wyraj.content.items import load_items
    from wyraj.content.loot import load_loot_tables
    from wyraj.content.origins import load_origins
    from wyraj.core.ecs import World
    from wyraj.core.events import EventBus
    from wyraj.persistence.meta import load_meta

    game.bestiary = load_bestiary()
    game.items_catalog = load_items()
    game.loot_tables = load_loot_tables()
    game.hooks_catalog = load_hooks()
    game.origins_catalog = load_origins()
    game.origin = game.origins_catalog[payload.get("origin", "wygnaniec")]
    game.drops = load_drops()
    game.prices = load_prices()
    game.village_shop = load_village_shop()
    game.meta = load_meta()
    game.meta_autosave = True
    game.dziad_traded_this_run = payload.get("dziad_traded_this_run", False)
    game.dziad_seen_this_run = payload.get("dziad_seen_this_run", False)
    game.dziad_met_this_run = payload.get("dziad_met_this_run", False)
    game.dziad_last_depth = payload.get("dziad_last_depth", 0)
    game.dziad_shop = load_dziad_shop()
    # M7 "Sylwetka" run state (cosmetic last_foe intentionally resets to None)
    game.blizny = payload.get("blizny", 0)
    game._was_dying = payload.get("was_dying", False)
    game.weapon_kills = dict(payload.get("weapon_kills", {}))
    game._dziad_greeted_weapon = payload.get("dziad_greeted_weapon", False)
    game.last_foe = None
    game.quickslot_auto_refill = True  # the config knob is re-applied by the app
    game.epithets_catalog = load_epithets()
    # M8 "Dno" run state
    from wyraj.content.errands import load_errands
    from wyraj.core.game import MAX_DEPTH, WIJ_RESPAWN_TURNS, _level_seed
    from wyraj.procgen.vault import generate_vault

    game.errands_catalog = load_errands()
    game.errands = dict(payload.get("errands", {}))
    game._fates_announced = payload.get("fates_announced", False)
    game.glebiej = payload.get("glebiej", False)
    game.kupala_bloomed = payload.get("kupala_bloomed", False)
    game.victory = False
    game.victory_epilogue = ""
    game.wij_phase = payload.get("wij_phase", "buried")
    game.wij_lift = payload.get("wij_lift", 0)
    game._wij_respawn = payload.get("wij_respawn", WIJ_RESPAWN_TURNS)
    game.vault = (
        generate_vault(_level_seed(game.seed, MAX_DEPTH))
        if str(MAX_DEPTH) in payload["levels"]
        else None
    )

    game.levels = {int(d): _decode_map(m) for d, m in payload["levels"].items()}

    game.world = World()
    game.bus = EventBus()
    game.bus.subscribe(AttackResolved, game._track_kill_cause)
    game.bus.subscribe(StarvationHit, game._track_starvation_cause)
    game.bus.subscribe(StatusTick, game._track_dot_cause)
    from wyraj.core.events import EntityDied, ItemBought, ItemPickedUp

    game.bus.subscribe(EntityDied, game._on_monster_died)
    game.bus.subscribe(AttackResolved, game._on_attack_for_pane)
    game.bus.subscribe(ItemPickedUp, game._on_item_gained)
    game.bus.subscribe(ItemBought, game._on_item_gained)
    for entity_str, component_dicts in payload["entities"].items():
        entity: Entity = int(entity_str)
        game.world.restore_entity(entity, [_decode_component(dict(c)) for c in component_dicts])

    game.scheduler = TurnScheduler(game.world)
    from wyraj.core.components import Position

    pos = game.world.expect(game.player, Position)
    game.map.update_fov((pos.x, pos.y), game.fov_radius)
    return game
