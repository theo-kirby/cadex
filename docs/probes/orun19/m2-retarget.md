# orun19 M2: the dog's gallop strides retargeted to leo v06

Verified against source: 2026-10-23. Charter M2 and O4. This covers the
retarget, its measurements and the M2 task bundle, with no training. The
training, judgement and film come later. The data is the AI4Animation dog
(Zhang et al. 2018, CC BY-NC 4.0, `docs/probes/orun18/SOURCES.md`,
unchanged). Clips, measures and the bundle stay in `~/mocap/`, never in the
repository.

## The probe

`dog_retarget.py` (this folder) reads the stride with orun18's
`retarget.dog_stride` and solves it with `retarget.retarget`, both
unchanged, as orun18 C2/C3 did on v05. It relabels the clip "leo v06",
records the model's hash and adds M1's three v06 measures from
`acino_retarget.py`: miss in stance and swing per leg, the heel pad over the
ground in hind stance, and the hock's angle there. The model is v06's MJCF as
s1-v06's bundle carries it (`f9b8ab82…`).

O4 on v06, as for M1: the solve reads each leg's chain from the model, so the
hind ball is placed through hip, knee and hock, and the fore ball through
abduction, scapula, shoulder and elbow, with no wrist. The spine goes to
`j_spine` / `j_spine_yaw`.

**Where the fore ball goes.** Unlike AcinoSet's FTE, the dog has a carpus
(`LeftHand`) and a paw end 72 mm below it (`LeftHand_end`). orun18 put v05's
paw on the paw end. O4 drops the carpus and digit angles and fits the fore
foot at the ball, which can be read two ways, so both were run:

- `paw`: the ball follows the dog's paw end (orun18's target);
- `carpus`: the ball follows the dog's carpus, as M1's ball follows the
  cheetah's wrist. The digits' fold in swing goes with the dropped angles.

Either way the floor, the length scale (fore 1.010, hind 1.007) and the
contact rule are the stride's own: the carpus track replaces only the two
fore targets, after `dog_stride` has read them. The hind targets, the spine,
tail and head are the same in both.

**The tail is mapped and the head is measured**, by M1's `map_tail` and
`measure_head`. `acino_retarget.py` now takes the capture's point names as
an argument, defaulting to AcinoSet's, so the cheetah's clips are unchanged
(cheetah59 re-run: `aa81d5ad…`, the same bytes). The dog's tail chord runs
`Tail` to `Tail1_end`, and its head chord `Neck` to `Head_end`.

## The strides (26 samples each)

orun18 C3's three, the only dog strides that keep one footfall order
(c3-task.md):

| clip (take, frames) | leo m/s, period, Fr | touchdown LF RF LH RH (paw / carpus) | flight (paw / carpus) |
|---|---|---|---|
| gallop27 (`D1_010_KAN01_001`, 404–432) | 2.76, 0.478 s, 2.12 | 0.19 / 0.15, 0.42, 0.00, 0.85 | 0.15 / 0.23 |
| gallop34 (`D1_010_KAN01_003`, 86–112) | 3.39, 0.435 s, 3.21 | 0.19, 0.38, 0.04, 0.88 | 0.23 / 0.31 |
| gallop42 (`D1_010_KAN01_002`, 66–92) | 4.23, 0.435 s, 5.00 | 0.19 / 0.23, 0.38, 0.00, 0.88 | 0.27 / 0.35 |

