# orun17: sgt-3b judged at 50; the fores still double, so sgt-4 (the duty 0.35 / 0.3 slow stance) is queued

Verified against source: 2026-10-23. Frozen evidence (orun17, iteration 10).
Follows `sgt-2-120.md` (sgt-3b's keep rule, read at 120, not here) and
`fore-pair.md` (the slow-duty reference option and its trigger).

```
R=~/cadex-projects/leo/runs/sgt-3b/train; E=~/cadex-projects/leo/evaluations; X=$R/cat_model-model.xml
cp $R/gallop_sg.000050.cxpolicy ~/orun17-queue/sgt-3b-50.cxpolicy                     # 8c8e365a
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun16/sg_judge.py \
    ~/cadex-projects/leo $R ~/orun17-queue/sgt-3b-50.cxpolicy sgt-3b-50 --cmd 700 1550 2400
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/sg_tables.py $X $E/sgt-3b-50-{700,1550,2400}
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun17/fore_pair.py $X $E/sgt-3b-50-700
python3 docs/probes/orun12/legs.py $E/sgt-3b-50-{700,1550,2400}
```

## sgt-3b at 50

Checkpoint `gallop_sg.000050.cxpolicy` (**`8c8e365a`**), cold on leo revision
`62025a13` (sgt-1's 18 terms, heel_sched W 12, half-width 40). Reward per
step 28.8 at 46 (sgt-2 27.9 at 50). 0/10 pass at every command; every seed
to the horizon (`terminations` `{"horizon": 10}`), no fall, no non-finite
seed. A cold screen at 50 is a midpoint (O8): its keep rule is read at 120.

| command mm/s | 700 | 1550 | 2400 |
|---|---|---|---|
| top 2 s m/s min / med / max | 1.61 / **1.74** / 1.80 | 2.15 / **2.19** / 2.23 | 2.53 / **2.56** / 2.60 |
| sgt-2-50 / sgt-1-50 | 1.70 / 1.64 | 2.20 / 2.33 | 2.65 / 2.74 |
| failing predicates (median) | top_speed, hock_down (0.165), no_tap 0 (1.77), overreach (−301), straight 2/10 | top_speed, hock_down (0.070), no_tap 7/10, overreach (−274), straight 0/10 | top_speed, hock_down (0.072), no_tap 8/10, overreach (−398) |
| heel share LH / RH (`hock_down`) | 0.18 / 0.18 | 0.12 / 0.07 | 0.10 / 0.07 |
| sgt-2-50 | 0.26 / 0.04 | 0.16 / 0.02 | 0.23 / 0.03 |
| heel stance height LH / RH mm | 11 / 16 | 14 / 21 | 13 / 20 |
| U LH / RH at 10° (5°) | 0.24 / 0.14 (0.33 / 0.22) | 0.27 / 0.05 (0.32 / 0.09) | **0.39** / 0.02 (0.49 / 0.04) |
| floor pitch at lift LH / RH °; lifts toes-up of floor | −2.9 / −3.1; 0.05 / 0.00 | −3.6 / −12.3; 0.00 / 0.00 | −4.2 / −24.1; 0.00 / 0.00 |
| pin p95 LH / RH °/s (worst seed); flapping | 664 / 560 (684); 0 | 711 / 506 (721); 0 | 698 / 345 (725); 0 |
| touchdown Hz LH / RH; stride mm LH / RH | 2.22 / 2.11; 842 / 855 | 2.44 / 2.44; 945 / 940 | 3.00 / 3.11; 876 / 861 |
| hind overreach LH / RH mm | +27 / −301 | +104 / −274 | +25 / −398 |
| rotary seeds, ordered strides | 10/10 | 10/10 | 10/10 |
| pair lag ms fore / hind, median (lowest seed) | **49 (20)** / 140 (120) | 20 (20) / 100 (100) | 20 (0) / 100 (80) |
| pair lag share fore / hind | 0.101 / 0.280 | 0.052 / 0.250 | 0.053 / 0.294 |
| strides landing together fore / hind | 0.27 / 0.00 | 0.43 / 0.00 | 0.38 / 0.00 |
| flight share; flight s | 0.80; 0.040 | 1.00; 0.080 | 0.96; 0.080 |
| spine range per stride (sum) °; at a stop; cable gap max ° | 50.3; 0.00; 0.37 | 46.8; 0.00; 0.46 | 24.6; 0.00; 0.46 |
| worst RMS / rated (drive); peak margin | 1.46 (`j_wrist_l`); 0.00 | 1.44 (`j_wrist_r`); 0.00 | 1.62 (`j_spine_yaw`); 0.00 |
| loop gap max mm | 3.1 | 3.5 | 3.6 |

Checked at the source: `~/cadex-projects/leo/evaluations/sgt-3b-50-700/
evaluation.json` (`judged_command_mm_s` 700, `summary.terminations`
`{"horizon": 10}`); the same for 1550 and 2400.

`sg_tables.py`: **SG fails** all five (slow heel 0.18 / 0.18 > 0.1; fast
heel 0.10 / 0.07; fast LH U 0.39; neither leg rising). **RL fails** three
of four: rotary 10/10 at every command passes; the fores fall under 40 ms
(0.47 / 0.62 / 0.79 of strides), the fore share does not fall (0.101 /
0.052 / 0.053), nor the hind (0.280 / 0.250 / 0.294). **O9**: pins, cable,
blow-up pass; loops 3.1–3.6 mm (Q2's deferred front rods).

At 50 the policy does not track: it runs 1.74 m/s at a 0.7 m/s command,
as sgt-1-50 and sgt-2-50 did at 50, and both slowed to 0.88–0.95 m/s by
120. The heel_sched change has not yet shown its fast heel (0.10 / 0.07,
below sgt-2-50's 0.23 / 0.03); the rule is read at 120.

## The slow fores (`fore_pair.py`, 700, stride 0)

| seed | touchdowns a stride LF / RF | RF after LF ms | within 40 ms | `fore_lag` (clip 0.400) |
|---|---|---|---|---|
| 1001 | 1.56 / 1.22 | +20 | 0.56 | 0.191 |
| 1002 | 1.89 / 1.33 | +0 | 0.48 | 0.224 |
| 1003 | 1.78 / 1.28 | +20 | 0.35 | 0.217 |
| 1004 | 1.72 / 1.44 | +20 | 0.48 | 0.206 |
| 1005 | 1.83 / 1.22 | +20 | 0.52 | 0.195 |
| 1006 | 1.89 / 1.17 | +20 | 0.50 | 0.204 |
| 1007 | 1.67 / 1.22 | +20 | 0.45 | 0.200 |
| 1008 | 1.78 / 1.17 | +20 | 0.55 | 0.204 |
| 1009 | 2.00 / 1.17 | +10 | 0.41 | 0.206 |
| 1010 | 1.61 / 1.33 | +20 | 0.45 | 0.188 |

All seeds: `fore_lag` 0.204 a step, 0.48 of fore touchdowns within 40 ms,
r −0.40. **The fores still double**, LF on every seed (1.56–2.00 strikes a
stride), RF on most (1.17–1.44): the trigger `fore-pair.md` set for the
reference option is met (sg-s9-80, the one screen that kept them, struck
1.00–1.33 / 1.00–1.17 and kept 180 ms on 10/10).

## sgt-4: the duty 0.35 / 0.3 slow stance on sgt-3b's terms

`~/orun17-queue/orun17-sgt4.py` is `orun17-sgt3b.py` with `SG_STRIDES`
carrying a duty and a swing per stride: sg0 (0.7 m/s) duty 0.35 and sg1
(1.0 m/s) duty 0.3, both on a 30 mm swing; sg2–sg4 at `GALLOP_DUTY` (0.2)
on 40 mm, as before. Nothing else changes.

- **Built** 2026-10-23 00:03:45 (ahead of the 50 checkpoint, so the GPU would not wait on a build; launched only because the trigger below was met) as leo revision **`b09a23b5`** (project commit
  `da06185`), model unchanged (the clearance verdicts are leo's baseline:
  14 static pairs, sweep 12 pairs; mounting passes).
- **The bundle against sgt-3b's** differs only in `reference`,
  `reference_schedule` and `tracking` (the clip's table and reset rows):
  the 18 reward terms, observations and model are the same. Its stride 0
  lands LF 4, LH 0, RF 13, RH 17 with nine stance samples a fore (was
  five), RF 180 ms after LF and the fores never down together:

```
sg0 duty 0.35, swing 30 mm          sg1 duty 0.3, swing 30 mm
LF ....#########............        LF .....########............
LH #########................        LH ########.................
RF .............#########...        RF .............#######.....
RH .................########        RH ..................#######
```

- **Queued** 00:38:31 behind sgt-3b through `orun13/queue_run.py
  ~/cadex-projects/leo sgt-4 11100 120 ... --expect-revision b09a23b5
  --seed 1 --task gallop_sg --envs 4096` in its own `systemd-run --user
  --scope -p MemoryMax=30G` (`~/orun17-queue/sgt-4.log`): cold, seed 1,
  4096 envs, 120 iterations, `budget_s` 11,100 (sgt-3b's sizing, ~83 s an
  iteration + 20 %). It registers when sgt-3b ends (near 02:20) and the
  machine lock frees; one trainer at a time.

**Its rule, written now:** judged at 50 and 120 at 700 / 1550 / 2400,
against sgt-3b at the same checkpoints. The duty schedule is kept if at
120 the fores at 700 strike at most 1.2 a stride on each paw (seed
median) with at most 0.2 of fore touchdowns within 40 ms, and the slow
heel (700) stays at or under 0.1 a leg, with the speed span ≥ 1.6 m/s and
2400 ≥ 2.6 m/s. If the fores still double, `fore_lag` (the candidate term,
`fore-pair.md`) is next.

sgt-3b's own 120 judgment (its heel_sched rule in `sgt-2-120.md`) decides
the heel_sched width for the bundle after sgt-4; sgt-4 carries 12:40, so
if 12:40 is not kept at 120, sgt-4's heel numbers are read against
sgt-3b's, not sgt-1's.
