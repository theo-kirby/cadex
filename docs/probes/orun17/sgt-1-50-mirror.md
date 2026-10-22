# orun17: sgt-1-50's LH fold is the policy's (mirror test), and what the two cut terms would pay

Verified against source: 2026-10-22. Frozen evidence (orun17, iteration 5).
Follows `sgt-1-50.md`: at 50 the trimmed task lands LH reaching on a paw
folded toes-up of the floor (U 0.36 / 0.35 / 0.60 at 10°) while RH stands
on its toe bulbs. The critic asked, while sgt-1 trains to 120 (CPU only):
is that the policy or the hardware (O5), and what would `paw_fold` and
`hind_overreach`, two of the six cut terms, pay per step (O7), so either
can come back at once if the 120 keep rule fails.

```
R=~/cadex-projects/leo/runs/sgt-1/train; E=~/cadex-projects/leo/evaluations; Q=~/orun17-queue
export CUDA_VISIBLE_DEVICES=
pixi run python docs/probes/orun12/mirror.py $R/cat_model-model.xml
mkdir -p /tmp/o17m && cp $Q/sgt-1-50.cxpolicy $R/gallop_sg-task.json /tmp/o17m/
pixi run python docs/probes/orun12/mirror_policy.py $R/cat_model-model.xml /tmp/o17m/sgt-1-50.cxpolicy $Q/sgt-1-50m.cxpolicy
PYTHONPATH=cli pixi run python docs/probes/orun16/sg_judge.py ~/cadex-projects/leo $R $Q/sgt-1-50m.cxpolicy sgt-1-50m --cmd 700 1550 2400
python3 docs/probes/orun12/legs.py $E/sgt-1-50-700 $E/sgt-1-50m-700        # and 1550, 2400
pixi run python docs/probes/orun17/sg_tables.py $R/cat_model-model.xml $E/sgt-1-50m-{700,1550,2400}
python3 docs/probes/orun14/lead_order.py $R/gallop_sg-task.json $E/sgt-1-50{,m}-{700,1550,2400}
pixi run python docs/probes/orun17/cut_terms.py $R/cat_model-model.xml $E/sgt-1-50-{700,1550,2400} $E/sg-s9-50-{700,1550,2400}
```

`mirror_policy.py` now maps the speed command `cmd` to itself (a forward
speed is mirror-invariant) and reads the scan offsets from
`gallop_sg-task.json` when there is no `gallop-task.json`; nothing else in
it changed.

## The model mirrors; the mirrored policy swaps the hind legs

`mirror.py` on sgt-1's model (`59bc5407`, leo v05): 471 left/right
checks, 27 differ, 0 without a partner; the 27 are the cosmetic bodies
(tail panels 1–7, `c_pnl_neck1_side`, `c_pnl_skull_muzzle`, `c_camera`),
as on v03–v04.3. `mirror_policy.py`: 73 channels, 22 actions, witness
exact to 3.6e-14; mirrored policy `4b067f2c`. Judged on the same 10 seeds
at the same three commands:

| command | evaluation | top 2 s m/s | heel share LH / RH | U LH / RH (10°) | heel stance mm LH / RH | overreach mm LH / RH | touchdown Hz LH / RH |
|---|---|---|---|---|---|---|---|
| 700 | sgt-1-50 | 1.64 | 0.14 / 0.04 | 0.36 / 0.07 | 16 / 39 | +121 / −335 | 2.00 / 2.56 |
| | sgt-1-50m | 1.64 | 0.05 / 0.15 | 0.07 / 0.37 | 35 / 17 | −346 / +73 | 2.50 / 2.00 |
| 1550 | sgt-1-50 | 2.33 | 0.08 / 0.05 | 0.35 / 0.08 | 16 / 38 | +214 / −295 | 2.44 / 2.78 |
| | sgt-1-50m | 2.33 | 0.05 / 0.09 | 0.13 / 0.33 | 37 / 16 | −306 / +214 | 2.72 / 2.44 |
| 2400 | sgt-1-50 | 2.74 | 0.16 / 0.08 | 0.60 / 0.09 | 11 / 24 | +198 / −344 | 3.00 / 3.22 |
| | sgt-1-50m | 2.72 | 0.08 / 0.16 | 0.08 / 0.62 | 24 / 11 | −340 / +194 | 3.17 / 3.00 |

