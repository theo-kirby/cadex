# ot10 — the design-quality contract

Verified against source: 2026-09-27. [Cadex-new]

**This is A1's frozen instrument.** Every ot10 design, including hex3's
baseline, is measured with it: the rubric, the measurable proxies, the A5
bar and the judging procedure. It was written before any A5 probe, and
before the renderer, xscript or the overlay changed. The machine-readable
copy is [`contract.json`](contract.json). `cli/tests/test_ot10_contract.py`
holds this page, that file and the judge runner equal. Changing any
frozen value is a recorded decision that re-scores every earlier probe,
including hex3. It is not an edit.

The language being judged is [`docs/DESIGN-LANGUAGE.md`](../../DESIGN-LANGUAGE.md).
The judge never sees it. It sees the rubric below, the ten core reference
images and the candidate's renders, and nothing else.

## The rubric

The text between the markers is passed to the judge byte for byte.
[`runner/judge.py`](runner/judge.py) reads it from this file, and the test
pins its hash.

<!-- rubric:start -->
Score the candidate robot on each of the seven traits below, 0 to 3, using the anchors. Judge the robot as shown in the candidate images; the reference images show what a 3 looks like. Score what is visible, not what might be intended. When a candidate falls between two anchors, give the lower score.

T1 shell: Shell over skeleton.
0: No enclosure. Servos, boards and battery sit exposed on plates or brackets.
1: A few parts are covered, but most purchased hardware is visible, and the covers are flat plates.
2: A continuous shell encloses the body's hardware. Some servo cases or boards still show on the limbs or through gaps.
3: Continuous shells hide every servo and board. The mechanism shows only as deliberate dark bands, rings or joints.

T2 palette: Two materials and one accent.
0: One undifferentiated colour everywhere, or many colours with no logic.
1: Two or more colours, but they do not follow roles (outer shell, mechanism, accent), or there are four or more.
2: A shell colour and a dark mechanism colour, applied consistently by role. The accent is absent or used at random.
3: Two materials by role plus at most one saturated accent, placed deliberately on joints, the face or the feet.

T3 joints: Joints as features.
0: Rotation axes cannot be seen, or read as bare servo horns and arms bolted on.
1: Joints are recognisable, but as unstyled hardware: a horn, a screw head, a bracket.
2: Most joints are round bosses, rings or caps concentric with their axes.
3: Every rotation axis is a deliberate round feature, the same across all joints.

T4 form: Soft primitives and large radii.
0: Rectangular boxes, plates and constant-section bars with sharp edges.
1: Box forms with small edge fillets. It still reads as plates and bars.
2: The body reads as one soft primitive (a hood, pill, sphere or rounded box) with generous radii. Most limbs are shaped.
3: Every visible part is a soft, continuous form with large radii, and parts merge into one another. Split lines are the only surface detail.

T5 character: A face and a silhouette.
0: There is no front and no face. The robot could be facing any direction.
1: A front can be inferred from the legs or layout, but there is no face.
2: There is a face element (a panel, slot, eye or lens), but it is small, generic or hard to find.
3: One clear focal face gives the robot a front and a character at a glance, and the silhouette is recognisable.

T6 proportion: Proportion and taper.
0: A flat, sprawling or arbitrary layout. Limbs are uniform bars with no feet.
1: A compact body, but limbs have a uniform section and the feet are undifferentiated.
2: Either the limbs taper towards the foot or the feet are distinct, but not both.
3: A compact body, and limbs that taper to distinct feet (caps, pads or points). The stance reads as balanced and intentional.

T7 presentation: A presented render.
0: A flat-shaded screenshot. Surfaces are unlit and forms are hard to read.
1: Shaded but plain. There is no backdrop or contact shadow, or the image has jagged edges or an awkward angle.
2: Lit so that curvature reads, on a clean background, from a good angle. It lacks a contact shadow or studio polish.
3: A studio hero: a seamless backdrop, a soft contact shadow, antialiased edges, a low three-quarter view, and materials that read.
<!-- rubric:end -->

The maximum total is 21. The traits map onto the language: T1 is §1, T2
§2, T3 §3, T4 §1, T5 §4, T6 §5 and T7 §7. Printability (§6) is not
judged from images. It is held by the fit checks and by proxy P2.

