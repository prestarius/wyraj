# WYRAJ — Intro & Onboarding Specification ("Próg" — The Threshold)

> **Status:** Draft v0.1 — addendum to `WYRAJ_PROJECT.md` (do not modify the main spec while CC executes; merge later)
> **Target milestone:** skeleton at end of M0 (title screen only), full experience in **M1**, origin-variant prologues in **M3** (when origins exist), PL prose in M4
> **Principle:** The intro is the first proof of the game's identity. A player should *read* something beautiful before they press a single movement key — and never see a tutorial popup, ever.

---

## 1. Flow

```
Launch
  └─ Title Screen ──────────────► Options / Codex / Morgue / Quit
        │  [New Journey / Continue]
        ▼
  Origin Selection (M3+; M1: skip straight to prologue)
        ▼
  Prologue Sequence  (novel-like, paged, skippable)
        ▼
  Arrival Scene      (playable village/forest edge, guided by narration)
        ▼
  Normal play        (first-encounter hint system active, §5)
```

## 2. Title Screen

- Full-screen Textual view: **WYRAJ** rendered as large Unicode/figlet-style lettering, with a slow ambient effect (Textual timers): occasional bird glyphs (`ˇ`, `v`, `w`) drifting across the top — the wedge of cranes motif, foreshadowing both the lore and the M6 crane flight.
- Beneath the title, a rotating **atmospheric line** (one per launch, from `data/narration/en/title_lines.yml`), e.g.:
  - "The birds know the way. The birds always knew."
  - "Every soul returns. Not every soul returns the same."
  - "Beyond the ninth forest, beyond the ninth river."
- Menu: `New Journey` / `Continue` (only if in-run save exists) / `Codex` (M6: persists) / `Morgue` / `Options` / `Quit`. Keyboard-only, styled like the rest of the game.
- Seed entry hidden behind `Options → New Journey (seeded)` — daily players and testers find it; new players never see a number.

## 3. Prologue Sequence

### 3.1 Presentation

- Paged, novel-like screens: one paragraph per page, centered column (max ~70 chars wide), Rich-styled serif-feel via dim/italic contrast.
- **Typewriter reveal** (per-character, ~15ms, configurable `intro.text_speed`, `instant` option); any key completes the current page, `Enter` advances, `Esc` skips the whole prologue (skip must always work — respect the 200th run).
- Subtle ambient color shift page to page (deep grey → moss green → cold blue) — dusk falling.
- After first completion, `New Journey` offers "skip prologue" as remembered preference (meta-state in M6, config file before that).

### 3.2 Draft prose (EN, v1 — generic, pre-origins)

> **Page 1**
> They say the birds fly to Wyraj when the cold comes — beyond the ninth
> forest, beyond the ninth river, to the land where souls wait to be born.
> They say the dead go there too, walking the same wind-road, and that
> what goes to Wyraj comes back in spring.
>
> They say many things, in the village at the edge of the puszcza.

> **Page 2**
> You came up the cart-road at dusk, when the mist was rising off the
> bagna and the last light hung in the birches like something snagged.
> The village took you in the way such places do: without questions,
> because questions invite answers, and answers invite the dark.

> **Page 3**
> But you have heard what they whisper by the fire. That the barrows in
> the deep forest have opened. That children hear singing from the marsh.
> That the old woman who kept the shrine of Weles is gone, and the offering
> bowl is licked clean each morning by no dog anyone owns.
>
> Something below is calling things up. Or calling them *back*.

> **Page 4**
> You did not come here to be safe. You came because the road behind you
> is closed, and the only way left runs down — under the kurhany, under
> the roots, toward whatever waits at the bottom of the dark.
>
> The birds know the way.
> The birds always knew.
>
> *(press Enter to begin)*

### 3.3 Origin variants (M3+)

