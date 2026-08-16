# Changelog

All notable changes to Wyraj. Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — M10 "Zlecenia" (errands, the village that remembers)

### Added
- **Zlecenia.** Each run assembles 1–3 errands from a YAML catalog
  (`data/errands/`), deterministically from (seed, meta), at most one
  ask per giver. Two kinds only — hunt (the kill guarantees a proof
  trophy at the corpse, once) and fetch (the item is stamped into its
  depth at generation). No escorts, no journal, no dialogue trees:
  bumping a villager speaks the ask once (heard = taken), bumping again
  with the proof hands it over.
- **Two new villagers.** Radzim the kowal at his open-air forge and
  Bogusz the młynarz, with EN/PL greetings — and reasons to need you.
- **Villager reputation.** Rewards pay into the banked wallet and into
  `meta.villagers` (per-role memory: favor, kept, broken). Total village
  favor opens the trader's good shelf (guaranteed extra stock at rep
  3 and 6); at favor 3 a villager greets you as a known face.
- **Village fates.** A chain ignored across 3 runs resolves off-screen,
  once, forever: the mill empties (Bogusz leaves, bread leaves the
  shelves), the kapliczka goes dark (shrine lines dim), the forge goes
  cold (Radzim leaves, weapons thin out). The next run's first step in
  the wieś announces it — told once, ever — and the morgue records
  broken words and the changed village.
- **Codex Zlecenia tab.** Tab cycles bestiary ↔ errand ledger in both
  the in-run codex and the title-menu codex (the latter reads meta
  alone); gossip rumors escalate to point at your unfinished business.

### Changed
- Golden transcript regenerated once (US 13.2): two new villager
  entities shift later entity ids; normalized diff is id-only.
- The utopiec finally drops proof (`utopcowa_luska`); prices for the
  M7 slot pieces (szkaplerz, baranica, łapcie).

## [0.10-kolo-roku] — merged 2026-08-16 — M9 "Koło Roku" (time, weather, festivals)

### Added
- **The wheel turns.** A 240-turn day (świt/dzień/zmierzch/noc) on a
  12-day wheel whose starting day is part of the seed's identity — all
  of it pure functions of (seed, turn), zero saved state. The pane shows
  phase, moon, weather, and festival; surface floors take the sky's
  color; the seed-42 golden walk turned out to begin on Gromniczna.
- **Night and weather.** Surface sight follows the sky (mist shortens
  it further; a carried flame pushes night back); rain drains an
  unprotected gromnica; during burza Perun is present — his shrine
  favor doubles and lightning cracks overhead. Spawn pools read the sky
  at generation time: strzygi hunt at night, and the południca — the
  noon demon in white linen — exists only at midday.
- **Festivals**, each with one ritual: Gromniczna halves candle burn;
  on Noc Kupały the fern flowers once per run somewhere on your level;
  Dożynki makes village rest free; on Dziady the dead walk under a
  truce and *talk* — the codex learns martwiaki from conversation, not
  killing.
- A first-night szept whisper; EN+PL narration for phases, weathers,
  festivals, the bloom, the talking dead, and the lightning.

