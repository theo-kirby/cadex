# orun17: the peak margin is real (drives at their clamp), and sgt-4-120's RH heel and fold are the policy's

Verified against source: 2026-10-23. Frozen evidence (orun17, iteration 16).
Follows `sgt-4-120.md`. The critic asked, while sgt-5 trains (CPU only):
is the "peak margin 0.00 at every command" in `sg_tables.py` a broken
column or a drive at peak (O6), and is RH's flat 0.00 heel at 1550 and
its fast fold (U 0.24) the policy's or the hardware's (O5)?

```
R=~/cadex-projects/leo/runs/sgt-4/train; E=~/cadex-projects/leo/evaluations; Q=~/orun17-queue; X=$R/cat_model-model.xml
export CUDA_VISIBLE_DEVICES=
pixi run python docs/probes/orun17/sg_tables.py $X $E/sgt-4-50-{700,1550,2400}     # reprint, with the new row
pixi run python docs/probes/orun17/sg_tables.py $X $E/sgt-4-120-{700,1550,2400}
pixi run python docs/probes/orun12/mirror.py $X
mkdir -p /tmp/o17m4 && cp $Q/sgt-4-120.cxpolicy $R/gallop_sg-task.json /tmp/o17m4/
pixi run python docs/probes/orun12/mirror_policy.py $X /tmp/o17m4/sgt-4-120.cxpolicy $Q/sgt-4-120m.cxpolicy
PYTHONPATH=cli pixi run python docs/probes/orun16/sg_judge.py ~/cadex-projects/leo $R $Q/sgt-4-120m.cxpolicy sgt-4-120m --cmd 1550 2400 700
python3 docs/probes/orun12/legs.py $E/sgt-4-120{,m}-{700,1550,2400}
pixi run python docs/probes/orun17/sg_tables.py $X $E/sgt-4-120m-{700,1550,2400}
pixi run python docs/probes/orun17/fore_pair.py $X $E/sgt-4-120{,m}-700
```

## O6: the margin column is right; the drives sit at their clamp

`sg_tables.py` takes `1 - median(effort_peak_ratio_max)`.
`CadexEvaluation.py` (the drives block, ~l. 1490) computes each drive's
`effort_peak_ratio` as `max|effort| / limit`, where the effort is the
actuator force **after** MuJoCo's `forcerange`, and the limit is that
clamp: 22,000 N·mm for the AK80-9 hock, spine and yaw drives (rated
9,000), 9,000 for the wrists (rated 3,000), 53,000 for the hips and
elbows (rated 18,000). So a ratio can never pass 1.0, and 1.0 means the
drive was held at its peak. In `sgt-4-120-2400/evaluation.json` every
seed's `effort_peak_ratio_max` is 1.0 and its `effort_clamp_share_max`
is 0.618 (`j_tail2`). **Not a bug: the 0.00 is a set of drives at peak.**
O6's "never exceed peak" holds by construction in the simulation; what
the number has to say is which drives saturate and how often.

`sg_tables.py` now adds that row: each drive at its clamp on at least
0.05 of frames, by the seed-median `effort_clamp_share` (the engine's own
share within its `clamp_tolerance` of the clamp). Nothing else in the
probe changed. Reprinted:

| evaluation | at peak, share of frames at the clamp (seed median) |
|---|---|
| sgt-4-50-700 | `j_tail2` 0.48, `j_hock_l` 0.29, `j_hock_r` 0.25, `j_wrist_l` 0.21, `j_wrist_r` 0.16, `j_elbow_r` 0.09, `j_elbow_l` 0.06 |
| sgt-4-50-1550 | `j_tail2` 0.42, `j_hock_l` 0.26, `j_wrist_l` 0.22, `j_hock_r` 0.18, `j_wrist_r` 0.13, `j_elbow_l` 0.09, `j_spine` 0.05 |
| sgt-4-50-2400 | `j_tail2` 0.57, `j_hock_l` 0.26, `j_hock_r` 0.21, `j_wrist_l` 0.20, `j_wrist_r` 0.16, `j_spine` 0.12, `j_elbow_l` 0.06 |
| sgt-4-120-700 | `j_tail2` 0.69, `j_hock_r` 0.32, `j_hock_l` 0.21, `j_wrist_r` 0.19, `j_wrist_l` 0.16, `j_elbow_r` 0.16 |
| sgt-4-120-1550 | `j_tail2` 0.80, `j_hock_l` 0.34, `j_hock_r` 0.31, `j_wrist_r` 0.20, `j_wrist_l` 0.13, `j_elbow_r` 0.12 |
| sgt-4-120-2400 | `j_tail2` 0.62, `j_hock_l` 0.33, `j_hock_r` 0.20, `j_wrist_r` 0.18, `j_wrist_l` 0.14 |
| hk12-s1-50 (single speed, v04.3) | `j_tail2` 0.52, `j_spine` 0.29, `j_wrist_l` 0.22, `j_wrist_r` 0.18, `j_hock_r` 0.17, `j_hock_l` 0.15, `j_elbow_r` 0.09, `j_elbow_l` 0.08 |
| v05-s1-50 (single speed, v05) | `j_tail2` 0.43, `j_spine` 0.27, `j_hock_l` 0.24, `j_wrist_l` 0.21, `j_wrist_r` 0.17, `j_hock_r` 0.16, `j_elbow_r` 0.11, `j_elbow_l` 0.08, `j_tail1` 0.06 |

