"""Game engine facade: owns world, map, scheduler, bus; advances turns.

UI and headless runners drive this identically: build Game(seed), then feed
player actions via `step()`. Between player actions the engine runs every
other actor that is due.
"""

import hashlib
import random

from wyraj.content.bestiary import MonsterDef, load_bestiary
from wyraj.content.items import ItemDef, load_items
from wyraj.content.loot import load_loot_tables
from wyraj.core.actions import (
    Action,
    Ascend,
    Descend,
    Get,
    Move,
    UseItem,
    Wait,
    WearItem,
    WieldItem,
)
from wyraj.core.components import (
    AI,
    Actor,
    ArmorStats,
    AttackStatus,
    Consumable,
    Health,
    Hunger,
    Inventory,
    Item,
    LightSource,
    Lore,
    Melee,
    OnLevel,
    Player,
    Position,
    Renderable,
    StatusEffects,
    WeaponStats,
    Wielding,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus, LevelChanged, LoreDiscovered, TurnEnded
from wyraj.core.map import GameMap, Tile
from wyraj.core.refs import ref_for
from wyraj.core.rng import RngStreams
from wyraj.core.scheduler import TurnScheduler
from wyraj.core.systems import ai, combat, hunger, items, movement, status
from wyraj.procgen.forest import generate_forest
from wyraj.procgen.kurhany import generate_kurhan

FOV_RADIUS = 8
MONSTER_COUNT = 6
ITEM_COUNT = 8
MIN_SPAWN_DISTANCE = 8
MAX_DEPTH = 3  # deepest kurhan level
CRYPT_FOV_RADIUS = 4  # unlit barrow darkness

PLAYER_HP = 20
PLAYER_SPEED = 100
PLAYER_DAMAGE = 4
PLAYER_TO_HIT = 75
PLAYER_SATIATION = 600


def _level_seed(master_seed: int, depth: int) -> int:
    digest = hashlib.sha256(f"{master_seed}:level:{depth}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


class Game:
    def __init__(
        self,
        seed: int,
        bestiary: dict[str, MonsterDef] | None = None,
        items_catalog: dict[str, ItemDef] | None = None,
    ) -> None:
        self.seed = seed
        self.rng = RngStreams(seed)
        self.world = World()
        self.bus = EventBus()
        self.turn = 0
        self.game_over = False
        self.codex_seen: set[str] = set()
        self.depth = 0
        self.levels: dict[int, GameMap] = {}

        self.bestiary = bestiary if bestiary is not None else load_bestiary()
        self.items_catalog = items_catalog if items_catalog is not None else load_items()
        self.loot_tables = load_loot_tables()

        self.levels[0] = generate_forest(_level_seed(seed, 0))
        floors = self.map.floor_tiles()
        level_rng = random.Random(_level_seed(seed, 0) ^ 0xA5A5)
        px, py = level_rng.choice(floors)
        self.player: Entity = self.world.create(
            Player(),
            Position(px, py),
            OnLevel(0),
            Renderable(glyph="@", style="bold white"),
            Health(PLAYER_HP, PLAYER_HP),
            Melee(damage=PLAYER_DAMAGE, to_hit=PLAYER_TO_HIT),
            Actor(speed=PLAYER_SPEED),
            Hunger(PLAYER_SATIATION, PLAYER_SATIATION),
            Inventory(),
            Wielding(),
            Lore(key="player", name="you"),
        )

        self._populate_level(0, level_rng, avoid=(px, py))

        self.scheduler = TurnScheduler(self.world)
        self.map.update_fov((px, py), FOV_RADIUS)
        self._advance_until_player_turn()

    @property
    def map(self) -> GameMap:
        return self.levels[self.depth]

    def _biome_defs(self, biome: str) -> list[MonsterDef]:
        return [d for d in sorted(self.bestiary.values(), key=lambda d: d.key) if biome in d.biomes]

    def _populate_level(
        self, depth: int, level_rng: random.Random, avoid: tuple[int, int] | None = None
    ) -> None:
        """Spawn monsters and items on a level. Pure function of the level RNG,
        so lazily generated levels are deterministic regardless of play order."""
        game_map = self.levels[depth]
        floors = game_map.floor_tiles()
        biome = game_map.biome

        monster_count = MONSTER_COUNT + (depth * 2 if biome == "kurhany" else 0)
        candidates = floors
        if avoid is not None:
            ax, ay = avoid
            candidates = [
                (x, y) for x, y in floors if max(abs(x - ax), abs(y - ay)) >= MIN_SPAWN_DISTANCE
            ]
        defs = self._biome_defs(biome)
        weights = [d.spawn_weight for d in defs]
        spots = level_rng.sample(candidates, min(monster_count, len(candidates)))
        for x, y in spots:
            chosen = level_rng.choices(defs, weights=weights)[0]
            self.spawn_monster(chosen, x, y, depth)

        table = self.loot_tables.get(biome)
        if table is not None:
            item_keys = sorted(table.weights)
            item_weights = [table.weights[k] for k in item_keys]
            item_count = table.items_for_depth(depth)
        else:
            item_keys = sorted(self.items_catalog)
            item_weights = [self.items_catalog[k].spawn_weight for k in item_keys]
            item_count = ITEM_COUNT
        item_candidates = [t for t in floors if t != avoid]
        item_spots = level_rng.sample(item_candidates, min(item_count, len(item_candidates)))
        for x, y in item_spots:
            chosen_key = level_rng.choices(item_keys, weights=item_weights)[0]
            self.spawn_item(self.items_catalog[chosen_key], x, y, depth)

    def _ensure_level(self, depth: int) -> None:
        if depth in self.levels:
            return
        self.levels[depth] = generate_kurhan(
            _level_seed(self.seed, depth), with_down_stairs=depth < MAX_DEPTH
        )
        self._populate_level(depth, random.Random(_level_seed(self.seed, depth) ^ 0xA5A5))

    def spawn_item(self, definition: ItemDef, x: int, y: int, depth: int = 0) -> Entity:
        entity = self.world.create(
            Position(x, y),
            OnLevel(depth),
            Renderable(
                glyph=definition.glyph,
                style=definition.style,
                ascii_glyph=definition.ascii_glyph,
            ),
            Item(key=definition.key, kind=definition.kind),
            Lore(key=definition.key, name=definition.name, description=definition.description),
        )
        if definition.kind == "weapon" and definition.damage is not None:
            self.world.add(entity, WeaponStats(damage=definition.damage))
        if definition.kind == "armor" and definition.protection is not None:
            self.world.add(entity, ArmorStats(protection=definition.protection))
        if definition.kind == "consumable" and definition.effect and definition.power:
            self.world.add(entity, Consumable(effect=definition.effect, power=definition.power))
        return entity

    def spawn_monster(self, definition: MonsterDef, x: int, y: int, depth: int = 0) -> Entity:
        entity = self.world.create(
            Position(x, y),
            OnLevel(depth),
            Renderable(
                glyph=definition.glyph,
                style=definition.style,
                ascii_glyph=definition.ascii_glyph,
            ),
            Health(definition.hp, definition.hp),
            Melee(damage=definition.damage, to_hit=definition.to_hit),
            Actor(speed=definition.speed),
            AI(behavior=definition.behavior),
            Lore(
                key=definition.key,
                name=definition.name,
                epithets=tuple(definition.epithets),
                description=definition.description,
            ),
        )
        if definition.attack_status is not None:
            spec = definition.attack_status
            self.world.add(
                entity,
                AttackStatus(
                    kind=spec.kind, chance=spec.chance, duration=spec.duration, power=spec.power
                ),
            )
        return entity

    def _change_level(self, new_depth: int, direction: str) -> None:
        self._ensure_level(new_depth)
        target_map = self.levels[new_depth]
        arrival = (
            target_map.find_tile(Tile.STAIRS_UP)
            if direction == "down"
            else target_map.find_tile(Tile.STAIRS_DOWN)
        )
        if arrival is None:  # defensive: generators always place stairs
            arrival = target_map.floor_tiles()[0]
        self.depth = new_depth
        self.world.add(self.player, OnLevel(new_depth))
        self.world.add(self.player, Position(*arrival))
        self.bus.publish(LevelChanged(depth=new_depth, direction=direction))

    def step(self, action: Action) -> None:
        """Execute one player action, then run other actors until it is the
        player's turn again (or the player is dead)."""
        if self.game_over:
            return
        self._apply_player_action(action)
        self._update_player_fov()
        self._tick_statuses()
        hunger.tick(self.world, self.bus, self.player, self.turn + 1)
        if self.world.expect(self.player, Health).hp <= 0:
            self.game_over = True
        self.scheduler.spend(self.player)
        self._advance_until_player_turn()
        self.turn += 1
        # TurnEnded closes the whole round (player + monsters) so the
        # narration TurnComposer can flush a complete paragraph.
        self.bus.publish(TurnEnded(self.turn))

    def _apply_player_action(self, action: Action) -> None:
        match action:
            case Move(dx=dx, dy=dy):
                pos = self.world.expect(self.player, Position)
                target = movement.blocking_entity_at(self.world, pos.x + dx, pos.y + dy, self.depth)
                if target is not None and target != self.player:
                    combat.attack(self.world, self.bus, self.rng.combat, self.player, target)
                else:
                    movement.try_move(self.world, self.map, self.bus, self.player, dx, dy)
            case Descend():
                pos = self.world.expect(self.player, Position)
                if self.map.tiles[pos.y][pos.x] is Tile.STAIRS_DOWN and self.depth < MAX_DEPTH:
                    self._change_level(self.depth + 1, "down")
            case Ascend():
                pos = self.world.expect(self.player, Position)
                if self.map.tiles[pos.y][pos.x] is Tile.STAIRS_UP and self.depth > 0:
                    self._change_level(self.depth - 1, "up")
            case Get():
                items.pick_up(self.world, self.bus, self.player)
            case UseItem(item=item):
                items.use_item(self.world, self.bus, self.player, item)
            case WieldItem(item=item):
                items.wield(self.world, self.bus, self.player, item)
            case WearItem(item=item):
                items.wear(self.world, self.bus, self.player, item)
            case Wait():
                pass

    def _advance_until_player_turn(self) -> None:
        while not self.game_over:
            entity = self.scheduler.next_actor(self.depth)
            if entity is None or entity == self.player:
                return
            if self.world.has(entity, AI):
                ai.take_turn(self.world, self.map, self.bus, self.rng.combat, entity)
                if self.world.expect(self.player, Health).hp <= 0:
                    self.game_over = True
            self.scheduler.spend(entity)

    @property
    def fov_radius(self) -> int:
        """Crypts are dark; a lit gromnica pushes the dark back."""
        if self.depth > 0 and self.world.get(self.player, LightSource) is None:
            return CRYPT_FOV_RADIUS
        return FOV_RADIUS

    def _tick_statuses(self) -> None:
        actors = [self.player] + [
            e
            for e in self.world.entities_with(StatusEffects)
            if e != self.player and movement.level_of(self.world, e) == self.depth
        ]
        for entity in actors:
            if self.world.is_alive(entity):
                status.tick(self.world, self.bus, entity)

    def _update_player_fov(self) -> None:
        pos = self.world.expect(self.player, Position)
        self.map.update_fov((pos.x, pos.y), self.fov_radius)
        self._discover_visible()

    def _discover_visible(self) -> None:
        for entity, (_ai, lore, pos) in self.world.query(AI, Lore, Position):
            if movement.level_of(self.world, entity) != self.depth:
                continue
            if (pos.x, pos.y) in self.map.visible and lore.key not in self.codex_seen:
                self.codex_seen.add(lore.key)
                self.bus.publish(LoreDiscovered(entity=ref_for(self.world, entity)))