- Speed and period equal orun18's on v05 to the digit. The Froude numbers
  are higher (2.12 against v05's 2.00 on gallop27) because v06's hind hip
  stands 0.366 m over its ball, lower than v05's 0.396 m over its paw. The
  cheetah's clips moved the same way.
- The order is LH, LF, RF, RH, a rotary gallop. The cheetah's is LH, RF, LF,
  RH, a transverse one.
- The carpus lifts before the paw end leaves the ground, so on the carpus
  target the fore duty is shorter (LF 0.31 / 0.23 / 0.15 against the paw's
  0.35 / 0.31 / 0.31) and the flight longer.

## What v06 follows, and where it misses (mm)

| clip, target | raw slip max LF/RF/LH/RH | solved slip max | miss in stance max LF/RF/LH/RH | miss in swing max LF/RF/LH/RH (share of stride > 5 mm) | violations, loops | seam max / step |
|---|---|---|---|---|---|---|
| gallop27, paw | 23 / 14 / 10 / 37 | 21.5 (LF) | 24 / 0 / 0 / 0 | **135** (0.50) / **139** (0.42) / 0 / 0 | 0, 0.000 | 22° / 38° (`j_knee_l`) |
| gallop27, carpus | 32 / 18 / 10 / 37 | 7.0 (LF) | 14 / 0 / 0 / 0 | **75** (0.35) / **81** (0.35) / 0 / 0 | 0, 0.000 | 22° / 35° (`j_knee_l`) |
| gallop34, paw | 13 / 17 / 8 / 37 | 8.6 (LF) | 20 / 0 / 0 / 0 | **112** (0.50) / **189** (0.38) / 23 (0.19) / 0 | 0, 0.000 | 21° / 43° (`j_elbow_l`) |
| gallop34, carpus | 20 / 18 / 8 / 37 | 0.0 | 0 / 0 / 0 / 0 | **75** (0.31) / **140** (0.42) / 23 (0.19) / 0 | 0, 0.000 | 22° / 34° (`j_shoulder_l`) |
| gallop42, paw | 49 / 50 / 23 / 8 | 26.6 (LF) | 56 / 4 / 0 / 0 | **156** (0.69) / **242** (0.50) / 33 (0.19) / 7 (0.04) | 0, 0.000 | 42° / 56° (`j_shoulder_l`) |
| gallop42, carpus | 22 / 48 / 23 / 8 | 0.0 | 0 / 0 / 0 / 0 | **108** (0.50) / **173** (0.50) / 33 (0.19) / 7 (0.04) | 0, 0.000 | 12° / 41° (`j_knee_l`) |

Fore joints at a stop, as a share of samples (scap, shoulder, elbow; left /
right):

| clip | paw | carpus |
|---|---|---|
| gallop27 | 0.42 0.39 0.15 / 0.50 0.35 0.23 | 0.27 0.31 0.35 / 0.15 0.31 0.35 |
| gallop34 | 0.42 0.42 0.15 / 0.54 0.35 0.19 | 0.19 0.46 0.39 / 0.27 0.42 0.42 |
| gallop42 | 0.69 0.50 0.31 / 0.73 0.46 0.31 | 0.31 0.65 0.46 / 0.50 0.58 0.35 |

How to read it:

- **No joint leaves its range, and the loops stay closed** on all six clips.
- **The carpus target is the one to train.** It holds stance (no stance miss
  over 14 mm, and none at all on gallop34 and gallop42), its solved slip is
  7 mm or less where the paw target's reaches 27 mm, and it misses 30–45%
  less in swing. The paw end's extra travel is the digits' fold and flick,
  which a ball on a straight forearm cannot make. **The M2 bundle uses the
  carpus clips.**
- **The fore leg cannot reach the dog's late swing.** Every large miss is in
  the second half of the fore swing, growing toward touchdown (RF on
  gallop42: 17 mm at sample 21, 94 at sample 0, 173 at sample 6, then 0 once
  it lands). The shoulder sits at
  its stop on 0.31–0.65 of samples and the elbow on 0.35–0.46. On v05,
  orun18 measured the same strides' fore misses at 14/38, 10/46 and 75/64 mm
  (LF/RF, c2-retarget.md and c3-task.md), with the wrist adding reach. v06's
  fore leg reaches less far forward than either the dog asks or v05 could.
- **The hind legs follow the dog.** The hind miss is 0 in gallop27 and at
  most 33 mm (LH, gallop42) elsewhere, against the cheetah's right hind at
  49–77 mm on v06.
- **The clip asks for a toe stance.** The heel pad stays 44–140 mm over the
  ground through every hind stance and touches on 0.0 of stance samples. The
  hock reads −7…+6° (left convention), never near −40°. As on M1, nothing in
  the clip sets the metatarsus's angle, so the solve's pull toward home
  keeps it there.
- **The spine** takes `j_spine` −10.6…+10.9° and `j_spine_yaw` −5.9…+7.3°,
  unclipped: the dog flexes its back in pitch about three times the
  cheetah's (−2.6…+3.3°), and yaws it less.

## The tail and the head

| clip | `j_tail1` (deg) | `j_tail2` (deg) | clamped share | head pitch / heading vs thorax (deg) |
|---|---|---|---|---|
| gallop27 | −8.5…14.4 | −4.2…4.6 | 0 | −32.7…16.7 / −20.3…−7.5 |
| gallop34 | −14.6…15.0 | −10.5…18.0 | 0 | −8.0…14.4 / −23.8…−7.3 |
| gallop42 | −18.4…27.1 | −25.0…25.0 | **0.19** | 4.0…25.6 / −21.1…−6.6 |

The dog swings its tail far more than the cheetah does (`j_tail1` up to
27° against 11°). On gallop42 `j_tail2` reaches its ±25° stop on 0.19 of
samples. The head is measured, not posed: leo's speed task holds
`j_neck1`, `j_neckyaw` and `j_headpitch`. The dog's head moves over a range
two to four times the cheetah's (up to 49° in pitch on gallop27).

## Retarget fit: dog against cheetah, on v06

| | cheetah (M1, 52/59/61) | dog (M2, carpus, 27/34/42) |
|---|---|---|
| leo speed | 4.63–5.33 m/s | 2.76–4.23 m/s |
| fore swing miss max, LF / RF | 39–96 / ≤ 18 | 75–108 / 81–173 |
| hind swing miss max, LH / RH | 15–46 / 49–77 | 0–33 / 0–7 |
| stance miss max | 6.2 | 14 |
| heel pad touch share | 0.0 | 0.0 |
| `j_spine` pitch | −2.6…+3.3° | −10.6…+10.9° |

On the retarget alone, the dog fits v06's hind legs and the cheetah fits its
fore legs. Which fits v06 better as a gait is M2's judgement on the trained
policies, not this table's.

## The M2 bundle

`~/mocap/ai4animation/m2-bundle/mocap_gallop-task.json` (sha256
`8e9e53fcc7cfee5edaa56c710b13eae2b979b6dcbfdd2389ce93670a18f9a0c7`), with
model XML `f9b8ab82…` (leo v06, unchanged). It carries the clips, so it is
CC BY-NC derived and stays in `~/mocap/`.

**Its base is leo_v06.py's speed task, not S2a's.** The bundle is built
from s1-v06's `speed-task.json` (`bca307a2…`), the bundle the engine built
from `leo_v06.py`'s unchanged speed task (b1-s2's ten rows on 24 drives),
the base M1's bundle used. S2a's `speed-task.json` (`d5b25b15…`, from
`leo_s2a.py`, command held per episode) is not used, so M1 and M2 differ
from each other only in their strides, and from S1 only in the tracking.

