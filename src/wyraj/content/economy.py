"""Economy data: drops, prices, village shop stock (M6 spec §4)."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from wyraj.content.paths import data_dir


class CoinDrop(BaseModel):
    chance: int = Field(ge=0, le=100)
    min: int = Field(ge=0)
    max: int = Field(ge=0)


class TrophyDrop(BaseModel):
    item: str
    chance: int = Field(ge=0, le=100)


class DropSpec(BaseModel):
    denary: CoinDrop | None = None
    trophies: list[TrophyDrop] = []


class Prices(BaseModel):
    sell_ratio: float = Field(gt=0, lt=1)
    dziad_multiplier: float = Field(ge=1)
    dziad_discount_per_rep: float = 0.03
    dziad_discount_cap: float = 0.15
    stash_upgrades: list[int] = []
    buy: dict[str, int] = {}


class StockEntry(BaseModel):
    item: str
    count: int = 1
    chance: int = Field(default=100, ge=0, le=100)


class VillageShop(BaseModel):
    guaranteed: list[StockEntry] = []
    rolls: list[StockEntry] = []


def load_drops(root: Path | None = None) -> dict[str, DropSpec]:
    raw = yaml.safe_load(((root or data_dir()) / "economy" / "drops.yml").read_text()) or {}
    return {key: DropSpec(**spec) for key, spec in raw.items()}


def load_prices(root: Path | None = None) -> Prices:
    raw = yaml.safe_load(((root or data_dir()) / "economy" / "prices.yml").read_text()) or {}
    return Prices(**raw)


def load_village_shop(root: Path | None = None) -> VillageShop:
    raw = yaml.safe_load(((root or data_dir()) / "economy" / "shop_village.yml").read_text()) or {}
    return VillageShop(**raw)


class DziadShop(BaseModel):
    first_eligible: int = 3
    base_chance: int = Field(default=60, ge=0, le=100)
    pity_level: int = 5
    repeat_chance: int = Field(default=40, ge=0, le=100)
    repeat_interval: int = 2
    stock_per_visit: int = 4
    tiers: dict[int, list[str]] = {}
    tier_unlocks: dict[int, int] = {}

    def stock_pool(self, reputation: int) -> list[str]:
        pool: list[str] = []
        for tier in sorted(self.tiers):
            required = self.tier_unlocks.get(tier, 0)
            if reputation >= required:
                pool.extend(self.tiers[tier])
        return pool


def load_dziad_shop(root: Path | None = None) -> DziadShop:
    raw = yaml.safe_load(((root or data_dir()) / "economy" / "shop_dziad.yml").read_text()) or {}
    return DziadShop(**raw)


class Offering(BaseModel):
    cost: int = Field(gt=0)
    kind: str
    duration: int = Field(gt=0)
    power: int = Field(ge=0)


def load_offerings(root: Path | None = None) -> dict[str, Offering]:
    raw = yaml.safe_load(((root or data_dir()) / "economy" / "offerings.yml").read_text()) or {}
    return {god: Offering(**spec) for god, spec in raw.items()}
