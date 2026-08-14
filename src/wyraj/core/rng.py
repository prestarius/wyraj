"""Named, independently seeded RNG streams.

Gameplay determinism rule (spec pillar 3): each concern draws from its own
stream so e.g. narration variety never perturbs combat rolls. All streams
derive from one master seed via a stable hash — never wall-clock time.
"""

import hashlib
import random

STREAM_NAMES = ("worldgen", "combat", "loot", "narration")


def _derive(master_seed: int, name: str) -> int:
    digest = hashlib.sha256(f"{master_seed}:{name}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


class RngStreams:
    def __init__(self, master_seed: int) -> None:
        self.master_seed = master_seed
        self._streams: dict[str, random.Random] = {
            name: random.Random(_derive(master_seed, name)) for name in STREAM_NAMES
        }

    @property
    def worldgen(self) -> random.Random:
        return self._streams["worldgen"]

    @property
    def combat(self) -> random.Random:
        return self._streams["combat"]

    @property
    def loot(self) -> random.Random:
        return self._streams["loot"]

    @property
    def narration(self) -> random.Random:
        return self._streams["narration"]
