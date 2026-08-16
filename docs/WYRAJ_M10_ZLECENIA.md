# WYRAJ — M10 "ZLECENIA" — Errands Specification

> **Status:** Draft v0.1 — **Milestone 10**, addendum to `WYRAJ_PROJECT.md`; expands the M10 outline in `WYRAJ_ROADMAP_M8PLUS.md`
> **Prerequisites:** M0–M9 (village hub & trade, meta-progression + HMAC meta.yml, trophy drops, codex tiers, narration engine with tag-conditioned variants, calendar)
> **Principle:** the village stops being a service hub and becomes a community that asks, remembers, and — if ignored — quietly breaks. No quest journal, no dialogue trees, no escorts. A zlecenie is heard, done, and paid the way everything in Wyraj happens: through the narration engine and the meta ledger. What you don't do resolves without you.

---

## 1. Zlecenia — assembled, not scripted

A new content type: errand templates in `data/errands/wies.yml`, pydantic-validated in `content/errands.py`:

```yaml
syn_mlynarza:
  giver: mlynarz          # villager key
  kind: hunt              # hunt | fetch — nothing else; this game doesn't do escorts
  target: utopiec         # monster key (hunt) / item key (fetch)
  proof: utopcowa_luska   # hunt only: guaranteed drop while the errand is active
  depth: 2                # where the target lives / where the item is placed
  reward: {denary: 60, reputation: 1}
  patience: 3             # ignored runs before the fate resolves (0 = no fate chain)
  fate: mlyn_pusty        # village flag this failure feeds ("" = rep loss only)
  weight: 3
```

