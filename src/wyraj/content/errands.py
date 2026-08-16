"""Errand loading: YAML → validated ErrandDef models (M10 "Zlecenia" §1).

Two kinds only. Hunt: kill the target monster, bring back its proof.
Fetch: recover the target item from the depth where it waits.
This game doesn't do escorts.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from wyraj.content.paths import data_roots

ERRAND_KINDS = ("hunt", "fetch")


class ErrandReward(BaseModel):
    denary: int = Field(gt=0)
    reputation: int = Field(default=1, ge=0)


class ErrandDef(BaseModel):
    key: str
    giver: str  # villager role, e.g. "mlynarz"
    kind: str  # "hunt" | "fetch"
    target: str  # monster key (hunt) / item key (fetch)
    proof: str = ""  # hunt only: item guaranteed to drop while the errand is active
    depth: int = Field(ge=1, le=8)
    reward: ErrandReward
    patience: int = Field(default=0, ge=0)  # ignored runs before the fate resolves; 0 = none
    fate: str = ""  # village flag this failure feeds; "" = reputation loss only
    weight: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def check_kind(self) -> "ErrandDef":
        if self.kind not in ERRAND_KINDS:
            raise ValueError(f"errand '{self.key}': unknown kind '{self.kind}'")
        if self.kind == "hunt" and not self.proof:
            raise ValueError(f"hunt errand '{self.key}' needs a proof item")
        if bool(self.fate) != (self.patience > 0):
            raise ValueError(f"errand '{self.key}': fate and patience come together or not at all")
        return self

    @property
    def proof_item(self) -> str:
        """What the player must carry to the giver to complete the errand."""
        return self.proof if self.kind == "hunt" else self.target


def load_errands(root: Path | None = None) -> dict[str, ErrandDef]:
    errands: dict[str, ErrandDef] = {}
    for base in [root] if root is not None else data_roots():
        errands_dir = base / "errands"
        if not errands_dir.is_dir():
            continue
        for path in sorted(errands_dir.glob("*.yml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for key, fields in raw.items():
                errands[key] = ErrandDef(key=key, **fields)
    return errands
