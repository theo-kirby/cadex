# orun18 C4: AcinoSet's cheetah gallop strides, and their noise

Verified against source: 2026-10-23. Data: AcinoSet (Joska et al., ICRA 2021,
arXiv 2103.13282), its FTE 3D trajectories, under the owner's D5a terms
(`SOURCES.md`). Everything fetched or derived sits in `~/mocap/acinoset/`, never
in the repository. The probe is `acino_strides.py`.

## What was fetched

- 90 `fte_pw/fte.pickle` files and their `reconstruction_params.json` (180
  files, 21 MB), found by walking the Dropbox folder the README links. Videos,
  2D labels and DLC outputs were skipped.
- Each file's size matched the listing. `~/mocap/acinoset/SHA256SUMS` (sha256
  `ad04186673454fbd…`, 182 lines with the two metadata pickles) holds every file's
  hash, and `LISTING.txt` (`19f29767f35da314…`) the folder as it stood.
- Each pickle holds the FTE's 20 points (eyes, nose, neck base, spine, tail
  base, mid and tip; per leg the girdle point, knee or elbow and the distal
  "ankle") in metres with z up, plus its 25-number state `x`, `dx` and `ddx`.
- **The model has no paws.** Its distal point is the wrist or hock.

**Frame rate, read from each file:** `dx / diff(x)` gives 90.0 for the 2017
takes and 120.0 for the 2019 takes. The DLC metadata says 90 and 119.88
(`~/mocap/acinoset/meta/`).

## The strides (12 Hz filter; `strides-12.json`, sha256 `c327844ac2f9d882…`)

The probe found 66 left-hind-to-left-hind strides across the 90 takes. **30 are
steady**: the heading turns under 10° and the speed changes under 10% between
the stride's halves, with each foot landing once.

- Speeds run from 5.20 to 14.17 m/s.
- **20 are rotary** gallops: every steady stride from 8.9 m/s up except
  `2019_02_27/ebony/run` at 13.7 m/s, plus one at 7.05 m/s.
- The rotary order is LH, LF, RF, RH (read cyclically: RH lands at phase
  0.84–0.92, just before LH, so the hind pair goes R then L and the fore pair L
  then R).
- **10 are transverse**, and they are the slow ones: all 7 from 5.20 to
  6.74 m/s, then 7.86, 8.50 and the 13.7 m/s exception. Two orders appear:
  - LH, RH, LF, RF (RH at 0.07–0.18);
  - LH, RF, LF, RH (RF at 0.05–0.10, on `cetane` and `zorro`).

The four slowest steady strides are the ones that reach leo's range:

| take | frames | v (m/s) | period (s) | order | gait | flight | hip (m) | Fr | leo at equal Fr (m/s) |
|---|---|---|---|---|---|---|---|---|---|
| 2017_12_12/top/cetane/run1_2 | 146–188 | 5.20 | 0.467 | LH RF LF RH | transverse | 0.43 | 0.49 | 5.7 | 4.69 |
| 2017_09_02/top/phantom/run1_2 | 71–109 | 5.84 | 0.422 | LH LF RH RF | transverse | 0.50 | 0.40 | 8.8 | 5.85 |
| 2017_12_12/top/cetane/run1_2 | 106–146 | 5.87 | 0.444 | LH RF LF RH | transverse | 0.43 | 0.49 | 7.2 | 5.29 |
| 2017_09_03/bottom/zorro/run2_1 | 32–73 | 6.08 | 0.456 | LH RF LF RH | transverse | 0.54 | 0.47 | 8.0 | 5.56 |

The full table of 30 strides is the probe's output.

- **Faster strides.** The next fastest are 6.3–6.7 m/s (leo 6.1–6.3 m/s). The
  rotary strides start at 7.05 m/s (leo 6.3). They lie above leo's 5 m/s command
  range.
- **The leo speeds are upper bounds.**
  - "hip" is the hind hip's height over the hind distal points' floor. That
    point is the hock, which stands above the planted paw by the metatarsus. The
    model does not carry the metatarsus, and this probe does not measure it.
  - So the cheetah's true hip height is greater. Its Froude number, and the
    leo-equivalent speed (v·√(0.396 / hip)), are smaller than shown.
- **Footfalls come from the hock and wrist, not the paw.** A point counts as
  down while it is within 40 mm of its floor and moving at under 0.35 of the
  trunk's speed. Both stop for only part of the paw's stance, so:
  - duty reads short (median 0.15 / 0.16 fore, 0.12 / 0.12 hind);
  - flight reads long (0.41–0.70).

  The touchdown order is what is claimed, not stance length. C4's retarget must
  supply the paw below the hock and find stance from it.