Every hind asymmetry changes side under the mirror, within a few
hundredths: the reaching, folded, heel-low leg is RH on the mirror. **The
fold is the policy's**, as orun15 found for hk12-sole (`hk12-mirror.md`):
no model change is argued for (O1). O9 on the mirror is the original's
(pins p95 417–713 °/s, cable ≤ 0.47°, loops 2.9–3.5 mm, no blow-up).

**One thing does not mirror: the fore lead.** `lead_order.py` (first fore
after the hind pair):

| command | sgt-1-50: hind first; fore first | sgt-1-50m: hind first; fore first |
|---|---|---|
| 700 | RH 0.98; LF 0.89 | LH 1.00; LF 0.81 (RF 15 of 78) |
| 1550 | RH 1.00; LF 1.00 (163 rotary) | LH 1.00; RF 117, LF 53 of 170 |

A clean mirror would land RF first on every stride. At 700, where the
fores are 20 ms apart (one frame), the mirror keeps LF first on 0.81, so
`sg_tables.py` reads it 0/10 rotary against the original's 10/10; at 1550
(60 ms) it flips on 0.69. So the fore order at a one-to-three-frame lag is
partly set outside the policy (the cosmetic mass differences, the contact
solve, or a frame-quantised tie); that is RL's 40 ms clause, and it says
the slow fore lag must open well past one frame before the rotary count
means anything. Not chased further here.

## The two cut terms, per step on the policy's own frames

`cut_terms.py` (new): per hind leg and `paw_floor.py` frame class, the
term's mean value (unweighted, per leg; the task averages the legs), and
its share of pay on U frames.

| evaluation | `paw_fold` a step LH / RH | on U LH / RH | share on U LH | weighted, both legs | `hind_overreach` a step LH / RH | weighted |
|---|---|---|---|---|---|---|
| sgt-1-50-700 | 0.117 / 0.008 | 0.81 / 0.30 | 0.99 | **−0.62** | 0.004 / 0.027 | +0.05 |
| sgt-1-50-1550 | 0.093 / 0.010 | 0.73 / 0.42 | 0.98 | **−0.52** | 0.005 / 0.022 | +0.04 |
| sgt-1-50-2400 | 0.131 / 0.010 | 0.62 / 0.36 | 0.98 | **−0.71** | 0.005 / 0.029 | +0.05 |
| sg-s9-50-700 (trained with both) | 0.046 / 0.007 | 0.52 / 0.31 | 0.96 | −0.27 | 0.028 / 0.033 | +0.09 |
| sg-s9-50-1550 | 0.057 / 0.018 | 0.52 / 0.42 | 0.97 | −0.38 | 0.038 / 0.024 | +0.09 |
| sg-s9-50-2400 | 0.076 / 0.016 | 0.53 / 0.41 | 0.97 | −0.46 | 0.030 / 0.013 | +0.07 |

On F and R frames `paw_fold` is 0.002–0.073 (the paw 5–10° toes-up still
reads F at `paw_floor`'s 10°); on T and in swing 0.

- **`paw_fold` charges the fold and little else.** 98–99 % of what it
  would take from LH falls on LH's U frames; on sgt-1-50 it would cost
  0.5–0.7 a step (about 2 % of the 30–32 a step sgt-1 now earns), twice
  what sg-s9-50, which trained with it, pays. It is the term to bring
  back if the keep rule's U clause fails at 120, as `sgt-1-50.md` said.
- **`hind_overreach` would not touch LH's reach.** It reads the gap
  between the paws at the same instant (subtree centres of mass), and on
  the floor LH sits 490–725 mm behind the fores' mean (U frames −487 to
  −530 mm), past the term's 450 mm, so it pays LH 0.004–0.005 a step. The
  engine's `overreach` (+121…+214 mm on LH) compares footprints across a
  stride, a different quantity. The term pays RH 0.02–0.03 on its F and U
  frames. Weighted, it is worth +0.04–0.05 a step (0.15 %) on sgt-1-50
  and was +0.07–0.09 on sg-s9-50: with or without it, the policy cannot
  feel it. It stays cut; it is no lever for LH's landing or for the
  `overreach` predicate (−295…−344 mm, RH the worst leg).

## What follows at 120

`b1-trim.md`'s keep rule is applied unchanged. If its U clause fails (LH
U at 2400 > 0.24), the next screen is the trimmed task with `paw_fold`
(w −10) back alone, cold, 120 iterations, judged at 50 and 120 like
sgt-1. `hind_overreach` does not come back on this evidence.
