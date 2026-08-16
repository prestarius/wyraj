"""Game engine facade: owns world, map, scheduler, bus; advances turns.

UI and headless runners drive this identically: build Game(seed), then feed
player actions via `step()`. Between player actions the engine runs every
other actor that is due.
"""

import hashlib
import random
from dataclasses import replace
from typing import ClassVar

from wyraj.content.bestiary import MonsterDef, load_bestiary
from wyraj.content.economy import (
    load_drops,
    load_dziad_shop,
    load_offerings,
    load_prices,
    load_village_shop,
)
from wyraj.content.epithets import load_epithets
from wyraj.content.hooks import HookDef, load_hooks
from wyraj.content.items import ItemDef, load_items
from wyraj.content.loot import load_loot_tables
from wyraj.content.origins import OriginDef, load_origins
from wyraj.core.actions import (
    Action,
    Ascend,
    BindQuickslot,
    BuyItem,
    ClearQuickslot,
    DepositItem,
    Descend,
    Get,
    MakeOffering,
    Move,
    Rest,
    SellItem,
    UnequipSlot,
    UpgradeStash,
    UseItem,
    UseQuickslot,
    Wait,
    WearItem,
    WieldItem,
    WithdrawStash,
)
from wyraj.core.components import (
    AI,
    Actor,
    ArmorStats,
    AttackStatus,
    Channeling,
    CoinPile,
    Consumable,
    Epithet,
    Health,
    Hunger,
    Inventory,
    Item,
    ItemMemory,
    Lifting,
    LightSource,
    Lore,
    Melee,
    OnLevel,
    Perch,
    Player,
    Position,
    Purse,
    Renderable,
    Rite,
    Shrine,
    StashChest,
    StatusEffect,
    StatusEffects,
    StoryHook,
    Swimmer,
    Villager,
    WeaponStats,
    Wearing,
    Wielding,
    Znamie,
)
from wyraj.core.ecs import Entity, World
from wyraj.core.events import (
    AttackResolved,
    BliznaEarned,
    CoinsBanked,
    CoinsPicked,
    CraneRefused,
    CraneReturn,
    CraneSummonCompleted,
    CraneSummonInterrupted,
    CraneSummonStarted,
    DeepDescended,
    DziadRecognized,
    EntityDied,
    EntityRef,
    EventBus,
    ItemBought,
    ItemPickedUp,
    ItemSold,
    LevelChanged,
    LoreDiscovered,
    MetaTransaction,
    OfferingMade,
    Outcome,
    QuickslotUsed,
    Rested,
    RiteCompleted,
    RiteInterrupted,
    RiteStarted,
    SeenByWij,
    ShrineVisited,
    StarvationHit,
    StashDeposited,
    StashOpened,
    StashUpgraded,
    StashWithdrawn,
    StatusTick,
    TalkedTo,
    TurnEnded,
    WeaponNamed,
    WeaponRecognized,
    WijAttackFutile,
    WijGazeOpened,
    WijLidLifted,
    WijStirred,
    ZnamiePlaced,
)
from wyraj.core.fov import compute_fov
from wyraj.core.map import GameMap, Tile
from wyraj.core.refs import ref_for
from wyraj.core.rng import RngStreams
from wyraj.core.scheduler import TurnScheduler
from wyraj.core.systems import ai, combat, hunger, items, movement, quickslots, status
from wyraj.persistence.meta import MetaState, StashedItem, save_meta
from wyraj.procgen.bagna import generate_bagna
from wyraj.procgen.forest import generate_forest
from wyraj.procgen.kurhany import generate_kurhan
from wyraj.procgen.vault import VaultLayout, generate_vault
from wyraj.procgen.village import generate_village

FOV_RADIUS = 8
MONSTER_COUNT = 6
ITEM_COUNT = 8
MIN_SPAWN_DISTANCE = 8
MAX_DEPTH = 8  # world chain: 0 wies, 1 puszcza, 2 bagna, 3-8 kurhany (M8 "Dno")
CRYPT_FIRST_DEPTH = 3
CRYPT_FOV_RADIUS = 4  # unlit barrow darkness at crypts 1-3
LAST_SKY_DEPTH = 6  # deepest crypt with collapsed-ceiling shafts (crane exit)
REST_SATIATION_COST = 100

PLAYER_HP = 20
PLAYER_SPEED = 100
DYING_BAND = 0.10  # M7 §2.3: below this, the run is one bad turn from over
EPITHET_KILLS = 7  # M7 §6.2 tuning knob: kills of one species to earn a name

