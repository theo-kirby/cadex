# orun19 M1: AcinoSet's cheetah strides retargeted to leo v06

Verified against source: 2026-10-23. Charter M1 and O4. This covers the
retarget and its measurements, with no training. The bundle, training and
film come later. The data is AcinoSet (Joska et al., ICRA 2021), under the
owner's D5a terms (`docs/probes/orun18/SOURCES.md`, unchanged). Clips and
measures stay in `~/mocap/acinoset/retargeted-v06/`, never in the repository.

## The probe

`acino_retarget.py` (this folder) wraps orun18's: `acino_retarget.cheetah_stride`
reads the stride (12 Hz low-pass, the wrist and hock as the paw, stance read
as the wrist or hock stopped), and `retarget.retarget` solves it. The trunk,
spine, foot-hold and clamped leg solve are the same, unchanged. It relabels the
clip "leo v06", records the model's hash and adds three v06 measures (below).

**O4 on v06 needed no change to the solve.** The solve reads each leg's chain
from the model, from the foot body to the trunk, and puts the foot body's
lowest collision geom on the target. In v06's MJCF (`f9b8ab82…`, s1-v06's
bundle):

- `c_paw_h*` holds only the hind ball (r 30 mm). The hind chain is `j_hhaa`,
  `j_hip`, `j_knee` and `j_ankle`, with the parallelogram's passive pins. Its
  loops stay closed: error 0.000 mm on every clip.
- `c_paw_f*` holds only the fore ball (r 22 mm) on the forearm. The fore chain
  is `j_fhaa`, `j_scap`, `j_shoulder` and `j_elbow`, with no wrist.
- The FTE model ends at the wrist and has no carpus or digit points. So O4's
  "carpus and digit angles dropped" drops nothing: the fore ball is fitted to
  the wrist's track.
- The spine goes to `j_spine` / `j_spine_yaw` as before.
- **The tail and head are not mapped.** The clip holds them at home, as
  orun18's did. The capture has three tail points and the eyes and nose, so
  O4's "where the capture has them" is open here, and M1's bundle tracks them
  at home.

The three added measures:

- the foot miss, split into stance and swing per leg;
- the hind heel pad's lowest point (r 16 mm, `c_heel_h*`) over the ground
  through each hind stance, and the share of stance samples with the pad
  within 5 mm of the ground;
- the hock's angle (`j_ankle`) through hind stance. The right leg's joints
  are mirrored, so its angle is negated to read as the left's.

## The clips (26 samples each)

| clip (take, frames) | leo m/s, period, Fr | s fore / hind | touchdown LF RF LH RH | duty LF/RF/LH/RH | flight |
|---|---|---|---|---|---|
| cheetah52 (cetane run1_2, 146–188) | 4.63, 0.416 s, 5.97 | 0.758 / 0.830 | 0.35 0.08 0.04 0.77 | 0.19/0.15/0.12/0.15 | 0.46 |
| cheetah59 (cetane run1_2, 104–144) | 5.20, 0.392 s, 7.53 | 0.718 / 0.834 | 0.38 0.12 0.04 0.85 | 0.15/0.15/0.12/0.15 | 0.46 |
| cheetah61 (zorro run2_1, 30–71) | 5.33, 0.398 s, 7.91 | 0.704 / 0.823 | 0.46 0.15 0.00 0.88 | 0.12/0.15/0.19/0.12 | 0.46 |
| cheetah58 (phantom run1_2, 71–109), not taken | 5.66, 0.411 s, 8.93 | 0.932 / 0.959 | 0.27 0.04 0.04 0.81 | 0.19/0.12/0.12/0.12 | 0.58 |

- **Speed, period, scale, duty and phase match orun18's v05 retarget**
  (c4-cheetah.md) to the digit. The capture and girdle heights set them, and
  v06 kept v05's girdle heights.
