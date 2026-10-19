# orun11: eq1-s1 judged on the gallop spec, and the plantigrade reach

Verified against source: 2026-10-18. Frozen evidence (orun11, iteration 4).

## eq1-s1, checkpoint by checkpoint

eq1-s1 is the ratio screen: `~/cadex-projects/orun11-cat-eq` (4ccf160f),
the paw held to the hock by an `equality/joint` coupling (−0.6, no physical
part, O2), trained cold for 150 iterations on orun11-cat's 17-term task and
tiptoe gallop clip (0.7 m, 2.4 Hz). It is a screen of the ratio, not M1
evidence. Every checkpoint was judged on the bundle's own ADR-774
`gallop_spec`, seeds 1001–1010, with the engine's evaluation on the CPU:

```
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py PROJECT RUN/train POLICY NAME
```

The reports are `orun11-cat-eq/evaluations/eq1-s1-<checkpoint>/evaluation.json`.
Each carries a `closure` block: each equality row's error over the window
from 1 s, read from the traces' body placements.

| checkpoint | pass | failing (median) | top 2 s m/s min / med / max | hock down LH / RH | hock at toe-off | hock stance height LH / RH mm | sole LH / RH deg | touchdown Hz LF RF LH RH | stride Hz | worst RMS/rated | peak ratio | paw coupling error median / max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 25 | 0/10 | straight 26.0 (4/10), top_speed 705, hock_down 0.03, no_tap 1.56, overreach −518 | 0.62 / 0.71 / 0.98 | 0.14 / 0.03 | 0 / 0 | 46 / 76 | 24 / 56 | 3.50 3.28 2.56 2.89 | 2.27 | 2.03 (j_hock_l) | 1.00 | 0.09° / 3.6° |
| 50 | 0/10 | top_speed 1702, hock_down 0.06, no_tap 1.42, overreach −268 | 1.67 / 1.70 / 1.72 | 0.18 / 0.06 | 0 / 0 | 46 / 75 | 29 / 63 | 2.44 2.72 3.39 2.67 | 2.38 | 1.79 (j_hock_l) | 1.00 | 0.14° / 4.4° |
| 75 | 0/10 | top_speed 2460, hock_down 0, no_tap 1.45, overreach −121 | 2.44 / 2.46 / 2.47 | 0.31 / 0 | 0 / 0 | 7 / 89 | 23 / 57 | 2.44 2.78 3.50 2.89 | 2.38 | 1.93 (j_spine) | 1.00 | 0.13° / 3.5° |
| 100 | 0/10 | top_speed 2746, hock_down 0, no_tap 2.01, overreach −3 (4/10) | 2.71 / 2.75 / 2.77 | 0.30 / 0 | 0 / 0 | 7 / 90 | 22 / 56 | 2.44 4.78 2.94 4.00 | 2.38 | 1.97 (j_spine) | 1.00 | 0.10° / 4.3° |
| 125 | 0/10 | top_speed 2950, hock_down 0, no_tap 1.89 | 2.93 / 2.95 / 2.98 | 0.25 / 0 | 0 / 0 | 12 / 93 | 19 / 52 | 2.44 4.50 2.44 2.89 | 2.38 | 1.96 (j_spine) | 1.00 | 0.12° / 4.5° |
| best (149) | 0/10 | top_speed 3165, hock_down 0, no_tap 1.91 | 3.16 / 3.17 / 3.18 | 0.19 / 0 | 0 / 0 | 14 / 93 | 17 / 52 | 2.44 4.56 2.33 2.44 | 2.38 | 2.00 (j_spine) | 1.00 | 0.18° / 4.4° |
| final (150) | 0/10 | the same as best, seed for seed | 3.16 / **3.17** / **3.18** | 0.19 / 0 | 0 / 0 | 14 / 93 | 17 / 52 | 2.44 4.56 2.33 2.44 | 2.38 | 2.00 (j_spine) | 1.00 | 0.18° / 4.4° |