### Changed
- Golden transcript regenerated once, intentionally (open decision #30):
  calendar boundary events necessarily enter the seed-42 walk.

## M8 "Dno" (ending, antagonist, victory) — merged 2026-08-16

### Added
- The world now bottoms out: crypts 4–6 (depths 6–8), unlit sight
  shrinking to 3/2/1 tiles, no collapsed-ceiling shafts below depth 6 —
  past the last open sky there is no crane home, and the narration marks
  the step once.
- **The Wij.** An authored vault at depth 8: the buried one in his stone
  cradle, sługa pallbearers walking out of wall niches to lift his lids
  against a meter you can only delay. He has no HP and cannot be
  attacked. When the gaze opens, the light economy inverts — a lit
  gromnica in his line of sight is death (6 true damage a turn),
  darkness hides you, and using a light while burning now douses it.
- **Winning.** Bump the cradle holding sól święcona to begin the
  zamknięcie-powiek rite: six turns of pressing, interrupted by moving
  or damage, the salt spent either way. Completion seals the lids —
  the run is won.
- Three epilogues (EN and PL, prologue-format): the long climb out, the
  dziad's impossible cart, the cranes coming down through the barrow —
  chosen by how the run was lived. Victory writes `meta.victories`, a
  morgue file reading "Fate: the lids stayed shut", the permanent title
  line "The birds returned, once.", and a ⁂ next to winning origins.
- **Głębiej** — post-victory modifier runs: sight −1, +2 spawns per
  level, +1 loot roll, +25% prices; flagged in the save and the record.
- A provisioned competent-bot descent sim (`WYRAJ_SIM=1`) measuring the
  win rate (1/30 at cut) with a CI smoke floor.

## M7 "Sylwetka" (character pane & quickslots) — merged 2026-08-16

### Added
- Layered, state-reactive portrait driven by YAML art under
  `data/portrait/{box,half,ascii}.yml`: base figure (hunched at low HP),
  weapon/armor overlays, a warm halo while the gromnica burns, wound
  decals over four HP bands (dying is now <10%), status decals with
  non-color redundancy (poison edges, blessing outline, wet lower third,
  fear recoil), blizna scar marks, and a tiny trophy belt. Monochrome
  distinguishability is enforced by tests.
- Equipment paper-doll in the pane (head/torso/weapon/offhand/amulet/
  feet) with stat suffixes, heirloom ⟲ rune, and the lit gromnica's
  remaining burn shown in the offhand. `e` opens a modal to free a slot.
  New slot-ready content: sheepskin baranica, bast łapcie, szkaplerz of
  Weles.
- Quickslots "Podręczne": bind in the pack (`1-4`, then a letter), use
  in-game on `1-4` (an empty press costs no turn), `Shift+1-4` clears.
  Bindings are by item key — stack counts show as `×N`, and a refilled
  stack revives the key; `quickslots.auto_refill: false` in config.yml
  unbinds an emptied slot instead. Bindings ride the in-run save.
- Status row: one family-colored line (glyph + name + turns), overflow
  as `+N more`.
- Blizny: surviving a dying dip leaves a permanent-for-the-run scar on
  the portrait, narrated once ("The scar has stopped weeping…").
- Named weapons: seven kills of one species name the weapon (Wilcza
  Zguba / Wolves' Bane…); announced in prose, shown in the paper-doll,
  greeted once by the dziad, and preserved through the skrzynia.
- Death portrait: the final composited portrait is captured into the
  morgue file — every death leaves a picture of who you were at the end.
- Pane extras: last-foe mini-line (name, in-fiction HP word, codex-tier
  mark) and a short-terminal fallback (4-row mini portrait, filled slots
  only, quickslots always visible).

### Deferred (recorded in the plan)
- Tab focus-cycling of pane regions, enchant/curse color coding (no
  identification system yet), burden indicator (no stamina system yet),
  quickslot-use flash animation.

## Szlif (UI polish & death flow) — merged 2026-08-15

### Added
- Death screen choices: `n` sets out again (fresh run, same origin; a
  pinned `--seed` stays pinned), `m` returns to the title screen, `q`
  leaves. `WyrajApp` now exits a typed outcome and the entrypoint loops.
- `q` mid-run asks before abandoning (an abandoned run is not saved);
  `s` remains the silent save+quit.
- Visual pass "czarnoles+": panel border titles (live place name, origin,
  "The Tale"), modals as lit bordered panels floating over the dimmed
  game, biome-tinted floors (wieś/puszcza/bagna/kurhany), a brief red
  flash on the player glyph when hit, themed footer and scrollbar.
- Narration presentation: each turn's paragraph is tinted by its dominant
  event family (combat ember, loot gold, lore purple, ambient grey) via a
  cosmetic `NarrationLine.category`; paragraphs are separated by blank
  lines. Narration *text* is byte-identical — the golden transcript is
  unchanged.
- Narration pane grew to 40% of the screen (min 12 rows).

### Fixed
- Escape actually closes the interactive modals (skrzynia, inventory,
  trade, shrine): their `on_key` stopped every key before the screen's
  Escape binding could run.
- Opening the inventory while carrying a trophy no longer crashes.
- Inventory letters on trinkets/trophies keep the dialog open instead of
  silently closing it.
- The death screen is modal: app keybindings no longer leak through it.

## [0.7-prog] — 2026-08-15 — Próg (intro & onboarding)

### Added
- Title screen: block-letter WYRAJ under a sky of drifting cranes, a
  rotating folklore tagline, and a keyboard menu — New Journey, Continue,
  Codex, Morgue, Options, Quit. Seeded starts hide in Options.
- Prologue: four pages of typewriter prose falling from grey to cold
  blue, with an origin-specific final page (why *your* road is closed);
  Esc always skips, and a profile that has read it once is never made to
  read it again. Authored natively in EN and PL.
- Szept: diegetic first-encounter whispers — nine one-time asides woven
  dim-italic into the log (movement, first hostile, low HP, hunger,
  darkness, loot, the forest edge, statuses, first kill), persisted per
  profile in meta, closed by a farewell line. Hints toggle in Options;
  never a popup, ever.
- Help (`?`): full key reference plus "How Wyraj works" written in-voice
  ("Death is not the end of knowledge. It is, regrettably, the end of you.").
- Options write `~/.wyraj/config.yml` (hints, text speed, portrait, language).

## [0.6-m6] — 2026-08-15 — Powroty (meta-progression)

### Added
- Meta-state (`~/.wyraj/meta.yml`): versioned, HMAC honesty flag (edits
  load fine, get marked), unknown fields preserved, atomic writes,
  `MetaTransaction` events at every defined mutation point.
- Economy: denary carried in an on-body purse (lost with the body),
  auto-banked in the wieś; lore-gated drops (beasts leave trophies, only
  the drowned and the buried carry coins), burial hoards, coin shop
  replacing barter, per-run village stock.
- The skrzynia: one iron-bound chest whose contents survive death;
  4→10 slot upgrades; heirlooms remember the hand that owned them.
- Death integration: achievement counters, morgue meta summary, and
  origins unlocked by deeds — Strzygobójca (die to her thrice) and
  Dziadowy Uczeń (dziad reputation 5) — announced on the death screen.
- The wandering dziad: pity-guaranteed crypt encounters, cruel prices
  softened by persistent reputation, tiered stock, and recognition that
  crosses deaths ("You again. Or… no. Someone *like* you.").
- Crane flight: żurawie pióro starts a 6-turn channel (broken by damage
  or movement, feather spent regardless), refused under watching eyes or
  closed sky; kurhany gained collapsed-ceiling shafts; znamię + żerdź
  make the round trip.
- Shrines of Perun and Weles: offerings buy run-scoped favors only.
- Codex knowledge tiers (glimpsed/studied/known) persisting across runs,
  with trophy values and weakness hints at higher tiers.
- 50-run shared-meta balance sim guarding the doctrine: heirlooms, not a
  savings account.

## [0.5-m5] — 2026-08-15 — AI Narrator (optional)

### Added
- `LLMNarrator` behind `--narrator llm` / config: Ollama-first with an
  OpenRouter alternative, fact-grounded prompt built on the deterministic
  template draft, strict timeout with template fallback, 60-word cap,
  per-run latency/fallback stats. Off by default; the game remains fully
  playable offline and byte-deterministic under the default narrator.
- M6 "Powroty" meta-progression spec filed (`docs/WYRAJ_M6_POWROTY.md`)
  with Epic 7 plan breakdown.

## [0.4-m4] — 2026-08-15 — Polski

### Added
- Native Polish narration packs (`data/narration/pl/`) with full rule
  parity to English, authored as original prose — not translations.
- Case-form tables (mian/dop/cel/bier/narz/miej) for every monster and
  item; the strzyga is *ona*, the player declines as *ty/ciebie/tobą*;
  per-rule English fallback if a PL rule is ever missing.
- `--lang pl` (also a `lang:` config key); UI catalog in
  `data/locale/{en,pl}.yml` covering panel, screens, death, trade, and
  character creation; Polish origin intros and descriptions.
- Blog draft: docs/blog/grammar-aware-narration.md.

## [0.3-m3] — 2026-08-15 — Public Release Cut

### Added
- The wieś: an authored village hub with karczmarka (rest), handlarz
  (barter trade v0), and the dziad whose rumors feed the narration.
  Bumping a villager talks; nobody in the wieś wants a fight.
- Bagna biome between forest and crypts: water pools you can see across
  but not wade, swimming utopce that haunt the shorelines, marsh loot and
  three new story hooks (the sunken cross, the fowler's hut, błędne ogniki).
- Character creation: Wygnaniec, Zielarka, Najemnik — distinct stats,
  starting kits, and opening narration; data-driven in `data/origins.yml`;
  `--origin` flag and selection screen.
- Morgue files on death, SQLite run history (`wyraj --history`),
  `~/.wyraj/config.yml`; cause of death tracked and shown.
- Licensing: AGPL-3.0-or-later (code), CC BY-SA 4.0 (`data/`), CLA;
  CONTRIBUTING, Code of Conduct, issue templates.
- Docs: ARCHITECTURE.md, CONTENT.md, NARRATION.md, README with screenshot.

### Changed
- World is now a fixed chain: wieś (0) → puszcza (1) → bagna (2) →
  kurhany (3–5); crypt darkness starts at depth 3. Save format v2.

## [0.2-m2] — 2026-08-14 — Depth & Danger

### Added
- Multi-level descent: BSP kurhany crypts under the puszcza, stairs,
  in-run level persistence, frozen off-level actors, lazy deterministic
  per-level generation (pure function of seed and depth).
- Status effects: bleeding and grave-rot poison (damage over time), fear
  and blessing (to-hit modifiers); inflicted by strzyga/martwiak/bies
  attacks from bestiary data; blessed salt now blesses.
- Lighting: crypts are dark (short FOV); the gromnica burns as a real
  light source and the `darkness` narration context goes live.
- Loot tables per biome; armor slot (wolfskin cloak, quilted kaftan) with
  full-absorb GRAZE outcome; AI behaviors: pack wilki with flanking bonus,
  ambusher strzyga, fleeing licho (new monster).
- Story hooks v1: three discoverable narrative seeds per biome with
  one-shot first-sight narration.
- Save/load: single gzip-JSON slot, RNG streams restored bit-exactly,
  save consumed on load and deleted on death (permadeath honored);
  `s` saves and quits, plain `wyraj` continues a saved run.

## [0.1-m1] — 2026-08-14 — It Reads Like a Story

### Added
- ContextEnricher: HP-band, unseen-attacker, and recency ("again") context
  tags; tag-filtered variant selection with anti-repetition.
- TurnComposer: one composed narrative paragraph per full round.
- Grammar-aware string-form tables (spec §7): EN def/indef/plural/pronoun
  accessors, PL case tables supported and tested; slots like
  `{defender.name.def}` in packs.
- Content wave 1: five monsters (bies, wilk, utopiec, strzyga, martwiak),
  ten items (folk remedies, weapons, trinkets), weighted spawns.
- Inventory (get/use/wield), hunger clock with starvation, weapon damage
  flowing into combat events.
- Examine screen, bestiary codex unlocked by sightings, per-monster
  first-sighting narration (`LoreDiscovered`).
- Reactive portrait: HP-band color wash + wound decals + weapon overlay;
  two prototype art directions (`--portrait half|box`) for decision #5.

## [0.0-m0] — 2026-08-14 — Walking Skeleton

### Added
- Project scaffold: uv-managed package, ruff/mypy/pytest toolchain, CI.
- Minimal hand-rolled ECS, typed event bus (events carry facts, not text),
  energy/speed-based turn scheduler, named seeded RNG streams.
- Cellular-automata puszcza map, symmetric shadowcasting FOV with
  explored-tile memory, bump movement.
- First monster (bies, YAML bestiary + pydantic validation), melee combat,
  permadeath with death screen showing the seed; `--seed` and `--ascii` flags.
- Narration pipeline v0: TemplateNarrator with weighted YAML grammar packs,
  first EN combat pack; narration draws from its own RNG stream.
- Textual three-pane UI ("czarnoles" dark theme): map with FOV dimming,
  character panel with portrait and HP bar, scrollable narrative log.
- Golden-run regression: seed 42 + scripted walk → full event+narration
  transcript snapshot (`GOLDEN_REGEN=1` to regenerate intentionally).
