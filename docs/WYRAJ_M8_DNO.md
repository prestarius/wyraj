# WYRAJ — M8 "DNO" — Ending, Antagonist, Victory Specification

> **Status:** Draft v0.1 — **Milestone 8**, addendum to `WYRAJ_PROJECT.md`; expands the M8 outline in `WYRAJ_ROADMAP_M8PLUS.md`
> **Prerequisites:** M0–M7 (crypt procgen, gromnica/light economy, crane flight, statuses, meta-progression, narration engine, epilogue-capable prologue renderer from Próg)
> **Principle:** the climax is *narrated*, not stat-blocked. The Wij has no HP bar. The player's light — the thing that has kept them alive for seven milestones — becomes the thing that kills them. Winning is a rite, not a DPS check.

---

## 1. Depth Extension — kurhany 4–6 (depths 6–8)

The world chain grows: wieś(0) → puszcza(1) → bagna(2) → kurhany 1–3 (3–5) → **kurhany 4–6 (6–8)**. `MAX_DEPTH` becomes 8. Same BSP generator family, new per-tier rules:

| depth | crypt | darkness | sky shafts | notes |
|------:|------:|----------|-----------|-------|
| 6 | 4 | ambient FOV 3 | 1 | tighter corridors, first sługi |
| 7 | 5 | ambient FOV 2 | 0 — **no crane exit** | the way out is back up, or through |
| 8 | 6 | **ambient FOV 1** (touch) — a lit gromnica is the only sight | 0 | the Wij's chamber replaces the down stairs |

- **Gromnica economy is the run's spine below depth 6.** Deep loot tables carry candles and food, little else of comfort; the dziad's deep stock leans candles at cruel prices. No new mechanics — the existing `LightSource` rules simply become load-bearing.
- **No crane flight below depth 6** (no shafts): the znamię/perch contract is untouched; the depth simply offers no open sky. Descending past 6 is a commitment the narration marks once.
- **Narration register shift ("the szept changes sides"):** new ambient/level rules for depths 6–8 address the player directly, in second person, increasingly certain — authored EN/PL like any pack content, plus a small set of one-time szept lines that stop *helping* and start *noticing* ("It knows the candle is half gone. So do you."). Pure content; no engine change.
- **Spawns:** existing deep roster (martwiak, licho, strzyga) at higher counts, plus one new creature (§2.1). No difficulty inflation via stats — pressure comes from darkness, hunger math, and candle attrition.

## 2. The Wij — a situation, not a boss

Folklore: the buried one, lids too heavy to lift himself; what his opened gaze falls upon dies. Mechanically he is a **countdown with servants**, fought in the dark.

### 2.1 The chamber and the sługi

- Depth 8 generates one authored **vault** (fixed layout stamped into the BSP level, like the village template): a long barrow hall, the **stone cradle** at its heart where the Wij lies, wall niches along the sides.
- New monster: **sługa** (`sluga`) — grave-servants, slow, weak in melee (they are pallbearers, not soldiers), immune to fear. Data-driven like any monster, but with behavior `lift`: they path to the cradle and **channel the lifting** while adjacent.
- Sługi respawn from niches every K turns (TUNING KNOB, default 12) up to a cap of 4 concurrent — the pressure is perpetual; you cannot clear the room, only buy time.

### 2.2 The lifting (phase state)

A per-level `WijState` with a **lifting meter** 0–100, ticking on `TurnEnded`:

- +N per servant adjacent to the cradle and channeling (default 2 each).
- Killing a servant knocks the meter back (−10) — corpses make poor pallbearers.
- Thresholds publish events (all narrated, EN/PL, `importance: high`):
  - 25 — `WijStirred`: the ground remembers how to breathe.
  - 60 — `WijLidLifted`: one eye. The hall's ambient FOV rises to 2 — *his* light, and it is wrong.
  - 100 — `WijGazeOpened`: the gaze is open.

### 2.3 The gaze — light inverts

While the gaze is open, **every turn the player is visible to the Wij** costs heavy true damage (default 6, ignores armor: "what he sees, dies"). Visibility is the game's own FOV run from the cradle — and here the whole light economy flips:

- **A lit gromnica marks you.** Carrying flame in his line of sight = seen.
- **Darkness hides you.** Unlit, behind pillars, out of his line — safe.
- Every rule the player learned ("light is life") betrays them in the last room, and the narration says so. Douse the candle (`1–4` quickslot on the gromnica or use from pack — dousing a lit gromnica becomes possible in this room's context, forfeiting its remaining turns) or break line of sight.

The Wij **cannot be attacked, damaged, or killed**. He has no Health component. Attacks into the cradle tile narrate futility once and are otherwise no-ops.

### 2.4 The rite — zamknięcie powiek

Victory = pressing the lids shut. Standing **adjacent to the cradle**, holding **sól święcona**, the player begins a 6-turn channel (reusing the crane `Channeling` machinery — interruptible by damage). Rules:

- The salt is consumed when the channel *begins* (harsh, consistent with feather doctrine, open decision #6).
- Taking damage interrupts; the salt is gone; you need another twist of it.
- The rite may be performed at any meter value — but while the gaze is open (100), you must reach the cradle unseen, which is the intended climax: candle out, in the dark, hands on stone lids, counting six turns while sługi grope toward you.
- Channel completes → `WijSealed` → the meter dies, the sługi fall where they stand, and the run is **won**.

## 3. Victory and epilogues

- `WijSealed` sets `game.victory = True`; the run ends (the UI transitions like death, but into the **epilogue**, not the morgue screen).
- **Epilogues** are prologue-format (paged, typewriter, per-language, `data/intro/{en,pl}/epilogues.yml`), selected by run state, first match wins:
  1. **"Gospodarz"** — dziad befriended (met this run and `dziad.reputation ≥ 3`): the cart is waiting where no cart could be; you ride out of the earth like goods with a destination.
  2. **"Ptaki"** — codex ≥ 80% known or any god's favor active at the seal: the cranes come down *into* the barrow; open sky is a formality for them.
  3. **"Świt"** (default): you climb. It takes days. The wieś argues about you at the church door — this time about something else.
- **Meta writes** (one transaction, `kind="victory"`): `meta.victories` gains `{origin, seed, turn, epilogue, date}`; the winning origin is marked in the origin-select; the title screen's tagline pool gains a permanent line — "The birds returned, once." / "Ptaki wróciły, raz." Morgue-equivalent: a **victory file** in `morgue/` (same format, `Fate: the lids stayed shut`, portrait included).

## 4. "Głębiej" — post-victory modifier runs

Unlocked by ≥1 victory; offered on the title screen next to New Journey. One toggle, v1:

- Ambient FOV −1 everywhere (min 1), spawn counts +2 per level, drop tables richer (+1 loot roll), prices +25%.
- The modifier is part of run identity: seeded identically, flagged in save/morgue/history (`głębiej: true`), and its deaths count into the same meta.
- No stacking tiers in v1 (open decision #23).

## 5. Balance doctrine

- Target: **10–20% win rate for a skilled player**. Proxy: a scripted "competent bot" (greedy heuristics: keep candle lit, eat at hungry, drink at wounded, flee at dying, descend when stable, perform the rite by the book) run headless over N seeds.
- The sim is a *tracked measurement*, not a CI gate: `tests/test_dno_sim.py` marked slow, run on demand; asserts only the sanity floor (bot can win at least once in the seed set, and never wins >50%).
- Tuning knobs live where the numbers are: sługa respawn K, lift rate, gaze damage, rite length — all module constants or YAML, all listed in one place in the spec's tuning table.

## 6. Content inventory (both languages, authored natively)

- Bestiary: `sluga.yml` (+ forms, codex entry, discovery line).
- Narration: `data/narration/{en,pl}/wij.yml` — stirred/lid/gaze/seen-by-gaze/futile-attack/rite started/interrupted/completed rules; deep-ambient additions to `levels.yml`.
- Szept: 3–4 deep lines that "change sides"; 1 first-descent-past-6 warning.
- Intro: `epilogues.yml` ×2 languages, 3 epilogues × 3–4 pages.
- Locale: victory screen chrome, Głębiej toggle labels, title line.
- Loot: `data/loot/kurhany_deep.yml`; economy: dziad deep stock tier.

## 7. Implementation order (CC execution plan)

Feature branch `feat/m8-dno`; each story keeps `main` playable; golden transcript untouched (all new content sits below the scripted walk).

1. **US 11.1 — Depth tiers**: MAX_DEPTH 8, per-tier darkness/shaft rules, deep loot + spawns, no-crane-below-6, descent-marker narration. *Verify: headless descent to 8; per-tier FOV asserted; golden unchanged.*
2. **US 11.2 — Vault & sługi**: authored chamber stamped at depth 8, sługa monster with `lift` behavior, niche respawns. *Verify: chamber deterministic per seed; sługi path and channel headlessly.*
3. **US 11.3 — WijState & gaze**: lifting meter, threshold events + narration, gaze visibility damage, light inversion (lit = seen), attack futility. *Verify: scripted fixtures for each phase; Wij provably unkillable.*
4. **US 11.4 — The rite & victory**: salt-consuming channel, `WijSealed`, `game.victory`, meta transaction, victory file. *Verify: scripted headless run wins end-to-end.*
5. **US 11.5 — Epilogues**: paged renderer reuse, 3 epilogues ×2 languages, selection logic, title-line + origin marking. *Verify: selection unit-tested for every branch in both languages.*
6. **US 11.6 — Głębiej**: unlock, toggle, modifier application, run flagging. *Verify: same seed ± Głębiej diverge deterministically; flag survives save.*
7. **US 11.7 — Balance sim & polish**: competent bot, N-seed measurement harness, tuning pass, docs/CHANGELOG. *Verify: sanity floor holds; tuning table documented.*

**Definition of done:** (a) a scripted headless run reaches depth 8, performs the rite, and wins — transcript-stable; (b) the golden run is byte-identical; (c) every epilogue branch renders in EN and PL with no unresolved slots; (d) the Wij takes no damage under a property test that attacks him every way the engine allows; (e) victory writes meta once, unlocks Głębiej, and changes the title pool; (f) the bot sim runs and reports within the sanity floor.

## 8. Open Decisions (for Prestarius)

20. **Antagonist confirmed as the Wij?** (Alternatives considered: Żmij — too draconic/heroic; Licho-matka — better kept ambient. The Wij's gaze mechanic is the only one that inverts the light economy.) Spec default: **Wij**.
21. **Rite requirement** — sól święcona consumed at channel start (spec default, harsh) vs. a bare-handed rite with a longer channel (10 turns)?
22. **New creatures** — just the sługa (spec default), or also a second deep ambient horror (e.g. "to-co-czeka", never fights, only follows)?
23. **Głębiej stacking** — single tier v1 (spec default) or victories stack deeper modifiers?
24. **Balance target** — accept 10–20% skilled-player win rate as the tuning goal?
25. **Epilogue count** — three (spec default) or cut to two (Świt + one earned) for v1 prose budget?