## The proxies (A3)

A3 computes these from the accepted solids and renders, and `look` and
review report them. Their definitions are frozen here; A3 implements them
and does not redefine them.

| id | proxy | definition | designed if |
|---|---|---|---|
| P1 | `hardware_silhouette_share` | In the hero view, of the pixels covered by the design (environment geometry left out), the fraction whose front-most surface belongs to a purchased (catalogued) component. | ≤ 0.20 |
| P2 | `sharp_outside_edge_share` | Over every non-seam BREP edge of every printed (uncatalogued) solid at the accepted revision: length of the **sharp convex** edges ÷ total edge length. An edge is sharp convex when the outward normals of its two faces, sampled at its midpoint, turn outward by more than 60°. A 90° corner is sharp; a 45° chamfer or a tangent fillet is not. A seam edge has the same face on both sides. With no printed edges the share is 0. | ≤ 0.25 |
| P3 | `material_count` | The number of distinct appearance materials drawn in the hero view. A part with a declared role and palette counts as its colour; a part with no declared role counts as the renderer's default for printed or purchased. | 2 or 3 |

Each proxy has a test that fails on a crude fixture (bare boxes, one
colour or rainbow, exposed hardware) and passes on a designed one. The
proxies are necessary, not sufficient. hex3 scores 2 on P3 with its
printed/purchased split, and it is still not a designed product. That is
why the bar also needs the judged score.

## The A5 bar

A design meets the bar when **all** of these hold:

1. **Judged total ≥ 14 of 21.** The total is the sum over traits of the
   median of three judge calls (see *Procedure*).
2. **No trait scores 0.**
3. **The judged total is above hex3's baseline total** (see *Baseline*).
4. **P1 ≤ 0.20, P2 ≤ 0.25, and P3 is 2 or 3**, as reported by `look` or
   review at the accepted revision.
5. **The fit gates from the charter**: accepted, with zero failing static
   fit checks and a complete, passing swept fit, and the electronics
   carried.

14 is two-thirds of the maximum, the level at which the average trait
reads *2, clearly designed*. One design that misses the bar fails A5.

## Procedure

`docs/probes/ot10/runner/judge.py` is the procedure. It is frozen with
these values:

- **Model**: `claude-opus-5-5` with no fallback, through the Claude Code
  CLI the user is already logged into (as the product agent is).
  Effort is `high`.
- **Isolation**: every call runs in a new, empty temporary directory
  outside the repository. It uses `--setting-sources project` (the empty
  directory has none, so no user hooks, memory or `CLAUDE.md`),
  `--strict-mcp-config` with no servers, `--no-session-persistence`, and
  `Read` as the only tool. `--add-dir` covers exactly two directories,
  and nothing else is readable: the reference directory, read in place,
  and the candidate directory.
- **What the judge sees**: a fixed system prompt (the instruction
  paragraph pinned in `judge.py`, then the rubric above, byte for byte);
  the ten files in `reference/images/1-core/`, read in place, in filename
  order and labelled only as references; and the candidate's renders.
  The renders are copied into the fresh directory as `candidate-1.png`,
  `candidate-2.png`, … so that no project name, run name or view name
  reaches the judge.
- **The candidate's renders** are every image the product produces for
  the design at the accepted revision: the A2 studio hero once it exists,
  then the `look` views `iso`, `iso_back`, `front`, `right` and `top`, in
  that order. hex3's baseline predates A2, so its set is the five `look`
  views.
- **Calls**: three independent calls per candidate. Each trait's score is
  the median of the three. Every raw reply is kept in the probe's score
  file.
- **Reply**: one JSON object,
  `{"T1": {"score": n, "reason": "..."}, …, "T7": {…}}`. A reply that does
  not parse, or has a score outside 0–3, is retried once. A second failure
  is a harness failure, not a score. A usage limit or a provider refusal
  is never scored.
- **No tuning against the judge.** No product prompt, overlay or tool may
  quote or paraphrase the judge's reasons. Changes answer the measured
  gap in the language's terms.

