# ot10 — the design-quality contract

Verified against source: 2026-09-28. [Cadex-new]

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

The run's closing summary, with every attempt and score in one table, is
[`REPORT.md`](REPORT.md).

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
| P2 | `sharp_outside_edge_share` | Over every non-seam BREP edge of every printed (uncatalogued) solid at the accepted revision, leaving out the world geometry the fit names (a floor), as P1 does (ADR-424): length of the **sharp convex** edges ÷ total edge length. An edge is sharp convex when the outward normals of its two faces, sampled at its midpoint, turn outward by more than 60°. A 90° corner is sharp; a 45° chamfer or a tangent fillet is not. A seam edge has the same face on both sides. With no printed edges the share is 0. | ≤ 0.25 |
| P3 | `material_count` | The number of distinct appearance materials drawn in the hero view. A part with a declared role and palette counts as its colour; a part with no declared role counts as the renderer's default for printed or purchased. | 2 or 3 |

Each proxy has a test that fails on a crude fixture (bare boxes, one
colour or rainbow, exposed hardware) and passes on a designed one. The
proxies are necessary, not sufficient. hex3 scores 2 on P3 with its
printed/purchased split, and it is still not a designed product. That is
why the bar also needs the judged score.

### Decision: P2 leaves out world geometry (ADR-424, 2026-09-28)

