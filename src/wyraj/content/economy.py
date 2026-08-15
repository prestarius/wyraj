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