Under the charter, the product agent never sees any reference, and the
judge never sees the design language, the prompt, the transcript or the
design's name.

## A5: the cold prompts

Frozen before the first A5 turn, and copied into `contract.json` as `a5`.
Each body plan gets exactly one design-only product turn on a new
`ot10-*` project, with no continuation, no coaching and nothing else in
the prompt:

    CADEX_EFFORT=medium ./cadex --project <new ot10-* project> \
        --model claude-opus-5-5 -p "<prompt>" --json

| body plan | prompt |
|---|---|
| hexapod | Design a hexapod walking robot using MG90S servos from the catalog (two per leg: hip yaw and knee), a printable body, and the hardware to assemble it. Then declare a training task that teaches it to walk forward on flat ground. |
| quadruped | Design a quadruped walking robot using MG90S servos from the catalog (two per leg: hip pitch and knee), a printable body, and the hardware to assemble it. Then declare a training task that teaches it to walk forward on flat ground. |
| biped | Design a biped walking robot using MG90S servos from the catalog (three per leg: hip pitch, knee and ankle), a printable body, and the hardware to assemble it. Then declare a training task that teaches it to walk forward on flat ground. |

The hexapod prompt is hex1–hex3's, word for word, so the only difference
from the baseline is the product. The other two change only the body plan
and its joints. None of them says anything about looks: the language
reaches the agent only through the overlay and the API reference. The
biped is this run's own choice, because it is the plan furthest from the
hexapod's flat deck and the one where a face and a silhouette decide the
most. `medium` is hex2's and hex3's effort, after hex1 stalled at `high`.
The training task is declared so that W2 can train an A5 design unchanged;
A5 itself trains nothing.

## A5 attempt 1: the hexapod (`ot10-hexapod-1`)

**Misses the bar, on three counts: the judged total is 13 of 21, P2 is
0.655, and the swept fit is incomplete.** It is the first A5 turn, the
frozen hexapod prompt run once on a new project on 2026-09-27, with
`CADEX_EFFORT=medium`, `--model claude-opus-5-5` and no continuation. The
turn ended on its own after 55 min 44 s with exit 0, at accepted revision
`7af6db090950…` (digest `ab571337a4d3…`).

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 1, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |

The three judge calls gave identical scores on every trait. Every raw
reply is kept in
[`ot10-hexapod-1-score.json`](ot10-hexapod-1-score.json), and the same
rule applies to it as to the baseline's: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 13 | **no** |
| no trait 0 | lowest is 1 (T3, T4) | yes |
| above hex3 (2) | 13 | yes |
| P1 ≤ 0.20 | **0.078** (15,101 of 193,831 subsamples) | yes |
| P2 ≤ 0.25 | **0.655** (21,133 of 32,275 mm, 17 printed components) | **no** |
| P3 2 or 3 | **3** (`#2A2C31`, `#E9E4D8`, `#F26A1B`) | yes |
| static fit | 1,035 pairs clear, 0 intersections; 32 welded pairs touching. The one failing row is the floor's advisory world-geometry row | yes |
| swept fit | **incomplete: 12 of 12 joints unswept** (`sweep_step_degrees` not declared) | **no** |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S | yes |

The candidate set, in the order the judge saw it, is the 1024 px studio
hero from `cadex render`, then the five `look` views at 768 px, drawn as
the look tool draws them (appearance roles and palette from the
inventory, floor left out):
[`hero`](ot10-hexapod-1-hero.png),
[`iso`](ot10-hexapod-1-look_iso.png),
[`iso_back`](ot10-hexapod-1-look_iso_back.png),
[`front`](ot10-hexapod-1-look_front.png),
[`right`](ot10-hexapod-1-look_right.png) and
[`top`](ot10-hexapod-1-look_top.png).
`cadex render` took 63.7 s for the whole command: 29.3 s of rebuild,
5.9 s drawing and 2.1 s for the hero, at 81,876 triangles.