- **Assembly is pure:** at `Game.__init__`, eligible templates (giver still present, fate not yet resolved) get a weighted deterministic draw of **1–3 errands** via `sha256(seed, "errands")` — no new RNG stream. Same seed + same meta = same zlecenia; a run's errands are part of its identity.
- Assembly publishes **nothing**. An errand exists in the world before it exists in the log.
- **Two kinds only.** *Hunt:* while active, the target monster's death guarantees the proof drop (the existing trophy roll becomes certain — `_on_monster_died` branch); reuse existing trophies where the bestiary has them (wilczy_kiel, zab_strzygi, grobowy_wosk). *Fetch:* the item is stamped into the target depth at level population (worldgen stream, deterministic per route).
- v1 catalog: **5–6 templates** across the givers — the miller's son (utopiec, bagna), the shrine-keeper's censer (fetch `kadzielnica` from crypt 2 = depth 4; the keeper is already dead in the prose — old Świętosław asks for what's left), wolves at the charcoal pits (kowal), the fourth-night strzyga (karczmarka), grave-wax for the trader. Adding a template = YAML + two pack rules; no engine change.

## 2. Hearing and handing in — bump, like everything

- **No notice-post.** The wieś doesn't read; word of mouth is the notice-post. Bumping a villager who holds an active errand narrates the ask once — `ErrandHeard(errand, giver)`, rule `errand_heard/<key>`, EN+PL. Old Świętosław's `talked_to/gossip` pool gains **tag-conditioned variants** (existing `Variant.tags` machinery, enricher supplies `errand_active_<key>` / fate tags) — the rumors stop being bestiary hints and start pointing at your unfinished business.
- **Heard = taken.** No accept/decline, no journal: a word given in the wieś binds (open decision #32). Whether you act on it is what the run is about.
- **Hand-in:** bump the giver while carrying the proof/item → `ErrandCompleted` — the giver keeps the proof, the reward lands in the **banked wallet** (village = meta money, existing doctrine), reputation ticks, `MetaTransaction(kind="errand_done")`. Run-scoped errand status (`heard/proof/done`) is one additive save field.

## 3. The village grows two souls

New named villagers, same bump-to-talk plumbing (template glyph + `_VILLAGER_LORE` + `talked_to/<role>` rules EN+PL):

- **Radzim the kowal** — the smith whose fire the szept already mentions; posts by the empty hut.
- **Bogusz the młynarz** — the miller, because someone has to have lost a son to the utopiec.

`meta.villagers: dict[str, VillagerMemory{reputation, errands_done, errands_failed}]` — the `DziadMemory` shape, additive, no migration (defaults + `extra="allow"` absorb old files; HMAC rides along untouched). Recognition narration via rep-conditioned `talked_to` variant tags: the smith remembers souls the way the dziad does.

**Rare stock unlocks:** total village reputation (sum over villagers) gates extra entries in Miłosz's stock pool — the dziad's `tier_unlocks` shape, applied to `shop_village.yml` (e.g. rep 3 → +3 items, rep 6 → the good shelf). Persistent, meta-driven, one transaction kind `villager_rep`.

## 4. Fates — the village changes across deaths

Every run that ends (death or victory) with an errand heard-but-undone increments its giver's `errands_failed` and the template's fate counter — resolved in `apply_death_to_meta`, the existing between-runs hinge. When a counter reaches `patience`, the fate **resolves off-screen**, once, forever (open decision #34):

| flag | chain | what changes |
|---|---|---|
| `mlyn_pusty` | the miller's son | Bogusz leaves the wieś (not spawned again); his errands leave the pool; chleb leaves the trader's guaranteed stock; the gossip pool gains a variant: "The mill stands empty now." |
| `ciemna_kapliczka` | the censer | shrine narration dims (cosmetic palette swap — offerings still work; the gods are patient, the wieś is not) |
| `zimna_kuznia` | the wolves | Radzim leaves; weapons thin out of the village stock pool; the forge line in arrival narration goes cold |

- **Light touch, per the roadmap:** three flags, not a simulation. Each fate = one absence, one narration change, at most one gentle stock nudge. Karczmarka/trader errands carry no fate — failing them only costs reputation.
- **The telling:** next run, on first arrival in the wieś, an unannounced resolved fate publishes `VillageFateResolved(flag)` once (announced-set persisted in meta like `szept_seen`), rule `village_fate/<flag>`, `importance: high`. The morgue file gains a village-state line.
- Fresh meta has no flags and offers narrate only on bump → **the golden transcript should stay byte-identical**; if the scripted walk turns out to bump a villager, one sanctioned regeneration, named in the commit (open decision #35).

## 5. Codex — the Zlecenia tab

The codex screens grow tabs (Tab cycles Bestiariusz ↔ Zlecenia), each tab a pure text builder beside `build_codex_text`:

- **In-run:** this run's errands with status (heard / proof in hand / done) and giver — the only errand UI in the game, and it's a ledger, not a journal.
- **Title menu:** meta-only view (the title codex has no `Game`) — per-villager reputation and done/failed counts, resolved fates in their own dim section.
- All chrome through `ui/i18n.t()` + `data/locale/{en,pl}.yml`; the EN/PL key-parity test polices it.

## 6. Content inventory (both languages, authored natively)

- Villagers: Radzim + Bogusz `talked_to` rules; rep- and fate-conditioned variants for all five villagers' pools.
- Errands: `data/errands/wies.yml` (5–6 templates); narration `data/narration/{en,pl}/zlecenia.yml` — `errand_heard/<key>`, `errand_completed/<key>`, `village_fate/<flag>`; enricher tags.
- Items: `utopcowa_luska` (the utopiec finally drops proof), `kadzielnica` (unique fetch item) — full PL case tables, `spawn_weight: 0`.
- Locale: codex tab labels, errand status words, morgue village line.
- Meta: `villagers`, `village` flags, announced-fates set; transaction kinds `errand_done`, `errand_failed`, `village_fate`, `villager_rep`.

## 7. Implementation order (CC execution plan)

Feature branch `feat/m10-zlecenia`; each story keeps `main` playable.

1. **US 13.1 — Errand model & assembly**: `content/errands.py` + `data/errands/wies.yml`, pure seeded assembly from `(seed, meta)`, run-scoped status + save field, `ErrandHeard`/`ErrandCompleted` events + rule keys. *Verify: same seed + same meta = same errands, property-tested; assembly publishes nothing; save round-trips status.*
2. **US 13.2 — Two villagers**: Radzim + Bogusz in the template, lore, `talked_to` rules EN+PL. *Verify: bump narrates in both languages; golden untouched.*
3. **US 13.3 — The loop**: guaranteed proof drops while active, fetch-item stamping at depth, bump hand-in, banked reward + rep + transactions. *Verify: headless hear→kill→proof→hand-in→paid, transcript-stable; fetch variant likewise.*
4. **US 13.4 — Reputation & stock**: `meta.villagers`, rep-gated village stock tiers, rep-aware `talked_to` variants. *Verify: rep thresholds unlock stock deterministically; recognition line fires at threshold.*
5. **US 13.5 — Fates**: failure accounting in `apply_death_to_meta`, patience counters, the three flags (absence + narration + stock nudge), next-run `VillageFateResolved`, morgue line. *Verify: N scripted deaths flip a fate exactly once; announcement fires once ever; miller provably gone.*
6. **US 13.6 — Codex tab & polish**: tabbed codex (both entry points), locale keys, gossip escalation variants, docs, CHANGELOG, sims re-measured. *Verify: tab renders in-run and meta-only from title; EN/PL parity green; meta-sim doctrine and dno-sim floor hold.*

**Definition of done:** (a) errand assembly is provably deterministic per `(seed, meta)`; (b) both errand kinds complete headlessly end-to-end with meta writes; (c) an ignored chain resolves its fate after exactly `patience` runs, is announced once, and permanently changes the village (spawn, stock, narration); (d) every new pack rule renders EN+PL against fixtures, locale parity green; (e) codex Zlecenia tab works from both entry points; (f) golden byte-identical (or one sanctioned, named regeneration); (g) 50-run meta sim stays inside the economy doctrine and the descent sim inside the M8 floor.

## 8. Open Decisions (for Prestarius)

31. **The two new villagers** — Radzim the kowal + Bogusz the młynarz (spec default), or fewer/other names?
32. **Acceptance model** — heard = taken, no accept/decline (spec default: a word given in the wieś binds) vs. an explicit take/leave prompt?
33. **Patience** — 3 ignored runs per fate chain (spec default)?
34. **Fates irreversible** — once the mill empties it stays empty (spec default, v1) vs. a redemption errand to undo a fate?
35. **Reward band** — 40–90 denary banked per errand (spec default; sized against `test_meta_sim.py`)? And sanction a golden regeneration only if the scripted walk provably bumps a villager?