It is built by `m1_bundle.py` unchanged: orun18's `c3_bundle.py` with M1's
v06 tracking terms (`track_pose` without the wrist and with `q_tail1` and
`q_tail2`, divisor 17100; `track_lift` at 20.9 mm fore and 29.3 mm hind;
`track_contact`; weights 1.5, 1.5 and 10). Nothing in those terms is
cheetah-specific.

- **Strides:** gallop27, gallop34 and gallop42 at 2756 / 3395 / 4233 mm/s,
  carpus target, 26 samples each. The footfall-order check passes.
- **Goal:** `cmd` from 2756 to 4233 mm/s, in the task and in its success
  spec, nominal 2850 (inside the span).
- **Reward:** 13 rows, S1's ten plus the three tracking terms. No style
  term; every row compiles.
- **Tracking channels:** 30, the clock and a 26 × 28 table (20 joint
  references, 4 lifts and 4 downs). 78 reset rows, random start.

Checked with the engine's readers on the bundle (`schedule_blend`,
`judged_reference`, `reference_start` with seed 0, `mj_forward`):

| cmd mm/s | blend (stride, w) | judged stride | start row |
|---|---|---|---|
| 2756 | 0, 0.00 | gallop27 | 12 |
| 3000 | 0, 0.38 | gallop27 | 12 |
| 3395 | 1, 0.00 | gallop34 | 38 |
| 3800 | 1, 0.48 | gallop34 | 38 |
| 4233 | 1, 1.00 | gallop42 | 64 |