**Diagnosis.** The design language reached the design: a rounded shell
over a dark belly tray, the hip servos hidden inside it, three materials
by role, one orange visor slot as the face, and ball feet. That is T1 2,
T2 3 and T5 2, against hex3's 0, 1 and 0. The two traits that stayed low,
T3 joints and T4 form, are the details the agent built and then **took
out to fit the engine's 300 CPU-second limit**. The limit refused 19 of
the turn's 33 refused calls. The agent's own `DECISIONS.md` records what
went: a spline-loft carapace, the joint caps, the leg fillets, the
servo-shaped pockets, the 34 screws, and the motion sweep. It identifies
total face count as the lever. P2's 0.655 is the unfilleted legs in a
number, and the incomplete sweep is the same cut. So the binding
constraint on this design was not what the agent knew. It was the cost
of checking what it built. The next change is to that cost, not to the
prompt: find out where a 46-component, 1,035-pair assembly spends 300
CPU-seconds when hex3's filleted brackets did not.

**A4's refusal classes in this transcript: none of the four recurred.**
There was no wrong horn style, no `edit_script` before a script existed,
no second assembly or diagnostics output, and no joint missing or
listed twice. Besides the 19 CPU-limit refusals, the other 14 were: two
from the sandbox (`import`, `dir`); a catalog body used as an
`assembly.component` source; six from the kernel and the selectors (two
post-boolean refines, a cut that produced 5 solids, an invalid bounding box,
a fillet selector with an unknown key, and one with the wrong count); two `edit_script` replacements that did not match, one
guessed JSON pointer, one reset-variation refusal (fixed by the named
lift), and one refusal to retire `joint_cap` while the script's own
assembly links still referenced it.

## A5 attempt 2: the hexapod (`ot10-hexapod-2`)

**Misses the bar on one count: the swept fit is incomplete.** The judged
total is 14 of 21, which meets the frozen 14, and P1, P2 and P3 are all
within their bars. This is the frozen hexapod prompt above, word for word,
run once on the new project `ot10-hexapod-2` with no continuation:

    CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-hexapod-2 \
        --model claude-opus-5-5 -p "<the frozen hexapod prompt>" --json

It started at 2026-09-27T21:01:51Z at revision `6dd4ce81`, which is after
ADR-418's four-CPU worker pin, the only product change since attempt 1.
It ran detached from the loop, and its stdout and stderr stayed outside
git. The turn ended on its own after 39 min 14 s with exit 0, at accepted
revision `996a0b7e7b90…` (digest `39be96a4b87a…`).

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 1, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |
| attempt 2, call 1 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 |
| attempt 2, call 2 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 |
| attempt 2, call 3 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 |
| attempt 2, median | 2 | 3 | 1 | 2 | 2 | 2 | 2 | **14** |

The three calls disagree only on T3 (2, 1, 1). Every raw reply is kept in
[`ot10-hexapod-2-score.json`](ot10-hexapod-2-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 14 | yes |
| no trait 0 | lowest is 1 (T3) | yes |
| above hex3 (2) | 14 | yes |
| P1 ≤ 0.20 | **0.022** (4,384 of 199,446 subsamples) | yes |
| P2 ≤ 0.25 | **0.088** (3,293 of 37,368 mm, 34 printed components) | yes |
| P3 2 or 3 | **3** (`#2A2C30`, `#ECE6DA`, `#FF6A1A`) | yes |
| static fit | 1,953 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row | yes |
| swept fit | **incomplete: 12 of 12 joints unswept** (`sweep_step_degrees` not declared) | **no** |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with 12 horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-2-hero.png),
[`iso`](ot10-hexapod-2-look_iso.png),
[`iso_back`](ot10-hexapod-2-look_iso_back.png),
[`front`](ot10-hexapod-2-look_front.png),
[`right`](ot10-hexapod-2-look_right.png) and
[`top`](ot10-hexapod-2-look_top.png).
`cadex render` took 2 min 4 s for the whole command: 58.5 s acquiring the
tessellation, 7.6 s drawing, and 2.3 s of that for the hero, at 134,850
drawn triangles (from 667,700 input triangles).

