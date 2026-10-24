# orun19 M1: AcinoSet's cheetah strides retargeted to leo v06

Verified against source: 2026-10-23. Charter M1 and O4. This covers the
retarget, its measurements and the M1 task bundle, with no training. The
training and film come later. The data is AcinoSet (Joska et al., ICRA 2021), under the
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
- **The tail is mapped; the head is measured** (below, "The tail and the
  head").

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

Re-running cheetah59 gives the same clip byte for byte (`aa81d5ad…`, with the tail).

## The tail and the head (O4)

The capture has three tail points (base, mid, tip) and the eyes and nose.

**The tail** (`map_tail`). The capture's tail chord, base to tip, is read
against its pelvis in pitch and heading, about the stride's mean, as the spine
is. It goes to `j_tail1` (pitch) and `j_tail2` (yaw), the speed task's two
tail actions, by leo's own gains. Those gains are measured on leo's tail
chord (`j_tail1`'s anchor to `c_tail_tip`'s centre of mass, against
`c_pelvis_frame`) with the model's cable couplings applied: `j_tail3p`…`7p`
follow at 0.4 × `j_tail1`, `j_tail3`…`7` follow `j_tail2`. The followers are
written into the clip's `qpos` as the cables hold them.

- Gains: −1.80 (pitch) and +2.85 (yaw) degrees of chord per degree of drive.
- About the mean, so leo's tail swings about its own home carriage. The
  cheetah's mean carriage is not copied, which keeps the speed task's `tail`
  term (tail off the floor) meaningful.

| clip | capture pitch / heading vs pelvis (deg) | `j_tail1` (deg) | `j_tail2` (deg) | clamped | seam `j_tail1` / `j_tail2` |
|---|---|---|---|---|---|
| cheetah52 | −5.0…24.9 / 0.7…20.1 | −7.0…9.6 | −3.0…3.8 | 0 | 6.2° / 0.8° |
| cheetah59 | −6.1…31.2 / 2.5…17.2 | −9.5…11.3 | −1.8…3.4 | 0 | 4.8° / 2.2° |
| cheetah61 | 27.6…42.4 / −19.5…14.6 | −4.0…4.2 | −5.3…6.6 | 0 | 1.8° / 4.3° |
| cheetah58 (not taken) | −1.5…18.1 / 23.1…42.4 | −5.8…5.2 | −1.7…5.1 | 0 | – |

- No sample reaches a stop (`j_tail1` −30…35°, `j_tail2` ±25°, followers
  ±15° and ±25°).
- The largest step between samples is 3.3°.
- The seam is the capture's own: its tail does not close over one stride.

**The head is measured, not posed** (`measure_head`). The capture's head
chord (neck base to nose) against its thorax reads, in pitch / heading:

- cheetah52: −9.8…3.2° / −7.7…−6.6°
- cheetah59: −4.9…7.4° / −7.6…−5.6°
- cheetah61: −0.6…12.0° / −10.2…−4.1°

The cheetah holds its head within about 13° in pitch and 6° in heading over a
stride. leo's speed task (S1's, unchanged) holds `j_neck1`, `j_neckyaw` and
`j_headpitch` at home: they are drives, not actions. A posed head could not be
tracked, and a reset row off the hold would only start the head away from
where the drive pulls it. Posing it needs three more actions in the task.
That is a task change beyond S1's, so it is left for a screen of its own if M1
asks for it.

The legs, spine and every measure above are unchanged by the tail. The four
clips were re-run, and their foot misses, limits, seams and heel shares are
identical to the tables above. Only the clips' hashes moved.

## The M1 bundle

`~/mocap/acinoset/m1-bundle/mocap_gallop-task.json` (sha256
`c3c099af5b25c19c84e0df45857845a8e4ac8787ec65e344ba4a4477f793850e`), with
model XML `f9b8ab82…` (leo v06, unchanged). It was built by `m1_bundle.py`
from s1-v06's `speed-task.json` (`bca307a2…`). It carries the clips, so it
stays in `~/mocap/` (D5a).

`m1_bundle.py` is orun18's `c3_bundle.py`, run unchanged: the engine's own
tracking, schedule, reset and reward compilers, and the footfall-order
refusal. Only its three tracking terms are rewritten for v06:

- **`track_pose`** drops the `("wrist", "carpus")` row and adds `q_tail1` and
  `q_tail2`. That gives 19 squared errors, as sgt-4's had, so the divisor
  stays 17100.
- **`track_lift`** offsets each foot body's centre of mass by its height
  over the ball's lowest point at v06's keyframe. That is 20.9 mm fore and
  29.3 mm hind, measured on the bundle's model. v05's paws used 22 and 16.
- **`track_contact`** is unchanged.
- The weights are sgt-4's: 1.5, 1.5 and 10.

What the bundle holds:

- **Strides:** cheetah52, 59 and 61 at 4629 / 5199 / 5328 mm/s, 26 samples
  each.
- **Goal:** `cmd` from 4629 to 5328 mm/s, in the task and in its success
  spec.
- **Reward:** 13 rows, S1's ten plus the three tracking terms. There is no
  style term, and every row compiles.
- **Tracking channels:** 30 in all, a 26 × 28 table:
  - the clock;
  - 20 joint references (16 leg, `q_spine`, `q_spine_yaw`, `q_tail1`,
    `q_tail2`);
  - 4 lifts and 4 downs.
- **Reset rows:** 78, with a random start.

Checked with the engine's readers on the bundle:

- `schedule_blend` at 4629 / 5000 / 5328 mm/s gives stride 0 at w 0.00,
  stride 0 at w 0.65, and stride 1 at w 1.00.
- `judged_reference` gives cheetah52 / cheetah59 / cheetah61.
- All 78 reset rows run `mj_forward` with finite accelerations. Row 30
  starts at 5.19 m/s forward, with the tail at 2.7° / 0.6°.
- The table's tail columns span the clips' ranges (`q_tail1_ref` −7.0…9.6°,
  `q_tail2_ref` −3.0…3.8°).

The bundle is not trained yet. The trainer has not loaded it, because
s1-v06 holds the GPU. It launches after s1-v06 ends and is judged.

The clips span 4.63–5.33 m/s on leo. At the fast end that is above S1's
5 m/s top, as it was on v05, because the capture holds no steady stride under
5.2 m/s.

## Reproduce

```
A=~/mocap/acinoset; O=$A/retargeted-v06
M=~/cadex-projects/leo/runs/s1-v06/train/cat_model-model.xml   # f9b8ab82…, leo v06
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 146 188 cheetah52 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_12_12/top/cetane/run1_2/fte_pw/fte.pickle 104 144 cheetah59 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_09_03/bottom/zorro/run2_1/fte_pw/fte.pickle 30 71 cheetah61 $O 26
pixi run python -I docs/probes/orun19/acino_retarget.py $M $A/2017_09_02/top/phantom/run1_2/fte_pw/fte.pickle 71 109 cheetah58 $O 26
pixi run python -I docs/probes/orun19/m1_bundle.py ~/cadex-projects/leo/runs/s1-v06/train/speed-task.json \
  $A/m1-bundle mocap_gallop $O/cheetah{52,59,61}.clip.json
```

| file (outside the repo) | sha256 |
|---|---|
| `cetane/run1_2/fte_pw/fte.pickle` | `8ceb3ff8f7689997…` (in full in `~/mocap/acinoset/SHA256SUMS`) |
| `zorro/run2_1/fte_pw/fte.pickle` | `9026e5788c49e629…` |
| `phantom/run1_2/fte_pw/fte.pickle` | `c02639c0ccd10a73…` |
| `retargeted-v06/cheetah52.clip.json` | `8ccbe89c6e61b584809aadd8634bd50174e647324eafc4a019c914f906e4e2f6` |
| `retargeted-v06/cheetah59.clip.json` | `aa81d5adacfd5def4ce461ffd7cdffff98fdb2326020ba2edd0ab61484599ee1` |
| `retargeted-v06/cheetah61.clip.json` | `81035ca2f1c9d53fc40c55eb0711bfbb4616f06bc2a9aad928d124cdeec95b5f` |
| `retargeted-v06/cheetah58.clip.json` (not taken) | `f185be63cb6897bedb5e1ab7b27e1bd35df114e467f17029116f3337c28d33ad` |
| `m1-bundle/mocap_gallop-task.json` | `c3c099af5b25c19c84e0df45857845a8e4ac8787ec65e344ba4a4477f793850e` |
