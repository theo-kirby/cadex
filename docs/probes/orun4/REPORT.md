# orun4 — closing report

Verified against source: 2026-10-06, at `5b460c99` (the orun4 run branch).
Charter: `.ouroboros/goal.md`, "What worked, made the default — and a page
arranged like Blender". Every number below was measured on sb1x (linux-64,
RTX 5090), on scratch projects named `orun4-*`; the reference project was
only read. The owner ticks the criteria; this report claims none of them.

## Where each criterion stands

| criterion | where the evidence stands | evidence | records |
|---|---|---|---|
| F1 command filter in evaluation | evidence recorded | ADR-558; §1; 9 tests that fail without the fix; packaged lifecycle gate 24 passed | `loyal-path-4209` |
| F2 a run reads as what happened | evidence recorded | ADR-559; stopped, killed, finished and crashed tested through `train_start` and `cadex walk`; fails without the fix. One legacy defect in §7 | `true-ridge-9252` |
| G1 base plus styles | evidence recorded | ADR-560; `agent.json` `style`, `cadex style`; `test_agent_guidance.py` pins that the base names no robot type, no style text without a choice, and no guidance file names a project | `lucky-peak-7846` |
| G2 the lessons in Cadex | evidence recorded, three rows *owner to confirm* | ADR-565, ADR-566, ADR-567; `LESSONS.md`; two fresh sessions (§2) | `civic-stream-8050`, `northern-stream-2677`, `ancient-trail-9417`, `nimble-garden-9555`, `wandering-dune-8500`, `witty-bay-1622` |
| H1 one normal font | evidence recorded | ADR-568; Noto Sans; six before/after images (§3) | `tiny-ash-6709` |
| H2 two heroes on a pass | evidence recorded | ADR-569, ADR-570; §4; `test_studio_print_bed.py` (non-overlap and bounds over 40 packings) and a passing and a failing evaluation | `noble-vale-4742`, `peaceful-nest-6589` |
| H3 a shove video on a pass | evidence recorded | ADR-571; §4; the outcome is read from the episode | `frosty-cabin-1461` |
| D1 the 3D viewport pans | evidence recorded | ADR-561; shift-, middle- and two-finger drag, pinch, Fit, under headless Chromium | `glad-basin-7496` |
| D2 Status is its own editor | evidence recorded | ADR-572; 317 × 769 px beside the 3D viewport at 1400 × 900, a 390 × 756 px tab at 390 × 844 | `neat-isle-1523` |
| D3 layout presets | evidence recorded | ADR-573; `test_review_layout.py` applies all eight presets and drags an area; §5 | `cold-mist-9459` |
| C1 this report | this file | §1–§7 | the record that adds this file |

The owner's note to lighten the CLI suite was worked too (ADR-562 to
ADR-564, §6).

## 1. F1 — a filtered policy, before and after

A policy trained with `action_filter_alpha` 0.5, evaluated on 10 frozen
seeds. "Before" is the old engine, which played it unfiltered; "after"
plays it under the alpha its `.cxpolicy` records (ADR-558).

| | before (played unfiltered) | after (played at its recorded 0.5) |
|---|---|---|
| terminations | tipped 10 | horizon 10 |
| W1 survives | 0/10 | 10/10 |
| duration s (min/med/max) | 1.42 / 2.86 / 5.98 | 10 / 10 / 10 |
| W2 max tilt ° (min/med/max) | 47.4 / 49.3 / 52.0 | 2.3 / 3.1 / 4.1 |
| W3 forward speed mm/s (median) | 73.6 (3/10 in band) | 115.9 (10/10 in band) |
| W4 heading pass | 0/10 | 1/10 |
| W5 lateral pass | 5/10 | 10/10 |
| W6 steps | 0/10 | 0/10 |
| verdict | fail | fail |

