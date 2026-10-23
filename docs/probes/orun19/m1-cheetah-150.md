# orun19 M1: m1-cheetah judged at 50 and 150; it gallops transverse on the cheetah's strides at 4.25–4.37 m/s, holds the slowest stride's command and plateaus above it

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 15).
Charter M1's judgement of `m1-cheetah`: the M1 bundle (`m1-retarget.md`,
`c3c099af`: the speed-only task plus the reference tracking terms on the
cheetah's cheetah52/59/61 strides retargeted to v06, no style term), trained
cold, seed 0, 4096 envs, 150 iterations. Judged at its midpoint and its end
beside S2's best, `s2a-hold-150` (`o3-reread.md`), and v05's `b1-s2-180`
(`../orun18/b1-s2-180.md`), under the revised O3 (over the command is never a
miss). The judge ran on the CPU while M2 trained on the GPU.

```
R=~/cadex-projects/leo/runs/m1-cheetah/train; E=~/cadex-projects/leo/evaluations
cp $R/mocap_gallop.000050.cxpolicy ~/orun19-queue/m1-cheetah-50.cxpolicy             # f88c1e8c
cp $R/mocap_gallop.000150.cxpolicy ~/orun19-queue/m1-cheetah-150.cxpolicy            # a1b5218a = mocap_gallop.cxpolicy
for n in 50 150; do CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun18/speed_judge.py \
    ~/cadex-projects/leo $R ~/orun19-queue/m1-cheetah-$n.cxpolicy m1-cheetah-$n --task mocap_gallop --cmd 4630 5000 5328; done
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py $E m1-cheetah-50 m1-cheetah-150 s2a-hold-150
python3 docs/probes/orun19/s1_tables.py $E/m1-cheetah-150-{4630,5000,5328}
python3 docs/probes/orun19/ref_tables.py $E/m1-cheetah-150-{4630,5000,5328}
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun18/b1_summary.py $E/m1-cheetah-150-{4630,5000,5328}
```

**The commands.** The bundle's `cmd` spans the strides' leo speeds,
4629.06–5328.04 mm/s, and `speed_judge.py` takes integer commands inside it:
4630 (cheetah52, the slowest stride), 5000 (a blend, and the command
s2a-hold-150 and b1-s2-180 were judged at) and 5328 (cheetah61, the
fastest). Nothing slower can be commanded on this bundle, so the 0.7–3.5 m/s
columns of S2 have no M1 twin. `ref_tables.py` (new, this iteration) reads
the engine's own `detail.reference` per seed: phase error and missed strides
per foot against the clip's footfall, stride Hz and duty against the
clip's.

## The checkpoints

