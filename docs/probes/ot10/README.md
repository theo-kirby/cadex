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