## Noise, and what the filter does

The FTE is already a smoothed estimate: a fixed-length kinematic model fitted
with a motion prior. The probe ran the same scan at three cutoffs of a
zero-phase 4th-order Butterworth low-pass, with medians over the 90 takes:

| cutoff | removed, head / trunk / tail / knees / distal (mm RMS) | raw acceleration power above cutoff | strides found / steady |
|---|---|---|---|
| 16 Hz | 0.1 / 0.3 / 1.2 / 1.3 / 1.9 | 0.03 | 71 / 33 |
| **12 Hz** | **0.3 / 0.9 / 3.6 / 4.0 / 5.5** | **0.11** | **66 / 30** |
| 8 Hz | 1.4 / 3.5 / 11.8 / 13.8 / 17.5 | 0.35 | 44 / 18 |

- **The noise is small.** Counting everything above 12 Hz as noise, it is at
  most 5.5 mm RMS at the distal points and 0.9 mm on the trunk. Above 16 Hz it is
  under 2 mm.
- **12 Hz removes it without cutting motion.**
  - 12 and 16 Hz share 22 steady strides, with the same frames and footfall
    order on all 22.
  - At 8 Hz the filter starts to remove the motion itself: strides found drop
    from 66 to 44, steady ones from 30 to 18, and the residual triples.
  - 12 Hz is about four harmonics of a ~3 Hz stride (periods 0.24–0.49 s).
- **The hock and wrist move about 43 mm (median) over a detected stance.** That
  is real motion, the joint rolling over the planted paw, not noise. The filter
  leaves it unchanged (47 mm filtered, ~2 m/s RMS either way). So planted-foot
  slip cannot be read off this model's points. C4's retarget measures slip on the
  paw it places.

## What this means for C4's retarget

- The cheetah's slowest steady gallops are **transverse**. Its rotary gallop
  starts above 7 m/s, i.e. above 6 m/s on leo even before the hip height bias.
  The dog clip in C3 is rotary at 2.8–4.2 m/s.
- So a cheetah reference in leo's range is a transverse gallop near leo's top
  command (about 4.7–5.9 m/s at the bound, less once the hip height is
  corrected). It is not a slower one: this capture has no cheetah stride under
  5.2 m/s that reads as steady.
- The spine is in the data (neck base, spine and tail base points, and the
  state's torso angles), for `j_spine` / `j_spine_yaw`.
- Two things were open for the retarget, and neither could be measured from
  this model: the paw below the hock and wrist, and the true hip height. The
  retarget below works around both, and says what that costs.

## The retarget (acino_retarget.py)

`acino_retarget.py` reads one stride into the shape `retarget.py` reads the
dog's in, and hands it to the same function (`retarget.retarget`, which now
takes a stride from any capture; the dog's `gallop27` clip comes out
byte-identical, `a88ad380…`). Same trunk, spine, foot-hold and leg solve as C2.
What differs is the cheetah's model:

- **No paw.** A planted-pivot paw (a fixed-length segment below the wrist or
  hock, turning about a point on the floor, fitted to every stance's arc) was
  tried and is ill-posed: floor height and segment length trade off on arcs of
  5–8 frames. On cetane it fitted a 34 mm fore and 81 mm hind segment, 12.8 mm
  RMS; on zorro and phantom it diverged (floors at −288 m and −1423 m). So
  **leo's paw follows the wrist and hock**, each over its own stance level.
- **Scale.** Each girdle's height is its pivots over its own wrists' or hocks'
  floor (0.48–0.53 m on cetane and zorro). `s` is 0.70–0.76 fore and
  0.82–0.83 hind. The cheetah's true pivot height is greater by the planted
  wrist's or hock's height, so `s` is too large. Leo's speed, at equal Froude
  number, is therefore an upper bound.
- **Stance is the wrist or hock stopped** (`acino_strides.py`'s rule: 40 mm,
  0.35 of trunk speed, 25 ms gaps closed). So duty reads short (0.12–0.19) and
  flight long (0.46). The clip teaches leo that long a flight; C3's dog clips
  carry 0.15–0.27.
- **Raw slip is the wrist's or hock's roll** over the planted paw, not paw
  slip. Through stance the target is held still, as for the dog.
- **12 Hz filter**, as measured above.

The three slowest steady strides share the order **LH, RF, LF, RH**. Two
windows start two frames before the strides table's, so that LH lands inside
the window's first sample, as it does in cheetah52 (it read 0.96 otherwise and
crossed the order check). phantom's order (LH, LF, RH, RF) crosses theirs, so
it is measured but not taken.