Medians over 10 seeds. Hock-down, stance height and sole (median pitch
from flat in stance, toes-down positive) are per leg. The predicate takes
the worse leg. Worst RMS/rated is each seed's worst drive, then the median;
the peak ratio of 1.00 is a drive at its clamp, a peak margin of 0. No seed
fell. Every checkpoint completes, upright and straight (from 50 on), and
`every_stride` passes. The started checkpoint is cold (no warm start).

**What it shows.**

- **The right hind never lays down.** Its sole stays 52–63° toes-down in
  stance and the case 75–93 mm up, on every checkpoint, as on the tiptoe
  clip it tracks. The left reaches a 7–14 mm median stance height and is
  down 19–31% of stance, but never at toe-off. A coupling alone does not
  make the stance plantigrade: the clip still asks for tiptoes.
- **The right fore taps** (4.5–4.8 Hz against a 2.4 Hz stride) from 100 on,
  as t2-g4 did. The left fore keeps the clip's 2.44 Hz.
- **Speed** climbs to 3.17 m/s at the end, still rising (+7% over iteration 125), on
  the clip's 2.38 Hz clock with a 1.31 m stride. Worst drive RMS is 2.0×
  rated (the spine).
- **The soft coupling holds:** median error 0.1–0.2°, worst 3.6–4.5°.

## The plantigrade reach (ADR-776)

`CadexGait.generate` now holds a leg's loop closures, and can hold a heel
body down from part of the stance to toe-off, under a crouched trunk.
`plantigrade_reach.py` asks it for a plantigrade clip on rod1-s1's
exported model (rod A, orun11-cat 4cd04aaf):

```
pixi run python docs/probes/orun11/plantigrade_reach.py <cat_model-model.xml>
```

- **The training clip, rod held:** over the hind stance the pin moves
  against the hock at slope −0.604 (LH) and −0.594 (RH), with closure
  error 0.0005 mm. Before ADR-776 the pin was free in the clip.
- **Inside the joint limits, no plantigrade clip is reachable:** 0 of 108.
  The grid is strides of 0.5 and 0.7 m, duties 0.2 and 0.25, the hock case
  down from half the stance to toe-off, trunk drops of 30, 45 and 60 mm,
  nose-up pitches of 3, 6 and 9°, and hind stances 0, 60 and 120 mm
  forward. What binds:
  - the knee stop with the heel down, 52;
  - the hock stop with the heel down, 3;
  - the right fore's swing at its stops, once crouched, 19;
  - the hind swing at the knee, hock or hip stops, 34.
- **With the hind hip, knee and hock unlimited**, 25 of the 108 are
  reachable. The mildest is a 0.5 m stride, duty 0.2, 30 mm drop, 9°
  pitch and 60 mm shift. It needs:
  - the left hip at −44..+20°, against its −30..+40 stops;
  - the left knee at −59..+50°, against −40..+50;
  - the right hip at −25..+44° and knee at −64..+63°.

  At 0.7 m every reachable row needs the 60 mm drop. Over the shortest
  ones, the hip needs about 15° more extension and the knee about 20° more
  range. The rest fail at full reach, with the leg straight.
- **M1's static check stood the hip low.** `foot_static.py` put the floor
  under the paw with the trunk level. In its passing poses the hip is
  313–326 mm over the floor, against 396 mm standing:

  | shin | hock | sole | hip over floor |
  |---|---|---|---|
  | 0 | −60.00 | +7.2 | 316 mm |
  | −6 | −60.00 | +1.2 | 313 mm |
  | −10 | −55.75 | −0.9 | 317 mm |
  | −14 | −52.25 | −3.5 | 321 mm |
  | −20 | −47.00 | −7.4 | 326 mm |

  The plantigrade pose holds for a cat crouched 70–84 mm at the hind,
  directly over the foot. On this leg, femur and shin together are about
  309 mm, and laying the metatarsus flat lowers the hock by about 95 mm.

**So rung 6 is blocked by the hind leg, not by the generator.** M1's
static check "in the gait reference's stance pose" needs a reachable
plantigrade reference. On orun11-cat that needs a leg change (O3): more
hip extension and knee range, through the sweep, or longer femur and
shin. A trunk 60 mm lower throughout only moves the bind to the fore legs.
