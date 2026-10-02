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

## The split, counted

The paragraph above says 27 dev and 28 held-out. Counting `ratings.json`
gives **29 dev and 26 held-out** (Love 2/2, Like 12/11, Meh 13/12, No 2/1;
the per-verdict figures above are right and their sums are not). The file
is ground truth and is not edited; every number below uses the counted
split. The held-out set has 26 designs, so 325 pairs, of which **37**
differ by two levels or more (Love × Meh 24, Love × No 2, Like × No 11).

## D1 baseline: ot10's frozen judge on the held-out set (pre-registered)

**This is the baseline, not a judge version.** It is ot10's instrument run
unchanged, so that every orun1 judge version has a number to beat. It is
measured once, its result is published whatever it is, and nothing about it
is tuned: no prompt, rubric, reference, view or aggregation changes after
the first held-out call. It is not a candidate for D1's frozen judge.

- **Judge.** `docs/probes/ot10/runner/judge.py` exactly as frozen by
  `docs/probes/ot10/README.md` (rubric sha256 `1c81caa2…`, the ten core
  references, `claude-opus-5-5`, effort `high`, three calls, median per
  trait, total 0–21). The runner is imported, not copied.
- **Inputs.** For each of the 26 held-out designs, a copy of its sweep
  project at `~/cadex-projects/orun1-ho-<id>` (the originals stay
  read-only; `cadex render` re-accepts, ADR-476). The renders are ot10's
  set: the 1024 px studio hero from `cadex render`, then the `look` views
  `iso`, `iso_back`, `front`, `right`, `top` at the look tool's size, drawn
  by the bridge's own `look` (dark prototype floor for the hero). The judge
  sees them as `candidate-N.png` only.
- **Score.** A design's score is its ot10 total (sum of the seven trait
  medians).
- **Pairwise agreement.** Over the 37 held-out pairs whose owner verdicts
  differ by two levels or more, a pair agrees when the higher-rated design
  has the strictly higher total. **A tie is a disagreement.** Ties are also
  counted and reported. The bar is 80%.
- **Love over No.** Every held-out Love's total is strictly above every
  held-out No's total (2 × 1 = 2 pairs).
- **Kendall's tau.** τ-b between owner verdict (0–3) and total over all
  325 held-out pairs, reported with the count of concordant, discordant and
  tied pairs.
- **Harness.** A judge harness failure (a reply that fails to parse twice),
  a usage limit or a refusal is not a score. Such a design is re-run; if
  it still cannot be scored, it is reported as missing and every metric
  names the pairs it drops.
- **Machinery.** `runner/render_set.py` draws one design's inputs from its
  copy. Per-design scores go to `baseline/<id>-score.json` and the summary
  to `baseline/summary.json`.
- **Status.** Run once, complete: 26 of 26 held-out designs scored, no
  harness failure, no design re-judged (commits `97ca4c14`, `c432146d` and
  this one). The first attempt to draw inputs had found that ADR-476
  stopped six held-out designs reopening; ADR-477 reverted that before any
  judge call.

### D1 baseline result

ot10's frozen judge **fails every part of D1's bar**, and on the pairs that
matter it is worse than chance: it prefers the design the owner rated lower.

| metric | ot10 judge (baseline) | D1 bar |
|---|---|---|
| pairwise agreement, owner gap ≥ 2 | **13.5%** (5 of 37; 3 ties, 29 reversed) | ≥ 80% |
| every Love above every No | **fails, 0 of 2** | holds |
| Kendall's τ-b, all held-out pairs | **−0.079** over 325 pairs (79 concordant, 98 discordant, 148 tied) | reported |

Totals (0–21) by owner verdict:

| owner | n | ot10 totals | mean |
|---|---|---|---|
| Love | 2 | 12, 14 | 13.0 |
| Like | 11 | 14, 14, 14, 16, 16, 16, 16, 17, 17, 18, 18 | 16.0 |
| Meh | 12 | 11, 12, 13, 13, 15, 15, 16, 16, 16, 17, 18, 18 | 15.0 |
| No | 1 | 18 | 18.0 |

- The held-out No (`biped-h-free`, the soft rounded box with a visor and
  dot eyes) gets 18, tied for the highest total; the two held-out Loves
  (`biped-c-exposed-mechanism` 12, `quadruped-e-hard-surface` 14) are in the
  bottom third. By kind of gap pair: Love × Meh 5 agree, 18 reversed,
  1 tied (of 24); Love × No 0 of 2; Like × No 0 of 11 (9 reversed, 2 tied).
- Reading, not measurement: ot10's rubric was written to score the finish
  ot10 prescribed (one soft body, a face, hidden hardware), which is the
  archetype the owner rejected. A judge built from it is aligned to the old
  design language, not to the owner.
- Per-design scores, trait medians and render receipts:
  `baseline/<id>-score.json`; the metric output with every reversed and
  tied pair named: `baseline/summary.json`.