| clip (take, frames) | cheetah m/s, Fr | leo m/s, period, Fr | touchdown LH RF LF RH | duty LF/RF/LH/RH | flight |
|---|---|---|---|---|---|
| cheetah52 (cetane run1_2, 146–188) | 5.20, 5.71 | 4.63, 0.416 s, 5.65 | 0.04 0.08 0.35 0.77 | 0.19/0.15/0.12/0.15 | 0.46 |
| cheetah59 (cetane run1_2, 104–144) | 5.90, 7.40 | 5.20, 0.392 s, 7.13 | 0.04 0.12 0.38 0.85 | 0.15/0.15/0.12/0.15 | 0.46 |
| cheetah61 (zorro run2_1, 30–71) | 6.10, 7.80 | 5.33, 0.398 s, 7.49 | 0.00 0.15 0.46 0.88 | 0.12/0.15/0.19/0.12 | 0.46 |
| cheetah58 (phantom run1_2, 71–109), not taken | 5.82, 8.29 | 5.66, 0.411 s, 8.45 | 0.04 0.04(RF) 0.27(LF) 0.81 | 0.19/0.12/0.12/0.12 | 0.58 |

Slip, miss, limits and stops, in mm (`<label>.measure.json`; miss per sample
is in `foot_miss_mm.per_sample`):

| clip | raw roll max LF/RF/LH/RH | solved slip max | foot miss max LF/RF/LH/RH (share > 5 mm) | miss in stance | violations, loops | paw pin at stop L/R | seam max / step |
|---|---|---|---|---|---|---|---|
| cheetah52 | 44 / 19 / 42 / 35 | 0.0 | 5 / 0 / 2 / **46 (0.46)** | none | 0, 0.001 | 0.73 / 0.35 | 18° / 29° (`j_elbow_l`) |
| cheetah59 | 14 / 11 / 40 / 60 | 2.8 (LH) | 11 (0.12) / 0 / 7 (0.12) / **36 (0.35)** | none | 0, 0.011 | 0.65 / 0.54 | 25° / 30° (`j_shoulder_l`) |
| cheetah61 | 46 / 25 / 67 / 37 | 0.0 | 28 (0.35) / 0 / 23 (0.31) / **61 (0.54)** | none | 0, 0.000 | 0.69 / 0.46 | 17° / 36° (`j_ankle_r`) |
| cheetah58 | 20 / 16 / 29 / 55 | 0.5 | 51 / 30 / 44 / **135** | none | 0, 0.000 | 0.62 / 0.27 | 30° / 36° (`j_elbow_l`) |

How to read it:

- **No joint leaves its range.** The loops stay closed (≤ 0.011 mm), and
  **no foot misses in stance**. Every miss falls in swing.
- **The right hind is what leo cannot follow.**
  - It misses 36–61 mm over the first 0.35–0.54 of the stride, through early
    swing, after push-off.
  - There the cheetah's right hock trails its hip by up to 0.42 m
    (cheetah52, before scaling; the left reaches 0.38 m). Leo's `j_hip_r`
    sits at its stop on 0.35–0.42 of samples, `j_ankle_r` on 0.27–0.31 and
    `j_hhaa_r` on 0.15–0.42.
  - On the dog it was the other way round: the hind legs followed (misses
    ≤ 0.1 mm, but gallop42's LH) and the fore legs missed 46–75 mm. The
    cheetah's fore legs follow, except cheetah61's LF at 28 mm.
- **Spine.** The cheetah bends 6–12° in pitch and 12–31° in heading through a
  stride, and leo's `j_spine` takes −2.6…+3.3° and `j_spine_yaw` −13…+18°
  (of ±20°). Nothing is clipped.
  - Against the dog's 40–43° pitch bend (C2), the cheetah's is small. That is
    the FTE's spine: one point between neck base and tail base, so a
    two-segment back. It is not a reading of the cheetah's flexion, which is
    known to be large.
- **The paw pin sits at its stop** on 0.65–0.73 of samples on the left and
  0.35–0.54 on the right. The dog's three strides read 0.61–0.73 on both
  sides. As in C3, this is the pin's home (its upper stop), asked for by the
  clip, not strain.

## The C4 bundle

`~/mocap/acinoset/c4-bundle/mocap_gallop-task.json` (sha256
`e6a04ce8ffc54fd4b43742440785c1463f5d5f6524f4e62b072e4ed83ee806c4`; model XML
`59bc5407…`, leo v05, unchanged). It was built by `c3_bundle.py` from b1-s2's
`speed-task.json`, exactly as C3's was, and it stays in `~/mocap/` (D5a).

- **Strides:** cheetah52, 59 and 61 at 4629 / 5199 / 5328 mm/s, periods
  0.416 / 0.392 / 0.398 s, 26 samples each, 78 reset rows. The first reset
  rows move forward at 4.99 / 5.41 / 6.40 m/s.
- **Goal:** `cmd` 4629–5328 mm/s, in the task and in its success spec. That
  is above B1's 5 m/s top, because the capture has no steady stride slower
  than 5.2 m/s (4.63 on leo).
- **Reward:** C3's 13 rows (D4's ten plus `track_pose`, `track_lift`,
  `track_contact`), no style term. The footfall order check passes, and every
  row compiles.