The "before" column reproduces that policy's recorded evaluation exactly,
so the old engine judged a different controller from the one trained.
Played correctly it stands for the whole horizon and still fails on
heading and steps: a real verdict, not an artefact. An unfiltered policy
(alpha 1.0, the reference's passing `walk_r13_i140`) re-evaluates 10/10
with summary metrics identical to its recorded report, and a header with
no `training` block loads and plays unfiltered.

## 2. G2 — the ledger and the fresh-session check

`LESSONS.md` has 25 rows, each with its evidence in the reference project:

- **base**: 16 rows (W4 was already there). They cover the simulated body
  being the built body, the target speed checked against the actuator's
  headroom, the forward-progress bound, motion-fit limits from the sweep,
  command range on the rest pose, upright-gated progress, a ceiling on
  charges against a degenerate motion, and four training practices
  (checkpoints on, warm starts, keep a good policy, `evaluate` is the
  judge).
- **printed-legged-robot style**: 7 rows (W3 and W5 were already there),
  plus the legged instance of L7's limit rule. They cover the twin-keel
  foot with a flat strip, a foot bounded by standing height, hips wide
  enough to clear and a bracketed inward roll limit, paying for the step,
  actuators hung inside the limb, and the look of a limb.
- **tool**: L18, evaluation ignoring the training filter, which F1 fixed.
- **not adopted**: W6, an observation never changed, so it is a hypothesis
  and not a rule.
- **owner to confirm**: L4 (the foot bound's numbers), W1 (knee placement
  is taste), and L5's reading of the charter. The reference moved its
  target speed *up*, so the rule reads as "headroom checked", not "slower".

**Fresh-session check.** Two `claude -p` sessions on empty `orun4-*`
projects, with the style chosen through `cadex style` and reads of other
projects, the probes and the graph denied. Each was asked for a small
printed two-legged robot, verbatim in `FRESH-SESSION.md`.

- **First** (`orun4-fresh-legged`, `fresh-legged-first-design.png`): the
  twin keel, the accent foot, the horn caps, the actuators inside the
  limb, the tapered windowed plates and no face were all unprompted, and
  the inward hip roll was tighter than the outward one. It missed foot
  compactness (a 72 × 40 mm slab under a 210 mm robot). It also declined
  the level-thigh rule for an upright biped, and was right to. ADR-566
  bounded the foot by standing height and scoped the thigh rule.
- **Second** (`orun4-fresh-legged-2`, `fresh-legged-2-first-design.png`,
  `FRESH-SESSION-2.md`): the sole was 54 × 27 mm under 225.6 mm (0.239 ×
  0.120 of standing height) from the first robot, and the agent recorded
  the ratios unprompted. The lean thigh held. It found that reading the
  roll limit off a wide range's `first_contact` would have set −25°,
  inside the collision. It bracketed instead and widened the hips to
  46 mm, clear at −15° and meeting at −20°. ADR-567 now tells the style
  to bracket outward from the standing pose.

## 3. H1 — before and after

Left is before, right is after. Only the text differs, measured pixel by pixel:

| kind | pixels changed outside the text | image |
|---|---|---|
| hero | 0 | `h1-hero-before-after.png` |
| concept sheet | 0 outside the lettered panel (28,657 inside) | `h1-sheet-before-after.png` |
| film overview | 0 outside the clock boxes (6,409 inside) | `h1-film-overview-before-after.png` |
| film detail | 0 outside (6,560 inside) | `h1-film-detail-before-after.png` |
| blueprint | drawing unchanged; the notes column re-flows to one line each | `h1-blueprint-before-after.png` |
| video frame | ≤ 32 grey levels outside the clock, VP9 coding noise | `h1-video-frame-before-after.png` |

The face is Noto Sans (SIL OFL 1.1), shipped as one font file and listed
in `docs/PROVENANCE.md` (ADR-568). `_FONT_ROWS` is deleted. Text is now
drawn in the case its caller wrote, so labels that relied on upper-casing
read lower-case.

## 4. H2 and H3 — what a passed evaluation makes

These were measured on `orun4-biped-sts`, a scratch copy of the
reference, re-filming its passing evaluation (policy `235b65eba72d`, 10/10).

- **Hero** (`h2-hero.png`, 178 KB): the studio shot of the design that
  passed, in the H1 font on the dark floor.
- **Print bed** (`h2-print-bed.png`, 223 KB): 10 printed parts laid on a
  flat face. On 256 × 256 mm beds with a 6 mm gap they need **2 beds**:
  bed 1 is 89% covered and `foot_r` spills to bed 2. On a 300 mm bed they
  fit on one. Beside the beds are 10 hardware rows from the inventory
  (6 × STS3215, bolts, boards, battery). The retained-geometry render is
  byte-identical to one drawn from a rebuild.
- **Shove video** (`h3-shove.png`, a still; `shove.webm` stays beside the
  evaluation and is not committed): pushes of 0.33 N at 3.12 s and 0.90 N
  at 5.75 s, each marked as it lands. **The walker tipped at 6.30 s**, and
  the caption reads `fell: tipped at 6.30 s`. That is a finding about the
  reference policy, not the film: it passes its walk spec but does not
  hold the pushes its own training band draws. A third push, due at 6.95 s,
  never landed.

A failed evaluation makes neither hero and no video, and says why.

## 5. D3 — the presets

These are headless Chromium at 1280 × 800 on the dark floor, serving
`orun4-biped-sts` on 127.0.0.1. Each preset was applied by one click on
View → Layout and screenshotted 2.5 s later.

| preset | areas, in reading order | screenshot |
|---|---|---|
| single | 3D viewport | `d3-preset-single.png` (234,107 B) |
| side by side | 3D, Status | `d3-preset-side.png` (187,109 B) |
| stacked | 3D, Status | `d3-preset-stacked.png` (210,671 B) |
| 2 over 1 | 3D, Status, 2D | `d3-preset-two_over_one.png` (211,237 B) |
| 1 over 2 | 3D, Status, 2D | `d3-preset-one_over_two.png` (273,640 B) |
| three columns | 3D, Status, 2D | `d3-preset-columns.png` (254,793 B) |
| three rows | 3D, Status, 2D | `d3-preset-rows.png` (204,710 B) |
| quad | 3D, Status, 2D, empty | `d3-preset-quad.png` (211,990 B) |

Quad's fourth area is empty, with only its editor picker. There are three
editors, and each shows at most once (ADR-573). The Status editor in these
shots reads **failed** for the reference's stopped run, which is defect 1
in §7.

## 6. The CLI suite, lighter

The owner asked for the suite in under 8 minutes as one command. Measured
whole, it went 1017 s → 793 s (ADR-562) → 647 s (ADR-563) → 614 s
(ADR-564). **The target is not met.** What remains is keep-listed
real-engine end-to-end tests, so the cuts stopped there, and the owner's
three interleaved thirds stay the gate of record. Each removed test and
its reason are listed in those ADRs.

## ADRs added by this run

| ADR | decision |
|---|---|
| ADR-558 | the engine plays a policy under the command filter it was trained with |
| ADR-559 | a run reads as what happened to it: stopped on request, or failed when killed |
| ADR-560 | the agent guidance is a domain-neutral base plus named, optional styles a project chooses |
| ADR-561 | the 3D viewport pans: shift- or middle-drag, two fingers on touch |
| ADR-562 | the CLI suite gets lighter: first cuts, measured |
| ADR-563 | the CLI suite gets lighter: second cuts, renders drawn small where pixels are not the claim |
| ADR-564 | the CLI suite gets lighter: last cut, the remote-walk parity test trains with the fixture trainer |
| ADR-565 | the reference legged robot's lessons enter the base and the printed-legged-robot style as general rules |
| ADR-566 | the style bounds the foot, scopes the level thigh, and derives the roll limit |
| ADR-567 | the style brackets the roll limit outward from the standing pose |
| ADR-568 | every render and video is lettered in Noto Sans, from a shipped font file; the 5×7 face is deleted |
| ADR-569 | the print-bed hero: printed parts laid flat on as many beds as it takes, beside the purchased hardware |
| ADR-570 | a passed evaluation presents the design that passed: the hero and the print bed, beside its report |
| ADR-571 | a passed evaluation is filmed taking the task's shoves, each push marked, the outcome read from the episode |
| ADR-572 | Status is an editor of its own, beside the 3D viewport, not an overlay on its model |
| ADR-573 | layouts come from one-click presets; an area may be empty; a drag previews where it lands |

## 7. Remaining defects

1. **A run recorded before ADR-559 still reads failed.** `walk-r13` in
   `orun4-biped-sts` was stopped on request before F2 landed. Its
   `training-status.json` says `stopped`, with the reason, but its
   `run.json` was written by the old `loop._record` as `failed`, and the
   Status editor shows **failed** (§5's screenshots). ADR-559 fixes how
   new endings are written; old records are not re-read or migrated. The
   same editor also shows "no telemetry update for over 30 s; process state
   unknown" under that long-ended run.
2. **`cadex smoke` false positives**, found by the fresh sessions: an
   exact-geometry pre-check refuses a distance mismatch under 1e-5 mm on a
   pair 70 mm apart, threaded screw engagement counts as overlap, and the
   exact-geometry stage timed out on 64+ components.
3. **The CLI suite is 614 s as one command**, over the 8-minute target
   (§6), and over the shell's 600 s limit once `pixi` overhead is added.
4. **A known flake**: `test_designing_turns_idle_once_the_window_passes`
   compares a minute prefix against a timestamp recomputed later, and fails
   across a minute boundary. It was left alone, as the question policy
   says.
5. **ADR-559's assumption**: a supervisor terminated by a signal with no
   stop request reads `interrupted` in `train_status` and failed on the
   page. The owner may revise this.
6. **The long-term rungs from orun3 were not worked**: a project reads "not
   found" until its first script, the trainer stalls 37–39 s before each
   checkpoint, and the guidance tells the agent to set `checkpoint_every`
   whenever the owner is watching.

## Done claim

Not made by this file. All ten build criteria, F1 to D3, have evidence
recorded. Two things are still due before C1 is claimed done for critic
review:

- the reconcile that folds `neat-isle-1523`, `cold-mist-9459` and this
  report's record, which work iterations are forbidden to run;
- a choice on defect 1: fix it, or leave it named.