The drives at peak are named:

- **The hocks (AK80-9, 22 N·m)**, 0.2–0.34 of frames on sgt-4-120 at
  every command, up from 0.15–0.24 on the single-speed policies, and the
  worst RMS over rated (1.44–1.48). This is the drive orun13 found at
  peak through stance; the heel schedule asks it to hold the metatarsus
  flat under load.
- **The wrists (9 N·m)**, 0.13–0.20, as on every policy since hk12.
- **`j_tail2`** (1.9 N·m clamp, no rating), 0.62–0.80, the most saturated
  drive: the tail's base pitch rides its clamp most of the episode.
- The elbows to 0.16 at 700; `j_spine` drops from 0.27–0.29 on the
  single-speed policies to under 0.05 on sgt-4-120.

It is a long-standing state, not a new failure: every leo policy judged
since hk12 has had a peak ratio of 1.0. The hock's saturation is what a
model change would have to measure against (O1); none is made here.

## O5: the model mirrors, and RH's heel and fold swap sides

`mirror.py` on sgt-4's model (leo `b09a23b5`, the same XML as sgt-5's
`89b5bb40`): 471 checks, 27 differ, 0 without a partner; the 27 are the
cosmetic bodies (tail panels 1–7, `c_pnl_neck1_side`,
`c_pnl_skull_muzzle`, `c_camera`), as on every v03–v05 build.
`mirror_policy.py`: 73 channels, 22 actions, witness exact to 4.3e-14;
mirrored policy **`afbc4ad2`**, judged on the same 10 seeds, every seed to
the horizon, no fall, no non-finite seed.

| command | evaluation | top 2 s m/s | heel share LH / RH | U LH / RH (10°) | heel stance mm LH / RH | overreach mm LH / RH | pin p95 °/s LH / RH |
|---|---|---|---|---|---|---|---|
| 700 | sgt-4-120 | 0.88 | 0.00 / 0.00 | 0.01 / 0.00 | 19 / 28 | −166 / −434 | 421 / 345 |
| | sgt-4-120m | 0.91 | 0.00 / 0.00 | 0.00 / 0.01 | 29 / 18 | −434 / −169 | 348 / 434 |
| 1550 | sgt-4-120 | 1.70 | **0.18 / 0.00** | 0.05 / 0.00 | 5 / 10 | +74 / −407 | 555 / 632 |
| | sgt-4-120m | 1.69 | **0.00 / 0.16** | 0.00 / 0.04 | 10 / 5 | −405 / +73 | 637 / 556 |
| 2400 | sgt-4-120 | 2.66 | 0.31 / 0.38 | **0.13 / 0.24** | 5 / 4 | +242 / −355 | 735 / 748 |
| | sgt-4-120m | 2.66 | 0.38 / 0.31 | **0.23 / 0.13** | 5 / 5 | −355 / +239 | 749 / 738 |

Every hind asymmetry changes side under the mirror, within 0.02 and a
few mm. **RH's 0.00 heel at 1550 and its fold at 2400 are the policy's**,
as sgt-1-50's LH fold was (`sgt-1-50-mirror.md`) and hk12-sole's was
(`orun15/hk12-mirror.md`). The over-reaching hind (LH +74 / +242 mm, RH
−407 / −355) is the same handed gait: one hind reaches past the fore, the
other lands behind it, and the reaching leg is the one that drops its
heel at 1550. No model change is argued for (O1). Torque mirrors too
(`j_hock_l` ↔ `j_hock_r` as the worst drive), and O9 on the mirror is the
original's (pins 348–749 °/s, cable ≤ 0.25°, loops 2.5–2.8 mm).

## What does not mirror: the slow fore pair's timing

At 700 the double strike swaps side (LF 1.89 a stride → RF 1.94 on the
mirror), so it is the policy's too. But the pair's timing does not
mirror cleanly:

| evaluation (700) | strikes a stride LF / RF | fore lag ms, median (lowest) | strides within 40 ms (`fore_pair`) | rotary seeds (ordered) |
|---|---|---|---|---|
| sgt-4-120 | 1.89 / 1.00 | 100 (100) | 0.24 | 4/10, 6 undecided |
| sgt-4-120m | 1.00 / 1.94 | 40 (30) | 0.51 | 1/10, 8 undecided |

At 1550 and 2400 the fore pair mirrors (120 / 80 ms, 10/10 rotary on
both). So at the slow end, where the fores tie or nearly tie, the fore
order and lag are partly set outside the policy, as `sgt-1-50-mirror.md`
found at a one-frame lag. The likely sources are the cosmetic bodies
`mirror.py` lists (three of them at the head, over the fores) or a
sensitive slow fore rhythm that a tiny asymmetry tips. It does not move
the RH heel question, and it is not chased further here; it says RL's
slow clause will read differently left-led and right-led until the slow
fore pair lands well apart, which is what sgt-5's `fore_lag` is for.