# M8 "Dno" tuning table (spec §5)
WIJ_LIFT_PER_SLUGA = 2  # lift gained per channeling servant per turn
WIJ_KNOCKBACK = 10  # lift lost when a servant dies at the bottom
WIJ_RESPAWN_TURNS = 12  # niche birthing cadence
WIJ_MAX_SLUGI = 4  # concurrent servants
WIJ_GAZE_DAMAGE = 6  # true damage per seen turn; armor means nothing to him
WIJ_GAZE_RADIUS = 30  # the gaze reaches the whole hall
WIJ_STIR_AT = 25
WIJ_LID_AT = 60
WIJ_GAZE_AT = 100
RITE_TURNS = 6  # zamknięcie powiek: turns of pressing
RITE_ITEM = "sol_swiecona"  # consumed the moment the rite begins
GLEBIEJ_SPAWN_BONUS = 2
GLEBIEJ_LOOT_BONUS = 1
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
        origin: str = "wygnaniec",
        bestiary: dict[str, MonsterDef] | None = None,
        items_catalog: dict[str, ItemDef] | None = None,
        meta: MetaState | None = None,
        meta_autosave: bool = True,
        glebiej: bool = False,
    ) -> None:
        self.seed = seed
        self.rng = RngStreams(seed)
        self.world = World()
        self.bus = EventBus()
        self.turn = 0
        self.game_over = False
        self.codex_seen: set[str] = set()  # seeded from meta after content loads
        self.depth = 0
        self.max_depth_reached = 0
        self.death_cause: str | None = None
        self.death_by_key: str | None = None
        self.levels: dict[int, GameMap] = {}
        self.bus.subscribe(AttackResolved, self._track_kill_cause)
        self.bus.subscribe(StarvationHit, self._track_starvation_cause)
        self.bus.subscribe(StatusTick, self._track_dot_cause)

        self.bestiary = bestiary if bestiary is not None else load_bestiary()
        self.items_catalog = items_catalog if items_catalog is not None else load_items()
        self.loot_tables = load_loot_tables()
        self.hooks_catalog = load_hooks()
        self.origins_catalog = load_origins()
        self.origin: OriginDef = self.origins_catalog[origin]
        self.drops = load_drops()
        self.prices = load_prices()
        self.village_shop = load_village_shop()
        self.meta = meta if meta is not None else MetaState()
        self.meta_autosave = meta_autosave
        self.dziad_shop = load_dziad_shop()
        self.offerings = load_offerings()
        # Knowledge survives death (M6 §8.1): pre-known kinds are not
        # re-discovered, and their entries open at their earned tier.
        self.codex_seen |= set(self.meta.codex.known)
        self.bus.subscribe(LoreDiscovered, self._on_lore_discovered)
        self.dziad_seen_this_run = False
        self.dziad_met_this_run = False
        self.dziad_traded_this_run = False
        self.dziad_last_depth = 0
        self.bus.subscribe(EntityDied, self._on_monster_died)
        # M7 "Sylwetka" run state
        self.blizny = 0  # near-deaths survived (portrait scars)
        self._was_dying = False
        self.weapon_kills: dict[str, int] = {}  # "weapon_entity:species" → kills
        self.last_foe: tuple[EntityRef, float] | None = None  # pane mini-line
        self.quickslot_auto_refill = True  # spec §5.1 knob, config `quickslots.auto_refill`
        self._dziad_greeted_weapon = False
        self.epithets_catalog = load_epithets()
        self.bus.subscribe(AttackResolved, self._on_attack_for_pane)
        self.bus.subscribe(ItemPickedUp, self._on_item_gained)
        self.bus.subscribe(ItemBought, self._on_item_gained)
        # M8 "Dno" run state
        self.glebiej = glebiej
        self.victory = False
        self.victory_epilogue = ""
        self.wij_phase = "buried"  # buried | stirring | lid | gaze | sealed
        self.wij_lift = 0
        self._wij_respawn = WIJ_RESPAWN_TURNS
        self.vault: VaultLayout | None = None

        layout = generate_village()
        self.levels[0] = layout.map
        px, py = layout.player_start
        self.player: Entity = self.world.create(
            Player(),
            Position(px, py),
            OnLevel(0),
            Renderable(glyph="@", style="bold white"),
            Health(self.origin.hp, self.origin.hp),
            Melee(damage=self.origin.damage, to_hit=self.origin.to_hit),
            Actor(speed=PLAYER_SPEED),
            Hunger(self.origin.satiation, self.origin.satiation),
            Purse(),
            Inventory(items=tuple(self.spawn_stock_item(k) for k in self.origin.starting_items)),
            Wielding(),
            Lore(key="player", name="you"),
        )

        for role, vx, vy in layout.npc_posts:
            self.spawn_villager(role, vx, vy)
        for kind, sx, sy in layout.special_posts:
            self._spawn_special(kind, sx, sy)

        self.scheduler = TurnScheduler(self.world)
        self.map.update_fov((px, py), FOV_RADIUS)
        self._advance_until_player_turn()

    _VILLAGER_LORE: ClassVar = {
        "innkeeper": (
            "karczmarka",
            "Dobrava the karczmarka",
            "She keeps the fire, the beds, and every secret in the wieś — in that order.",
        ),
        "trader": (
            "handlarz",
            "Miłosz the handlarz",
            "His cart has been everywhere the roads go and several places they don't.",
        ),
        "gossip": (
            "dziad",
            "old Świętosław",
            "The village dziad. He remembers the woods from before the woods went wrong.",
        ),
    }

    def spawn_villager(self, role: str, x: int, y: int) -> Entity:
        key, name, description = self._VILLAGER_LORE[role]
        entity = self.world.create(
            Position(x, y),
            OnLevel(0),
            Renderable(glyph="☺", style="light_goldenrod2", ascii_glyph="P"),
            Health(10, 10),
            Villager(role=role),
            Lore(key=key, name=name, description=description),
        )
        if role == "trader":
            stock: list[Entity] = []
            for entry in self.village_shop.guaranteed:
                stock += [self.spawn_stock_item(entry.item) for _ in range(entry.count)]
            for entry in self.village_shop.rolls:
                if self.rng.loot.randint(1, 100) <= entry.chance:
                    stock += [self.spawn_stock_item(entry.item) for _ in range(entry.count)]
            self.world.add(entity, Inventory(items=tuple(stock)))
        return entity

    def _spawn_special(self, kind: str, x: int, y: int) -> Entity:
        base = [Position(x, y), OnLevel(0)]
        if kind == "skrzynia":
            return self.world.create(
                *base,
                Renderable(glyph="▣", style="gold3", ascii_glyph="8"),
                StashChest(),
                Lore(
                    key="skrzynia",
                    name="the skrzynia",
                    description=(
                        "An iron-banded chest, older than anyone who claims to own it. "
                        "What you lock inside will outlive you — that is the point."
                    ),
                ),
            )
        if kind == "perch":
            return self.world.create(
                *base,
                Renderable(glyph="⊥", style="grey66", ascii_glyph="T"),
                Perch(),
                Lore(
                    key="zerdz",
                    name="the żerdź",
                    description=(
                        "A tall crane-roost of weathered pine. The birds set travelers "
                        "down here; stand close and they will remember you."
                    ),
                ),
            )
        god = kind.removeprefix("shrine_")
        glyph = "Λ" if god == "perun" else "Ω"
        descriptions = {
            "perun": (
                "A weather-split oak post cut with the thunder-sign. Perun answers "
                "in favors, and he counts what you bring."
            ),
            "weles": (
                "A low stone slick with old milk and older promises. Weles keeps "
                "the low places, and he keeps accounts."
            ),
        }
        return self.world.create(
            *base,
            Renderable(
                glyph=glyph,
                style="light_goldenrod2",
                ascii_glyph="^" if god == "perun" else "O",
            ),
            Shrine(god=god),
            Lore(
                key=f"shrine_{god}",
                name=f"shrine of {god.capitalize()}",
                description=descriptions.get(god, ""),
            ),
        )

    @property
    def run_tag(self) -> str:
        return f"run-{self.seed}"

    def spawn_stock_item(self, item_key: str) -> Entity:
        """Spawn an item with no position — it lives in someone's pack."""
        definition = self.items_catalog[item_key]
        entity = self.world.create(
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

        monster_count = MONSTER_COUNT + (max(depth - 2, 0) * 2 if biome == "kurhany" else 0)
        if self.glebiej:
            monster_count += GLEBIEJ_SPAWN_BONUS
        candidates = floors
        if avoid is not None:
            ax, ay = avoid
            candidates = [
                (x, y) for x, y in floors if max(abs(x - ax), abs(y - ay)) >= MIN_SPAWN_DISTANCE
            ]
        defs = self._biome_defs(biome)
        weights = [d.spawn_weight for d in defs]
        water_adjacent = [
            (x, y)
            for x, y in candidates
            if any(
                game_map.in_bounds(x + dx, y + dy) and game_map.tiles[y + dy][x + dx] is Tile.WATER
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
            )
        ]
        spots = level_rng.sample(candidates, min(monster_count, len(candidates)))
        for x, y in spots:
            chosen = level_rng.choices(defs, weights=weights)[0]
            if chosen.prefers_water and water_adjacent:
                x, y = level_rng.choice(water_adjacent)  # ecology: utopce near pools
                water_adjacent.remove((x, y))
            self.spawn_monster(chosen, x, y, depth)

        table = self.loot_tables.get(biome)
        if table is not None:
            item_keys = sorted(table.weights)
            item_weights = [table.weights[k] for k in item_keys]
            item_count = table.items_for_depth(depth) + (GLEBIEJ_LOOT_BONUS if self.glebiej else 0)
        else:
            item_keys = sorted(self.items_catalog)
            item_weights = [self.items_catalog[k].spawn_weight for k in item_keys]
            item_count = ITEM_COUNT
        item_candidates = [t for t in floors if t != avoid]
        item_spots = level_rng.sample(item_candidates, min(item_count, len(item_candidates)))
        for x, y in item_spots:
            chosen_key = level_rng.choices(item_keys, weights=item_weights)[0]
            self.spawn_item(self.items_catalog[chosen_key], x, y, depth)

        if biome == "kurhany":
            hoard_spots = level_rng.sample(item_candidates, min(3, len(item_candidates)))
            for x, y in hoard_spots:
                amount = level_rng.randint(4, 8 + 6 * max(depth - 2, 1))
                self.spawn_coins(amount, x, y, depth)

        hook_defs = [
            h for h in sorted(self.hooks_catalog.values(), key=lambda h: h.key) if biome in h.biomes
        ]
        taken = set(spots) | set(item_spots)
        hook_candidates = [t for t in floors if t not in taken and t != avoid]
        hook_spots = level_rng.sample(hook_candidates, min(len(hook_defs), len(hook_candidates)))
        for definition, (x, y) in zip(hook_defs, hook_spots, strict=False):
            self.spawn_hook(definition, x, y, depth)

    def spawn_hook(self, definition: HookDef, x: int, y: int, depth: int = 0) -> Entity:
        return self.world.create(
            Position(x, y),
            OnLevel(depth),
            Renderable(
                glyph=definition.glyph,
                style=definition.style,
                ascii_glyph=definition.ascii_glyph,
            ),
            StoryHook(key=definition.key),
            Lore(key=definition.key, name=definition.name, description=definition.description),
        )

    def _ensure_level(self, depth: int) -> None:
        if depth in self.levels:
            return
        level_seed = _level_seed(self.seed, depth)
        if depth == 1:
            self.levels[depth] = generate_forest(level_seed)
        elif depth == 2:
            self.levels[depth] = generate_bagna(level_seed)
        elif depth == MAX_DEPTH:
            # The Dno (M8 §2.1): an authored hall, no random spawns, no dziad.
            layout = generate_vault(level_seed)
            self.levels[depth] = layout.map
            self.vault = layout
            self._populate_vault(depth)
            return
        else:
            self.levels[depth] = generate_kurhan(
                level_seed,
                with_down_stairs=depth < MAX_DEPTH,
                with_shafts=depth <= LAST_SKY_DEPTH,
            )
        self._populate_level(depth, random.Random(level_seed ^ 0xA5A5))
        self._maybe_spawn_dziad(depth)

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
        if definition.swims:
            self.world.add(entity, Swimmer())
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
        if new_depth == LAST_SKY_DEPTH + 1 and self.max_depth_reached <= LAST_SKY_DEPTH:
            self.bus.publish(DeepDescended(depth=new_depth))
        self.depth = new_depth
        self.max_depth_reached = max(self.max_depth_reached, new_depth)
        self.world.add(self.player, OnLevel(new_depth))
        self.world.add(self.player, Position(*arrival))
        self.bus.publish(LevelChanged(depth=new_depth, direction=direction))
        if new_depth == 0:
            self._bank_purse()

    def step(self, action: Action) -> None:
        """Execute one player action, then run other actors until it is the
        player's turn again (or the player is dead)."""
        if self.game_over:
            return
        self._tick_rite(action)
        flight_completed = False
        if not self.game_over:  # a completed rite ends the run mid-step
            flight_completed = self._tick_channel(action)
        if not flight_completed and not self.game_over:
            self._apply_player_action(action)
            self._check_perch_return()
        hp_before_round = self.world.expect(self.player, Health).hp
        self._update_player_fov()
        self._tick_statuses()
        hunger.tick(self.world, self.bus, self.player, self.turn + 1)
        self._tick_wij()
        if self.world.expect(self.player, Health).hp <= 0:
            self.game_over = True
        self._track_blizna()
        self.scheduler.spend(self.player)
        self._advance_until_player_turn()
        channeling = self.world.get(self.player, Channeling)
        if channeling is not None and self.world.expect(self.player, Health).hp < hp_before_round:
            self.world.remove(self.player, Channeling)
            self.bus.publish(
                CraneSummonInterrupted(actor=ref_for(self.world, self.player), reason="damage")
            )
        rite = self.world.get(self.player, Rite)
        if rite is not None and self.world.expect(self.player, Health).hp < hp_before_round:
            self.world.remove(self.player, Rite)
            self.bus.publish(
                RiteInterrupted(actor=ref_for(self.world, self.player), reason="damage")
            )
        self.turn += 1
        # TurnEnded closes the whole round (player + monsters) so the
        # narration TurnComposer can flush a complete paragraph.
        self.bus.publish(TurnEnded(self.turn))

    def _apply_player_action(self, action: Action) -> None:
        match action:
            case Move(dx=dx, dy=dy):
                pos = self.world.expect(self.player, Position)
                if (
                    self.depth == MAX_DEPTH
                    and self.vault is not None
                    and (pos.x + dx, pos.y + dy) == self.vault.cradle
                ):
                    self._touch_cradle()
                    return
                target = movement.blocking_entity_at(self.world, pos.x + dx, pos.y + dy, self.depth)
                interact = self._interactable_at(pos.x + dx, pos.y + dy)
                if interact is not None:
                    kind, _entity_i = interact
                    if kind == "skrzynia":
                        self.bus.publish(StashOpened(actor=ref_for(self.world, self.player)))
                    elif kind.startswith("shrine_"):
                        self.bus.publish(
                            ShrineVisited(
                                actor=ref_for(self.world, self.player),
                                god=kind.removeprefix("shrine_"),
                            )
                        )
                    return
                if target is not None and target != self.player:
                    villager = self.world.get(target, Villager)
                    if villager is not None:
                        if villager.role == "dziad_wedrowny" and not self.dziad_met_this_run:
                            self.dziad_met_this_run = True
                            self.meta.dziad.met_count += 1
                            self.bus.publish(MetaTransaction(kind="dziad_met", detail=""))
                            self._save_meta()
                            if self.meta.dziad.reputation >= 3:
                                self.bus.publish(
                                    DziadRecognized(reputation=self.meta.dziad.reputation)
                                )
                        self.bus.publish(
                            TalkedTo(villager=ref_for(self.world, target), role=villager.role)
                        )
                        if villager.role == "dziad_wedrowny":
                            self._dziad_greets_weapon()
                    else:
                        combat.attack(self.world, self.bus, self.rng.combat, self.player, target)
                else:
                    movement.try_move(self.world, self.map, self.bus, self.player, dx, dy)
            case Rest():
                if self.depth == 0:
                    health = self.world.expect(self.player, Health)
                    hunger_c = self.world.expect(self.player, Hunger)
                    self.world.add(self.player, Health(health.max_hp, health.max_hp))
                    self.world.add(
                        self.player,
                        Hunger(
                            max(hunger_c.satiation - REST_SATIATION_COST, 1),
                            hunger_c.max_satiation,
                        ),
                    )
                    self.bus.publish(Rested(actor=ref_for(self.world, self.player)))
            case MakeOffering(god=god):
                self._make_offering(god)
            case DepositItem(item=item):
                self._deposit(item)
            case WithdrawStash(index=index):
                self._withdraw(index)
            case UpgradeStash():
                self._upgrade_stash()
            case BuyItem(trader=trader, item=item):
                self._buy(trader, item)
            case SellItem(trader=trader, item=item):
                self._sell(trader, item)
            case Descend():
                pos = self.world.expect(self.player, Position)
                if self.map.tiles[pos.y][pos.x] is Tile.STAIRS_DOWN and self.depth < MAX_DEPTH:
                    self._change_level(self.depth + 1, "down")
            case Ascend():
                pos = self.world.expect(self.player, Position)
                if self.map.tiles[pos.y][pos.x] is Tile.STAIRS_UP and self.depth > 0:
                    self._change_level(self.depth - 1, "up")
            case Get():
                pos = self.world.expect(self.player, Position)
                pile = self._coin_pile_at(pos.x, pos.y)
                if pile is not None:
                    amount = self.world.expect(pile, CoinPile).amount
                    self.world.destroy(pile)
                    purse = self.world.get(self.player, Purse) or Purse()
                    new_total = purse.denary + amount
                    self.world.add(self.player, Purse(denary=new_total))
                    self.bus.publish(
                        CoinsPicked(
                            actor=ref_for(self.world, self.player),
                            amount=amount,
                            purse_total=new_total,
                        )
                    )
                else:
                    items.pick_up(self.world, self.bus, self.player)
            case UseItem(item=item):
                consumable = self.world.get(item, Consumable)
                if consumable is not None and consumable.effect == "crane":
                    self._use_crane_feather(item, consumable.power)
                else:
                    items.use_item(self.world, self.bus, self.player, item)
            case WieldItem(item=item):
                items.wield(self.world, self.bus, self.player, item)
            case WearItem(item=item):
                items.wear(self.world, self.bus, self.player, item, slot=self._slot_for(item))
            case UnequipSlot(slot=slot):
                items.unequip(self.world, self.bus, self.player, slot)
            case BindQuickslot(index=index, item=item):
                quickslots.bind(self.world, self.bus, self.player, index, item)
            case ClearQuickslot(index=index):
                quickslots.clear(self.world, self.bus, self.player, index)
            case UseQuickslot(index=index):
                entity = quickslots.bound_entity(self.world, self.player, index)
                if entity is not None:
                    self._use_quickslot(index, entity)
            case Wait():
                pass

    def _advance_until_player_turn(self) -> None:
        if movement.level_of(self.world, self.player) != self.depth:
            return  # defensive: never spin the AI loop without the player present
        while not self.game_over:
            entity = self.scheduler.next_actor(self.depth)
            if entity is None or entity == self.player:
                return
            if self.world.has(entity, AI):
                ai.take_turn(self.world, self.map, self.bus, self.rng.combat, entity)
                if self.world.expect(self.player, Health).hp <= 0:
                    self.game_over = True
            self.scheduler.spend(entity)

    # ------------------------------------------------------------------ economy

    CODEX_TIERS = ("unknown", "glimpsed", "partial", "full")

    def codex_tier(self, key: str) -> str:
        return self.meta.codex.known.get(key, "unknown")

    def _raise_codex_tier(self, key: str, tier: str) -> None:
        current = self.CODEX_TIERS.index(self.codex_tier(key))
        if self.CODEX_TIERS.index(tier) > current:
            self.meta.codex.known[key] = tier
            self.bus.publish(MetaTransaction(kind="codex", detail=f"{key}:{tier}"))

    def _on_lore_discovered(self, event: LoreDiscovered) -> None:
        if event.entity.key in self.bestiary:
            self._raise_codex_tier(event.entity.key, "glimpsed")

    def _drop_luck(self, chance: int) -> int:
        kinds = status.active_kinds(self.world, self.player)
        favor = kinds.get("weles_favor")
        if favor is not None:
            return min(100, round(chance * (1 + favor.power / 100)))
        return chance

    def _on_monster_died(self, event: EntityDied) -> None:
        if event.entity.is_player:
            return
        if event.entity.key == "sluga" and self.depth == MAX_DEPTH:
            # Corpses make poor pallbearers (M8 §2.2).
            self.wij_lift = max(0, self.wij_lift - WIJ_KNOCKBACK)
        if event.entity.key in self.bestiary:
            counter = f"kills_{event.entity.key}"
            kills = self.meta.achievements.get(counter, 0) + 1
            self.meta.achievements[counter] = kills
            self._raise_codex_tier(event.entity.key, "full" if kills >= 3 else "partial")
        if event.position is None:
            return
        spec = self.drops.get(event.entity.key)
        if spec is None:
            return
        x, y = event.position
        if spec.denary is not None and self.rng.loot.randint(1, 100) <= self._drop_luck(
            spec.denary.chance
        ):
            amount = self.rng.loot.randint(spec.denary.min, spec.denary.max)
            if amount > 0:
                self.spawn_coins(amount, x, y, event.depth)
        for trophy in spec.trophies:
            if self.rng.loot.randint(1, 100) <= self._drop_luck(trophy.chance):
                self.spawn_item(self.items_catalog[trophy.item], x, y, event.depth)

    def spawn_coins(self, amount: int, x: int, y: int, depth: int) -> Entity:
        return self.world.create(
            Position(x, y),
            OnLevel(depth),
            Renderable(glyph="$", style="gold3", ascii_glyph="$"),
            CoinPile(amount=amount),
            Lore(key="denary", name="denary"),
        )

    def _coin_pile_at(self, x: int, y: int) -> Entity | None:
        for entity, (pos, _pile) in self.world.query(Position, CoinPile):
            if (pos.x, pos.y) == (x, y) and movement.level_of(self.world, entity) == self.depth:
                return entity
        return None

    def _save_meta(self) -> None:
        if self.meta_autosave:
            save_meta(self.meta)

    def _bank_purse(self) -> None:
        purse = self.world.get(self.player, Purse) or Purse()
        if purse.denary <= 0:
            return
        self.meta.currency.denary += purse.denary
        amount = purse.denary
        self.world.add(self.player, Purse(denary=0))
        self.bus.publish(CoinsBanked(amount=amount, wallet_total=self.meta.currency.denary))
        self.bus.publish(MetaTransaction(kind="bank", detail=f"+{amount} denary"))
        self._save_meta()

    def price_for(self, item_key: str, trader: Entity) -> int:
        base = self.prices.buy.get(item_key, 10)
        if self.glebiej:
            base = round(base * 1.25)  # M8 §4: a crueler market
        villager = self.world.get(trader, Villager)
        if villager is not None and villager.role == "dziad_wedrowny":
            markup = base * self.prices.dziad_multiplier
            discount = min(
                self.meta.dziad.reputation * self.prices.dziad_discount_per_rep,
                self.prices.dziad_discount_cap,
            )
            return max(1, round(markup * (1 - discount)))
        return base

    def sell_price_for(self, item_key: str) -> int:
        return max(1, round(self.prices.buy.get(item_key, 10) * self.prices.sell_ratio))

    def _wallet_total(self) -> int:
        """Spendable coins here: banked wallet in the wieś, purse below."""
        purse = self.world.get(self.player, Purse) or Purse()
        return self.meta.currency.denary if self.depth == 0 else purse.denary

    def _spend(self, amount: int) -> None:
        if self.depth == 0:
            self.meta.currency.denary -= amount
            self.bus.publish(MetaTransaction(kind="purchase", detail=f"-{amount} denary"))
            self._save_meta()
        else:
            purse = self.world.get(self.player, Purse) or Purse()
            self.world.add(self.player, Purse(denary=purse.denary - amount))

    def _earn(self, amount: int) -> None:
        if self.depth == 0:
            self.meta.currency.denary += amount
            self.bus.publish(MetaTransaction(kind="sale", detail=f"+{amount} denary"))
            self._save_meta()
        else:
            purse = self.world.get(self.player, Purse) or Purse()
            self.world.add(self.player, Purse(denary=purse.denary + amount))

    def _buy(self, trader: Entity, item: Entity) -> None:
        trader_inv = self.world.get(trader, Inventory) or Inventory()
        item_c = self.world.get(item, Item)
        if item not in trader_inv.items or item_c is None:
            return
        price = self.price_for(item_c.key, trader)
        if self._wallet_total() < price:
            return
        self._spend(price)
        player_inv = self.world.get(self.player, Inventory) or Inventory()
        self.world.add(trader, Inventory(items=tuple(i for i in trader_inv.items if i != item)))
        self.world.add(self.player, Inventory(items=(*player_inv.items, item)))
        self._mark_dziad_trade(trader)
        self.bus.publish(
            ItemBought(
                actor=ref_for(self.world, self.player),
                item=ref_for(self.world, item),
                price=price,
            )
        )

    def _sell(self, trader: Entity, item: Entity) -> None:
        player_inv = self.world.get(self.player, Inventory) or Inventory()
        item_c = self.world.get(item, Item)
        if item not in player_inv.items or item_c is None:
            return
        price = self.sell_price_for(item_c.key)
        self.world.add(
            self.player, Inventory(items=tuple(i for i in player_inv.items if i != item))
        )
        trader_inv = self.world.get(trader, Inventory) or Inventory()
        self.world.add(trader, Inventory(items=(*trader_inv.items, item)))
        wielding = self.world.get(self.player, Wielding)
        if wielding is not None and wielding.item == item:
            self.world.add(self.player, Wielding(item=None))
        wearing = self.world.get(self.player, Wearing)
        if wearing is not None and wearing.item == item:
            self.world.add(self.player, Wearing(item=None))
        self._earn(price)
        self._mark_dziad_trade(trader)
        self.bus.publish(
            ItemSold(
                actor=ref_for(self.world, self.player),
                item=ref_for(self.world, item),
                price=price,
            )
        )

    def _use_crane_feather(self, item: Entity, channel_turns: int) -> None:
        player_ref = ref_for(self.world, self.player)
        if self.depth == 0:
            self.bus.publish(CraneRefused(actor=player_ref, reason="in_village"))
            return
        pos = self.world.expect(self.player, Position)
        if self.map.biome == "kurhany" and self.map.tiles[pos.y][pos.x] is not Tile.SHAFT:
            self.bus.publish(CraneRefused(actor=player_ref, reason="no_sky"))
            return
        if self._hostile_watching():
            self.bus.publish(CraneRefused(actor=player_ref, reason="watched"))
            return
        # The feather is spent the moment the call goes up (spec default: harsh).
        inventory = self.world.get(self.player, Inventory) or Inventory()
        self.world.add(self.player, Inventory(items=tuple(i for i in inventory.items if i != item)))
        self.world.destroy(item)
        self.world.add(self.player, Channeling(turns_left=channel_turns))
        self.bus.publish(CraneSummonStarted(actor=player_ref, turns=channel_turns))

    def _hostile_watching(self) -> bool:
        for entity, (_ai, pos) in self.world.query(AI, Position):
            if movement.level_of(self.world, entity) != self.depth:
                continue
            if (pos.x, pos.y) in self.map.visible:
                return True
        return False

    def _tick_channel(self, action: Action) -> bool:
        """Advance or break an active summoning channel. True if flight happened."""
        channeling = self.world.get(self.player, Channeling)
        if channeling is None:
            return False
        if not isinstance(action, Wait):
            self.world.remove(self.player, Channeling)
            self.bus.publish(
                CraneSummonInterrupted(actor=ref_for(self.world, self.player), reason="moved")
            )
            return False
        if channeling.turns_left > 1:
            self.world.add(self.player, Channeling(turns_left=channeling.turns_left - 1))
            return False
        self.world.remove(self.player, Channeling)
        self._complete_crane_flight()
        return True

    def _complete_crane_flight(self) -> None:
        pos = self.world.expect(self.player, Position)
        from_depth = self.depth
        # Only one znamię may exist; a new flight moves it.
        for old in self.world.entities_with(Znamie):
            self.world.destroy(old)
        self.world.create(
            Position(pos.x, pos.y),
            OnLevel(from_depth),
            Renderable(glyph="⌖", style="grey93", ascii_glyph="+"),
            Znamie(),
            Lore(
                key="znamie",
                name="the znamię",
                description=(
                    "The cranes' mark, pressed into the ground where they lifted "
                    "you. It holds your place on the way back down."
                ),
            ),
        )
        self.bus.publish(ZnamiePlaced(depth=from_depth, position=(pos.x, pos.y)))
        perch = self.world.entities_with(Perch)
        target = self.world.expect(perch[0], Position) if perch else None
        self.depth = 0
        self.world.add(self.player, OnLevel(0))
        if target is not None:
            self.world.add(self.player, Position(target.x, target.y))
        self.bus.publish(
            CraneSummonCompleted(actor=ref_for(self.world, self.player), from_depth=from_depth)
        )
        self._bank_purse()

    def _check_perch_return(self) -> None:
        if self.depth != 0:
            return
        marks = self.world.entities_with(Znamie)
        if not marks:
            return
        ppos = self.world.expect(self.player, Position)
        perch = self.world.entities_with(Perch)
        if not perch:
            return
        perch_pos = self.world.expect(perch[0], Position)
        if (ppos.x, ppos.y) != (perch_pos.x, perch_pos.y):
            return
        mark = marks[0]
        mark_pos = self.world.expect(mark, Position)
        mark_depth = movement.level_of(self.world, mark)
        self.world.destroy(mark)  # the feather covered one round trip
        self.depth = mark_depth
        self.world.add(self.player, OnLevel(mark_depth))
        self.world.add(self.player, Position(mark_pos.x, mark_pos.y))
        self.bus.publish(CraneReturn(actor=ref_for(self.world, self.player), depth=mark_depth))

    def _make_offering(self, god: str) -> None:
        spec = self.offerings.get(god)
        if spec is None or self.depth != 0:
            return
        if self.meta.currency.denary < spec.cost:
            return
        self.meta.currency.denary -= spec.cost
        self.bus.publish(MetaTransaction(kind="offering", detail=f"{god}:-{spec.cost}"))
        self._save_meta()
        status.apply_status(
            self.world,
            self.bus,
            self.player,
            StatusEffect(kind=spec.kind, duration=spec.duration, power=spec.power),
        )
        self.bus.publish(
            OfferingMade(actor=ref_for(self.world, self.player), god=god, cost=spec.cost)
        )

    def _interactable_at(self, x: int, y: int) -> tuple[str, Entity] | None:
        for entity, (pos, _chest) in self.world.query(Position, StashChest):
            if (pos.x, pos.y) == (x, y) and movement.level_of(self.world, entity) == self.depth:
                return ("skrzynia", entity)
        for entity, (pos, shrine) in self.world.query(Position, Shrine):
            if (pos.x, pos.y) == (x, y) and movement.level_of(self.world, entity) == self.depth:
                return (f"shrine_{shrine.god}", entity)
        return None

    STACKABLE_KINDS = ("consumable", "trophy")

    def stash_is_full(self) -> bool:
        return len(self.meta.stash.items) >= self.meta.stash.slots_total

    def _deposit(self, item: Entity) -> None:
        inventory = self.world.get(self.player, Inventory) or Inventory()
        item_c = self.world.get(item, Item)
        if item not in inventory.items or item_c is None:
            return
        stacked = False
        if item_c.kind in self.STACKABLE_KINDS:
            for stashed in self.meta.stash.items:
                if stashed.item_id == item_c.key:
                    stashed.count += 1
                    stacked = True
                    break
        if not stacked:
            if self.stash_is_full():
                return
            instance: dict[str, object] = {"memory_tag": self.run_tag}
            epithet = self.world.get(item, Epithet)
            if epithet is not None:  # a named weapon stays named (M7 §6.2)
                instance["epithet"] = epithet.species
            self.meta.stash.items.append(StashedItem(item_id=item_c.key, instance=instance))
        item_ref = ref_for(self.world, item)
        self.world.add(self.player, Inventory(items=tuple(i for i in inventory.items if i != item)))
        wielding = self.world.get(self.player, Wielding)
        if wielding is not None and wielding.item == item:
            self.world.add(self.player, Wielding(item=None))
        wearing = self.world.get(self.player, Wearing)
        if wearing is not None and wearing.item == item:
            self.world.add(self.player, Wearing(item=None))
        self.world.destroy(item)
        self.bus.publish(StashDeposited(item=item_ref))
        self.bus.publish(MetaTransaction(kind="stash_deposit", detail=item_c.key))
        self._save_meta()

    def _withdraw(self, index: int) -> None:
        if not (0 <= index < len(self.meta.stash.items)):
            return
        stashed = self.meta.stash.items[index]
        if stashed.count > 1:
            stashed.count -= 1
        else:
            self.meta.stash.items.pop(index)
        entity = self.spawn_stock_item(stashed.item_id)
        tag = str(stashed.instance.get("memory_tag", ""))
        heirloom = bool(tag) and tag != self.run_tag
        if heirloom:
            self.world.add(entity, ItemMemory(memory_tag=tag))
        species = stashed.instance.get("epithet")
        if isinstance(species, str) and species:
            self.world.add(entity, Epithet(species=species))
        inventory = self.world.get(self.player, Inventory) or Inventory()
        self.world.add(self.player, Inventory(items=(*inventory.items, entity)))
        self.bus.publish(StashWithdrawn(item=ref_for(self.world, entity), heirloom=heirloom))
        self.bus.publish(MetaTransaction(kind="stash_withdraw", detail=stashed.item_id))
        self._save_meta()

    def _upgrade_stash(self) -> None:
        upgrades = self.prices.stash_upgrades
        step = (self.meta.stash.slots_total - 4) // 2
        if step >= len(upgrades) or self.meta.stash.slots_total >= 10:
            return
        price = upgrades[step]
        if self.meta.currency.denary < price:
            return
        self.meta.currency.denary -= price
        self.meta.stash.slots_total += 2
        self.bus.publish(StashUpgraded(slots=self.meta.stash.slots_total, price=price))
        self.bus.publish(MetaTransaction(kind="stash_upgrade", detail=str(price)))
        self._save_meta()

    def _maybe_spawn_dziad(self, depth: int) -> None:
        cfg = self.dziad_shop
        if self.levels[depth].biome != "kurhany" or depth < cfg.first_eligible:
            return
        if self.dziad_seen_this_run:
            if depth < self.dziad_last_depth + cfg.repeat_interval:
                return
            chance = cfg.repeat_chance
        else:
            chance = 100 if depth >= cfg.pity_level else cfg.base_chance
        if self.rng.worldgen.randint(1, 100) > chance:
            return
        self.dziad_seen_this_run = True
        self.dziad_last_depth = depth
        floors = self.levels[depth].floor_tiles()
        x, y = self.rng.worldgen.choice(floors)
        dziad = self.world.create(
            Position(x, y),
            OnLevel(depth),
            Renderable(glyph="☺", style="grey66", ascii_glyph="D"),
            Health(10, 10),
            Villager(role="dziad_wedrowny"),
            Lore(
                key="dziad_wedrowny",
                name="the wandering dziad",
                epithets=("always already there",),
                description=(
                    "An old peddler with a cart no one has ever seen him pull, met "
                    "deeper underground than any living man should be. He is never "
                    "surprised to see you. He is never surprised at all."
                ),
            ),
        )
        pool = self.dziad_shop.stock_pool(self.meta.dziad.reputation)
        count = min(cfg.stock_per_visit, len(pool))
        stock = tuple(self.spawn_stock_item(self.rng.worldgen.choice(pool)) for _ in range(count))
        self.world.add(dziad, Inventory(items=stock))

    def apply_death_to_meta(self) -> list[str]:
        """Fold the run's fate into the meta-state; return newly unlocked origins."""
        counters = self.meta.achievements
        counters["runs"] = counters.get("runs", 0) + 1
        counters["deepest_level"] = max(counters.get("deepest_level", 0), self.max_depth_reached)
        if self.death_by_key:
            key = f"{self.death_by_key}_deaths"
            counters[key] = counters.get(key, 0) + 1
        newly_unlocked = []
        for origin_key, definition in sorted(self.origins_catalog.items()):
            if definition.unlock is None or origin_key in self.meta.unlocks.origins:
                continue
            rule = definition.unlock
            threshold = int(rule.get("threshold", 1))
            if rule.get("type") == "achievement":
                current = counters.get(str(rule.get("key", "")), 0)
            elif rule.get("type") == "dziad_reputation":
                current = self.meta.dziad.reputation
            else:
                continue
            if current >= threshold:
                self.meta.unlocks.origins.append(origin_key)
                newly_unlocked.append(origin_key)
        self.bus.publish(MetaTransaction(kind="death", detail=self.death_cause or ""))
        self._save_meta()
        return newly_unlocked

    def _mark_dziad_trade(self, trader: Entity) -> None:
        villager = self.world.get(trader, Villager)
        if villager is None or villager.role != "dziad_wedrowny":
            return
        if not getattr(self, "dziad_traded_this_run", False):
            self.dziad_traded_this_run = True
            self.meta.dziad.reputation += 1
            self.bus.publish(MetaTransaction(kind="dziad_rep", detail="+1"))
            self._save_meta()

    # ---- M8 "Dno" ---------------------------------------------------------

    def _populate_vault(self, depth: int) -> None:
        assert self.vault is not None
        cx, cy = self.vault.cradle
        self.world.create(
            Position(cx, cy),
            OnLevel(depth),
            Renderable(glyph="Ø", style="grey93", ascii_glyph="0"),
            Lore(
                key="wij",
                name="the Wij",
                epithets=("the buried one",),
                description=(
                    "He lies in the stone cradle the way a river lies in its bed. "
                    "The lids over his eyes are older than the hill above you, and "
                    "the things in grave-linen want them open. Whatever you do, do "
                    "not be worth looking at when they are."
                ),
            ),
        )
        for x, y in self.vault.niches[:2]:
            self._spawn_sluga(x, y, depth)

    def _spawn_sluga(self, x: int, y: int, depth: int) -> Entity:
        assert self.vault is not None
        entity = self.spawn_monster(self.bestiary["sluga"], x, y, depth)
        self.world.add(entity, Lifting(x=self.vault.cradle[0], y=self.vault.cradle[1]))
        return entity

    def _alive_slugi(self) -> list[Entity]:
        return [
            entity
            for entity, (_lift, _pos) in self.world.query(Lifting, Position)
            if self.world.is_alive(entity)
        ]

    def _touch_cradle(self) -> None:
        """Bumping the cradle: with blessed salt it begins the rite; without,
        it teaches you what edges are worth here (M8 §2.3-2.4)."""
        player_ref = ref_for(self.world, self.player)
        if self.world.get(self.player, Rite) is not None:
            return
        inventory = self.world.get(self.player, Inventory) or Inventory()
        salt = next(
            (
                e
                for e in inventory.items
                if (item := self.world.get(e, Item)) is not None and item.key == RITE_ITEM
            ),
            None,
        )
        if salt is None:
            self.bus.publish(WijAttackFutile(actor=player_ref))
            return
        # The salt is spent the moment the pressing begins (feather doctrine).
        self.world.add(self.player, Inventory(items=tuple(i for i in inventory.items if i != salt)))
        self.world.destroy(salt)
        self.world.add(self.player, Rite(turns_left=RITE_TURNS))
        self.bus.publish(RiteStarted(actor=player_ref, turns=RITE_TURNS))

    def _tick_rite(self, action: Action) -> None:
        rite = self.world.get(self.player, Rite)
        if rite is None:
            return
        if not isinstance(action, Wait):
            self.world.remove(self.player, Rite)
            self.bus.publish(
                RiteInterrupted(actor=ref_for(self.world, self.player), reason="moved")
            )
            return
        if rite.turns_left > 1:
            self.world.add(self.player, Rite(turns_left=rite.turns_left - 1))
            return
        self.world.remove(self.player, Rite)
        self._seal_wij()

    def _seal_wij(self) -> None:
        self.wij_phase = "sealed"
        self.wij_lift = 0
        for sluga in self._alive_slugi():
            self.world.destroy(sluga)  # they fold where they stand; no death cries
        self.victory = True
        self.victory_epilogue = self._epilogue_key()
        self.game_over = True
        self.bus.publish(RiteCompleted(actor=ref_for(self.world, self.player), turn=self.turn))

    def _tick_wij(self) -> None:
        if self.depth != MAX_DEPTH or self.vault is None or self.wij_phase == "sealed":
            return
        cx, cy = self.vault.cradle
        slugi = self._alive_slugi()
        # Servants adjacent to the cradle lift; corpses were handled on death.
        channeling = 0
        for sluga in slugi:
            pos = self.world.expect(sluga, Position)
            if max(abs(pos.x - cx), abs(pos.y - cy)) <= 1:
                channeling += 1
        if channeling and self.wij_phase != "gaze":
            self.wij_lift = min(WIJ_GAZE_AT, self.wij_lift + channeling * WIJ_LIFT_PER_SLUGA)
        self._advance_wij_phase()
        # Niches keep birthing pallbearers; the room cannot be cleared.
        self._wij_respawn -= 1
        if self._wij_respawn <= 0:
            self._wij_respawn = WIJ_RESPAWN_TURNS
            if len(slugi) < WIJ_MAX_SLUGI:
                occupied = {(p.x, p.y) for _e, (p,) in self.world.query(Position)}
                for x, y in self.vault.niches:
                    if (x, y) not in occupied:
                        self._spawn_sluga(x, y, self.depth)
                        break
        if self.wij_phase == "gaze":
            self._gaze_falls()

    def _advance_wij_phase(self) -> None:
        order = ("buried", "stirring", "lid", "gaze")
        thresholds = {"stirring": WIJ_STIR_AT, "lid": WIJ_LID_AT, "gaze": WIJ_GAZE_AT}
        events = {"stirring": WijStirred, "lid": WijLidLifted, "gaze": WijGazeOpened}
        current = order.index(self.wij_phase) if self.wij_phase in order else 0
        for phase in order[current + 1 :]:
            if self.wij_lift >= thresholds[phase]:
                self.wij_phase = phase
                self.bus.publish(events[phase](lift=self.wij_lift))

    def _gaze_falls(self) -> None:
        """The open gaze (M8 §2.3): light inverts — flame marks you, dark hides you."""
        assert self.vault is not None
        if self.world.get(self.player, LightSource) is None:
            return  # unlit: the hall is dark and you are part of it
        pos = self.world.expect(self.player, Position)
        game_map = self.map
        seen = compute_fov(
            self.vault.cradle,
            WIJ_GAZE_RADIUS,
            is_blocking=lambda x, y: not game_map.is_transparent(x, y),
        )
        if (pos.x, pos.y) not in seen:
            return
        health = self.world.expect(self.player, Health)
        self.world.add(self.player, replace(health, hp=max(0, health.hp - WIJ_GAZE_DAMAGE)))
        self.bus.publish(SeenByWij(actor=ref_for(self.world, self.player), damage=WIJ_GAZE_DAMAGE))
        if self.world.expect(self.player, Health).hp <= 0:
            self.death_cause = "seen by the Wij"
            self.death_by_key = "wij"

    def _epilogue_key(self) -> str:
        """Which ending the run earned (M8 §3), first match wins."""
        if self.dziad_met_this_run and self.meta.dziad.reputation >= 3:
            return "gospodarz"
        known = sum(1 for key in self.bestiary if key in self.meta.codex.known)
        codex_full = self.bestiary and known / len(self.bestiary) >= 0.8
        statuses = self.world.get(self.player, StatusEffects)
        favored = statuses is not None and any(
            effect.kind in ("perun_favor", "weles_favor") for effect in statuses.effects
        )
        if codex_full or favored:
            return "ptaki"
        return "swit"

    def apply_victory_to_meta(self) -> None:
        from wyraj.persistence.meta import VictoryRecord

        self.meta.victories.append(
            VictoryRecord(
                origin=self.origin.key,
                seed=self.seed,
                turn=self.turn,
                epilogue=self.victory_epilogue,
                glebiej=self.glebiej,
            )
        )
        counters = self.meta.achievements
        counters["victories"] = counters.get("victories", 0) + 1
        self.bus.publish(MetaTransaction(kind="victory", detail=self.victory_epilogue))
        self._save_meta()

    # ---- M7 "Sylwetka" ----------------------------------------------------

    def _slot_for(self, item: Entity) -> str:
        component = self.world.get(item, Item)
        definition = self.items_catalog.get(component.key) if component is not None else None
        if definition is not None and definition.slot in ("head", "amulet", "feet"):
            return definition.slot
        return "torso"

    def _use_quickslot(self, index: int, item: Entity) -> None:
        item_ref = ref_for(self.world, item)
        consumable = self.world.get(item, Consumable)
        if consumable is not None and consumable.effect == "crane":
            self._use_crane_feather(item, consumable.power)
        else:
            items.use_item(self.world, self.bus, self.player, item)
        self.bus.publish(
            QuickslotUsed(actor=ref_for(self.world, self.player), item=item_ref, index=index)
        )
        key = quickslots.slots_of(self.world, self.player).key_at(index)
        if (
            not self.quickslot_auto_refill
            and key is not None
            and quickslots.count_of(self.world, self.player, key) == 0
        ):
            quickslots.clear(self.world, self.bus, self.player, index)

    def quickslot_entity(self, index: int) -> Entity | None:
        """UI helper: what a `1-4` press would use (None = no turn spent)."""
        return quickslots.bound_entity(self.world, self.player, index)

    def _on_item_gained(self, event: ItemPickedUp | ItemBought) -> None:
        if event.actor.is_player:
            quickslots.note_gained(self.world, self.bus, self.player, event.item.entity)

    def _track_blizna(self) -> None:
        if self.game_over:
            return
        fraction = self.world.expect(self.player, Health).fraction
        if fraction < DYING_BAND:
            self._was_dying = True
        elif self._was_dying:
            self._was_dying = False
            self.blizny += 1
            self.bus.publish(
                BliznaEarned(actor=ref_for(self.world, self.player), count=self.blizny)
            )

    def _on_attack_for_pane(self, event: AttackResolved) -> None:
        if event.attacker.is_player and not event.defender.is_player:
            self.last_foe = (event.defender, event.defender_hp_frac)
            self._tally_weapon_kill(event)
        elif event.defender.is_player and not event.attacker.is_player:
            health = self.world.get(event.attacker.entity, Health)
            fraction = health.fraction if health is not None else 1.0
            self.last_foe = (event.attacker, fraction)

    def _tally_weapon_kill(self, event: AttackResolved) -> None:
        if event.outcome is not Outcome.KILL or event.weapon is None:
            return
        tally_key = f"{event.weapon.entity}:{event.defender.key}"
        self.weapon_kills[tally_key] = self.weapon_kills.get(tally_key, 0) + 1
        if (
            self.weapon_kills[tally_key] >= EPITHET_KILLS
            and event.defender.key in self.epithets_catalog
            and self.world.get(event.weapon.entity, Item) is not None
            and self.world.get(event.weapon.entity, Epithet) is None
        ):
            self.world.add(event.weapon.entity, Epithet(species=event.defender.key))
            self.bus.publish(
                WeaponNamed(actor=event.attacker, weapon=event.weapon, species=event.defender.key)
            )

    def _dziad_greets_weapon(self) -> None:
        if self._dziad_greeted_weapon:
            return
        wielding = self.world.get(self.player, Wielding)
        if wielding is None or wielding.item is None:
            return
        epithet = self.world.get(wielding.item, Epithet)
        if epithet is None:
            return
        self._dziad_greeted_weapon = True
        self.bus.publish(
            WeaponRecognized(weapon=ref_for(self.world, wielding.item), species=epithet.species)
        )

    def _track_kill_cause(self, event: AttackResolved) -> None:
        if event.defender.is_player and event.outcome is Outcome.KILL:
            self.death_cause = f"slain by {event.attacker.name}"
            self.death_by_key = event.attacker.key

    def _track_starvation_cause(self, event: StarvationHit) -> None:
        if event.actor.is_player and event.hp_frac <= 0:
            self.death_cause = "starved, far from any table"

    def _track_dot_cause(self, event: StatusTick) -> None:
        if event.actor.is_player and event.hp_frac <= 0:
            causes = {"bleeding": "bled out drop by drop", "poison": "taken by grave-rot"}
            self.death_cause = causes.get(event.kind, f"succumbed to {event.kind}")

    @property
    def in_darkness(self) -> bool:
        return self.depth >= CRYPT_FIRST_DEPTH and self.world.get(self.player, LightSource) is None

    @property
    def fov_radius(self) -> int:
        """Crypts are dark; a lit gromnica pushes the dark back.

        M8 §1: the dark deepens below the crypts' third level — unlit sight
        shrinks to 3/2/1 tiles at depths 6/7/8. At the bottom, a burning
        gromnica is the only way to see; the lid phase brightens the hall
        with the Wij's own grey light (never a kindness).
        """
        if not self.in_darkness:
            radius = FOV_RADIUS
        else:
            radius = max(1, CRYPT_FOV_RADIUS - max(0, self.depth - (CRYPT_FIRST_DEPTH + 2)))
            if self.depth == MAX_DEPTH and self.wij_phase in ("lid", "gaze"):
                radius = max(radius, 2)
        if self.glebiej:
            radius = max(1, radius - 1)
        return radius

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
        discoverable = list(self.world.query(AI, Lore, Position)) + [
            (e, (h, lore, pos)) for e, (h, lore, pos) in self.world.query(StoryHook, Lore, Position)
        ]
        for entity, (_marker, lore, pos) in discoverable:
            if movement.level_of(self.world, entity) != self.depth:
                continue
            if (pos.x, pos.y) in self.map.visible and lore.key not in self.codex_seen:
                self.codex_seen.add(lore.key)
                self.bus.publish(LoreDiscovered(entity=ref_for(self.world, entity)))
