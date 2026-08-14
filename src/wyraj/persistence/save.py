"""Single-slot save/load: gzip-compressed JSON.

Permadeath contract: the save is deleted the moment it is loaded and on
death; quitting with save re-writes it. Narration session state (variant
memory, recency) is not persisted — narration is cosmetic; gameplay RNG
streams are restored bit-exactly.
"""

import gzip
import json
import os
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from wyraj.core import components as components_module
from wyraj.core.components import StatusEffect, StatusEffects
from wyraj.core.ecs import Entity
from wyraj.core.game import Game
from wyraj.core.map import GameMap, Tile
from wyraj.core.rng import STREAM_NAMES, RngStreams
from wyraj.core.scheduler import TurnScheduler

SAVE_VERSION = 1

_TILE_TO_CHAR = {
    Tile.WALL: "#",
    Tile.FLOOR: ".",
    Tile.WATER: "~",
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
    home = os.environ.get("WYRAJ_HOME")
    base = Path(home) if home else Path.home() / ".wyraj"
    return base / "save.json.gz"


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
    game.player = payload["player"]

    game.rng = RngStreams(game.seed)
    for name in STREAM_NAMES:
        version, internal, gauss = payload["rng"][name]
        game.rng.set_state(name, (version, tuple(internal), gauss))

    from wyraj.content.bestiary import load_bestiary
    from wyraj.content.hooks import load_hooks
    from wyraj.content.items import load_items
    from wyraj.content.loot import load_loot_tables
    from wyraj.core.ecs import World
    from wyraj.core.events import EventBus

    game.bestiary = load_bestiary()
    game.items_catalog = load_items()
    game.loot_tables = load_loot_tables()
    game.hooks_catalog = load_hooks()

    game.levels = {int(d): _decode_map(m) for d, m in payload["levels"].items()}

    game.world = World()
    game.bus = EventBus()
    for entity_str, component_dicts in payload["entities"].items():
        entity: Entity = int(entity_str)
        game.world.restore_entity(entity, [_decode_component(dict(c)) for c in component_dicts])

    game.scheduler = TurnScheduler(game.world)
    from wyraj.core.components import Position

    pos = game.world.expect(game.player, Position)
    game.map.update_fov((pos.x, pos.y), game.fov_radius)
    return game