All 78 reset rows run `mj_forward` with finite accelerations; row 30 starts
at 2.75 m/s forward. The table's tail columns span gallop27's mapped range
(`q_tail1_ref` −8.5…14.4°, `q_tail2_ref` −4.2…4.6°).

The bundle is not trained. S2a holds the GPU; M1 trains first (O5, one
trainer at a time, and the charter's order).

## Reproduce

```
X=~/mocap/ai4animation/extract; M=~/cadex-projects/leo/runs/s1-v06/train/cat_model-model.xml   # f9b8ab82…
for T in paw carpus; do O=~/mocap/retargeted-v06/$T
  pixi run python -I docs/probes/orun19/dog_retarget.py $M $X/D1_010_KAN01_001.bvh 404 432 gallop27 $O 26 $T
  pixi run python -I docs/probes/orun19/dog_retarget.py $M $X/D1_010_KAN01_003.bvh 86 112 gallop34 $O 26 $T
  pixi run python -I docs/probes/orun19/dog_retarget.py $M $X/D1_010_KAN01_002.bvh 66 92 gallop42 $O 26 $T
done
pixi run python -I docs/probes/orun19/m1_bundle.py ~/cadex-projects/leo/runs/s1-v06/train/speed-task.json \
  ~/mocap/ai4animation/m2-bundle mocap_gallop ~/mocap/retargeted-v06/carpus/gallop{27,34,42}.clip.json
```

| file (outside the repo) | sha256 |
|---|---|
| `retargeted-v06/carpus/gallop27.clip.json` | `ee0ec468f99768aeab42311041207be8d2e3f2de5ee0200759366a0e19c60fc5` |
| `retargeted-v06/carpus/gallop34.clip.json` | `a5cf10d771900f0d477635d8be5950a6f3a702acbfb8fbef7d0439f9d67f8ab6` |
| `retargeted-v06/carpus/gallop42.clip.json` | `a5dee19c1792f83481c7e98144768a6dd6090993fc7ab2fb3036ca872120fdd8` |
| `retargeted-v06/paw/gallop27.clip.json` (not taken) | `b76d827dd2219485a21fa627a71ece1bd3fca3c45da12a6ff196d42894394cfe` |
| `retargeted-v06/paw/gallop34.clip.json` (not taken) | `6c30bd10384b751c91c0e26e240a0c91123e0da78524987a5093f6516f3d424d` |
| `retargeted-v06/paw/gallop42.clip.json` (not taken) | `703c1a62e11ac935885777a990d86522fda168b55641eb09f8da57bf3c05cb5d` |
| `m2-bundle/mocap_gallop-task.json` | `8e9e53fcc7cfee5edaa56c710b13eae2b979b6dcbfdd2389ce93670a18f9a0c7` |

The takes' own hashes are in `~/mocap/SHA256SUMS` and in each measure file
(`bvh_sha256`).