**Diagnosis.** Against attempt 1, T4 rose from 1 to 2 and the median
total from 13 to 14. P2 fell from 0.655 to 0.088: the legs, feet and hip
pods are now blended. CPU-limit refusals fell from 19 to 3, which is
ADR-418's pin measured on a real turn. The one bar item missed is the
same one as in attempt 1, for a different reason. The agent did try the
sweep: it declared 15° steps, saw the engine's sweep budget run out on the
first hip, and switched the sweep off (its `DECISIONS.md` ADR-005 and
`docs/rejected.md`). That budget is
`cadex_assembly_worker.py`'s `_SWEEP_TOTAL_SECONDS = 180`, with 90 s per
joint. A 12-servo robot therefore has 15 s per joint on average to sweep
1,953 pairs, and at 63 components it did not finish one. Each joint's
bounded child is also sent every component's BREP again. No prompt can
reach a complete sweep on a design this size inside that budget. So the
next change is again to the cost of checking, not to the prompt: measure
where one hip joint's sweep spends its time on this accepted revision (a
read-only copy), and make a 12-joint sweep fit. The likely candidates are
sweeping only pairs whose relative pose the joint changes, a
bounding-box cull before `distToShape`, and serialising the BREPs once
per sweep rather than once per joint. The weakest judged trait is T3:
two of three calls saw orange caps only on the knee axes, with the hip
yaw axes showing bare horns. Attempt 1's T3 was also 1.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 10 refused calls. The notes' `refusals.py` counted one as a
horn style, but that was a false match on an output named `horn`: it was a
`write_script` refusal to drop the accepted outputs `horn` and `servo`
without `replace=true`, which is a different class. The other nine
were three CPU-limit refusals; two sandbox refusals (`getattr`, an import);
one `assembly.component` whose source was a name rather than a part
value built in the script; two guessed JSON pointers (`/revision`, `/failing`);
and one reset-variation refusal that named the lift, which the agent then
applied.

## A5 attempt: the quadruped (`ot10-quadruped-2`)

**Misses the bar on one count: the swept fit is incomplete.** The judged
total is 16 of 21, which clears the frozen 14 and is the best in the run so
far. P1, P2 and P3 are all within their bars. This is the frozen quadruped
prompt above, word for word, run once on the new project
`ot10-quadruped-2` with no continuation, the same argv and
`CADEX_EFFORT=medium`. It started at 2026-09-27T21:48:11Z at revision
`b6c61073`, with no product change since hexapod attempt 2. It ran
detached from the loop, and its stdout and stderr stayed outside git. The
turn ended on its own at 22:32:00Z (43 min 49 s) with exit 0, at accepted
revision `27ba92c66728…` (digest `0b530c4bdbd0…`). It was scored on the
unchanged engine, before ADR-419 landed.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| quadruped, call 1 | 2 | 3 | 2 | 1 | 2 | 3 | 2 | 15 |
| quadruped, call 2 | 3 | 3 | 3 | 1 | 2 | 3 | 2 | 17 |
| quadruped, call 3 | 2 | 3 | 3 | 1 | 2 | 3 | 2 | 16 |
| quadruped, median | 2 | 3 | 3 | 1 | 2 | 3 | 2 | **16** |

Every raw reply is kept in
[`ot10-quadruped-2-score.json`](ot10-quadruped-2-score.json), under the
same rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 16 | yes |
| no trait 0 | lowest is 1 (T4) | yes |
| above hex3 (2) | 16 | yes |
| P1 ≤ 0.20 | **0.004** (962 of 241,713 subsamples) | yes |
| P2 ≤ 0.25 | **0.238** (8,346 of 35,110 mm, 24 printed components) | yes |
| P3 2 or 3 | **3** (`#2A2D33`, `#ECE7DC`, `#F26A1B`) | yes |
| static fit | 1,953 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row | yes |
| swept fit | **incomplete: 8 of 8 joints unswept** (`sweep_step_degrees` not declared) | **no** |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8 × MG90S with 8 horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-quadruped-2-hero.png),
[`iso`](ot10-quadruped-2-look_iso.png),
[`iso_back`](ot10-quadruped-2-look_iso_back.png),
[`front`](ot10-quadruped-2-look_front.png),
[`right`](ot10-quadruped-2-look_right.png) and
[`top`](ot10-quadruped-2-look_top.png).
`cadex render` took 4 min 55 s for the whole command: 135.0 s acquiring
the tessellation, 9.4 s drawing, and 2.9 s of that for the hero, at
145,880 drawn triangles.