- Page 4 is replaced per origin — same structure, different "why the road behind you is closed":
  - **Wygnaniec** (exile): cast out for a crime the prologue only hints at.
  - **Zielarka** (herbalist): the shrine-keeper was her teacher; she owes the dead a debt.
  - **Najemnik** (sellsword): paid half in advance by a man who has since been buried — twice.
- Authored in `data/narration/en/prologue.yml` (paged structure, per-origin blocks) — content, not code.

## 4. Arrival Scene (playable prologue tail)

- The run begins at the **village edge at dusk** — not mid-dungeon. First 20–30 turns are a soft space: no hostiles spawn within the village radius.
- The narrator carries the guidance **diegetically** — no popups, no "PRESS I FOR INVENTORY" overlays. Instead, one-time narration lines woven into the log as the player acts:
  - On first step: "The village is quiet. The smith's fire is banked; the trader's door stands open. *(move with arrows or hjkl; ? shows everything else)*" — mechanical hints appear as dim italic asides, visually separate from prose, and only in hint mode (§5).
  - Standing near the trader's door: "Warmth and tallow-smell drift out. Whatever the dark needs of you, it can wait a moment more."
  - At the forest edge: "The puszcza begins where the fences end. Past the first trees, no one will hear you." — crossing it is the informed consent moment; the game truly starts.

## 5. First-Encounter Hint System ("Szept" — whisper)

- A thin system subscribed to the event bus: on the **first occurrence per profile** of key situations, emit one dim-italic guidance aside after the normal narration. Fired-once flags persist (config file pre-M6, `meta.yml → szept` after).
- Trigger table (`data/narration/en/szept.yml`), initial set:

  | Trigger | Aside (example) |
  |---|---|
  | First hostile sighted | *(bump into a creature to strike it)* |
  | HP first drops below 50% | *(wounds heal with rest and remedies — fleeing is not cowardice here)* |
  | First hunger warning | *(you carry food; i opens your pack)* |
  | First darkness tile | *(light matters: gromnice burn, and some things fear them)* |
  | First item on floor | *(g gathers what lies at your feet)* |
  | First stairs | *(> descends. What goes down is not owed a way back up)* |
  | First status effect | *(c shows what afflicts you)* |
  | First codex-worthy kill | *(x examines; the codex remembers what you learn)* |

- **Hints mode:** `on` (default first profile) / `off`. Auto-offers to switch off after the player has seen all core triggers ("The whispers fall silent; you know this world now."). Veterans never see them again — the flags persist.
- Hard rule: szept lines never block, never modal, never repeat. One miss is fine — the `?` help screen is the complete reference.

## 6. Help Screen (`?`)

- Full keybinding reference + a "How Wyraj works" one-pager (permadeath, hunger, light, stash once M6 lands) written in-voice, not manual-voice: "Death is not the end of knowledge. It is, regrettably, the end of you."
- Always available; this is the safety net that lets the diegetic system stay minimal.

## 7. Implementation Notes (CC)

- New Textual screens: `TitleScreen`, `PrologueScreen`, reuse main game screen for arrival. All prose/data in YAML — zero hardcoded strings (i18n rule from main spec §7 applies; PL prologue authored natively in M4, not translated).
- Typewriter effect: Textual `work`/timer-based; must remain responsive to skip keys at all times.
- Szept system: `narration/szept.py`, subscribes to existing events, no new core systems needed.
- Tests: Pilot smoke test (title → prologue → skip → game), szept fired-once persistence test, prologue YAML schema validation.
- Estimated size: small — 2 screens, 1 subscriber system, 3 content files. Fits at the end of M1 without displacing anything.

## 8. Open Decisions (for Prestarius)

1. Prologue prose above — keep/edit? (It sets the voice for the whole game; worth a careful read.)
2. Should `Esc`-skipping the prologue on the very first run require one confirmation ("You will not see this again the same way")? I lean no — respect the player.
3. Title ambience: drifting bird glyphs — delightful or distracting? Prototype and feel it.
4. Szept asides styled as dim italics in-log vs. a separate one-line hint bar under the log. Spec assumes in-log (less UI, more diegetic).