- **Not trained yet.** It launches after c3-s1 ends and is judged (D1, D7),
  by `queue_bundle.py` as c3-s1 was.

Reproduce (`A=~/mocap/acinoset`, `M` = c3-s1's `cat_model-model.xml`):

```
pixi run python -I docs/probes/orun18/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 146 188 cheetah52 $A/retargeted 26
pixi run python -I docs/probes/orun18/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 104 144 cheetah59 $A/retargeted 26
pixi run python -I docs/probes/orun18/acino_retarget.py $M $A/2017_09_03/bottom/zorro/run2_1/fte_pw/fte.pickle 30 71 cheetah61 $A/retargeted 26
pixi run python docs/probes/orun18/c3_bundle.py ~/cadex-projects/leo/runs/b1-s2/train/speed-task.json \
  $A/c4-bundle mocap_gallop $A/retargeted/cheetah{52,59,61}.clip.json
```

| file (outside the repo) | sha256 |
|---|---|
| `cetane/run1_2/fte_pw/fte.pickle` | `8ceb3ff8f7689997…` (whole in `~/mocap/acinoset/SHA256SUMS`) |
| `zorro/run2_1/fte_pw/fte.pickle` | `9026e5788c49e629…` |
| `cheetah52.clip.json` | `0df87d2773d77363914bb8f2de440d315814273612364e11dd3766d48ae9f5a9` |
| `cheetah59.clip.json` | `ef6917882a648e48be112d5a0163574e84cff5478406b457953fb5db067d0726` |
| `cheetah61.clip.json` | `dae3366bbda8cc7af8b4e60fd899638fc4afa3858c93db44712019bf3448fb29` |
| `cheetah58.clip.json` (not taken) | `d0eff867dd3208a8c4d6d9ee0c5d5d720bc5f02f993f2e750d9ed4c08faccf3e` |

## The film

`retarget_film.py` now takes an AcinoSet `fte.pickle` wherever it took a BVH,
reading the stride through `acino_retarget.cheetah_stride`, so the film shows
exactly the retargeted clip. The FTE skeleton gained a drawing tree
(`SKELETON_PARENT`: spine to the girdles and down each leg, head and tail
left out as for the dog). The tree is only for drawing: cheetah59's clip and
measure re-run byte-identical (`ef691788…`). Each of the three strides plays
three times at real time and once at 1/4 speed.

`~/mocap/films/c4-cheetah-strides.webm` is 8.4 s long, 506 frames at 60 fps,
with every frame decoded (sha256
`24902f6f1d58cc591773436b0b97d163898a4d89b917212687540421d2c78217`). It is a
drawing of AcinoSet's data, so it stays out of the repository (D5a) and goes
on the run's page. What it shows:

- **The grey cheetah ends at the wrist and hock.** It is scaled by the mean of
  the fore and hind `s`, and each half stands over its own distal floor. Its
  distal points can therefore dip under the floor line while rolling.
- **Leo's paws follow those points**, and its spine bends with the cheetah's.
  The misses are measured in the table above; the film is a drawing, not a
  measurement of them.

```
M=~/cadex-projects/leo/runs/b1-s2/train/cat_model-model.xml   # 59bc5407, c3-s1's model too
pixi run python docs/probes/orun18/retarget_film.py $M ~/mocap/films/c4-cheetah-strides.webm 26 3 4 \
  $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle:146:188:cheetah52 \
  $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle:104:144:cheetah59 \
  $A/2017_09_03/bottom/zorro/run2_1/fte_pw/fte.pickle:30:71:cheetah61
```

Still open for C4: the cheetah screen and its judgement beside C3, sgt-4-120
and B1.