P2 as first frozen counted every uncatalogued solid, and a floor is
uncatalogued. It is world geometry, not a printed part: the fit reports
it as such, and P1 and `look` already leave it out. Counted, it pulled
the share either way by what the agent happened to do to the ground. A
bare floor box is all sharp edge and pushed P2 up (hex3's 3,612 mm,
quadruped-2's 7,220 mm). A filleted one had none and diluted it
(hexapod-4's floor is 24,019 mm of smooth edge, nearly half its total).
So P2 now counts only printed parts. The definition above says so, and
`render.edge_proxy` takes the fit's world geometry and reports what it
left out under `left_out_as_environment`. No threshold, trait, bar or
judging step changed.

Every earlier P2 was re-measured at its accepted revision from the
engine's own per-component edge facts
(`cadex_cli.inventory.printed_edges`, now keeping `by_component`). The
judged scores cannot move, because the judge never sees P2. One verdict
changed: hex3's P2 now passes. hex3 is the baseline, not a candidate,
and it still misses P1 (0.373) and the judged bar (2 of 21).

| probe | world geometry | P2 with it | P2 without it (ADR-424) | verdict |
|---|---|---|---|---|
| hex3 (baseline) | `c_floor`, 3,612 mm, all sharp | 0.332 | **0.189** (3,181 of 16,856 mm, 13 printed) | **no → yes** |
| hexapod 1 | `c_floor`, 9,608 mm, all sharp | 0.655 | **0.508** (11,525 of 22,667 mm, 16 printed) | no, unchanged |
| hexapod 2 | `c_floor`, 12,807 mm, none sharp | 0.088 | **0.134** (3,293 of 24,561 mm, 33 printed) | yes, unchanged |
| quadruped 2 | `c_floor`, 7,220 mm, all sharp | 0.238 | **0.040** (1,126 of 27,890 mm, 23 printed) | yes, unchanged |
| biped 1 | `floor`, 12,810 mm, none sharp | 0.068 | **0.103** (2,611 of 25,323 mm, 21 printed) | yes, unchanged |
| hexapod 3 | `floor`, 9,608 mm, all sharp | 0.240 | **0.048** (1,810 of 37,953 mm, 22 printed) | yes, unchanged |
| hexapod 4 | `c_floor`, 24,019 mm, none sharp | 0.114 | **0.220** (5,706 of 25,947 mm, 16 printed) | yes, unchanged |

No A5 verdict changes. hexapod 4 moves closest to the bar: its links
kept their edge breaks, and its filleted floor had hidden that. Figures
elsewhere on this page are shown as re-measured, with the earlier
floor-inclusive value in brackets where the text discusses it.

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
| P2 ≤ 0.25 | **0.508** (11,525 of 22,667 mm, 16 printed components; 0.655 with the floor, before ADR-424) | **no** |
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
total face count as the lever. P2's 0.508 (0.655 before ADR-424) is the unfilleted legs in a
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
| P2 ≤ 0.25 | **0.134** (3,293 of 24,561 mm, 33 printed components; 0.088 with the floor, before ADR-424) | yes |
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
total from 13 to 14. P2 fell from 0.508 to 0.134 (0.655 to 0.088 before ADR-424): the legs, feet and hip
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
| P2 ≤ 0.25 | **0.040** (1,126 of 27,890 mm, 23 printed components; 0.238 with the floor, before ADR-424) | yes |
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
rectangular blocks. P2 first read 0.238, close to its 0.25 bar, with
`c_floor` (world geometry, not a printed part) in its measured set. That
concern was settled by a recorded re-score decision, ADR-424 (see *The
proxies*): without the floor, P2 is 0.040.

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
| P2 ≤ 0.25 | **0.103** (2,611 of 25,323 mm, 21 printed components; 0.068 with `floor`, before ADR-424) | yes |
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

## A5 attempt 3: the hexapod (`ot10-hexapod-3`)

**Misses the bar on one count: the judged total is 13 of 21, under the
frozen 14.** Every other item passes. That includes the first complete,
passing swept fit on a hexapod in the run: 12 of 12 joints. This is the
frozen hexapod prompt above, word for word, run once on the new project
`ot10-hexapod-3` with no continuation, the same argv and
`CADEX_EFFORT=medium`. It started at 2026-09-28T00:34:31Z at revision
`3a2d2aee`, which is after ADR-419, ADR-420 and ADR-421. It ran detached
from the loop, and its stdout and stderr stayed outside git. The turn
ended on its own at 02:09:48Z (1 h 35 min) with exit 0 and `ok: true`,
at accepted revision `39dc8d60a26a…` (digest `d7bf27d9ded3…`).

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 2, median | 2 | 3 | 1 | 2 | 2 | 2 | 2 | **14** |
| attempt 3, call 1 | 2 | 3 | 2 | 1 | 1 | 2 | 2 | 13 |
| attempt 3, call 2 | 2 | 3 | 2 | 1 | 1 | 2 | 2 | 13 |
| attempt 3, call 3 | 2 | 2 | 2 | 1 | 1 | 2 | 2 | 12 |
| attempt 3, median | 2 | 3 | 2 | 1 | 1 | 2 | 2 | **13** |

Every raw reply is kept in
[`ot10-hexapod-3-score.json`](ot10-hexapod-3-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 13 | **no** |
| no trait 0 | lowest is 1 (T4, T5) | yes |
| above hex3 (2) | 13 | yes |
| P1 ≤ 0.20 | **0.007** (1,037 of 156,494 subsamples) | yes |
| P2 ≤ 0.25 | **0.048** (1,810 of 37,953 mm, 22 printed components; 0.240 with `floor`, before ADR-424) | yes |
| P3 2 or 3 | **3** (`#2E3136`, `#ECE8DF`, `#F26B1D`) | yes |
| static fit | 1,326 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row. 38 fixed-joint pairs touching | yes |
| swept fit | **complete and passing: 12 of 12 joints** at 20° steps, 0 failing pairs. The 12 floor contacts are advisory world geometry (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with 12 horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-3-hero.png),
[`iso`](ot10-hexapod-3-look_iso.png),
[`iso_back`](ot10-hexapod-3-look_iso_back.png),
[`front`](ot10-hexapod-3-look_front.png),
[`right`](ot10-hexapod-3-look_right.png) and
[`top`](ot10-hexapod-3-look_top.png).
`cadex render` took 9 min 15 s for the whole command: 286.8 s acquiring
the tessellation, 10.2 s drawing, and 2.7 s of that for the hero, at
207,828 drawn triangles (from 1,509,140 input triangles).

**Diagnosis.** The tool changes did their job. The sweep that attempt 2
switched off now completes. The agent tried 10°, 15° and 20° steps. It hit the time budget at 8 of 12 joints and again at 10 of 12, and
then accepted at 20°.
CPU-limit refusals were 4, against attempt 2's 3. What moved was the
design, on two traits:

- **T5 fell from 2 to 1 in all three calls. The face is too small to
  find.** The agent did declare a face: its `DECISIONS.md` ADR-004 puts a
  visor in a front notch at +X, on the IMU's axis, as §4 of the language
  asks. The visor has the `mechanism` role and colour, though. It is a
  slot about 60 × 8 px in a 768 px `right` view, over a graphite tub about
  350 px wide. That is far under §4's "about 25–50% of the body's front
  face". §4 also says the face "sits in `mechanism` graphite and may
  carry the accent". On this body the graphite surface around the notch
  is the same colour, and the accent went to the feet. So the gap is §4's
  proportion rule, which the agent did not meet. It sits beside a colour
  rule that only works on a shell-coloured surround, and the language does
  not say that. The quadruped and the biped, with faces on white shells,
  both scored T5 2.
- **T4 stayed at 1, as in attempt 1 and the biped.** All three calls
  read the body as a flat star plate with box-shaped coxa covers. The
  agent's first body was a scaled-ellipsoid dome (a B-spline surface). It
  pushed the fit check past the 300 CPU-second limit, a 3D offset of it
  failed, and it was replaced by a clipped sphere (`docs/rejected.md`).
  The dome is 10 mm high over a 240 mm star, so it reads as a shallow
  dish. The coxae, by contrast, got post-cut edge breaks for P2 and still
  kept their box sections. P2 read 0.240 with the floor, close to its bar; without it (ADR-424) it is 0.048.

The next change answers the measured gap in the language's own terms.
§4 must make the face findable on any body: a proportion the agent can
check, and a contrast rule (graphite on shell, or the accent when the
face sits on graphite). The overlay must teach checking it with `look`
from the face's own side before accepting. That is a documentation and
overlay change, with no judge wording in it. T4 on the hexapod stays open
until a body can be a soft primitive inside the CPU budget.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 20 refused calls:
- 4 CPU-limit refusals;
- 1 call to a tool name that does not exist (`inspect` without its
  prefix);
- 2 sandbox refusals (`dir`, an import);
- 7 kernel refusals:
  - three booleans that produced several solids;
  - one failed 3D offset;
  - one invalid bounding box;
  - two fillets that refused their radius;
- 1 edit whose `old` text did not occur;
- 2 guessed JSON pointers (`/summary`, `/printed_edges`);
- 1 reset-variation refusal that named the lift, which the agent then
  applied;
- 2 refusals to retire an output that a component still linked.

## A5 attempt 4: the hexapod (`ot10-hexapod-4`)

**Misses the bar on one count: the judged total is 12 of 21, under the
frozen 14.** Every other item passes. The face rule it was run to measure
held (T5 rose from 1 to 2 in all three calls), but T2 and T3 fell. This is
the frozen hexapod prompt above, word for word, run once on the new project
`ot10-hexapod-4` with no continuation, the same argv and
`CADEX_EFFORT=medium`. It started at 2026-09-28T03:07:21Z at revision
`c3abb3ab`, which is ADR-422 (§4's face size and contrast rules, and the
overlay's `look` at `right` before accepting). It ran detached from the
loop, and its stdout and stderr stayed outside git. The turn ended on its
own at 03:48Z (41 min) with `ok: true`, at accepted revision
`f0b98de47b17…` (digest `1af54879ada4…`).

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 3, median | 2 | 3 | 2 | 1 | 1 | 2 | 2 | **13** |
| attempt 4, call 1 | 2 | 2 | 1 | 1 | 2 | 2 | 2 | 12 |
| attempt 4, call 2 | 2 | 2 | 1 | 1 | 2 | 2 | 2 | 12 |
| attempt 4, call 3 | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 10 |
| attempt 4, median | 2 | 2 | 1 | 1 | 2 | 2 | 2 | **12** |

Every raw reply is kept in
[`ot10-hexapod-4-score.json`](ot10-hexapod-4-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 12 | **no** |
| no trait 0 | lowest is 1 (T3, T4) | yes |
| above hex3 (2) | 12 | yes |
| P1 ≤ 0.20 | **0.013** | yes |
| P2 ≤ 0.25 | **0.220** (5,706 of 25,947 mm, 16 printed components; 0.114 with the floor, before ADR-424) | yes |
| P3 2 or 3 | **2** (`#2A2C31`, `#E9E4D8`) | yes |
| static fit | 1,035 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row. 32 fixed-joint pairs touching | yes |
| swept fit | **complete and passing: 12 of 12 joints** at 15° steps, 0 failing pairs. The floor contacts are advisory world geometry (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with 12 horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-4-hero.png),
[`iso`](ot10-hexapod-4-look_iso.png),
[`iso_back`](ot10-hexapod-4-look_iso_back.png),
[`front`](ot10-hexapod-4-look_front.png),
[`right`](ot10-hexapod-4-look_right.png) and
[`top`](ot10-hexapod-4-look_top.png).
`cadex render` took 3 min 23 s for the whole command, 102.1 s of it
acquiring the tessellation, at 73,695 drawn triangles (from 486,396 input
triangles).

**Diagnosis.** ADR-422 did what it was written to do, and the design lost
elsewhere.

- **The face now meets §4, and T5 rose from 1 to 2.** The agent's
  `DECISIONS.md` puts a graphite visor band split out of the bone front
  wall, 76 mm wide and about 13 mm tall, facing +X. In the `right` view it
  spans about 55% of the body's width and about 36% of its height, and it
  is graphite on bone. The agent looked at `right` twice, both times on
  earlier revisions; its looks on the accepted revision were `hero`, `iso`
  and a focused `iso` of one leg. It still reads as a generic slot rather than a character:
  one dark rectangle, with no eye, lens or accent in it.
- **T2 fell from 3 to 2, and T3 from 2 to 1. Both follow from the CPU
  budget.** The agent's summary says so itself. Its orange accent feet
  were separate components; it merged them into the leg links to fit the
  300 CPU-second limit, which left two materials and no accent. The hip
  joints got no caps: the judge saw bare horn discs and shaft stubs. The
  turn hit the CPU limit 8 times (attempt 3: 4). The agent's own
  experiment found that the geometry built fine without the leg
  components and that the assembly measurement was the cost. It dropped
  a B-spline body, a B-spline leg outline, per-edge fillets, the separate
  feet and the 24 tab screws, each one for CPU.
- **T4 stayed at 1.** The body is a rounded rectangular slab with box
  pods on top and constant-section bent legs.

Four hexapod attempts have now scored 13, 14, 13 and 12. What limits the
hexapod is no longer a rule the agent has not been taught. It is what the
agent can afford to build under the 300 CPU-second limit with about 46
components. Each attempt spends that budget on a different trait, and
this one spent it on the face. The next unit measures where a
46-component hexapod's accepted build spends its CPU seconds, on this
project read-only, before any further prompt or language change. A second
open concern: the hero camera looks from 35° round from −Y, so a face at
+X is seen nearly edge-on in the hero (ADR-422, *Not taken*).

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 14 refused calls:
- 8 CPU-limit refusals;
- 3 sandbox refusals (`hasattr`, `dir`, an import);
- 1 boolean that produced 10 solids;
- 1 edit whose `old` text did not occur;
- 1 guessed JSON pointer (`/facts`).

## A5 attempt 3: the quadruped (`ot10-quadruped-3`)

**Meets the bar on every item, the second A5 design in the run to do
so and the first quadruped.** The judged total is 15 of 21, P1, P2 and P3
are within their bars, and the swept fit is complete and passing on all
8 joints. This is the frozen quadruped prompt above, word for word, run
once on the new project `ot10-quadruped-3` with no continuation:

    CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-quadruped-3 \
        --model claude-opus-5-5 -p "<the frozen quadruped prompt>" --json

The prompt was read from `contract.json` at launch, and the process
list at launch shows that argv, `--model claude-opus-5-5` and
`CADEX_EFFORT=medium`, so the attempt conforms. It started at
2026-09-28T02:52:54Z at revision `b20bb7a0`, which is after ADR-419,
ADR-420 and ADR-421 and **before** ADR-422's face rules, so the overlay
it read did not have them. It ran detached from the loop, and its stdout
and stderr stayed outside git. The turn ended on its own at 03:41:39Z
(48 min 45 s) with `ok: true`, at accepted revision `7de6eea6212e…`
(digest `d929e47d0f60…`). The iteration that launched it left no record,
so it was published two iterations late, after ADR-422, ADR-423 and
ADR-424. It was rendered and judged from a `/tmp` copy of the project,
at the accepted revision; the project itself is unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| quadruped, median (`ot10-quadruped-2`) | 2 | 3 | 3 | 1 | 2 | 3 | 2 | **16** |
| quadruped 3, call 1 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 |
| quadruped 3, call 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 |
| quadruped 3, call 3 | 2 | 3 | 2 | 2 | 2 | 3 | 2 | 16 |
| quadruped 3, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |

Every raw reply is kept in
[`ot10-quadruped-3-score.json`](ot10-quadruped-3-score.json), under the
same rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 15 | yes |
| no trait 0 | lowest is 2 (every trait but T2) | yes |
| above hex3 (2) | 15 | yes |
| P1 ≤ 0.20 | **0.0001** (36 of 264,671 subsamples) | yes |
| P2 ≤ 0.25 | **0.116** (3,108 of 26,853 mm, 24 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2A2C31`, `#ECE8DF`, `#FF6A1A`) | yes |
| static fit | 1,891 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row. 52 fixed-joint pairs touching | yes |
| swept fit | **complete and passing: 8 of 8 joints** at 10° steps, 0 failing pairs. The 4 floor contacts are advisory world geometry (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8 × MG90S with 8 horns, 16 × M2×8 | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-quadruped-3-hero.png),
[`iso`](ot10-quadruped-3-look_iso.png),
[`iso_back`](ot10-quadruped-3-look_iso_back.png),
[`front`](ot10-quadruped-3-look_front.png),
[`right`](ot10-quadruped-3-look_right.png) and
[`top`](ot10-quadruped-3-look_top.png).
`cadex render` took 2 min 47 s for the whole command: 75.4 s acquiring
the tessellation, 6.9 s drawing, and 2.6 s of that for the hero, at
78,419 drawn triangles (from 650,316 input triangles).

**Against `ot10-quadruped-2`.** The total fell by one, 16 to 15, and the
design now clears every other bar item where quadruped 2 missed the
swept fit. T4 rose from 1 to 2: the hood is one large-radius shell over
the tray and the shins taper from 22 mm to 10 mm into ball feet. T3 fell
from 3 to 2: every outer hip and knee axis carries an orange cap (one
print per leg, the two caps joined by a spine), but all three calls
name bare horns on the inner axes. T6 fell from 3 to 2 in two of three
calls: the body reads long and the thigh pods stand out sideways. T5 is
2, as before: one dark oval visor at +X, with no ADR-422 guidance
behind it, since the turn predates it.

**What the agent spent its budget on.** It hit no CPU limit at all,
where every hexapod since attempt 2 hit it between 3 and 8 times. It
hit the sweep's 2,000-pair limit instead: screw-and-nut mounting gave 82
components and 3,321 pairs. It dropped the nuts for thread-forming
screws and merged each leg's two caps into one part, reaching 62
components and 1,891 pairs, and then the sweep completed at 10°. It also
removed blanket fillets from the thigh pockets and deck peg roots,
where they caused intersections (its `docs/rejected.md`).

**P2 and the floor.** Before ADR-424, the agent read P2 at 31% and
found that "the 1.2 m floor slab's own edges were being counted as
printed". It rounded the floor, and its own reading fell to 6.8%. That
is the dilution ADR-424 describes, reached from inside a turn. Under
ADR-424 the floor's 19,207 mm of rounded edge is left out, and the
printed parts alone read 0.116, still well inside the bar. The agent's
rounded floor changes no verdict here.

**It ran at the same time as hexapod attempt 4.** The two turns
overlapped from 03:07:21Z to 03:41:39Z. Seven of hexapod 4's eight
CPU-limit refusals (03:22Z to 03:39Z) fall inside that window; the
eighth, at 03:43:05Z, came after this turn had ended. The limit is
`RLIMIT_CPU`, which charges CPU time rather than wall time, and
ADR-423 located hexapod 4's cost in its own static clearance pass
(83 s of worker CPU to 28 s on a read-only copy). So the overlap is
recorded, but it is not the cause of hexapod 4's refusals.

**One product gap the agent named itself.** Its summary says "the
build replies were too large for me to read, so I never saw their fit
summaries". It checked fit by reading `inspect scope=clearance` pages
instead, which found and fixed a 2.3 mm³ battery-to-tray overlap. That
is a cost in turns, not a refusal, and is left for a later unit.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 10 refused calls:
- 2 sandbox refusals (`getattr`, an import);
- 2 guessed JSON pointers (both `/facts/bounding_box`);
- 3 kernel refusals: one `fuse` that produced 2 solids, and two fillets
  where 4 of 12 and 3 of 18 edges refused the radius;
- 1 reset-variation refusal that named the lift, which the agent then
  applied;
- 2 refusals to retire an output that a component still linked.

## A5 attempt 5: the hexapod (`ot10-hexapod-5`)

**Misses the bar on one count: the swept fit is incomplete, 10 of 12
joints.** Every other item passes, and the judged total is 16 of 21, the
highest of any hexapod in the run and above the frozen 14. This is the
frozen hexapod prompt above, word for word, read from `contract.json`
`a5.prompts.hexapod` and run once on the new project `ot10-hexapod-5`
with no continuation, the same argv and `CADEX_EFFORT=medium`. It started
at 2026-09-28T05:27:20Z at revision `3008e1f7`, which is after ADR-422's
face rules, ADR-423's bounded static clearance and ADR-424's P2. The
iteration that launched it ended in a harness error before the turn
finished, so the turn is published here, one iteration later; it
conforms, and no other hexapod turn was started. The turn ended on its
own at 06:52:46Z (85 min) with `ok: true`, at accepted revision
`d2198144a58a…` (digest `dbab6d5c9585…`). It was rendered and judged from
a `/tmp` copy of the project at the accepted revision; the project itself
is unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 4, median | 2 | 2 | 1 | 1 | 2 | 2 | 2 | **12** |
| attempt 5, call 1 | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 16 |
| attempt 5, call 2 | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 16 |
| attempt 5, call 3 | 2 | 3 | 3 | 2 | 2 | 2 | 2 | 16 |
| attempt 5, median | 2 | 3 | 3 | 2 | 2 | 2 | 2 | **16** |

Every raw reply is kept in
[`ot10-hexapod-5-score.json`](ot10-hexapod-5-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 16 | yes |
| no trait 0 | lowest is 2 (every trait but T2 and T3) | yes |
| above hex3 (2) | 16 | yes |
| P1 ≤ 0.20 | **0.013** (2,232 of 166,930 subsamples) | yes |
| P2 ≤ 0.25 | **0.168** (4,394 of 26,115 mm, 28 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2A2C31`, `#E8E3D6`, `#F2692A`) | yes |
| static fit | 1,653 pairs clear, 0 intersections. The one failing row is the floor's advisory world-geometry row. 44 fixed-joint pairs touching | yes |
| swept fit | **incomplete: 10 of 12 joints** at 80° steps (two samples, the range ends), 0 failing pairs. `hip_rr` exceeded the runtime budget and `knee_rr` was never reached. The 5 floor contacts are advisory world geometry (ADR-420) | **no** |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with 6 cross and 6 single-arm horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-5-hero.png),
[`iso`](ot10-hexapod-5-look_iso.png),
[`iso_back`](ot10-hexapod-5-look_iso_back.png),
[`front`](ot10-hexapod-5-look_front.png),
[`right`](ot10-hexapod-5-look_right.png) and
[`top`](ot10-hexapod-5-look_top.png).
`cadex render` took 9 min 5 s for the whole command: 269.4 s acquiring
the tessellation, 9.2 s drawing, and 2.6 s of that for the hero, at
183,671 drawn triangles (from 894,400 input triangles).

**Against attempt 4.** The total rose from 12 to 16, and all three calls
agree on every trait. T2 rose from 2 to 3 and T3 from 1 to 3: every hip
and knee axis carries an orange cap concentric with it (12 accent
components), and the orange is used nowhere else. T4 rose from 1 to 2:
the body is a dome over a rounded base, and the legs are curved rods,
though the servo pods are still boxes. T5 stays at 2: a graphite visor
across the front of the dome marks a front, with no eye or focal detail.
T6 stays at 2: ball feet, but legs of nearly constant section and a wide
stance. The design has 58 components, against attempt 4's 46.

**ADR-423 did what it was written to do.** Attempt 4 lost its accent
feet and its joint caps to the 300 CPU-second limit, eight times. This
turn hit the CPU limit **zero** times and kept both accents and caps.
That is the diagnosis of attempt 4, confirmed on the next attempt.
ADR-424 changes no verdict here: the judge never sees P2, and the P2
above is already measured without the floor.

**Diagnosis: the binding limit moved to the swept fit's runtime
budget.** ADR-423's own record named this as the next wall ("a much
larger robot may meet the sweep wall budget next"). The sweep runs one
`FreeCADCmd` child per joint, in series, under a 180 s total
(`_SWEEP_TOTAL_SECONDS`) and 90 s per joint. With 58 components and
1,653 pairs, the budget ran out on the eleventh joint. The agent
coarsened the step from 10° to 20°, 30° and then 80°, rebuilding each
time; the transcript has 34 `runtime budget exceeded` rows, and at 80°,
two samples per joint, the sweep still stopped at 10 of 12. The
remaining cost therefore does not scale with the number of poses. It is
fixed per joint: each child deserialises every component's BREP and
prepares every moving pair before it measures anything. This is an
inference from the step changes, not yet a profile. The next unit
measures where the sweep's wall seconds go on this project, read-only,
as ADR-423 did for the static pass, before any prompt or language
change.

**A second product gap, named for the second time.** As in quadruped 3,
the agent said the build reply was too large for it to read (59.8 KB
once), and it paged `inspect scope=clearance` and checked 250 of 1,653
static pairs by hand instead. That cost it turns, not a verdict.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 20 refused calls, none of them a CPU-limit refusal:
- 4 sandbox or argument refusals (`getattr`, an import, one `fillet`
  without `expected_count`, one `edit_script` given an unknown
  `replace` argument);
- 3 guessed JSON pointers (two `/facts/bounding_box`, one `/summary`);
- 5 kernel refusals: a `fuse` whose refine was invalid, a `fuse` that
  produced 2 solids, a fillet that refused its radius, and two `cut`s
  that returned a null shape;
- 4 MJCF export refusals: one re-diagonalised knee-horn inertia and
  three body-position drifts, all resolved by the agent;
- 1 reset-variation refusal that named the lift, which the agent then
  applied;
- 3 refusals to retire an output that a component still linked.

The refusal counter tags the knee-horn inertia refusal as a horn-style
refusal, because the body is named `c_knee_horn_fl`. It is not one: it
names no horn style.

## A5 attempt 6: the hexapod (`ot10-hexapod-6`)

**Misses the bar: the accepted revision's swept fit is incomplete, 0 of
12 joints, because it exceeds the sweep's pair budget.** The judged
half clears the bar at 15 of 21, and all three proxies pass. This is the
frozen hexapod prompt, word for word, run once on the new project
`ot10-hexapod-6` with no continuation, the same argv, `claude-opus-5-5`
and `CADEX_EFFORT=medium`. It started at 2026-09-28T08:07:15Z at
revision `feb2190b`, which is after ADR-425's boundary-shell sweep, on
the rebuilt engine. The turn ended on its own at 08:39:33Z (32 min) with
`ok: true`, at accepted revision `3cb2b1d0847d…` (digest
`18f182fbf270…`). It was rendered and judged from a `/tmp` copy of the
project; the project itself is unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 5, median | 2 | 3 | 3 | 2 | 2 | 2 | 2 | **16** |
| attempt 6, call 1 | 2 | 3 | 2 | 1 | 2 | 2 | 2 | 14 |
| attempt 6, call 2 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 |
| attempt 6, call 3 | 2 | 3 | 2 | 2 | 2 | 2 | 2 | 15 |
| attempt 6, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |

Every raw reply is kept in
[`ot10-hexapod-6-score.json`](ot10-hexapod-6-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | 15 | yes |
| no trait 0 | lowest is 2 | yes |
| above hex3 (2) | 15 | yes |
| P1 ≤ 0.20 | **0.009** (1,778 of 194,975 subsamples) | yes |
| P2 ≤ 0.25 | **0.198** (6,199 of 31,322 mm, 33 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2A2C31`, `#E8E4DA`, `#FF6A1A`) | yes |
| static fit | 3,741 pairs, 0 intersections, 73 fixed-joint pairs touching. **Seven failing rows**: the floor's advisory world-geometry row, and six `below clearance` rows where each ball foot rests on `c_floor` at 0.0 mm with no common volume. The static pass does not mark these as advisory; the sweep does (ADR-420) | as reported, no |
| swept fit | **incomplete: 0 of 12 joints**, every joint `pair budget exceeded` at 5° steps | **no** |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S, 24 × M2×8 screws | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-6-hero.png),
[`iso`](ot10-hexapod-6-look_iso.png),
[`iso_back`](ot10-hexapod-6-look_iso_back.png),
[`front`](ot10-hexapod-6-look_front.png),
[`right`](ot10-hexapod-6-look_right.png) and
[`top`](ot10-hexapod-6-look_top.png).
`cadex render` took 1 min 25 s for the whole command: 38.5 s acquiring
the tessellation, 7.6 s drawing, and 2.4 s of that for the hero, at
141,438 drawn triangles (from 929,000 input triangles).

**ADR-425 did what it was written to do, and a different limit bound.**
With the design at 63 components (1,953 pairs), the sweep came back
complete and passing, **12 of 12 joints at 5° steps**, with no runtime
budget row anywhere in the turn. Attempt 5 needed 80° steps and still
stopped at 10 of 12. The agent then added 24 M2×8 screws on the servo
tabs, which took the design to 87 components and 3,741 pairs. The sweep
refuses any request whose baseline has more than `_SWEEP_MAX_PAIRS`
(2,000) pairs, before it measures anything, so every joint came back
`pair budget exceeded`. The agent saw this, put the screws behind a
`fasteners` parameter, checked the sweep with `fasteners=0`, and
published `fasteners=1` as the default. It said so in its reply: the
default build's motion check is incomplete. A bar that counts the
accepted revision cannot take the `fasteners=0` sweep in its place.

**Diagnosis: the pair budget counts pairs the sweep never moves.** The
check is `len(baseline) > _SWEEP_MAX_PAIRS`, and the baseline is every
pair in the assembly. A rigid pair's row is copied from the solved pose
unchanged, and only the pairs with one side in the joint's moving
subtree are measured. From the component names, a hip moves at most
10 of the 87 components (horn, coxa, cap, knee servo and its two screws,
knee horn, leg, knee cap, foot), so at most 10 × 77 = 770 moving pairs;
a knee moves about 4, so about 332. Both are well under 2,000. **This
is read from the names and the code, not measured**: the next unit
measures each joint's moving-pair count on the accepted request before
changing anything. The budget stays at 2,000. The candidate fix is to
count what the sweep measures, not to raise the number.

**A second finding: feet on the floor fail the static fit.** Each ball
foot rests exactly on `c_floor` (0.0 mm, no common volume), and the
static pass reports it as `below clearance`. The swept fit already
treats contacts against the fit's world geometry as advisory (ADR-420).
The static pass only does so for the floor's own row. Earlier designs
stood clear of the floor, so this is the first time it shows.

**Decided afterwards (ADR-427), with the accepted project unchanged.** The
feet rest on the floor and do not sink into it: 0.0 mm³ common volume on
all six. The static block now reports a `below clearance` row against world
geometry as `world_geometry_contacts`, never as failing; an intersection
with world geometry still fails. A fresh `/tmp` rebuild of revision
`3cb2b1d0` on the ADR-426 and ADR-427 source reads 1 failing static row
(the floor's own advisory row), 6 world-geometry contacts and a complete,
passing sweep of 12 joints. Attempt 6's published verdict stays a miss:
the bar counts the turn as it ran.

**Against attempt 5.** The total fell from 16 to 15. T3 fell from 3 to
2: the judges read the hip rings and the knee disc caps as two
different treatments, with bare shaft stubs beside the knees. T4 held
at 2 on the median (one call gave 1): a generously rounded body, but
legs of nearly constant section and servo pods that are filleted
boxes. T5 held at 2 (a graphite visor band on the +X nose, no focal
face), and so did T7: each call named a high camera and a faint contact
shadow. Those are properties of the renderer, the same for every design,
and are a renderer unit of their own, next to attempt 4's open hero-camera
concern.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 8 refused calls, none of them a CPU-limit refusal:
- 2 sandbox refusals (`type` and `dir` are not defined);
- 2 guessed JSON pointers (`/facts/bounding_box`);
- 2 refusals to retire an output that a component still linked;
- 1 worker crash on a fillet over a fused coxa, which the agent routed
  around by filleting each primitive before the union;
- 1 `edit_script` replacement whose text did not occur.

The agent again said the build reply was too large to read, the third
time in the run, and read the fit report pair by pair.

## A5 attempt 7: the hexapod (`ot10-hexapod-7`)

**Misses the bar on one count: the judged total is 13 of 21, under the
frozen 14.** Every measured item passes. Under ADR-426 and ADR-427 this is
the first hexapod whose accepted revision has both a clean static fit and a
complete, passing sweep. This is the frozen hexapod prompt, word for word,
read from `contract.json` `a5.prompts.hexapod`. It ran once on the new
project `ot10-hexapod-7`, with no continuation, the same argv,
`claude-opus-5-5` and `CADEX_EFFORT=medium`. It started at
2026-09-28T09:36:19Z at revision `cafd3960`, which is after ADR-426 and
ADR-427, on the dev-tree engine. The turn ended on its own at 10:06:56Z
(31 min) with `ok: true`, at accepted revision `f0a77bfb1936…` (digest
`839d779f4627…`). It was rendered and judged from a `/tmp` copy of the
project; the project itself is unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 6, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |
| attempt 7, call 1 | 1 | 3 | 1 | 1 | 2 | 2 | 2 | 12 |
| attempt 7, call 2 | 2 | 3 | 1 | 1 | 2 | 2 | 2 | 13 |
| attempt 7, call 3 | 2 | 3 | 2 | 1 | 2 | 3 | 2 | 15 |
| attempt 7, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |

Every raw reply is kept in
[`ot10-hexapod-7-score.json`](ot10-hexapod-7-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **13** | **no** |
| no trait 0 | lowest is 1 | yes |
| above hex3 (2) | 13 | yes |
| P1 ≤ 0.20 | **0.033** (5,125 of 157,257 subsamples) | yes |
| P2 ≤ 0.25 | **0.247** (5,654 of 22,870 mm, 28 printed components; `c_ground` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2E3136`, `#ECE7DC`, `#FF7A1A`) | yes |
| static fit | 1,653 pairs: 1,647 clear, 0 intersections, 0 below clearance. One failing row, the floor's own advisory world-geometry row. Six ball feet rest on `c_ground` at 0.0 mm with 0.0 mm³, reported as world-geometry contacts (ADR-427) | yes |
| swept fit | **complete and passing, 12 of 12 joints** at 17.5° steps. The busiest hip moves 357 of 1,653 pairs (ADR-426). Six knee-into-ground rows are advisory (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with cross horns | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-7-hero.png),
[`iso`](ot10-hexapod-7-look_iso.png),
[`iso_back`](ot10-hexapod-7-look_iso_back.png),
[`front`](ot10-hexapod-7-look_front.png),
[`right`](ot10-hexapod-7-look_right.png) and
[`top`](ot10-hexapod-7-look_top.png).
`cadex render` took 6 min 55 s for the whole command: 202.7 s acquiring
the tessellation (a full engine rebuild, reported separately under A2) and
8.2 s drawing, at 152,601 drawn triangles. This machine was also running
both test suites for part of that time.

**Diagnosis: T3 and T4 fell to 1, and the turn spent its budget before it
refined.** All three calls named the same two things:
- **T4, form.** The legs are "flat, bent, constant-section bars", and the
  graphite boxes at each leg read as "sharp-edged servo boxes". The
  agent's `leg_thick` is one 4.0 mm parameter from hip to foot, so the
  legs taper only in plan. The overlay's TAPER TO A FOOT asks for about
  60% of the hip section near the foot.
- **T3, joints.** The orange knee discs "read as plain servo horns", and
  the hip yaw axes are "bare dark shafts under the body". One cap design
  does not serve every axis.

**What the judges read as servo cases is mostly printed cradle.** P1
counts only 3.3% of the hero silhouette as purchased hardware. The dark
boxes cover much more than that in the hero. The agent's DECISION line
puts each knee servo "in a cradle on the coxa", and the cradle (`c_cx_*`)
is a `mechanism`-role box that follows the servo's case and has
`fillet_r` = 1.5 mm. So a printed box the colour of the servo, shaped
like the servo, reads as an exposed servo. P1 cannot see this; T1 and T4
can.

**The build budget crowded out refinement.** The turn had one CPU-limit
refusal: its first full build ran past 300 CPU-seconds. Its own notes
say:
- "Filleting the lofted floor and deck edges was dropped when the first
  full build ran out of CPU time";
- "the full build at a 10° step ran past the 300 CPU-second limit", so
  the sweep step is 17.5°.

It then called `look` twice (hero, iso and right, then one leg in
focus). It accepted after 8 `write_script`, 6 `edit_script` and 52
`inspect` calls. Attempt 5 reached 16 in 85 minutes; this turn ended in
31. **The sweep's share of the accepted build's CPU is inferred from the
agent's words, not measured.** The next unit measures it on a `/tmp`
copy of `f0a77bfb` before any overlay or budget change.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 9 refused calls:
- 1 CPU-limit refusal (above);
- 3 guessed JSON pointers (`/facts/bounding_box` twice, `/facts`);
- 1 sandbox refusal (`dir` is not defined) and 1 source-policy refusal
  (an import);
- 1 `loft_cage` call given the whole cage spec rather than one named
  cage;
- 1 task refusal: a 3° reset tilt drove the wide stance 7.17 mm into the
  floor, so the agent narrowed it to 0–2°;
- 1 `edit_script` replacement whose text did not occur.

**Against the quadruped.** `ot10-quadruped-3` met the bar before ADR-426
and ADR-427. Both decisions only turn refusals and failures into
measurements or advisories, and that design's sweep was already complete
and its static fit already clean. So its verdict stands and it is not
rerun.

## A5 attempt 8: the hexapod (`ot10-hexapod-8`)

**Misses the bar on four counts: the judged total is 8 of 21, T5 is 0,
the swept fit is incomplete, and the design carries no electronics.** The
turn did not finish a design. Its accepted revision is a leg probe, and
the agent says so itself. This is the frozen hexapod prompt, word for
word, from `contract.json` `a5.prompts.hexapod`. It ran once on the new
project `ot10-hexapod-8`, with no continuation, the same argv,
`claude-opus-5-5` and `CADEX_EFFORT=medium`. It started at
2026-09-28T11:02:54Z at revision `070a8c23`, which is after ADR-428, on
the dev-tree engine. So it measures ADR-428's overlay change alone. The
turn ended on its own at 11:36:59Z (34 min), exit 0 with `ok: true`, at
accepted revision `b69465f94e40…` (digest `3e3927796084…`). It was
rendered and judged from a `/tmp` copy of the project; the project itself
is unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 7, median | 2 | 3 | 1 | 1 | 2 | 2 | 2 | **13** |
| attempt 8, call 1 | 1 | 1 | 2 | 1 | 0 | 1 | 2 | 8 |
| attempt 8, call 2 | 1 | 1 | 2 | 1 | 0 | 1 | 2 | 8 |
| attempt 8, call 3 | 1 | 1 | 2 | 1 | 0 | 2 | 2 | 9 |
| attempt 8, median | 1 | 1 | 2 | 1 | 0 | 1 | 2 | **8** |

Every raw reply is kept in
[`ot10-hexapod-8-score.json`](ot10-hexapod-8-score.json), under the same
rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **8** | **no** |
| no trait 0 | **T5 is 0** | **no** |
| above hex3 (2) | 8 | yes |
| P1 ≤ 0.20 | 0.020 | yes |
| P2 ≤ 0.25 | 0.097 | yes |
| P3 2 or 3 | 2 (`#2F3237`, `#E9E6DF`); only `c_tub` declares a role, and everything else is drawn by supplier | yes |
| static fit | 946 pairs: 940 clear, 0 intersections, 0 below clearance. One failing row, the floor's advisory world-geometry row; six world-geometry contacts. 30 welded pairs touching | yes |
| swept fit | **incomplete: 12 of 12 joints unswept** (`sweep_step_degrees` not declared) | **no** |
| electronics | **none**: 12 × MG90S with single-arm horns, a plain box for a body, no board, IMU, regulator or battery. No MJCF and no training task | **no** |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-8-hero.png),
[`iso`](ot10-hexapod-8-look_iso.png),
[`iso_back`](ot10-hexapod-8-look_iso_back.png),
[`front`](ot10-hexapod-8-look_front.png),
[`right`](ot10-hexapod-8-look_right.png) and
[`top`](ot10-hexapod-8-look_top.png).
`cadex render` took 1 min 13 s for the whole command: 38.2 s acquiring
the tessellation and 8.5 s drawing, at 172,659 drawn triangles.

**Diagnosis: the design did not fail on looks. The live document wedged,
and no later write could publish.** In order, from the transcript:
1. The first two full builds (a superellipse B-spline hood and pan,
   about 76 components) each ran past the 300 CPU-second limit.
2. The agent bisected the cost with smaller probes. A two-leg probe and
   then a six-leg probe (940 pairs clear) both passed, with a box for a
   body, and the six-leg probe was accepted under the assembly output
   name `probe`.
3. The third full build also ran past the CPU limit. After that, every
   write was refused with `PUBLICATION_UNTAGGED_OBJECT: ['Joints']`, then
   `['Joints', 'Joints001']`, even a one-box script. Two attempts to
   retire outputs (`tray`, `tub`) were refused because "foreign document
   objects still reference" them.
4. With no tool to reset the live document, the agent stopped and
   reported what went wrong.

The agent says that renaming or retiring an assembly output orphans its
`Joints` group. That is its claim, not yet a measurement. What the source
does show is this: publication creates an `Assembly::JointGroup` named
`Joints` under each assembly (`CadexScriptedDomainPublication.py`), and
the ownership check refuses any untagged object left in the document. **So
a document state that no script can publish past is a product defect. The
next unit reproduces it with a regression test before any overlay or
prompt change.** It is not a design verdict, and the looks were never
reached.

**What the renders show of ADR-428.** The legs are curved and
round-sectioned and narrow towards a ball foot in the side view, which is
what the TAPER TO A FOOT change asked for. The judge still scores T4 1,
for a flat plate body and boxy covers. That is the probe's box body, not
a finished shell. T5 is 0 because the probe has no face. None of this
measures ADR-428 fairly, because the design the agent intended (a pillow
hood, a visor face, orange foot tips) was never published.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 20 refused calls, out of 19 `write_script`, 3
`edit_script`, 2 `rebuild`, 37 `inspect`, 4 `describe_api` and 1 `look`:
- 3 CPU-limit refusals;
- 7 refusals after the wedge: 4 `PUBLICATION_UNTAGGED_OBJECT` and 3
  retirement refusals;
- 4 sandbox or source-policy refusals (`dir` and `hasattr` are not
  defined; an import; a private attribute);
- 2 `api.fuse` refusals (a missing `output_type`; a solid declared where
  OpenCascade made a 3-solid compound);
- 2 `edit_script` replacements whose text occurred 0 and 102 times;
- 1 guessed JSON pointer (`/revision`);
- 1 `inspect` refusal (`attach=true` outside image scope).

## A5 attempt 10: the hexapod (`ot10-hexapod-10`)

**Meets the bar on every item, the first hexapod in the run to do so.**
The judged total is 14 of 21, which meets the frozen 14, and no trait
scores 0. P1, P2 and P3 are within their bars. The static fit is clean,
the swept fit is complete and passing on all 12 joints, and the design
carries its electronics. This is the frozen hexapod prompt, word for
word, read from `contract.json` `a5.prompts.hexapod`. It ran once on the
new project `ot10-hexapod-10`, with no continuation, the same argv,
`claude-opus-5-5` and `CADEX_EFFORT=medium`. It started at
2026-09-28T12:25:51Z at revision `9f13d33d`, which is after ADR-429, on
the dev-tree engine. The turn ended on its own at 13:09:33Z (44 min), exit
0 with `ok: true`, at accepted revision `e8a82deb1a06…` (digest
`1e0f233588da…`). It was rendered and judged from a `/tmp` copy of the
project; the project itself is unchanged.

**Attempt 9 is not counted.** The same prompt started on `ot10-hexapod-9`
at 12:13:49Z. Its process was killed at about 12:17Z, four minutes in, when
the loop session that launched it ended. It had no exit status and never
wrote an accepted revision. That is a harness interruption, not a design
attempt. The project is kept read-only as the receipt, and it is neither
scored nor reused.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 8, median | 1 | 1 | 2 | 1 | 0 | 1 | 2 | **8** |
| attempt 10, call 1 | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 14 |
| attempt 10, call 2 | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 14 |
| attempt 10, call 3 | 2 | 2 | 1 | 2 | 2 | 3 | 2 | 14 |
| attempt 10, median | 2 | 2 | 1 | 2 | 2 | 3 | 2 | **14** |

Every raw reply is kept in
[`ot10-hexapod-10-score.json`](ot10-hexapod-10-score.json), under the
same rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **14** | yes |
| no trait 0 | lowest is 1 (T3) | yes |
| above hex3 (2) | 14 | yes |
| P1 ≤ 0.20 | **0.0026** (602 of 229,169 subsamples) | yes |
| P2 ≤ 0.25 | **0.1415** (4,842 of 34,217 mm, 22 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2A2C30`, `#E9E4D8`, `#F26B1D`), every component's role declared | yes |
| static fit | 1,326 pairs: 1,320 clear, 0 intersections, 0 below clearance. One failing row, the floor's advisory world-geometry row. Six ball feet rest on `c_floor` as world-geometry contacts (ADR-427). 38 fixed-joint pairs checked, none reported | yes |
| swept fit | **complete and passing, 12 of 12 joints** at 10° steps, 0 failing pairs. Twelve leg-into-floor rows are advisory (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with cross horns. MJCF and a walking task were accepted in the same turn | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-10-hero.png),
[`iso`](ot10-hexapod-10-look_iso.png),
[`iso_back`](ot10-hexapod-10-look_iso_back.png),
[`front`](ot10-hexapod-10-look_front.png),
[`right`](ot10-hexapod-10-look_right.png) and
[`top`](ot10-hexapod-10-look_top.png).
`cadex render` took 3 min 47 s for the whole command. Acquiring the
tessellation took 108.7 s, and drawing took 9.0 s (2.7 s for the 1024 px
hero), at 162,427 drawn triangles.

**What the renders show.** A pillow-topped tub with a dark visor across
its front stands on six curved legs that taper to orange ball feet. The
judge's weakest trait is T3, at 1 in all three calls: the knees have
round caps, but the hip axes show as bare dark pins, and the hip servo
covers are shell-coloured boxes that hang under the body (T1 and T4 name
them too). T5 is 2, because the visor gives the robot a front but is a
generic slot. That is where the next hexapod gains would come from.

**How the turn got there.** The agent's own notes name the change that
made it fit the CPU budget. A superellipse `loft_cage` body with a
`part.offset` inner wall ran past the 300 CPU-second limit at the fit
stage. So did an inner loft once the electronics were added. It replaced
both with filleted-box primitives, which is the ADR-428 advice. ADR-429's
fix was not visibly exercised: no `PUBLICATION_UNTAGGED_OBJECT` refusal
appears.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 15 refused calls, out of 12 `write_script`, 13
`edit_script`, 1 `rebuild`, 51 `inspect`, 4 `describe_api` and 3 `look`:
- 6 CPU-limit refusals;
- 3 sandbox or source-policy refusals (`dir` and `hasattr` are not
  defined; an import);
- 3 guessed JSON pointers (`/facts/bounding_box`, `/clearance/failing`,
  `/facts`);
- 1 `api.fuse` refusal (a solid declared where OpenCascade made a
  6-solid compound);
- 1 `api.cut` refusal (refining the result produced an invalid shape);
- 1 `edit_script` replacement whose text occurred 0 times.

## A5 confirmation round, pre-registered

Registered on 2026-09-28 before any of its turns started, at revision
`96ed90d0`. It is the next step after `REPORT.md` found A5 not met by its
letter.

- **One turn per body plan.** Each runs once, on the frozen prompt from
  `contract.json` `a5.prompts`, with the frozen argv above:
  `claude-opus-5-5`, `CADEX_EFFORT=medium` and no continuation. Each runs
  on a new project: `ot10-hexapod-11`, then `ot10-quadruped-4`, then
  `ot10-biped-2`.
- **The hexapod goes first**, because it is the weakest plan. It passed
  only on its ninth counted turn.
- **Every earlier turn still counts.** The twelve counted turns and their
  verdicts above stay published and unchanged. This round adds to them. It
  does not replace them, and it does not redefine A5.
- **Scoring is unchanged.** Each design is scored blind with
  `runner/judge.py` under the frozen rubric, proxies and bar. It is
  rendered and judged from a `/tmp` copy of the project, as attempt 10 was.
- **A miss is diagnosed before anything changes.** No prompt, overlay or
  tool change happens between turns until that miss is diagnosed and
  recorded.
- **A harness kill is not an attempt.** A turn killed before it has an exit
  status is kept read-only as the receipt, as attempt 9 was, and the plan
  gets a new project.

## A5 attempt 11: the hexapod (`ot10-hexapod-11`), confirmation round

**Meets the bar on every item. This is the confirmation round's first turn,
and the second hexapod in a row to meet the bar.** The judged total is 14 of
21, which meets the frozen 14, and no trait scores 0. P1, P2 and P3 are
within their bars. The static fit is clean, and the swept fit is complete
and passing on all 12 joints. The design carries its electronics. It ran
exactly as pre-registered above. The frozen hexapod prompt was read from
`contract.json` `a5.prompts.hexapod`. It ran once on the new project
`ot10-hexapod-11`, with no continuation, `claude-opus-5-5` and
`CADEX_EFFORT=medium`. It was launched detached (`setsid`) at
2026-09-28T18:20:23Z at revision `4288ef42`, on the dev-tree engine. No
product code changed between `96ed90d0` and that revision. The turn ended
on its own at 19:01:35Z (41 min), exit 0 with `ok: true`, at accepted
revision `42cbfa0dc717…` (digest `cc0e06aa9e55…`). It was rendered and
judged from a `/tmp` copy of the project, so the project itself is
unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| attempt 10, median | 2 | 2 | 1 | 2 | 2 | 3 | 2 | **14** |
| attempt 11, call 1 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 |
| attempt 11, call 2 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 |
| attempt 11, call 3 | 2 | 3 | 1 | 2 | 2 | 2 | 2 | 14 |
| attempt 11, median | 2 | 3 | 1 | 2 | 2 | 2 | 2 | **14** |

Every raw reply is kept in
[`ot10-hexapod-11-score.json`](ot10-hexapod-11-score.json), under the
same rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **14** | yes |
| no trait 0 | lowest is 1 (T3) | yes |
| above hex3 (2) | 14 | yes |
| P1 ≤ 0.20 | **0.0186** (3,685 of 197,646 subsamples) | yes |
| P2 ≤ 0.25 | **0.2285** (4,621 of 20,221 mm, 22 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2B2D31`, `#E9E6DF`, `#F26A1B`), every component's role declared | yes |
| static fit | 2,850 pairs: 2,850 clear, 0 intersections, 0 below clearance. One failing row, the floor's advisory world-geometry row. The agent declared the six foot–floor pairs as contacts. 62 fixed-joint pairs checked, all touching | yes |
| swept fit | **complete and passing, 12 of 12 joints** at 7° steps, 0 failing pairs. Twelve leg-into-floor rows are advisory (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 12 × MG90S with single-arm horns, 24 M2 screws. MJCF and a walking task were accepted in the same turn | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-hexapod-11-hero.png),
[`iso`](ot10-hexapod-11-look_iso.png),
[`iso_back`](ot10-hexapod-11-look_iso_back.png),
[`front`](ot10-hexapod-11-look_front.png),
[`right`](ot10-hexapod-11-look_right.png) and
[`top`](ot10-hexapod-11-look_top.png). The same `cadex render` wrote its
concept sheet, [`ot10-hexapod-11-sheet.png`](ot10-hexapod-11-sheet.png)
(215 KB): 0.618 kg, 12 servos, 227 × 231 × 116 mm. The whole command took
9 min 11 s of wall time. Acquiring the tessellation took 252.3 s, and
drawing took 11.1 s (2.9 s for the 1024 px hero), at 231,185 drawn
triangles.

**What the renders show.** A low, bone-coloured pillow dome sits on a
dark base ring, with a dark visor band wrapping its +X corner. Six curved
tubular legs hang from knee pods under the rim and end in orange ball
feet. It is the same family as attempt 10, and it scores the same total by
a different route. T2 rises to 3, because the orange is only on the feet.
T6 falls to 2, because the legs are uniform tubes splayed from a wide, flat
body. T3 is again the weakest trait, at 1 in all three calls. The
single-arm horns, screw stubs and brackets show dark at the hips, and only
some axes are capped. So the two hexapods that met the bar both sit
exactly on it. Both are held back by the same joint treatment.

**How the turn got there.** The agent's notes name its concept first: a
turtle dome over a graphite tray, a visor as the face and orange feet. It
chose a dome over a flat plate so that the shell hides all 12 servos and
the electronics. No write ran past the CPU limit, where attempt 10 met it
six times. Three `edit_script` calls failed with `DOMAIN_WORKER_NO_RESULT`.
The agent attributed them to OCCT's fillet kernel crashing on 0.7–0.8 mm
fillets over every edge after the boolean cuts. It records the stack as
`ChFi3d PerformThreeCorner`. The crash is recorded here as a defect: the
worker died, and the refusal did not name the operation. The agent reached
an accepted revision by filleting before the cuts. Its own report says it
read 1,000 of the 2,850 static pairs, not all of them. The published fit
above is the engine's measurement of all 2,850, not the agent's reading.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 12 refused calls, out of 11 `write_script`, 5
`edit_script`, 70 `inspect`, 4 `describe_api` and 2 `look`:
- 3 worker crashes (`DOMAIN_WORKER_NO_RESULT`, above);
- 2 sandbox or source-policy refusals (`hasattr`; an import);
- 2 guessed JSON pointers (`/facts/bounding_box`, twice);
- 2 kernel refusals (a fillet radius refused on 4 of 21 edges; a refined
  fuse produced an invalid shape);
- 1 `api.loft` refusal (sections given as edges, not wires);
- 1 `assembly.component` source given as a reference, not a value;
- 1 reset-variation refusal that named the 3.08 mm lift.

**Next, as pre-registered:** `ot10-quadruped-4`, on the frozen quadruped
prompt, with nothing changed.

## A5 attempt 4: the quadruped (`ot10-quadruped-4`), confirmation round

**Meets the bar on every item. This is the confirmation round's second
turn.** The judged total is 16 of 21, the highest of any counted design,
and no trait scores 0. P1, P2 and P3 are within their bars. The static fit
is clean, and the swept fit is complete and passing on all 8 joints. The
design carries its electronics. It ran exactly as pre-registered. The
frozen quadruped prompt was read from `contract.json` `a5.prompts.quadruped`.
It ran once on the new project `ot10-quadruped-4`, with no continuation,
`claude-opus-5-5` and `CADEX_EFFORT=medium`. It was launched detached
(`setsid`) at 2026-09-28T19:25:47Z at revision `c2ee7399`, on the dev-tree
engine. No product code changed between `4288ef42` and that revision. The
turn ended on its own at 19:46:22Z (21 min), exit 0 with `ok: true`, at
accepted revision `0a49c1fdb3fa…` (digest `4357bdf75659…`). It was rendered
and judged from a `/tmp` copy of the project, so the project itself is
unchanged. The loop session that launched it ended before the turn did.
The turn was not killed: it kept running, and the next session found it
live and waited for its exit status.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| quadruped attempt 3, median | 2 | 3 | 2 | 2 | 2 | 2 | 2 | **15** |
| quadruped attempt 4, call 1 | 2 | 3 | 3 | 1 | 2 | 3 | 2 | 16 |
| quadruped attempt 4, call 2 | 2 | 3 | 3 | 1 | 2 | 3 | 2 | 16 |
| quadruped attempt 4, call 3 | 2 | 3 | 3 | 1 | 2 | 2 | 2 | 15 |
| quadruped attempt 4, median | 2 | 3 | 3 | 1 | 2 | 3 | 2 | **16** |

Every raw reply is kept in
[`ot10-quadruped-4-score.json`](ot10-quadruped-4-score.json), under the
same rule as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **16** | yes |
| no trait 0 | lowest is 1 (T4) | yes |
| above hex3 (2) | 16 | yes |
| P1 ≤ 0.20 | **0.0022** (591 of 263,991 subsamples) | yes |
| P2 ≤ 0.25 | **0.1624** (3,057 of 18,824 mm, 23 printed components; `c_floor` left out under ADR-424) | yes |
| P3 2 or 3 | **3** (`#2F3237`, `#E9E6DF`, `#F26A1B`), every component's role declared | yes |
| static fit | 990 pairs: 986 clear, 0 intersections, 0 below clearance, 4 declared foot–floor contacts. One failing row, the floor's advisory world-geometry row. 35 fixed-joint pairs checked, all touching | yes |
| swept fit | **complete and passing, 8 of 8 joints** at 10° steps, 0 failing pairs. Eight leg-into-floor rows are advisory (ADR-420) | yes |
| electronics | ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 8 × MG90S with single-arm horns. MJCF and a walking task were accepted in the same turn | yes |

The candidate set, in the order the judge saw it:
[`hero`](ot10-quadruped-4-hero.png),
[`iso`](ot10-quadruped-4-look_iso.png),
[`iso_back`](ot10-quadruped-4-look_iso_back.png),
[`front`](ot10-quadruped-4-look_front.png),
[`right`](ot10-quadruped-4-look_right.png) and
[`top`](ot10-quadruped-4-look_top.png). The same `cadex render` wrote its
concept sheet, [`ot10-quadruped-4-sheet.png`](ot10-quadruped-4-sheet.png)
(192 KB): 0.37 kg, 8 servos, 197 × 106 × 116 mm. The whole command took
1 min 10 s of wall time. Acquiring the tessellation took 30.3 s, and
drawing took 7.4 s (2.5 s for the 1024 px hero), at 106,937 drawn
triangles.

**What the renders show.** An off-white rounded-box body stands on four
flat leg plates that taper to dark ball feet. A dark rectangular visor is
on its front end, and the same orange cap sits on every hip and knee axis,
each in a rounded lobe of its plate. T3 is 3 in all three calls. That is
the first 3 on joints of any counted design, and it is the trait both
counted hexapods scored 1 on. T4 is the weakest, at 1 in all three calls.
The body is a filleted box, the legs are constant-thickness plates, and
the front hip blocks sit as separate boxes. T5 stays at 2, because the
visor gives a front but little character.

**How the turn got there.** The agent's notes name its concept first: a
compact robot dog with a visor face, orange joint caps and dark feet. It
took a `look` before auditing the pairs. It found the feet 2 mm into the
floor, because its height formula left out the foot offset, and fixed
that. It declared the servo–horn spline seats as contacts and raised the
reset lift to pay for the tilt. It records one rejected option: open
knee-servo pockets were closed with a 1.8 mm wall because the servo case
showed from below. So the housing needs a split for assembly. No write ran
past the CPU limit, and no worker crashed.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 6 refused calls, out of 6 `write_script`, 7 `edit_script`,
45 `inspect`, 4 `describe_api`, 1 `rebuild` and 2 `look`:
- 1 sandbox refusal (`type` is not defined);
- 2 guessed JSON pointers (`/facts/bounding_box`, twice);
- 1 kernel refusal (a fillet radius refused on 4 of 12 edges);
- 1 `edit_script` replacement whose text occurred 0 times;
- 1 reset-variation refusal that named the 2.63 mm lift.

**Next, as pre-registered:** `ot10-biped-2`, on the frozen biped prompt,
with nothing changed.

## A5 attempt 2: the biped (`ot10-biped-2`), confirmation round

**Misses the bar on every item it could be measured on. This is the
confirmation round's third and last turn.** The turn did not publish a
design. Its accepted revision is the agent's servo-orientation probe:
four MG90S servos in four orientations, overlapping about one shaft, and
one horn, with no assembly. The agent says so
itself. It ran exactly as pre-registered. The frozen biped prompt was read
from `contract.json` `a5.prompts.biped`. It ran once on the new project
`ot10-biped-2`, with no continuation, `claude-opus-5-5` and
`CADEX_EFFORT=medium`. It was launched detached (`setsid`) at
2026-09-28T20:13:42Z at revision `15f2bf9e`, on the dev-tree engine. No
product code changed between `c2ee7399` and that revision, only probe docs
and tests. The turn ended
on its own at 20:32:22Z (19 min), exit 0 with `ok: true`, at accepted
revision `6447da4ae63e…` (digest `2a6fb6856355…`). It was rendered and
judged from a `/tmp` copy of the project, so the project itself is
unchanged.

| trait | T1 | T2 | T3 | T4 | T5 | T6 | T7 | **total** |
|---|---|---|---|---|---|---|---|---|
| hex3 baseline | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |
| biped attempt 1, median | 2 | 3 | 3 | 1 | 2 | 2 | 2 | **15** |
| biped attempt 2, call 1 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 2 |
| biped attempt 2, call 2 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 3 |
| biped attempt 2, call 3 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| biped attempt 2, median | 0 | 1 | 0 | 0 | 0 | 0 | 1 | **2** |

Every raw reply is kept in
[`ot10-biped-2-score.json`](ot10-biped-2-score.json), under the same rule
as before: no product prompt may quote it.

| bar item | measured | meets |
|---|---|---|
| judged total ≥ 14 | **2** | **no** |
| no trait 0 | **T1, T3, T4, T5 and T6 are 0** | **no** |
| above hex3 (2) | **2, equal to hex3** | **no** |
| P1 ≤ 0.20 | **unmeasured**: the probe publishes no inventory, so purchased and printed cannot be told apart | **no** |
| P2 ≤ 0.25 | **unmeasured**, for the same reason | **no** |
| P3 2 or 3 | **4** (`#5B9DCD`, `#73B687`, `#B486C8`, `#E6974C`): no role is declared, so each object takes an index colour | **no** |
| static fit | **unavailable**: the probe places no assembly component, so no pair was measured | **no** |
| swept fit | **unavailable**: no published sweep | **no** |
| electronics | **none published**: the accepted revision is four servos and a horn. No MJCF and no training task | **no** |

The candidate set, in the order the judge saw it:
[`hero`](ot10-biped-2-hero.png),
[`iso`](ot10-biped-2-look_iso.png),
[`iso_back`](ot10-biped-2-look_iso_back.png),
[`front`](ot10-biped-2-look_front.png),
[`right`](ot10-biped-2-look_right.png) and
[`top`](ot10-biped-2-look_top.png). The same `cadex render` wrote its
concept sheet, [`ot10-biped-2-sheet.png`](ot10-biped-2-sheet.png) (81 KB),
which leaves mass and servo count blank because the revision has no
dynamics model and no inventory. The whole command took 6 s of wall time,
at 13,390 drawn triangles.

**Diagnosis: the design did not fail on looks. A refused publish left its
half-built assembly in the live document, and no later write could
publish.** In order, from the transcript:
1. The agent read the catalog specs and accepted a probe of four servos to
   learn the placement convention. It named its concept before building:
   a rounded torso split at a hood seam, a dark flush visor on the front,
   bone shell over graphite mechanism, legs in printed cradles with shell
   covers.
2. Its first full build was refused at the task stage: the reset
   variation drove the feet 4.6 mm into the floor. That refusal comes
   from the worker and left the document as accepted.
3. The corrected build passed geometry, assembly, MJCF export and the
   task's reset check. It then stored each servo's actuator as a result
   output (`result["act_…"] = sv.actuator(...)`). The assembly pass had
   already created its components, links and `Joints` group when
   `_native_type` raised `No native publisher exists for output type
   'actuator'`. The refusal said `accepted_live_state_preserved: true`.
4. That was false. Every later write, including an unchanged rebuild of
   the accepted probe, was refused with `PUBLICATION_UNTAGGED_OBJECT`
   naming 43 leftover objects (`VibeAssembly_project_c_*`, `j_*`,
   `Joints`, `Origin001`, …), or with `Cannot retire XScript output
   'floor'` because a leftover link still pointed at it. With no tool to
   reset the live document, the agent stopped and reported the cause.

**Measured, not inferred.** The document the daemon publishes into
(`cadexd.py`, `App.newDocument("CadexdEphemeral")`) runs with `UndoMode
0`. Under `FreeCADCmd`, a document opened that way, given
`openTransaction`, `addObject` and `abortTransaction`, still holds the
added object afterwards. So every `abortTransaction` in
`CadexScriptedDomainPublication.py` restores nothing, and any publish that
raises after it has created an object leaks that object. ADR-429 recorded
this as a known gap ("`accepted_live_state_preserved: true` in a refusal
is not guaranteed while `UndoMode` is 0"), and recorded the retire-linked
refusal as "found, not fixed". `ot10-hexapod-8` wedged through the rename
path, which ADR-429 closed; this turn wedged through the general path it
left open. A second, smaller cause sits upstream: validation accepted an
output of a type that no publisher can write, so the refusal came only
after the assembly pass had started.

**So the miss is a product defect, not a design verdict.** It is still a
counted miss: the turn has an exit status and the pre-registration counts
every turn. The next unit reproduces the leak with a regression test
before any overlay or prompt change, as the round requires.

**A4's refusal classes in this transcript: none of the four recurred.**
The turn had 7 refused calls, out of 7 `write_script`, 1 `rebuild`, 24
`inspect`, 4 `describe_api` and no `look`:
- 3 refusals from the leak: 2 `PUBLICATION_UNTAGGED_OBJECT` and 1
  retirement refusal;
- 1 publication refusal (`No native publisher exists for output type
  'actuator'`), the one that caused the leak;
- 1 reset-variation refusal that named the 4.6 mm lift;
- 1 guessed JSON pointer (`/revision`);
- 1 call to a tool name that does not exist (`inspect`, without its MCP
  prefix).

**The confirmation round is complete: 2 of its 3 turns meet the bar.**
`ot10-hexapod-11` scored 14 and `ot10-quadruped-4` 16. `ot10-biped-2`
misses, on a publication defect.

## A5 biped turn 3, pre-registered

Registered on 2026-09-28 before the turn started, at revision `d1ce5b1f`.
It follows the fix for the defect that ended `ot10-biped-2` (ADR-434: a
refused project publish rolls back, and an argument value such as an
actuator in `result` is refused at validation with the fix named).

- **One turn, once.** It runs on the new project `ot10-biped-3`, on the
  frozen prompt from `contract.json` `a5.prompts.biped`, with the frozen
  argv above: `claude-opus-5-5`, `CADEX_EFFORT=medium` and no
  continuation. It runs on the ADR-434 engine; the installed
  `build/release/Mod/cadex` was compared file by file with
  `src/Mod/cadex` before launch and is identical.
- **Nothing is re-scored.** The confirmation round's result stands at 2 of
  3, and the ten failed attempts stand as published misses. This turn adds
  a counted attempt. It does not replace `ot10-biped-2`, and it does not
  redefine A5.
- **Scoring is unchanged.** The design is rendered and scored blind with
  `runner/judge.py` from a `/tmp` copy of the project, under the frozen
  rubric, proxies, bar and judging procedure.
- **A miss is diagnosed before anything changes.** No prompt, overlay or
  tool change follows a miss until it is diagnosed and recorded.
- **A harness kill is not an attempt.** A turn killed before it has an exit
  status is kept read-only as the receipt, and the plan gets a new project.

## A4: the refusal census, every ot10 transcript

**None of A4's four refusal classes recurred in any ot10 product-agent
transcript: 0 of 208 refused calls across 17 transcripts.** That covers the
five counted A5 designs, the ten failed attempts, and the two aborted
turns that were not attempts. The count is mechanical.
[`runner/refusals.py`](runner/refusals.py) reads each session transcript
(local to this machine, never committed), takes every tool result marked
`is_error`, and gives it one class. The class comes from the engine's own
refusal sentence or `failure_code`, in the hex2/hex3 wording and the
ADR-416 wording alike. It is not a keyword guess. The notes-directory
counter this replaces matched `horn|style`. That counted an output named
`horn` as a horn-style refusal on hexapod attempt 2, and this classifier
does not.
[`refusals.json`](refusals.json) keeps each transcript's sha256, its counts
and every refusal's tool, `failure_code` and first 200 characters of error.
`cli/tests/test_ot10_contract.py` pins the counts below, re-derives them
from that file, and holds this table equal to it. It also feeds the
classifier the real hex2/hex3 refusal texts, and the texts the engine
emits today, for all four classes.

| project | status | horn style | edit before script | output count | joint listing | refused | CPU limit | sandbox | kernel | JSON pointer | rest |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ot10-biped-1` | counted | 0 | 0 | 0 | 0 | 7 | 0 | 1 | 1 | 0 | 5 |
| `ot10-hexapod-10` | counted | 0 | 0 | 0 | 0 | 15 | 6 | 3 | 2 | 3 | 1 |
| `ot10-hexapod-11` | counted | 0 | 0 | 0 | 0 | 12 | 0 | 2 | 2 | 2 | 6 |
| `ot10-quadruped-3` | counted | 0 | 0 | 0 | 0 | 10 | 0 | 2 | 3 | 2 | 3 |
| `ot10-quadruped-4` | counted | 0 | 0 | 0 | 0 | 6 | 0 | 1 | 1 | 2 | 2 |
| `ot10-hexapod-1` | failed attempt | 0 | 0 | 0 | 0 | 33 | 19 | 2 | 5 | 1 | 6 |
| `ot10-hexapod-2` | failed attempt | 0 | 0 | 0 | 0 | 10 | 3 | 2 | 0 | 2 | 3 |
| `ot10-hexapod-3` | failed attempt | 0 | 0 | 0 | 0 | 20 | 4 | 2 | 7 | 2 | 5 |
| `ot10-hexapod-4` | failed attempt | 0 | 0 | 0 | 0 | 14 | 8 | 3 | 1 | 1 | 1 |
| `ot10-hexapod-5` | failed attempt | 0 | 0 | 0 | 0 | 20 | 0 | 2 | 5 | 3 | 10 |
| `ot10-hexapod-6` | failed attempt | 0 | 0 | 0 | 0 | 8 | 0 | 2 | 0 | 2 | 4 |
| `ot10-hexapod-7` | failed attempt | 0 | 0 | 0 | 0 | 9 | 1 | 2 | 0 | 3 | 3 |
| `ot10-hexapod-8` | failed attempt | 0 | 0 | 0 | 0 | 20 | 3 | 4 | 1 | 1 | 11 |
| `ot10-quadruped-2` | failed attempt | 0 | 0 | 0 | 0 | 11 | 0 | 3 | 4 | 0 | 4 |
| `ot10-biped-2` | failed attempt | 0 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 1 | 6 |
| `ot10-hexapod-9` | not an attempt | 0 | 0 | 0 | 0 | 4 | 0 | 2 | 0 | 2 | 0 |
| `ot10-quadruped-1` | not an attempt | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 |
| **all** | 17 transcripts | **0** | **0** | **0** | **0** | 208 | 44 | 35 | 32 | 27 | 70 |

"Rest" is the 70 refusals outside those eight columns. They are: 16
`Cannot retire` refusals of an output that a component still linked, 11
`edit_script` replacements that did not match, 10 reset-variation refusals
that named the lift, 3 `PROJECT_OUTPUTS_DROPPED` guards, and 30 others. The
30 are single-cause API, MJCF, publication and worker refusals, plus two
calls to a tool name that does not exist. Three of them are worker crashes
in `ot10-hexapod-11`, and three are the publication refusals that ended
`ot10-biped-2`. After the CPU limit (44), the
recurring costs are sandbox refusals (35: `dir`, `getattr`, `hasattr`,
`type`, imports, private attributes) and guessed JSON pointers (27). Each one costs
turns. None is one of the four classes A4 closed.

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
them. All three now are (ADR-414, ADR-415, ADR-424; see *A3* below): P1
**0.373**, over its bar, P2 **0.189** (0.332 with its floor, before
ADR-424) and P3 **2**, both within theirs.

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
| P2 `sharp_outside_edge_share` | not measured | **0.189** (3,181 of 16,856 mm, 13 printed components; ADR-424. ADR-415 measured 0.332 with the floor) | ≤ 0.25 | yes |
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
hero it wrote is again byte for byte `hex3-studio_hero.png`. It read
0.332, a third of the edge length as a bare convex corner, but 3,612 mm
of that was the floor box. ADR-424 leaves the floor out, and hex3's
printed parts alone read **0.189**, within the bar. hex3's plates are
thin, so their long faces dominate the edge length and their sharp rims
are under a fifth of it. P2 does not see T4's 0 on this design. P1 and
the judge do, which is the necessary-not-sufficient point again.

## A6: the concept sheets

ADR-430 has `cadex render` write a concept sheet beside the hero, and
`cadex review` opens on it. Each A5 design that met the bar has a committed sheet.
Each was drawn on a fresh `/tmp` copy of the project (`cp -a`) with
`./cadex render --project <copy>`, so the ot10 projects are unchanged. The
hero in each sheet is that render's own `hero.png`, pixel for pixel.

| Design | Revision | Mass | Servos | Size X × Y × Z (mm) | Sheet | Sheet s | Render s | Rebuild s | Command s |
|---|---|---|---|---|---|---|---|---|---|
| biped | `44b8497b5c54` | 0.389 kg | 6 | 92 × 108 × 221 | [`ot10-biped-1-sheet.png`](ot10-biped-1-sheet.png) (138 KB) | 1.2 | 7.1 | 57.8 | 128 |
| quadruped | `7de6eea6212e` | 0.479 kg | 8 | 178 × 151 × 123 | [`ot10-quadruped-3-sheet.png`](ot10-quadruped-3-sheet.png) (210 KB) | 1.1 | 7.0 | 61.8 | 141 |
| hexapod | `e8a82deb1a06` | 0.654 kg | 12 | 212 × 231 × 136 | [`ot10-hexapod-10-sheet.png`](ot10-hexapod-10-sheet.png) (212 KB) | 1.9 | 9.3 | 98.2 | 213 |

*Mass* is the sum of each accepted MJCF model's inertials, without the
floor. *Servos* counts the placed components in catalog family `servo`.
*Sheet s* is the time to compose the sheet. *Render s* covers the four views
and the hero, not the sheet. *Rebuild s* is the time to acquire the
tessellation. *Command s* is the wall time of the whole `cadex render`
command, including engine start-up and project commit, and it ran while other
work shared the CPU. The sheets'
line views use the product's own axis names. The biped faces +X, so its
visor shows in `right`, not `front`: that is how the design is oriented,
not a fault in the sheet.

## W1: the rollout video, in the studio look

ADR-431 makes the studio look the default for `python -m cadex_cli.video`.
None of the ot10 projects has a trained policy yet, so W1 is measured on a
`/tmp` copy (`cp -a`) of ot6 Finch. Its walk `finch1-final` has an accepted
policy with a verified rollout. `./cadex render --project <copy>` rebuilt
the run's own revision and digest, which gave the render summary its
materials. Nothing under `~/cadex-projects/ot6-finch` was touched.

| Run | Revision | Policy | Seed | Sim s | Frames | Triangles | Bound s | Render s | Materials |
|---|---|---|---|---|---|---|---|---|---|
| `finch1-final` | `b6862234556355f7` | `0f0997e148c0b675` | 0 | 8.0 | 81 at 10 fps, 512 px | 95,212 | 300 | 117.5 | 2, from `review/render/summary.json` |

Before and after, as frames 0, 40 and 80 of each video, decoded from the
webm the dashboard plays:

| Style | Strip |
|---|---|
| scene (ADR-332, before) | [`w1-finch-rollout-scene.png`](w1-finch-rollout-scene.png) (259 KB) |
| studio (ADR-431, after) | [`w1-finch-rollout-studio.png`](w1-finch-rollout-studio.png) (219 KB) |

The two cameras face the robot from sides about 100° apart. By 8 s the
pelvis has yawed about 100° and tilted about 25°, which is why the poses
look different. Re-drawing the 8 s pose from the scene camera's yaw and
pitch gives the scene's pose. The video itself stays in the copy's
`runs/finch1-final/`, never in git. W1's remaining half is a video of an
A5 design's own policy, which W2's training run will produce.

### W1 on an A5 design: `ot10-quadruped-3`, run `w2-1`

The video of W2 run 1's installed policy on its own model was rendered
with `python -m cadex_cli.video --project <copy> --run w2-1` on the W2
copy. It is stored in the copy's `runs/w2-1/` and not in git.

| Run | Revision | Policy | Sim s | Frames | Triangles read → drawn | Bound s | Render s | Materials |
|---|---|---|---|---|---|---|---|---|
| `w2-1` | `f6d32a586ecc6d38` | `d8b87d2e1215ed7b` | 4.38 | 45 at 10 fps, 512 px | 2,528,456 → 86,200 (0.586 mm cell) | 300 | 72.8 | declared, from `review/render/<revision>/summary.json`; `c_floor` omitted as environment |

The webm is `rollout-bdd0da27ec4e….webm`, 153,574 bytes. The rollout
seed field is empty in both the run record and the trace, and the video
records it as it found it.

The first attempt refused. The W2 notes predicted "no further decimation",
and that was wrong: the rollout's solids are 611 MB of ASCII STL, not the
render's 78,419 triangles. ADR-432 reads them under their own caps and
clusters them to a drawn budget. Its first render (72.8 s) then floated the
robot above its shadow. The floor sat at the solids' lowest reach,
−18.5 mm, because the tipping solids pass through the floor, and the
rollout collides on proxies. The floor is now `c_floor`'s top face at
0.0 mm.

| Floor | Strip (frames 0, 22 and 44, decoded from each webm) |
|---|---|
| lowest reach, −18.5 mm (before) | [`w1-quadruped-rollout-reach-floor.png`](w1-quadruped-rollout-reach-floor.png) (284 KB) |
| declared floor, 0.0 mm (after) | [`w1-quadruped-rollout-studio.png`](w1-quadruped-rollout-studio.png) (289 KB) |

The strip shows what W2's verdict says. At 2.2 s the robot stands with its
body yawed. At 4.4 s the body is tilted about 47°, past the 45° at which
the `tipped` termination fires. The dashboard's Videos tab lists
this video first. It serves the exact bytes as `video/webm`, and headless
Chromium plays it: `currentTime` passes 1.0 s of a 4.5 s, 512×512 clip,
with the revision and policy prefixes in the identity strip.

## W2: the walk, pre-registered

Written and committed **before** the run starts. Nothing below changes
once it has started; a second run is a new section with its own settings.

**The design is `ot10-quadruped-3`** (accepted revision `7de6eea6212e…`).
The biped and the quadruped tie as the best-scoring A5 designs at 15 of 21,
and the hexapod scores 14. The tie goes to the quadruped because W2's bar is
`walked = true`: four feet stand without balancing, and six MG90S joints on
two legs have to balance first. The task is the agent's own, declared in the
same design turn under the ADR-410 overlay, and it is trained unchanged:
alive bonus 2.0, upright 1.0, speed error −1.0 at 80 mm/s, sideways −0.5,
yaw rate −0.3, with the `tipped` and `collapsed` terminations, 10 s
episodes at 50 Hz.

**The project stays read-only.** `cadex walk` rewrites the script to
declare the policy, so it runs on a copy, `cp -a ot10-quadruped-3
ot10-quadruped-3-w2`, which starts at the same accepted revision.

| setting | value |
|---|---|
| command | `./cadex walk --project ~/cadex-projects/ot10-quadruped-3-w2 --out ~/cadex-projects/ot10-quadruped-3-w2/runs/w2-1 --iterations 1000 --envs 2048 --seed 0 --timeout 10800 --json` |
| design turns | none (`--prompt` not given: no tokens, no geometry change) |
| trainer | local, on this machine's RTX 5090, `~/cadex-train-venv` |
| seed | 0 |
| budget | 1,000 PPO iterations × 2,048 environments |
| wall-clock cap | trainer `--timeout 10800` (3 h); the other legs keep the default `--leg-timeout` of 3,600 s |
| collapse stop | `--stop-on-collapse`, which `cadex walk` always passes to the trainer (ADR-410) |
| grounding | enforced; `--allow-ungrounded` is not given |
| gait thresholds | unchanged. The bar is the walk review's `walked = true` |
| process | launched with `setsid nohup`, so it outlives the loop session that starts it; attempt 9 was lost that way |

**Stop rule.** The run ends at whichever comes first: 1,000 iterations, the
3 h trainer cap, or a detected collapse. Whatever policy it saved then goes
through the walk's own store, declare, verify, roll-out and review legs.
A policy that does not walk is reported as an incomplete result, with a
diagnosis and a next step. The thresholds do not move, and no second run
starts until this one is diagnosed.

### W2 run 1 (`w2-1`): trained to the stop rule, and did not walk

**`walked = false`.** This is an honest incomplete result under the rule
above. Nothing was re-run, and no threshold moved.

The walk started at 14:23:23Z on `d94c845f`, detached. The engine/source
comparison was `match` (57 files). It exited 0 after 2,241.7 s. All legs
passed: train 1,944.8 s, declare 59.5 s, roll-out 130.9 s, then review.
The trainer ran all 1,000 iterations on the GPU in 1,611 s, and the
collapse detector never fired. The policy `walk_task.cxpolicy`
(`d8b87d2e1215…`) was stored with `--put`, and its witness agrees to
1.2e-7. It was declared by the walk's own script rewrite (policy switch on),
verified and rolled out at revision `f6d32a586ecc…`, digest
`7d7f0c2eca9e…`. The run's files, video inputs included, stay in the
copy's `runs/w2-1/` and its project git, never in this repository.

**Training curve.** Each value is the mean of the published curve's
samples in that bucket (about 51 per bucket; the curve keeps 512 of 1,000
iterations):

| iterations | reward/step | mean episode steps |
|---|---|---|
| 0–99 | 1.161 | 1,647.2 |
| 100–199 | 1.601 | 499.6 |
| 200–299 | 2.097 | 523.9 |
| 300–399 | 2.287 | 541.7 |
| 400–499 | 2.398 | 528.2 |
| 500–599 | 2.457 | 527.1 |
| 600–699 | 2.496 | 513.9 |
| 700–799 | 2.551 | 522.9 |
| 800–899 | 2.585 | 522.3 |
| 900–999 | 2.620 | 523.8 |

Reward per step was still rising at the stop. The best iteration was the
last, at 2.654.

**The gait verdict.** Rollout seed from the script, 220 frames:

| finding | measured |
|---|---|
| tipped | the body passed 45° at 4.36 s and reached 46.8°. It was upright (tilt ≤ 30°) for 96.4% of frames |
| terminated | `tipped` at step 218 of 500 |
| training survival | 213 of 500 steps at the last iteration, which is 0.43 against the 0.90 bar |
| travel | 97.7 mm planar in 4.38 s (22 mm/s): +19.0 mm in X (forward), −95.9 mm in Y. Heading drifted to −51.9° |
| reward totals | alive 438.0, upright 207.1, speed error −202.8, sideways −45.0, yaw rate −39.0; total 358.2 |

**Diagnosis.**
1. **The policy learned to stand, not to walk.** Over 219 roll-out steps the
   speed error averages 0.93 per step. Under `abs(comv_x / 80 − 1)`, that
   means forward speed was about 7% of the 80 mm/s target, and 19 mm
   forward in 4.4 s agrees. Its travel is a sideways drift and a yaw, not a
   gait. The ADR-410 weights make standing net about +2 per step: alive 2.0
   plus upright 1.0, minus a speed error of 1.0 when still. Walking at the
   target adds at most +1. So survival pays twice what progress does.
   Surviving is what 1,000 iterations found first, and the curve was still
   climbing when the budget ran out.
2. **It tips late.** The tip at 4.36 s falls inside the task's own
   disturbance window, a 0.3–1.5 N horizontal push at 2–8 s. The trace
   does not say whether a push caused it; the review does not record push
   times.
3. **The survival finding reads one noisy sample.** `training_survival`
   reads only the last iteration's mean episode length, 213.3. The last
   fifty sampled iterations have a median of 487.6. The same curve reports
   means above the 500-step horizon (1,647 in the first bucket), so the
   trainer's episode-length figure is not a clean survival fraction.
   Findings 1 and 2 stand without it: the roll-out tipped and did not go
   forward. So this does not change the verdict. It is a separate defect
   in the gait check, recorded here and not fixed in this run.

**Next step.** First, render W1's video of this policy on this model. It
draws 78,419 triangles, decimated at a 0.59 mm cell from 650,316, below
Finch's 95,212. So the 512 px, 300 s bound stated for W1 applies with no
further decimation. Then pre-register a second bounded run in its own
section before it starts. It would warm-start from `w2-1`'s policy on the
unchanged task digest (`--init-from`), with a stated iteration budget and
cap, and the same thresholds. The reward and the design stay the agent's.
A reward change would mean a new design turn, not an edit by the actor.

### W2 run 2 (`w2-2`): pre-registered

Written and committed **before** the run starts, on the diagnosis of
`w2-1` above. Nothing in this section changes once it has started.

**Why a second run.** `w2-1`'s reward per step was still rising at its
last iteration (2.620 over iterations 900–999, best 2.654 at the last),
so its budget, not its task, is the first thing to extend. The task, the
reward and the design stay the agent's: a reward change would be a new
design turn, not an actor edit. So this run warm-starts the actor from
`w2-1`'s policy on the **unchanged** task, and changes nothing else.

| setting | value |
|---|---|
| command | `./cadex walk --project ~/cadex-projects/ot10-quadruped-3-w2 --out ~/cadex-projects/ot10-quadruped-3-w2/runs/w2-2 --iterations 1000 --envs 2048 --seed 0 --init-from ~/cadex-projects/ot10-quadruped-3-w2/runs/w2-1/train/walk_task.cxpolicy --timeout 10800 --json` |
| project | the same copy, `ot10-quadruped-3-w2`, at `w2-1`'s declared revision. The original `ot10-quadruped-3` stays read-only |
| warm start | `--init-from` `w2-1`'s `walk_task.cxpolicy`, sha256 `d8b87d2e1215…`, trained on task bundle sha256 `b0913fa0fb93…`. The trainer refuses a warm start across a changed task digest unless `--init-from-task-change` is given; it is not given, so a changed digest ends the run as a refusal rather than a silent task change |
| design turns | none (`--prompt` and `--set` not given: no tokens, no geometry change) |
| trainer | local, on this machine's RTX 5090, `~/cadex-train-venv` |
| training seed | 0 |
| rollout seed | `null` in the script. `assembly.rollout(pol)` passes no seed, so the verified roll-out uses the script's (the engine default), not training's seed 0. The review's `comparison.rollout_seed` reads `null`, as it did for `w2-1` |
| budget | 1,000 further PPO iterations × 2,048 environments |
| wall-clock cap | trainer `--timeout 10800` (3 h); the other legs keep the default `--leg-timeout` of 3,600 s |
| collapse stop | `--stop-on-collapse`, which `cadex walk` always passes to the trainer (ADR-410) |
| grounding | enforced; `--allow-ungrounded` is not given |
| gait thresholds | unchanged. The bar is the walk review's `walked = true` |
| process | launched with `setsid nohup`, so it outlives the loop session that starts it |

**Stop rule.** The run ends at whichever comes first: 1,000 iterations, the
3 h trainer cap, or a detected collapse. Whatever policy it saved then goes
through the walk's own store, declare, verify, roll-out and review legs,
and W1's video is rendered from it with `python -m cadex_cli.video`.
A policy that does not walk is reported as an incomplete result, with a
diagnosis and a next step. The thresholds do not move, `w2-1`'s survival
defect (finding 3) is not fixed inside this run, and no third run starts
until this one is diagnosed.

### W2 run 2 (`w2-2`): walked 1.44 m upright, and the verdict is still `walked = false`

**`walked = false`.** This is an honest incomplete result under the
pre-registered rule. Nothing was re-run, and no threshold moved. The only
finding against the gait is `training_survival`, and the diagnosis below
shows that it reads a measurement artifact, not the policy.

The walk started at 15:49:25Z on `1c4600e1`, detached. The engine/source
comparison was `match` (57 files). The exported task bundle was
byte-identical to `w2-1`'s (sha256 `b0913fa0fb93…`), so the warm start ran
on the unchanged task and no `--init-from-task-change` was needed. The walk
exited 0 after 2,157.5 s. All legs passed: train 1,866.3 s, declare
59.7 s, roll-out 126.7 s, then review. The trainer ran all 1,000
iterations on the GPU, and the collapse detector never fired. The policy
(`7a4e8c233214…`, witness agreement 1.3e-7) was stored, declared by the
walk's own script rewrite, verified and rolled out at revision
`84ff4c98adab…`, digest `d67ac96c2fe0…`. The review's
`comparison.rollout_seed` is `null` and `training_seed` is 0, as
pre-registered. The run's files stay in the copy's `runs/w2-2/` and its
project git, never in this repository.

**Training curve.** Each value is the mean of the published curve's
samples in that bucket (about 51 per bucket; the curve keeps 512 of 1,000
iterations). The reward starts at 1.61 rather than `w2-1`'s final 2.62
because the warm start carries the actor only; the critic starts fresh.

| iterations | reward/step | mean episode steps (trainer's figure) |
|---|---|---|
| 0–99 | 2.283 | 4,609.8 |
| 100–199 | 2.482 | 2,385.6 |
| 200–299 | 2.532 | 1,855.6 |
| 300–399 | 2.555 | 1,952.2 |
| 400–499 | 2.595 | 1,721.9 |
| 500–599 | 2.615 | 1,691.3 |
| 600–699 | 2.634 | 1,452.9 |
| 700–799 | 2.647 | 1,504.5 |
| 800–899 | 2.650 | 1,633.6 |
| 900–999 | 2.662 | 1,450.9 |

The best iteration was 998, at 2.697.

**The gait verdict.** Rollout seed from the script, 501 frames, the full
10 s episode:

| finding | measured | threshold |
|---|---|---|
| tipped | never; maximum tilt 15.9°, final 4.1° | 45° |
| upright | 100% of frames | tilt ≤ 30° |
| terminated | no; the episode ran to its 500-step horizon | — |
| travel | 1,474.0 mm planar in 10 s (147 mm/s): +1,443.8 mm in X (forward), +297.0 mm in Y | — |
| heading | between −19.5° and +30.5°, final +16.3° | turned < 90° |
| training survival | **32 of 500 steps at the last iteration, 0.06: fails** | 0.90 |
| reward totals | alive 1,000.0, upright 496.1, speed error −651.3, sideways −151.1, yaw rate −79.3; total 614.4 (`w2-1`: 358.2) | — |

The feet step rather than slide. Each foot's height was read from the
trace (the foot solid's centre, carried by its placement). Relative to its
own 5th-percentile height, the front feet rise up to 46 and 54 mm and
cross a 3 mm lift line 48 and 52 times. The rear feet rise up to 26 and
19 mm and cross it 100 and 124 times. It overshoots the 80 mm/s target at
about 147 mm/s, which is where most of the speed-error total comes from.

W1's video of this policy on this model was rendered with
`python -m cadex_cli.video --project <copy> --run w2-2`:

| Run | Revision | Policy | Sim s | Frames | Triangles read → drawn | Bound s | Render s | Materials |
|---|---|---|---|---|---|---|---|---|
| `w2-2` | `84ff4c98adabb6e5` | `7a4e8c233214341e` | 10.0 | 101 at 10 fps, 512 px | 2,528,456 → 86,200 (0.586 mm cell) | 300 | 153.9 | declared, from `review/render/<revision>/summary.json`; `c_floor` omitted as environment |

The webm is `rollout-e64ac61844fc….webm`, 322,440 bytes, in the copy's
`runs/w2-2/`. Its strip, frames 0, 50 and 100 decoded from the webm, is
[`w2-2-quadruped-rollout-studio.png`](w2-2-quadruped-rollout-studio.png)
(245 KB). It shows the body level at 0, 5 and 10 s with the legs at
different points in the stride. The dashboard playback check was not
repeated for this video; W1's Chromium check covered `w2-1`'s.

**Diagnosis.**
1. **The one failing finding measures the time limit, not survival.**
   The trainer's `episode_steps` is `unroll × envs / endings`, where
   `endings` counts every `done` in the batch (`done = terminated or timeout`), **including time-limit
   truncations** (`training/cadex_train.py`, the mean-episode-length
   block). With the default unroll of 20 and a 500-step horizon, every
   25th iteration's batch ends exactly on a horizon boundary. Envs that
   have not fallen since they last reset together truncate together there.
   Iteration 999 is always such an iteration when the budget is 1,000.
   The published curve shows it for both runs. For every sampled
   iteration where `(i + 1) % 25 == 0`, `w2-2` reads 30.7–31.9 and
   `w2-1` 204.8–213.3. Every other sampled iteration reads at least
   787.7 in `w2-2` (median 1,517) and at least 350.1 in `w2-1` (median
   525). A reading of 31.9 means about 1,285 of 2,048 environments ended
   in that batch. Here that is mostly envs reaching the horizon together,
   the opposite of "ended early". `training_survival` reads only the
   last entry, so it reads this artifact every time. This is `w2-1`'s
   finding 3, now with its mechanism named.
2. **The roll-out alone meets every other gait threshold.** It did not tip
   or terminate, stayed upright for all 501 frames, turned less than 90°,
   and went 1.44 m forward in the full 10 s episode.
3. **Warm-starting fixed what `w2-1` lacked.** `w2-1` stood, drifted
   sideways and tipped at 4.36 s. Another 1,000 iterations on the
   unchanged task produced forward travel 76 times greater (1,443.8 mm
   against 19.0 mm). The survival-over-progress weighting from `w2-1`'s
   diagnosis delayed the gait but did not prevent it.

**Next step.** Fix the survival measurement, not the threshold. In its own
unit, with a regression test that fails on the current source, make
`training_survival` count only true terminations (the trainer already
separates `terminals` from `dones`). Alternatively, read survival over a
trailing window that no horizon boundary can dominate. Keep the 0.90 bar.
Then re-review `w2-1` and `w2-2` from their stored artifacts under the
fixed check. That needs no retraining, and it re-scores both runs. Until
that lands, W2's recorded verdict is `walked = false`.

### W2 re-review under ADR-433: `w2-2` walked

ADR-433 corrects how the gait check reads training survival: the median of
the trainer's episode length over the last 50 iterations, each sample capped
at the horizon, instead of the last iteration alone, which closes on a
horizon boundary and counts every time-limit truncation as an ending. **The
0.90 bar did not move**, and neither did any other gait threshold. Both
runs were re-reviewed from the inputs their stored `review.json` was built
from, with no retraining and no new rollout. Every other gait field agrees
exactly with the stored review. The results are written beside each review
as `runs/<run>/gait-adr433.json` in the project copy, never in this
repository.

| run | survival, before | survival, ADR-433 | other findings | verdict |
|---|---|---|---|---|
| `w2-1` | 213.3 of 500 (last iteration): fails | median 487.6 (0.975) over 950–999: passes | tipped at 4.36 s; terminated at step 218 | `walked = false` |
| `w2-2` | 31.9 of 500 (last iteration): fails | median 500 (1.00) over 950–999: passes | none | **`walked = true`** |

As a cross-check that does not rest on the cap, the unroll the policy
header records (20) and the 2,048 envs give total steps over total endings
across the two full horizon periods in 950–999: 485.5 steps for `w2-1` and
489.5 for `w2-2`.

W2's bar is `walked = true` on one A5 design through `cadex walk` with the
unchanged ADR-410 overlay and `--stop-on-collapse`. `w2-2` on
`ot10-quadruped-3` meets it: its settings and stop rule were recorded
before it started, its policy was installed through the supported path, and
its W1 video and training curve are above. `w2-2` was a warm start from
`w2-1` on a byte-identical task bundle, which the pre-registration stated.
