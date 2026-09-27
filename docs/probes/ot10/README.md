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
