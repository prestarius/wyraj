"""Generate the M11 starter sound set (spec §3, open decision #38).

Stdlib only, deterministic (fixed seed): every asset is synthesized —
filtered noise, sine partials, envelopes — and committed to data/audio/.
Curated freesound.org picks replace files one by one later; until then the
project credits itself. Regenerate with:  uv run python tools/gen_sounds.py

Output: mono 16-bit 22050 Hz WAV under data/audio/{beds,sfx,voices}/ plus
a regenerated data/audio/CREDITS.yml covering exactly these files.
"""

import math
import random
import wave
from pathlib import Path

RATE = 22050
ROOT = Path(__file__).resolve().parents[1] / "data" / "audio"
RNG = random.Random(505)

# ---- tiny dsp -------------------------------------------------------------


def silence(seconds: float) -> list[float]:
    return [0.0] * int(seconds * RATE)


def white(seconds: float) -> list[float]:
    return [RNG.uniform(-1, 1) for _ in range(int(seconds * RATE))]


def lowpass(samples: list[float], alpha: float) -> list[float]:
    out, y = [], 0.0
    for x in samples:
        y += alpha * (x - y)
        out.append(y)
    return out


def sine(freq: float, seconds: float, vibrato: float = 0.0, vib_rate: float = 5.0) -> list[float]:
    out, phase = [], 0.0
    for i in range(int(seconds * RATE)):
        t = i / RATE
        f = freq * (1 + vibrato * math.sin(2 * math.pi * vib_rate * t))
        phase += 2 * math.pi * f / RATE
        out.append(math.sin(phase))
    return out


def env(samples: list[float], attack: float, release: float) -> list[float]:
    n = len(samples)
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    out = list(samples)
    for i in range(min(a, n)):
        out[i] *= i / a
    for i in range(min(r, n)):
        out[n - 1 - i] *= i / r
    return out


def gain(samples: list[float], g: float) -> list[float]:
    return [s * g for s in samples]


def mix(*layers: list[float]) -> list[float]:
    n = max(len(layer) for layer in layers)
    out = [0.0] * n
    for layer in layers:
        for i, s in enumerate(layer):
            out[i] += s
    return out


def place(base: list[float], sound: list[float], at: float) -> None:
    start = int(at * RATE)
    for i, s in enumerate(sound):
        if start + i < len(base):
            base[start + i] += s


def seamless(samples: list[float], overlap: float = 1.0) -> list[float]:
    """Crossfade the tail into the head so the bed loops without a click."""
    k = int(overlap * RATE)
    body, tail = samples[:-k], samples[-k:]
    out = list(body)
    for i in range(min(k, len(out))):
        w = i / k
        out[i] = out[i] * w + tail[i] * (1 - w)
    return out


def write(rel: str, samples: list[float]) -> None:
    peak = max(1e-9, max(abs(s) for s in samples))
    norm = min(1.0, 0.9 / peak)
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(
            b"".join(
                int(max(-1.0, min(1.0, s * norm)) * 32767).to_bytes(2, "little", signed=True)
                for s in samples
            )
        )
    print(f"  {rel}  ({len(samples) / RATE:.1f}s)")


# ---- beds (spec §4) --------------------------------------------------------


def bed_wind(seconds: float, alpha: float, depth_gain: float, mod_rate: float) -> list[float]:
    base = lowpass(white(seconds), alpha)
    return [
        s * depth_gain * (0.6 + 0.4 * math.sin(2 * math.pi * mod_rate * i / RATE))
        for i, s in enumerate(base)
    ]


def bed_wies() -> list[float]:
    crackle = lowpass(white(6.0), 0.04)
    out = gain(crackle, 0.5)
    for _ in range(10):  # hearth pops
        place(out, env(gain(lowpass(white(0.03), 0.5), 0.8), 0.002, 0.02), RNG.uniform(0, 5.8))
    return seamless(out)


def bed_puszcza(night: bool) -> list[float]:
    out = bed_wind(6.0, 0.03 if night else 0.05, 0.9, 0.17)
    if night:
        for _ in range(2):  # something far off, twice a loop
            hoot = env(gain(sine(390, 0.25, vibrato=0.02), 0.12), 0.05, 0.12)
            place(out, lowpass(hoot, 0.15), RNG.uniform(0.5, 5.0))
    return seamless(out)


def bed_bagna(night: bool) -> list[float]:
    out = bed_wind(6.0, 0.02, 0.7, 0.11)
    for _ in range(4 if night else 7):  # blub
        f = RNG.uniform(160, 320)
        blub = env(
            [
                math.sin(2 * math.pi * f * (1 - 0.4 * i / (0.09 * RATE)) * i / RATE)
                for i in range(int(0.09 * RATE))
            ],
            0.005,
            0.05,
        )
        place(out, gain(blub, 0.2), RNG.uniform(0, 5.7))
    return seamless(out)


