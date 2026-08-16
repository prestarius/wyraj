# WYRAJ — M7 "SYLWETKA" — Character Pane & Quickslots Specification

> **Status:** Draft v0.2 — **Milestone 7**, addendum to `WYRAJ_PROJECT.md` (main spec under CC execution — merge as M7 after M6 lands)
> **Prerequisites:** M0–M5 (equipment slots from M2, statuses from M2); §2 layer 6 and §6.2 heirloom/dziad interactions additionally require **M6**
> **Sequencing note:** basic portrait (HP band + weapon glyph) still ships in M1 and the placeholder pane in M2 as per the main spec — M7 is the full replacement described here. If quickslots prove painfully missed during M2–M6 playtesting, §5 is self-contained and may be pulled forward as a mid-milestone insert.
> **Principle:** the character pane is not a stat readout — it is the *portrait of a soul in trouble*. Everything mechanical it shows should also be readable as fiction.

---

## 1. Pane Layout (revised)

Replaces the M0 placeholder layout of the right-hand panel:

```
┌ Character ──────────────────────┐
│        [ PORTRAIT ]             │  ← layered art, §2
│      Jarosz the Wygnaniec       │
│                                 │
│ HP  ██████████░░░░  34/52       │
│ Sta ████████████░░  41/48       │
│ Sat ██████░░░░░░░░  hungry      │
│                                 │
│ ☠ bleeding(4) 🜁 blessed(12)    │  ← status row, §4
│                                 │
│ ─ Wyposażenie ────────────────  │  ← paper-doll, §3
│  ⛑ head   —                    │
│  🜃 torso  kaftan skórzany      │
│  ⚔ weapon topór ciesielski ①   │
│  ⛨ off    gromnica (lit, 87)   │
│  ♦ amulet szkaplerz Welesa     │
│  ⬡ feet   łapcie               │
│                                 │
│ ─ Podręczne ──────────────────  │  ← quickslots, §5
│ [1]odwar żywokostu ×3           │
│ [2]sól święcona ×1              │
│ [3]gromnica ×2                  │
│ [4]—                            │
└─────────────────────────────────┘
```

Space-constrained fallback (short terminals): portrait collapses to 4-row mini variant; equipment list truncates names with ellipsis; quickslots always visible (they are the most action-relevant element).

---

## 2. Portrait — Layered, State-Reactive (extends main spec §6)

Layer stack (compositing order, all data-driven under `data/portrait/`):

1. **Base figure** — per origin (posture/build variant).
2. **Equipment silhouette overlays** — torso armor changes the outline; weapon glyph in hand mirrors the wielded item class (axe/sword/spear/staff); lit gromnica adds a small halo glow (color style, not extra glyphs) that also brightens the portrait background.
3. **Wound decals** — driven by HP band (healthy / bloodied <2/3 / wounded <1/3 / dying <10%): progressive darkening, hunch posture variant at *wounded*, red-styled marks.
4. **Status decals** — poison: green tint edges; fear: portrait shifts half a column as if recoiling; blessing: faint bright outline; wet (bagna): dark lower third.
5. **Scar layer (fabular)** — surviving a *dying* state (<10% HP) leaves a permanent-for-this-run **blizna** (scar mark) on the portrait. Multiple near-deaths accumulate. Pure narrative weight: a late-run portrait should *look like the run it survived*. Narrator references it once: "The scar has stopped weeping. It will not let you forget."
6. **Heirloom marker (M6)** — items carrying `memory_tag` render with a small ⟲ rune next to their name in the paper-doll and quickslots; the dziad comments on them (M6 §5.3).

Art direction: box-drawing/halfblock hybrid, ~12–16 rows; both style candidates from main-spec open decision #5 must implement the same layer contract, so the choice stays swappable. `--ascii` mode: layers degrade to plain ASCII with style-only (color/bold) state signaling.

---

## 3. Equipment Paper-Doll

- **Slots:** head, torso, weapon, offhand (shield *or* light source — a real tactical choice: protection vs. sight), amulet, feet. (Rings/gloves deliberately cut for v1 — six slots fit the pane and the low-fantasy tone; expanding later is data + one row each.)
- Each row: slot glyph, slot name, item display name with **enchant/curse color coding** (enchanted: cyan; cursed-known: dark red; unidentified-suspicious: dim yellow "?"). Empty slot: `—`.
- **Light source as first-class equipment:** a lit gromnica in offhand shows its **remaining burn turns** — fuel anxiety belongs on the pane, not buried in inventory.
- Quantified item state stays out of the pane except charges/burn — no durability system (explicitly out of scope; folk-horror items break narratively via curses, not condition bars).
- Selecting the paper-doll region (Tab-cycle focus or `e`) allows unequip/swap without opening full inventory — small but constant QoL.

---

## 4. Status Row

- Horizontal strip of status glyph + name + **remaining turn counter** in parentheses; color-coded (harmful red-family, beneficial gold-family, neutral blue-family).
- Overflow (>4 statuses): show 3 + `+N more` (full list on character sheet `c`).
- Every status here must map 1:1 to a `StatusEffects` component entry — the pane is a projection of ECS state, never its own bookkeeping (headless-testable as a pure render function).

---

## 5. Quickslots ("Podręczne" — at-hand)

### 5.1 Mechanics