**Diagnosis.** The swept fit is the same miss as hexapod attempt 2, for the
same cause. The agent declared 15° steps, then 45°. It hit the 2,000-pair
limit on an earlier, larger revision, then the 90 s per-joint and 180 s
total budgets, and it switched the sweep off (its `DECISIONS.md` ADR-009
and `docs/rejected.md`). ADR-419, the next unit, is the tool change for
exactly this. The weakest judged trait is T4 (1 in all three calls): the
body is a soft rounded box, but the thigh links are sharp-edged
rectangular blocks. P2 reads 0.238, close to its 0.25 bar, and its
measured set includes `c_floor`, which is world geometry, not a printed
part. That concern is open. Changing what P2 counts changes a frozen
proxy, so it needs a recorded re-score decision, not a quiet fix.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 11 refused calls. The notes' `refusals.py` again counted one
as a horn style, but it was the `write_script` guard against dropping the
accepted outputs `horn` and `servo`, a different class. The other ten
were:
- three sandbox refusals (`type`, `hasattr`, an import);
- one edit whose `old` text did not occur;
- five kernel refusals: two `fuse` topology errors, one `fuse` refine,
  and two fillets at too large a radius;
- one domain worker that exited without a result.

**An earlier quadruped turn was aborted and is not an attempt.** The
frozen quadruped prompt was started on `ot10-quadruped-1` at
2026-09-27T20:49:25Z by an iteration that did not detach it. It was
killed with its session 8 minutes in. By then it had written three probe
scripts and had not written a design. No turn ended, so no design
reached a verdict. Under the question policy that is a harness stop, not
an attempt. The project stays as it is, read-only, and the quadruped's
A5 attempt will run on a new project.

## A5 attempt: the biped (`ot10-biped-1`)

**Meets the bar on every item, the first A5 design in the run to do so.**
The judged total is 15 of 21, P1, P2 and P3 are within their bars, and
every fit gate passes, including the first complete, passing swept fit in
the run. This is the frozen biped prompt above, word for word, run once on
the new project `ot10-biped-1` with no continuation:

    CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-biped-1 \
        --model claude-opus-5-5 -p "<the frozen biped prompt>" --json

It started at 2026-09-27T23:25:23Z at revision `2bdafcee` (after ADR-419
and ADR-420). It ran detached from the loop, and its stdout and stderr
stayed outside git. The turn ended on its own at 23:59:53Z (34 min 30 s)
with exit 0, at accepted revision `44b8497b5c54…` (digest
`10e2fd59cfd7…`). It was first unscored because the product could not
reopen it (below). It was scored after ADR-421, which changed the
engine's restore comparison and nothing about the design.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| biped, call 1 | 2 | 3 | 3 | 1 | 2 | 2 | 2 | 15 |
| biped, call 2 | 2 | 3 | 3 | 1 | 2 | 2 | 2 | 15 |
| biped, call 3 | 2 | 3 | 3 | 1 | 3 | 2 | 2 | 16 |
| biped, median | 2 | 3 | 3 | 1 | 2 | 2 | 2 | **15** |