def bed_kurhany(deep: bool) -> list[float]:
    rumble = gain(lowpass(white(6.0), 0.006 if deep else 0.01), 0.5 if deep else 0.35)
    out = rumble
    for _ in range(1 if deep else 3):  # stone settles
        tick = env(gain(lowpass(white(0.02), 0.4), 0.7), 0.001, 0.015)
        place(out, tick, RNG.uniform(0.5, 5.5))
    return seamless(out)


def bed_dno() -> list[float]:
    out = gain(lowpass(white(6.6), 0.004), 0.25)
    beat = 60.0 / 55  # 55 bpm — His, not yours
    t = 0.2
    while t < 6.2:
        for offset, strength in ((0.0, 1.0), (0.28, 0.6)):
            thump = env(gain(sine(48, 0.18), strength), 0.005, 0.15)
            place(out, thump, t + offset)
        t += beat
    return seamless(out)


def bed_kupala() -> list[float]:
    out = bed_wind(8.0, 0.03, 0.35, 0.09)
    scale = [220.0, 247.5, 293.3, 330.0, 371.25]  # far-off voices on the water
    t = 0.4
    while t < 7.0:
        note = env(gain(sine(RNG.choice(scale), 1.1, vibrato=0.012, vib_rate=4.5), 0.16), 0.4, 0.5)
        place(out, lowpass(note, 0.2), t)
        t += RNG.uniform(0.8, 1.4)
    return seamless(out)


# ---- sfx (spec §5) ---------------------------------------------------------


def sfx_hit(low: bool) -> list[float]:
    burst = lowpass(white(0.09), 0.12 if low else 0.3)
    return env(gain(burst, 0.9), 0.002, 0.06)


def sfx_kill() -> list[float]:
    thud = env(gain(lowpass(white(0.16), 0.08), 1.0), 0.002, 0.12)
    drop = env(gain(sine(180, 0.22), 0.4), 0.01, 0.18)
    for i in range(len(drop)):
        drop[i] *= 1 - 0.6 * i / len(drop)
    return mix(thud, drop)


def sfx_death() -> list[float]:
    out = silence(1.3)
    place(out, env(gain(sine(220, 0.6), 0.6), 0.02, 0.4), 0.0)
    place(out, env(gain(sine(147, 0.8), 0.6), 0.05, 0.6), 0.45)
    return lowpass(out, 0.35)


def sfx_click(freq: float, seconds: float = 0.05) -> list[float]:
    return env(gain(sine(freq, seconds), 0.5), 0.002, 0.03)


def sfx_whoosh(rising: bool) -> list[float]:
    n = int(0.35 * RATE)
    noise = white(0.35)
    out, y = [], 0.0
    for i, x in enumerate(noise):
        a = 0.02 + 0.3 * (i / n if rising else 1 - i / n)
        y += a * (x - y)
        out.append(y)
    return env(gain(out, 0.8), 0.03, 0.15)


def sfx_steps(descending: bool) -> list[float]:
    out = silence(0.5)
    freqs = (0.35, 0.2) if descending else (0.2, 0.35)
    for i, alpha in enumerate(freqs):
        step = env(gain(lowpass(white(0.05), alpha), 0.9), 0.002, 0.04)
        place(out, step, 0.05 + i * 0.22)
    return out


def sfx_crane() -> list[float]:
    out = silence(2.1)
    for i in range(5):  # wingbeats, nearer each time — the one big sound
        beat = env(gain(lowpass(white(0.16), 0.18), 0.4 + 0.14 * i), 0.02, 0.12)
        place(out, beat, 0.15 + i * 0.38)
    place(out, env(gain(lowpass(white(0.5), 0.06), 0.5), 0.1, 0.4), 1.55)
    return out


def sfx_rumble(seconds: float, swell: bool) -> list[float]:
    base = lowpass(white(seconds), 0.012)
    n = len(base)
    return [s * 0.9 * ((i / n) if swell else (1 - i / n) ** 0.5) for i, s in enumerate(base)]


def sfx_grind() -> list[float]:
    return env(gain(lowpass(white(1.1), 0.06), 0.8), 0.15, 0.4)


def sfx_gaze() -> list[float]:
    dyad = mix(gain(sine(233, 1.4), 0.5), gain(sine(247, 1.4), 0.5))
    n = len(dyad)
    return [s * (i / n) for i, s in enumerate(dyad)]


def sfx_rite() -> list[float]:
    chord = mix(gain(sine(196, 1.6), 0.4), gain(sine(294, 1.6), 0.3))
    return env(lowpass(chord, 0.4), 0.05, 1.0)


# ---- voices (spec §5) -------------------------------------------------------