| | iteration 50 | iteration 150 |
|---|---|---|
| policy (the evaluations' `policy_sha256`) | `f88c1e8c` | **`a1b5218a`** (= `mocap_gallop.cxpolicy`) |
| reward per step; σ; episode steps | 15.16; 0.73; 282 | 27.95 (at 149); 0.52; 385 |
| trained task; model | `c3c099af`; `f9b8ab82` (leo v06) | the same |

## Speed, and O3

A fall here is an episode that does not complete (`tipped`) as well as the
engine's `falls` (which counts only after the 1 s settle), as in
`../orun18/c3-s1-50.md`.

| command m/s | 4.63 | 5.00 | 5.33 |
|---|---|---|---|
| **m1-cheetah-150, last 2 s m/s, median (min / max)** | **4.25** (4.23 / 4.26) | **4.37** (4.32 / 4.43) | **4.36** (4.33 / 4.39) |
| slowest seed / command; seeds ≥ 0.9 × command; falls | 0.914; 10/10; 0 | 0.864; 0/10; 0 | 0.813; 0/10; 0 |
| tracks (revised O3) | **yes** | no | no |
| mean forward m/s over the episode; max tilt ° (median) | 4.25; 9.8 | 4.38; 10.9 | 4.37; 10.8 |
| m1-cheetah-50, last 2 s m/s median (min / max); falls | 1.11 (0.00 / 2.75); 3 | 1.24 (0.00 / 2.28); 2 | 1.60 (0.13 / 3.14); 9 |
| s2a-hold-150 (S2's best), last 2 s m/s median | – | 4.53 (9/10 ≥ 0.9) | – |
| v05 b1-s2-180, last 2 s m/s median | – | 1.62 | – |

**At 150 it holds the slowest stride's command and no faster one.** Speed
barely moves with the command: 4.25 → 4.37 → 4.36 m/s across 4.63–5.33
commanded, every seed within 0.1 m/s of its command's median, 0 falls on 30
seeds. Under O3 it tracks one command (4.63), and its top held speed is
4.37 m/s (Fr 4.92 on v06's hip height 0.396 m, as in `s1-v06-180.md`). At
5.0 it is 0.16 m/s slower than s2a-hold-150 (4.53) and 2.7× v05's B1
(1.62). **At 50 it is not standing yet:** 14 of 30 episodes tip (3, 2 and 9
by command), the rest run 1.1–1.6 m/s.

## Footfall against the clip

From `s1_tables.py` and `ref_tables.py` at 150 (t ≥ 4 s for the phases):

| command m/s | 4.63 | 5.00 | 5.33 |
|---|---|---|---|
| touchdown phase of RH / LF / RF in LH's stride | 0.75 / 0.38 / 0.19 | 0.79 / 0.40 / 0.20 | 0.80 / 0.40 / 0.20 |
| stride Hz, policy / clip | 2.38 / 2.40 | 2.50 / 2.55 | 2.50 / 2.51 |
| step advance mm LF / RF; LH / RH | 1194 / 1481; 1750 / 1742 | 1227 / 1471; 1730 / 1724 | 1230 / 1482; 1718 / 1708 |
| touchdown Hz LF / RF; LH / RH | 4.8 / 4.3; 2.4 / 2.4 | 5.0 / 4.3; 2.6 / 2.5 | 5.0 / 4.7; 2.6 / 2.5 |
| **missed strides LF / RF / LH / RH** (of strides counted, 10 seeds) | **120 / 48 / 0 / 0** of 208 | **44 / 37 / 0 / 0** of 217 | **37 / 21 / 0 / 0** of 217 |
| phase error LF / RF / LH / RH (stride share, median) | 0.50 / 0.13 / 0.00 / 0.02 | 0.05 / 0.13 / 0.00 / 0.06 | 0.06 / 0.20 / 0.00 / 0.08 |
| duty LF / RF / LH / RH (clip) | 0.19 / 0.10 / 0.15 / 0.16 (0.15) | 0.18 / 0.10 / 0.15 / 0.16 (0.14) | 0.17 / 0.10 / 0.15 / 0.17 (0.14) |
| flight share; flight s | 1.00; 0.10 | 1.00; 0.16 | 1.00; 0.16 |
| heel pad share of hind stance LH / RH; pad height mm | 0.00 / 0.00; 133 / 133 | 0.00 / 0.00; 133 / 131 | 0.00 / 0.00; 134 / 133 |

- **The footfall order is the clip's.** LH, RF (0.20), LF (0.40), RH
  (0.79): transverse, as the cheetah's strides are (`m1-retarget.md`: LH,
  RF, LF, RH). A flight phase every stride, 0.10–0.16 s.
- **The stride is the clip's** (2.38–2.50 Hz against 2.40–2.55), with
  ~1.7 m hind step advance. Speed is held by stride frequency, and the
  frequency stays at the clip's: that is the plateau.
- **The hind feet hit every stride (0 misses on 642). The fore feet miss.**
  They touch down twice a stride (4.3–5.0 Hz against 2.4–2.6), so the
  engine reads 21–120 of ~210 strides missed per fore foot; the left fore
  is the worse at 4.63 (phase error 0.50). The retarget already showed
  v06's left fore the hardest to fit in swing (39–96 mm, `m1-retarget.md`).
- **The heel pad is never used**, as in every v06 policy so far and the
  clip itself.

At 50 (not tabled): the order is not yet settled (RH / LF / RF at 0.19–0.61
/ 0.38–0.63 / 0.63–0.72), stride Hz 2.5–3.8 against the clip's 2.4–2.6, and
every foot but the left hind misses 20–84 strides.

## O6: torque, left against right, a clean simulation (150)

| command m/s | 4.63 | 5.00 | 5.33 |
|---|---|---|---|
| worst RMS / rated (drive); peak margin | 1.48 (`j_spine`); 0.00 | 1.53 (`j_spine`); 0.00 | 1.48 (`j_spine`); 0.00 |
| drives at their clamp ≥ 0.05 of frames (seed median) | `j_elbow_l` 0.16, `j_tail2` 0.14, `j_knee_l` 0.13, `j_knee_r` 0.08, `j_hip_l` 0.07, `j_spine_yaw` 0.07, `j_hip_r` 0.06, `j_hock_l` 0.05, `j_shoulder_l` 0.05, `j_hock_r` 0.05 | `j_elbow_l` 0.15, `j_knee_l` 0.13, `j_knee_r` 0.12, `j_tail2` 0.10, `j_hip_l` 0.09, `j_spine_yaw` 0.09, `j_hock_l` 0.06, `j_hock_r` 0.05, `j_shoulder_l` 0.05 | `j_elbow_l` 0.14, `j_knee_r` 0.13, `j_knee_l` 0.12, `j_hip_l` 0.09, `j_hock_r` 0.08, `j_tail2` 0.07, `j_hock_l` 0.07, `j_shoulder_l` 0.05 |
| hind rod loop gap max mm; cable gap max ° (`coupling/cable_tail4`) | 1.8; 3.4 | 1.9; 3.0 | 1.9; 3.1 |
| falls; non-finite seeds | 0; 0 | 0; 0 | 0; 0 |

RMS over rated, seed median, left / right (`b1_summary.py`; its `nan` rows,
the wrist v06 does not have and `j_tail2`, are dropped):

| drive | 4.63 | 5.00 | 5.33 |
|---|---|---|---|
| fore abduction | 0.65 / 0.48 | 0.63 / 0.50 | 0.59 / 0.51 |
| scapula | 1.13 / 0.93 | 1.16 / 1.00 | 1.16 / 1.00 |
| shoulder | 1.02 / 0.77 | 1.07 / 0.84 | 1.06 / 0.84 |
| elbow | **1.35 / 0.81** | **1.33 / 0.86** | **1.32 / 0.85** |
| hind abduction | 0.71 / 0.79 | 0.71 / 0.86 | 0.69 / 0.87 |
| hip | 1.20 / 1.10 | 1.28 / 1.05 | 1.26 / 1.03 |
| knee | 1.15 / 1.10 | 1.17 / 1.17 | 1.13 / 1.19 |
| hock | 0.74 / 0.73 | 0.76 / 0.77 | 0.76 / 0.84 |
| `j_spine`, `j_spine_yaw`, `j_tail1` | 1.48, 1.35, 0.95 | 1.53, 1.40, 0.97 | 1.48, 1.36, 0.94 |

- **The spine binds.** `j_spine` at 1.48–1.53× rated and `j_spine_yaw` at
  1.35–1.40× are the worst drives at every command (s2a-hold-150 at 5.0:
  0.70 and 1.37). The clip asks the spine to flex through the stride, and
  tracking it costs more spine torque than speed alone used.
- **Left against right: the left fore works harder.** Elbow 1.32–1.35
  against 0.81–0.86 and at its clamp 0.14–0.16 of frames, with the left
  shoulder and scapula also higher: the same left-fore lean as every judged
  v06 policy, and the foot that misses most. The hind legs are nearer
  even than s2a-hold's (knee 1.13–1.17 / 1.10–1.19; s2a-hold at 5.0 0.51 /
  1.22).
- **Clean:** peak margin 0.00 at every command (a drive reaches its peak),
  hind rod loops ≤ 1.9 mm (within 2 mm), no NaN, 0 falls.

## Read

M1 has its judgement at three commands beside S2's best and v05's B1. On the
cheetah's strides v06 learns the clip's transverse gallop, its stride
frequency and a flight every stride, with the hind feet on the clip every
stride. It holds 4.25–4.37 m/s with 0 falls: it holds the slowest stride's
command (4.63, within 10%) and not the two faster ones. It is a little
slower than speed alone at 5.0 (4.37 against 4.53) and works the spine
harder (1.53× against 1.37×). What binds it: the stride frequency stays at
the clip's ~2.5 Hz while the commanded speed rises, and the fore feet
double-tap rather than follow the clip's one touchdown a stride. The
motion comparison M2 asks for waits for m2-dog (training, `8e9e53fc`).

M1's film beside the retargeted clip (F1) is not made yet.