Every raw reply is kept in
[`ot10-biped-1-score.json`](ot10-biped-1-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 15 | yes |
| no trait 0 | lowest is 1 (T4) | yes |
| above hex3 (2) | 15 | yes |
| P1 ≤ 0.20 | **0.002** (493 of 230,650 subsamples) | yes |
| P2 ≤ 0.25 | **0.068** (2,611 of 38,133 mm, 22 printed components, `floor` among them) | yes |
| P3 2 or 3 | **3** (`#2B2F36`, `#E9E4D8`, `#F26A1B`) | yes |
| static fit | 1,275 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row. 43 fixed-joint pairs touching | yes |
| swept fit | **complete and passing: 6 of 6 joints** at 15° steps, 0 failing pairs. The 6 floor contacts are advisory world geometry (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 6 × MG90S with 6 horns, 12 × M2×6 | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-biped-1-hero.png),
[`iso`](ot10-biped-1-look_iso.png),
[`iso_back`](ot10-biped-1-look_iso_back.png),
[`front`](ot10-biped-1-look_front.png),
[`right`](ot10-biped-1-look_right.png) and
[`top`](ot10-biped-1-look_top.png).
`cadex render` took 3 min 31 s for the whole command: 101.2 s acquiring
the tessellation, 7.2 s drawing, and 2.4 s of that for the hero, at
91,619 drawn triangles. Its `rebuild` re-accepted the same revision under
a new byte digest (`e3b08e38a04a…`), because this design's bytes are not
reproducible; the revision and the design are unchanged.

**Where it is weakest.** T4 is 1 in all three calls: the body is a soft
rounded box, but the limbs are flat constant-thickness link plates with
box-shaped servo covers, and nothing merges. That is the same weakest
trait as the quadruped. T7 is 2: call 1 names no contact shadow, a high
camera and jagged edges in the top view. The top view is a `look` view,
not the hero, so that remark is about the A2 tooling as much as the design.

**Why it could not be scored at first.** `cadex render` exited 1 after
1 min 45 s, with `The restore pass digest does not match the accepted
digest`. All three retained attempts of the one revision produce 127
outputs with identical recipes. Exactly one output differs: `src_hood`,
which is `part.fillet(part.cut(part.fillet(part.box), …, refine=true))`,
with no `part.offset` in it. Its vertex set, counts and bounding box are
bit-identical across processes. Two things are not. One face's area
differs by 6.8 × 10⁻¹³ mm² (114.68601535158916 against …984), on a
16-edge plane of the kind `refine` makes. Two 0.4π mm fillet arcs differ
in length by 8.2 × 10⁻¹⁵ mm (1.256637061435912 against …9201). The arcs
were found only after the fix for areas alone still refused. ADR-389's
fingerprint hashed both exactly. ADR-421 drops every integrated measure
from it, keeping the vertex set, the counts, the bounds and the recipe.
After that the render opened the project through the geometry path and
went on to draw it.

The failed restore also rewrote the project's `script.json`
`latest_candidate` to name the restore attempt with status `accepted`.
That was reverted by hand to the project's own commit (`48c994f`).
ADR-421 fixes the cause: the second refused open, before the fix for
arcs, left `latest_candidate` untouched.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 7 refused calls. `refusals.py` counted one as a horn style,
but it was again the `write_script` guard against dropping accepted
outputs. The other six were:
- one sandbox refusal (`dir`);
- one fillet selector without `expected_count`;
- one fillet where 4 of 12 edges refused the radius;
- one reset-variation refusal that named the lift, which the agent then
  applied;
- two refusals to retire an output that a component still linked.

## Baseline

hex3's accepted design is the baseline: revision `c1704bfcb631…`, digest
`24103b9a3eee…`, on the project hex3, read-only. It was rendered from a
copy outside the project with the five `look` views at 768 px
(ADR-406/410 renderer, inventory colouring, floor left out). Those views
are committed here as `hex3-look_*.png`.

| trait | call 1 | call 2 | call 3 | median |
|---|---|---|---|---|
| T1 | 0 | 0 | 0 | **0** |
| T2 | 2 | 1 | 1 | **1** |
| T3 | 0 | 0 | 0 | **0** |
| T4 | 0 | 0 | 0 | **0** |
| T5 | 0 | 0 | 0 | **0** |
| T6 | 0 | 0 | 0 | **0** |
| T7 | 1 | 1 | 1 | **1** |
| **total** | 3 | 2 | 2 | **2** |

**hex3 scores 2 of 21.** The three calls agree on every trait
except T2 (2, 1, 1). Each call took about 20 s. Every raw reply, with
the judge's reasons, is kept in
[`hex3-baseline-score.json`](hex3-baseline-score.json). They are evidence of the baseline and are not to be quoted in any
product prompt (see *Procedure*). In the language's terms: there is no
shell (T1), no joint features (T3), only plates and bars (T4), no face
(T5), a flat sprawl with no feet (T6), and a flat-shaded orthographic
render (T7). The two colours follow printed versus purchased, which the
judge read as partly by role (T2).

hex3's proxies were not measured when it was scored, because A3 builds
them. All three now are (ADR-414, ADR-415; see *A3* below): P1 **0.373**
and P2 **0.332**, both over their bars, and P3 **2**, within it.

| view | file | bytes |
|---|---|---|
| iso | [`hex3-look_iso.png`](hex3-look_iso.png) | 32,756 |
| iso_back | [`hex3-look_iso_back.png`](hex3-look_iso_back.png) | 28,506 |
| front | [`hex3-look_front.png`](hex3-look_front.png) | 14,578 |
| right | [`hex3-look_right.png`](hex3-look_right.png) | 14,290 |
| top | [`hex3-look_top.png`](hex3-look_top.png) | 22,425 |

## A2: the studio renderer, before and after

ADR-412 replaced the flat renderer with a studio one. The judge's candidate
set for every design from here on leads with its 1024 px hero. These are
hex3's accepted design (revision `c1704bfcb631…`) from the same `/tmp` copy
and the same snapshot as the baseline, with the floor left out and the
inventory deciding printed and purchased. The before image is the
baseline's own `iso` view.

| view | before (ADR-406, flat) | after (ADR-412, studio) |
|---|---|---|
| iso, 768 px | [`hex3-look_iso.png`](hex3-look_iso.png), 32,756 B | [`hex3-studio_iso.png`](hex3-studio_iso.png), 110,996 B |
| hero, 1024 px | — (no hero view existed) | [`hex3-studio_hero.png`](hex3-studio_hero.png), 120,991 B |

`cadex render` on the copy, on this machine (Ryzen 9 9950X, Python 3.11,
one process, no display, no GPU): the four 512 px views and the 1024 px
hero took **6.5 s** in all, the hero **2.2 s**, at 106,326 drawn
triangles and 4.1 million subsample visits. Acquiring the tessellation
took 207 s more. That is the engine's rebuild of the accepted design and
is unchanged by the renderer. The whole command took 6 min 59 s.

hex3 is not re-scored here. The rubric scores the design as shown, and
only T7 (presentation) is about the render. The baseline stays as
frozen. The first scored studio renders are A5's.

## A3: the proxies, measured on hex3

ADR-414 implements P1 and P3 as frozen above. `cadex render`'s summary,
the review's `render` block and the agent's `look` all report them,
measured on the hero at 512 px with 2×2 subsamples by a depth pass alone
(`render.design_proxies`). The floor is left out, and the inventory decides
printed and purchased. ADR-415 adds P2, a BREP measure: the part worker
reports each output's solid edge length and its sharp convex part, and the
CLI sums both over the printed placements.

| proxy | hex3 before (A1) | hex3 after (ADR-414) | bar | meets |
|---|---|---|---|---|
| P1 `hardware_silhouette_share` | not measured | **0.373** (76,170 of 204,356 subsamples) | ≤ 0.20 | no |
| P2 `sharp_outside_edge_share` | not measured | **0.332** (6,793 of 20,468 mm, 14 printed components; ADR-415) | ≤ 0.25 | no |
| P3 `material_count` | 2 by construction | **2** (`#2F3237`, `#E9E6DF`) | 2 or 3 | yes |

That is the same `/tmp` copy at revision `c1704bfcb631…`, from
`./cadex render --project <copy> --json` (7 min 2 s in all, 207 s of it the
rebuild). Measuring does not change a pixel: the hero it wrote is byte for
byte [`hex3-studio_hero.png`](hex3-studio_hero.png) (sha256 `83cc8beb…`),
so there is no new image for this unit. Over a third of what hex3 shows
from the hero angle is bought servos and boards. That is T1's 0 in a
number. Its two materials pass P3 while the judge gave T2 only a 1, which
is the README's point that the proxies are necessary, not sufficient.

P2 was measured by ADR-415 on a fresh copy of hex3 at the same revision
`c1704bfcb631…`, with the engine rebuilt and staged and `./cadex render
--project <copy> --engine <payload> --json` (7 min 1 s, most of it the
rebuild, which is what gives the accepted parts their new edge fact). The
hero it wrote is again byte for byte `hex3-studio_hero.png`. A third of
hex3's printed edge length is a bare convex corner: plates and bars with
no blend, T4's 0 in a number.