def voice_wilk() -> list[float]:
    n = int(1.4 * RATE)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        f = 320 + 180 * math.sin(math.pi * t) - 60 * t
        phase += 2 * math.pi * f / RATE
        out.append(math.sin(phase))
    return env(gain(lowpass(out, 0.3), 0.5), 0.15, 0.5)


def voice_strzyga() -> list[float]:
    n = int(0.7 * RATE)
    squeal = [math.sin(2 * math.pi * (1100 - 500 * i / n) * i / RATE) for i in range(n)]
    return env(gain(mix(gain(squeal, 0.4), gain(lowpass(white(0.7), 0.5), 0.25)), 0.9), 0.02, 0.3)


def voice_martwiak() -> list[float]:
    groan = sine(82, 1.1, vibrato=0.08, vib_rate=2.2)
    for k in (3, 5):  # rasp
        groan = mix(groan, gain(sine(82 * k, 1.1, vibrato=0.08, vib_rate=2.2), 0.15 / k))
    return env(gain(lowpass(groan, 0.25), 0.5), 0.2, 0.4)


def voice_bies() -> list[float]:
    base = lowpass(white(0.9), 0.05)
    growl = [s * (0.5 + 0.5 * math.sin(2 * math.pi * 28 * i / RATE)) for i, s in enumerate(base)]
    return env(gain(growl, 0.9), 0.05, 0.3)


def voice_utopiec() -> list[float]:
    out = silence(0.9)
    for _ in range(6):
        f = RNG.uniform(140, 400)
        blub = env(
            [
                math.sin(2 * math.pi * f * (1 - 0.5 * i / (0.08 * RATE)) * i / RATE)
                for i in range(int(0.08 * RATE))
            ],
            0.004,
            0.05,
        )
        place(out, gain(blub, 0.4), RNG.uniform(0, 0.8))
    return lowpass(out, 0.3)


# ---- manifest ---------------------------------------------------------------

ASSETS: dict[str, list[float]] = {}


def build() -> None:
    ASSETS.update(
        {
            "beds/wies.wav": bed_wies(),
            "beds/puszcza.wav": bed_puszcza(night=False),
            "beds/puszcza_noc.wav": bed_puszcza(night=True),
            "beds/bagna.wav": bed_bagna(night=False),
            "beds/bagna_noc.wav": bed_bagna(night=True),
            "beds/kurhany.wav": bed_kurhany(deep=False),
            "beds/kurhany_deep.wav": bed_kurhany(deep=True),
            "beds/dno.wav": bed_dno(),
            "beds/kupala.wav": bed_kupala(),
            "sfx/hit.wav": sfx_hit(low=False),
            "sfx/hurt.wav": sfx_hit(low=True),
            "sfx/kill.wav": sfx_kill(),
            "sfx/death.wav": sfx_death(),
            "sfx/pickup.wav": sfx_click(880),
            "sfx/tick.wav": sfx_click(1320, 0.03),
            "sfx/candle_lit.wav": sfx_whoosh(rising=True),
            "sfx/candle_out.wav": sfx_whoosh(rising=False),
            "sfx/stairs_down.wav": sfx_steps(descending=True),
            "sfx/stairs_up.wav": sfx_steps(descending=False),
            "sfx/crane.wav": sfx_crane(),
            "sfx/thunder.wav": sfx_rumble(1.8, swell=False),
            "sfx/wij_stirred.wav": sfx_rumble(1.4, swell=True),
            "sfx/wij_lid.wav": sfx_grind(),
            "sfx/wij_gaze.wav": sfx_gaze(),
            "sfx/rite.wav": sfx_rite(),
            "voices/wilk.wav": voice_wilk(),
            "voices/strzyga.wav": voice_strzyga(),
            "voices/martwiak.wav": voice_martwiak(),
            "voices/bies.wav": voice_bies(),
            "voices/utopiec.wav": voice_utopiec(),
        }
    )
    for rel, samples in ASSETS.items():
        write(rel, samples)
    credits = [
        "# Auto-generated by tools/gen_sounds.py — the starter set credits itself.",
        "# Curated replacements (freesound.org, CC0/CC-BY only) must replace their",
        "# entry here by hand: file, author, source_url, license.",
    ]
    for rel in ASSETS:
        credits.append(f"- file: {rel}")
        credits.append("  author: Prestarius (synthesized)")
        credits.append(
            "  source_url: https://github.com/prestarius/wyraj/blob/main/tools/gen_sounds.py"
        )
        credits.append('  license: "CC-BY-SA-4.0 (project original)"')
    (ROOT / "CREDITS.yml").write_text("\n".join(credits) + "\n", encoding="utf-8")
    print(f"  CREDITS.yml  ({len(ASSETS)} entries)")


if __name__ == "__main__":
    build()
