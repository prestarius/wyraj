"""Game engine facade: owns world, map, scheduler, bus; advances turns.

UI and headless runners drive this identically: build Game(seed), then feed
player actions via `step()`. Between player actions the engine runs every
other actor that is due.
"""

from wyraj.content.bestiary import MonsterDef, load_bestiary
from wyraj.content.items import ItemDef, load_items
from wyraj.core.actions import Action, Get, Move, UseItem, Wait, WieldItem
from wyraj.core.components import (
    AI,
    Actor,
    Consumable,
    Health,
    Hunger,
    Inventory,
    Item,
    Lore,
    Melee,
    Player,
    Position,
    Renderable,
    WeaponStats,
    Wielding,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import EventBus, TurnEnded
from wyraj.core.map import GameMap
from wyraj.core.rng import RngStreams
from wyraj.core.scheduler import TurnScheduler
from wyraj.core.systems import ai, combat, hunger, items, movement
from wyraj.procgen.forest import generate_forest

FOV_RADIUS = 8
MONSTER_COUNT = 6
ITEM_COUNT = 8
MIN_SPAWN_DISTANCE = 8

PLAYER_HP = 20
PLAYER_SPEED = 100
PLAYER_DAMAGE = 4
PLAYER_TO_HIT = 75
PLAYER_SATIATION = 600


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

        self.map: GameMap = generate_forest(self.rng.worldgen.getrandbits(32))
        self.bestiary = bestiary if bestiary is not None else load_bestiary()
        self.items_catalog = items_catalog if items_catalog is not None else load_items()

        floors = self.map.floor_tiles()
        px, py = self.rng.worldgen.choice(floors)
        self.player: Entity = self.world.create(
            Player(),
            Position(px, py),
            Renderable(glyph="@", style="bold white"),
            Health(PLAYER_HP, PLAYER_HP),
            Melee(damage=PLAYER_DAMAGE, to_hit=PLAYER_TO_HIT),
            Actor(speed=PLAYER_SPEED),
            Hunger(PLAYER_SATIATION, PLAYER_SATIATION),
            Inventory(),
            Wielding(),
            Lore(key="player", name="you"),
        )

        self._spawn_monsters(floors, (px, py))
        self._spawn_items(floors, (px, py))

        self.scheduler = TurnScheduler(self.world)
        self.map.update_fov((px, py), FOV_RADIUS)
        self._advance_until_player_turn()

    def _spawn_monsters(self, floors: list[tuple[int, int]], player_pos: tuple[int, int]) -> None:
        px, py = player_pos
        candidates = [
            (x, y) for x, y in floors if max(abs(x - px), abs(y - py)) >= MIN_SPAWN_DISTANCE
        ]
        spots = self.rng.worldgen.sample(candidates, min(MONSTER_COUNT, len(candidates)))
        defs = sorted(self.bestiary.values(), key=lambda d: d.key)
        weights = [d.spawn_weight for d in defs]
        for x, y in spots:
            chosen = self.rng.worldgen.choices(defs, weights=weights)[0]
            self.spawn_monster(chosen, x, y)

    def _spawn_items(self, floors: list[tuple[int, int]], player_pos: tuple[int, int]) -> None:
        px, py = player_pos
        candidates = [(x, y) for x, y in floors if (x, y) != (px, py)]
        spots = self.rng.loot.sample(candidates, min(ITEM_COUNT, len(candidates)))
        defs = sorted(self.items_catalog.values(), key=lambda d: d.key)
        weights = [d.spawn_weight for d in defs]
        for x, y in spots:
            chosen = self.rng.loot.choices(defs, weights=weights)[0]
            self.spawn_item(chosen, x, y)

    def spawn_item(self, definition: ItemDef, x: int, y: int) -> Entity:
        entity = self.world.create(
            Position(x, y),
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
        if definition.kind == "consumable" and definition.effect and definition.power:
            self.world.add(entity, Consumable(effect=definition.effect, power=definition.power))
        return entity

    def spawn_monster(self, definition: MonsterDef, x: int, y: int) -> Entity:
        return self.world.create(
            Position(x, y),
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

    def step(self, action: Action) -> None:
        """Execute one player action, then run other actors until it is the
        player's turn again (or the player is dead)."""
        if self.game_over:
            return
        self._apply_player_action(action)
        self._update_player_fov()
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
                target = movement.blocking_entity_at(self.world, pos.x + dx, pos.y + dy)
                if target is not None and target != self.player:
                    combat.attack(self.world, self.bus, self.rng.combat, self.player, target)
                else:
                    movement.try_move(self.world, self.map, self.bus, self.player, dx, dy)
            case Get():
                items.pick_up(self.world, self.bus, self.player)
            case UseItem(item=item):
                items.use_item(self.world, self.bus, self.player, item)
            case WieldItem(item=item):
                items.wield(self.world, self.bus, self.player, item)
            case Wait():
                pass

    def _advance_until_player_turn(self) -> None:
        while not self.game_over:
            entity = self.scheduler.next_actor()
            if entity is None or entity == self.player:
                return
            if self.world.has(entity, AI):
                ai.take_turn(self.world, self.map, self.bus, self.rng.combat, entity)
                if self.world.expect(self.player, Health).hp <= 0:
                    self.game_over = True
            self.scheduler.spend(entity)

    def _update_player_fov(self) -> None:
        pos = self.world.expect(self.player, Position)
        self.map.update_fov((pos.x, pos.y), FOV_RADIUS)
