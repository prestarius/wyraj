"""Koło Roku (M9 §1): pure time. Everything derives from (seed, turn).

No state, no RNG streams — the calendar, the weather, and the festivals are
deterministic functions, so a fresh Game(seed) at turn N agrees with one
that walked there. The wheel turns underground too (open decision #29).
"""

import hashlib

DAY_TURNS = 240
# (phase, first turn-of-day inclusive, last exclusive)
PHASES = (("swit", 0, 20), ("dzien", 20, 140), ("zmierzch", 140, 160), ("noc", 160, 240))
WHEEL_DAYS = 12
FESTIVALS = {2: "gromniczna", 5: "kupala", 8: "dozynki", 11: "dziady"}
WEATHERS = ("jasno", "deszcz", "mgla", "burza")
_WEATHER_WEIGHTS = (5, 3, 2, 2)
LIGHTNING_MODULUS = 37  # storm turns that crack (M9 §2)


def _digest(*parts: object) -> int:
    joined = ":".join(str(part) for part in parts)
    return int.from_bytes(hashlib.sha256(joined.encode()).digest()[:8], "big")


def start_day(seed: int) -> int:
    """The run's wheel-day at turn 0 — festivals are seed identity."""
    return _digest(seed, "calendar") % WHEEL_DAYS


def absolute_day(turn: int) -> int:
    return turn // DAY_TURNS


def wheel_day(seed: int, turn: int) -> int:
    return (start_day(seed) + absolute_day(turn)) % WHEEL_DAYS


def phase_of(turn: int) -> str:
    turn_of_day = turn % DAY_TURNS
    for name, first, last in PHASES:
        if first <= turn_of_day < last:
            return name
    return "noc"


def festival_of(seed: int, turn: int) -> str | None:
    return FESTIVALS.get(wheel_day(seed, turn))


def weather_of(seed: int, turn: int) -> str:
    """One weather per absolute day; surface-only in effect."""
    roll = _digest(seed, "weather", absolute_day(turn)) % sum(_WEATHER_WEIGHTS)
    for name, weight in zip(WEATHERS, _WEATHER_WEIGHTS, strict=True):
        if roll < weight:
            return name
        roll -= weight
    return "jasno"


def lightning_cracks(seed: int, turn: int) -> bool:
    if weather_of(seed, turn) != "burza":
        return False
    return _digest(seed, "lightning", turn) % LIGHTNING_MODULUS == 0


def moon_glyph(seed: int, turn: int, use_ascii: bool = False) -> str:
    glyphs = ("O", ")", "*", "(") if use_ascii else ("○", "◐", "●", "◑")
    return glyphs[(wheel_day(seed, turn) // 3) % 4]