- **4 slots, keys `1–4`.** Pressing the key uses/activates the assigned item as a normal turn action (drink odwar, throw sól, light/douse gromnica, read modlitwa).
- **Assignment from the inventory pane** (as requested): highlight an item, press `1–4` to bind. Rebinding overwrites silently. `Shift+1–4` in-game clears a slot.
- Assignable item classes: consumables, throwables, light sources, readables. Weapons/armor are *not* quickslottable in v1 — swap-gear-mid-fight is a different (bigger) design; revisit post-M6.
- **Stack-aware:** slot shows count (`×3`); using the last one leaves the slot bound-but-empty (`[1] odwar żywokostu ×0`, dimmed) — and **auto-refills** if another item of the identical `item_id` enters inventory. TUNING KNOB `quickslots.auto_refill: true`. This prevents the classic mid-fight "my potion key is suddenly dead" betrayal while still honoring "you carry what you carry."
- Empty-slot press: no turn consumed; szept-style dim aside on first occurrence only.
- Persistence: bindings live in the in-run save. Cross-run *preferences* (e.g., "always try to bind healing to 1") are a possible M6 meta nicety — parked in open decisions.

### 5.2 Display

- Pane strip as in §1: keycap, item name (epithet if named, §6.2), count, charge/burn state where relevant. Dimmed when unusable (e.g., modlitwa while mute-cursed).
- On use: brief highlight flash of the slot row (Textual animation, ~200ms) — eyes stay on the map, peripheral vision confirms the action.

### 5.3 Events

`QuickslotBound/Cleared/Used/AutoRefilled` through the bus — narration can react sparingly (first bind: "Close at hand, where fear can find it."), and golden-run tests capture bindings as input-affecting state.

---

## 6. Additional Improvements (Claude's additions)

### 6.1 Functional

- **Examine target mini-line** (bottom of pane, one line): last examined/attacked creature with its name, HP descriptor in-fiction (unharmed/bloodied/near death — never enemy numbers), and codex-tier icon. Keeps `x`-examine flow fast without a modal.
- **Burden indicator, 3 states only** (unburdened / laden / overladen — affects stamina regen, nothing else): one glyph next to Sta bar. Full encumbrance simulation explicitly rejected — inventory Tetris is not this game.
- **Pane focus mode:** `Tab` cycles map → paper-doll → quickslots for keyboard-only manipulation; consistent with roguelike sensibilities and screen-reader friendliness.
- **Color-blind safety:** every color-coded state above must carry a redundant non-color signal (glyph, brackets, dim/bold). CI check: portrait/pane snapshot tests rendered in monochrome must remain distinguishable.

### 6.2 Fabular

- **Named weapons (epithets):** a weapon that lands N kills of one species (TUNING KNOB, default 7) *earns a name* from the narrator — "Wilcza Zguba" (Wolves' Bane) — announced in prose, displayed thereafter in paper-doll/quickslots/log. Zero mechanical change in v1 (pure identity), but heirloom-stashed named weapons (M6) become legend objects the dziad greets by name. This is the strongest single bridge between the pane and the narration engine.
- **Trophy belt:** most recent 1–2 trophies (kuny pelt, fangs) render as tiny belt glyphs on the portrait — the hunter *looks like* a hunter walking home. Purely cosmetic, data-driven from inventory.
- **Portrait posture as fear/mood output:** if the fear meter stays narration-only (main spec open decision #4), the portrait is still allowed to *show* it (recoil shift, hunched variant) — the player reads dread on their own face before any mechanic exists. Cheap, atmospheric, reversible.
- **Death portrait:** the final composited portrait (scars, wounds, gear) is captured into the morgue file as ASCII art — every death leaves a picture of who you were at the end. Trivial to implement, huge sentimental payoff, great for sharing (→ community/marketing angle post-M3).

---

## 7. Implementation Order (CC execution plan)

Feature branch `feat/m7-sylwetka`; each step keeps `main` playable.

1. **Portrait compositor** — pure function `(components, layers_data) → list[Strip]`; layer contract (§2), both art-style candidates behind a config switch; snapshot-test matrix (HP bands × statuses × styles, monochrome pass included).
2. **Paper-doll widget** — six slots, color coding, gromnica burn counter, Tab-focus + `e` unequip/swap flow.
3. **Status row** — pure ECS projection, overflow handling.
4. **Quickslots** — `core/systems/quickslots.py` (bind/use/clear/auto-refill), `QuickslotBar` widget, events, in-run save integration, golden-run update.
5. **Fabular layer** — scars (blizna), trophy belt, named-weapon epithets (`data/narration/en/epithets.yml`), heirloom ⟲ markers + dziad recognition hooks (M6 integration).
6. **Morgue death-portrait capture** — final composite into morgue file.
7. **Polish pass** — pane focus cycling, short-terminal fallback, `--ascii` degradation, color-blind CI snapshot check.

New widgets: `PaperDollWidget`, `QuickslotBar`, `StatusRow`, extended `PortraitWidget`. All render from ECS projections — no widget-owned state. Content under `data/portrait/{base,overlays,decals}/*.yml`.

**Definition of done:** (a) full snapshot matrix green in both art styles and monochrome; (b) golden-run tests green with quickslot bindings as recorded input state; (c) a scripted headless run reaching *dying* twice produces a morgue file whose captured portrait carries two blizna marks; (d) Pilot test: bind → use → auto-refill → clear cycle via keyboard only.

## 8. Open Decisions (for Prestarius)

1. Offhand = shield *xor* light source — keep this tension, or allow a belt-hung gromnica (weaker radius) so shields aren't strictly punished?
2. Auto-refill quickslots — default on (spec) or off (hardcore)?
3. Named-weapon threshold and whether epithets may ever grant a tiny mechanical bonus (+1 vs. named species) — pure flavor is the safe default.
4. Death portrait in morgue: ASCII capture only, or also exported as a small PNG (Rich can render to SVG/PNG) for easy sharing?
5. Cross-run quickslot *preferences* (M6): worth it, or is per-run binding part of the ritual?
