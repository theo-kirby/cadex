# orun1 — the owner's design preferences, measured

Verified against source: 2026-10-02. Provenance: `[Cadex-new]`.

The charter for orun1 is `.ouroboros/goal.md`. This file holds the
evidence it starts from: a design-only sweep the operator ran before the
run, and the owner's blind ratings of it. The run adds its own contract
and results below the marker at the end.

## The sweep

ot10 (ADR-411 to ADR-444) gave Cadex robots a finish: a light shell, round
joints, an accent and a studio render. The owner's verdict on the result
(2026-10-01) was that the robots *look* finished but are not well
*designed*: the quadruped is "a rounded box with four legs", the motor
pods on its thighs look stuck on, and most hexapods "look really bad".
Writing more rules was unlikely to capture what was missing, so the
operator measured it instead.

- **Grid.** 7 robot types × 8 design theses = 56 designs, one fresh
  project each (`sweep-<type>-<thesis>`), one design turn each, design
  only, no training. `ratings.json` → `briefs` holds every prompt word for
  word.
- **Types.** Quadruped, hexapod, biped, 5-axis arm, 3-axis arm,
  two-wheeled balancer, wildcard (body plan of the agent's choosing).
- **Theses.** (a) the servo is the joint, (b) motors in the body, (c)
  clean exposed mechanism, (d) consumer product shell, (e) panelled
  hard-surface, (f) creature anatomy, (g) minimal geometry, (h) the
  agent's own choice.
- **Every brief** asked for real catalog parts at true size, design from
  the inside out (pack the components, then shape the structure and shell
  around them), refinement with `look`, and closing DESIGN NOTES.
- **Model.** `claude-opus-5-5`, `CADEX_EFFORT=medium`, at revision
  `2c34ab64`. Turns took 3 to 67 minutes.
- **Completed.** 55 of 56. The 56th (`hexapod-h-free`) was stopped
  unfinished at the owner's request and is not rated.

## The ratings

The owner rated all 55 **blind** on 2026-10-02: designs shuffled within
each type and labelled only by type and number; the thesis and the agent's
notes appeared only after a verdict was given. The scale is Love (3),
Like (2), Meh (1), No (0). No notes were written. The renders the owner
saw are the 640 px heroes in `sweep/` (downscaled from the 1024 px
studio hero, dark prototype floor).

Totals: 4 Love, 23 Like, 25 Meh, 3 No.

| thesis | arm3 | arm5 | balancer | biped | hexapod | quadruped | wildcard | mean |
|---|---|---|---|---|---|---|---|---|
| a servo is the joint | meh | like | meh | **no** | meh | like | like | 1.29 |
| b motors in the body | like | meh | meh | like | like | like | like | 1.71 |
| c exposed mechanism | like | like | **love** | **love** | like | like | meh | **2.14** |
| d product shell | like | like | like | meh | meh | meh | meh | 1.43 |
| e hard-surface | meh | meh | like | like | meh | **love** | like | 1.71 |
| f creature | meh | meh | like | meh | meh | meh | like | 1.29 |
| g minimal | meh | **love** | meh | like | **no** | meh | like | 1.43 |
| h own choice | meh | meh | like | **no** | — | meh | meh | 1.00 |
| **type mean** | 1.38 | 1.62 | 1.75 | 1.38 | **1.14** | 1.62 | 1.62 | |

## What the ratings say

These are the operator's reading. The owner has not yet confirmed them,
and the charter marks the three it depends on as owner-revisable.

1. **The three Nos are one archetype.** `biped-a-servo-joint`,
   `hexapod-g-minimal` and `biped-h-free` are each a large, soft, rounded
   box with a dark visor and two orange dot eyes, over short legs or
   stubby limbs, with boxes hanging under it. This is the "rounded box"
   the owner described, and it is what `docs/DESIGN-LANGUAGE.md` §0
   prescribes: "one soft body primitive with a face".
2. **Faces cost points.** 47 of the 55 sets of notes mention a face, eyes or
   a visor, because §4 of the design language asks for one. Those 47 average
   1.43. The 8 without one average 2.00. None of the four Loves has eyes.
3. **The Loves show how they are built.** `balancer-c-exposed-mechanism`
   (two slotted side frames, an orange cradle carrying the electronics, a
   visible cable loop, spoked wheels), `biped-c-exposed-mechanism` (a
   stacked servo column with orange horn caps, a board deck with routed
   wires, plain flat feet), `quadruped-e-hard-surface` (a chamfered body,
   a bolted hatch of dark panels, large dark hip actuators, a sensor slot
   instead of eyes) and `arm5-g-minimal` (a clean industrial arm with no face
   and no decoration). They read as engineered machines, not characters.
4. **The design language contradicts the owner on exposure.** §1 says
   purchased hardware is "never an exposed case or a bare board". The
   highest-rated thesis is the one that exposes them.
5. **Hexapods are the weakest type** (mean 1.14), as the owner said
   before the sweep.

Caution: 55 ratings, 4 Loves and 3 Nos are a small set, and a thesis is
confounded with the agent's execution of it. Read the per-thesis means as
direction, not as measurement.

## The split

`ratings.json` assigns every design to `dev` (27) or `heldout` (28),
stratified by verdict with the seed `orun1-split-2026-10-02`: Love 2/2,
Like 12/11, Meh 13/12, No 2/1. The split was fixed before orun1 started.
How the run may use it is the charter's rule (D1).

<!-- orun1: the run's contract and results go below this line. -->