- **The Froude numbers are higher** (5.97 against v05's 5.65 on cheetah52).
  v06's hind hip stands 0.366 m over its ball's contact point; v05 stood
  0.396 m over its paw.
- The order is LH, RF, LF, RH, the transverse gallop of orun18's three. The
  speeds stay upper bounds, for the reason c4-cheetah.md gives: the FTE has no
  paw, so `s` is too large.

## What v06 follows, and where it misses (mm)

| clip | raw roll max LF/RF/LH/RH | solved slip max | miss in stance max LF/RF/LH/RH | miss in swing max LF/RF/LH/RH (share of stride > 5 mm) | violations | seam max / step |
|---|---|---|---|---|---|---|
| cheetah52 | 44 / 19 / 42 / 35 | 0.0 | 0 / 0 / 0 / 0 | **50** (0.31) / 18 (0.15) / 15 (0.12) / **58** (0.50) | 0 | 30° / 36° (`j_shoulder_l`) |
| cheetah59 | 14 / 11 / 40 / 60 | 6.2 (LH) | 0 / 0 / 6.2 / 0 | **39** (0.23) / 7 (0.04) / 21 (0.23) / **49** (0.38) | 0 | 28° / 36° (`j_ankle_r`) |
| cheetah61 | 46 / 25 / 67 / 37 | 0.2 | 0 / 0 / 0.2 / 0 | **96** (0.50) / 0 / **46** (0.46) / **77** (0.58) | 0 | 28° / 35° (`j_ankle_r`) |
| cheetah58 | 20 / 16 / 29 / 55 | 16.5 (RF) | 17 / 25 / 0 / 8 | 74 / 88 / 59 / **150** | 0 | 40° / 46° (`j_shoulder_l`) |

Joints at a stop, as a share of samples (cheetah58 is left out):

| clip | hind L: hhaa hip knee ankle | hind R: hhaa hip knee ankle | fore L: fhaa scap shoulder elbow | fore R: fhaa scap shoulder elbow |
|---|---|---|---|---|
| cheetah52 | 0 0.23 0.08 0.15 | 0.31 0.42 0 0.35 | 0 0.42 0.38 0.08 | 0 0.12 0.23 0.04 |
| cheetah59 | 0.12 0.27 0.15 0.23 | 0.15 0.38 0.12 0.35 | 0 0.27 0.31 0.27 | 0 0.12 0.08 0.12 |
| cheetah61 | 0.15 0.31 0.31 0.46 | 0.42 0.42 0.19 0.46 | 0.15 0.27 0.35 0.35 | 0 0 0 0 |

How to read it:

- **No joint leaves its range**, and the loops stay closed.
  - On the three taken clips, no foot misses in stance by more than 6.2 mm
    (cheetah59's LH). Stance holds.
  - Every larger miss falls in swing, where a stop costs reach.
- **The right hind misses as it did on v05** (58 / 49 / 77 mm against v05's
  46 / 36 / 61). It falls in early swing, after push-off, with `j_hip_r` at
  its stop on 0.38–0.42 of samples. The cheetah's hock trails its hip further
  than leo's hip can swing back.
- **The fore leg is what v06 changed.**
  - v05's fore paw missed at most 11 mm on cheetah52 and cheetah59, and 28 mm
    on cheetah61's LF. On v06 the LF misses 50 / 39 / 96 mm, in swing, over
    0.23–0.50 of the stride.
  - The LF's scapula and shoulder sit at a stop on 0.27–0.42 of samples. With
    no wrist, the swing's lift and reach come from the scapula, shoulder and
    elbow alone.
  - This is the limit the charter named for the engine's own trot and gallop
    ("the fore foot cannot lift 40 mm with scapula or elbow at a stop").
  - The RF follows (≤ 18 mm). On this capture the left fore swings more
    widely than the right.
- **The clip asks for a toe stance.**
  - The heel pad stays 109–141 mm over the ground through every hind stance
    of all four clips. It touches on 0.0 of stance samples.
  - The hock reads −4…+40° (left convention) in stance, never near the −40°
    where ball and pad touch together.
  - The reason: the capture's hock is mapped to leo's ball, so nothing in the
    clip sets the metatarsus's angle. The solve's pull toward home keeps it at
    home, where the pad sits 109 mm over the ball's contact (measured at the
    keyframe).
  - This holds for a cheetah, which stands digitigrade. Whether v06's pad
    carries load is a measurement for the trained policy (S1's heel share),
    not for this clip.
- **The spine** takes `j_spine` −2.6…+3.3° and `j_spine_yaw` −12.9…+18.2°
  (of ±20°), with nothing clipped. This equals v05's.
- **cheetah58 stays out**, as on v05. Its order (LH, LF, RH, RF) crosses the
  others', and it misses in stance (RF 25 mm).

Re-running cheetah59 gives the same clip byte for byte (`a7d61231…`).

## For M1's bundle (next)

- `c3_bundle.py` maps orun18's reward terms over named joints, including
  `("wrist", "carpus")`, which v06 does not have. Its v06 copy must drop that
  row. It is built from `runs/s1-v06/train/speed-task.json`.
- The clips span 4.63–5.33 m/s on leo. That is above S1's 5 m/s top at the
  fast end, as on v05, because the capture holds no steady stride under
  5.2 m/s.

## Reproduce

```
A=~/mocap/acinoset; O=$A/retargeted-v06
M=~/cadex-projects/leo/runs/s1-v06/train/cat_model-model.xml   # f9b8ab82…, leo v06
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 146 188 cheetah52 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 104 144 cheetah59 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_09_03/bottom/zorro/run2_1/fte_pw/fte.pickle 30 71 cheetah61 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_09_02/top/phantom/run1_2/fte_pw/fte.pickle 71 109 cheetah58 $O 26
```

| file (outside the repo) | sha256 |
|---|---|
| `cetane/run1_2/fte_pw/fte.pickle` | `8ceb3ff8f7689997…` (in full in `~/mocap/acinoset/SHA256SUMS`) |
| `zorro/run2_1/fte_pw/fte.pickle` | `9026e5788c49e629…` |
| `phantom/run1_2/fte_pw/fte.pickle` | `c02639c0ccd10a73…` |
| `retargeted-v06/cheetah52.clip.json` | `01b4b5e2b096f595def90ffbe4ba681a80bb476cca433e656f72b99488daf295` |
| `retargeted-v06/cheetah59.clip.json` | `a7d6123160206b0d4b2633d9db8d989171cdf7694520b8044da4316642618c61` |
| `retargeted-v06/cheetah61.clip.json` | `0456beee37e2a0a252162998f8cdae3a6fb056c7e5f0b94d94c9d5be84ff9850` |
| `retargeted-v06/cheetah58.clip.json` (not taken) | `82b6d0645fed02a515b1e7aca8279b4de7cb0e484c0c0a31d7ad5910074f9430` |
