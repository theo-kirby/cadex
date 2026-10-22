# orun16 Q2: the front push-rod loop gap is dynamic, and no solver setting at the 2 ms step closes it

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 7).
The critic asked where in the stride the front loops open (3.2–4.3 mm
against O9's 2 mm), and whether a solver setting closes them without a
model change.

## Method

`rod_solver.py` re-judges a policy with the engine's own judge
(`CadexDynamics.evaluate_success`, the call `evaluate_runner.py` makes) on
the CPU, with the model XML patched in memory per variant; `rod_fight.py`
plays the same judge with `mj_step` wrapped and reads the loop's
constraint rows on every solver step over 2 mm. Policy: **v05-s1-50**
(`runs/v05-s1/train/gallop.cxpolicy`, leo-v05, 2.39 m/s; `v05-s1.md`), on
its judged task, all 10 frozen seeds; traces in `/tmp/orun16-rodsolver/`.

```
R=~/cadex-projects/leo/runs/v05-s1/train; E=~/cadex-projects/leo/evaluations/v05-s1-50
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/rod_solver.py $R/cat_model-model.xml \
    $E/judged-task.json $R/gallop.cxpolicy /tmp/orun16-rodsolver base carpus4 stop4 iter eq2 dt1 dt1keep dt1rod
pixi run python docs/probes/orun14/rod_gap.py $R/cat_model-model.xml /tmp/orun16-rodsolver/<variant>
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/rod_fight.py $R/cat_model-model.xml \
    $E/judged-task.json $R/gallop.cxpolicy 1001 1002 1003
```

`base` reproduces the engine's evaluation exactly (top speed median
2389.549 mm/s, rod gap rows identical to `v05-s1-50`'s), so the patched
runs differ only by their patch.

## Where it opens

`rod_fight.py`, seeds 1001–1003, solver steps from 1 s:

| loop | steps > 2 mm | max mm | fore paw on floor | wrist drive ≥ 0.95 of 9 N·m | carpus / wrist past stop | loop force N | separation speed m/s | quasi-static gap f·R/k mm |
|---|---|---|---|---|---|---|---|---|
| `j_frodbot_l` | 182 of 13,503 | 3.54 | 0.99 | 1.00 | 0.01 / 0.00 | 1,292 | 0.50 | 0.016 |
| `j_frodbot_r` | 88 of 13,503 | 2.91 | 0.98 | 0.98 | 0.93 / 0.58 | 869 | 0.54 | 0.011 |

- **In fore stance, with the wrist drive saturated**, every time (as
  orun14 found on v03). The hind loops never pass 2 mm (max 1.6 mm).
- **The loop carries the paw's ground load**, 0.9–1.3 kN, three to four
  times what the 9 N·m drive can put through its ~27 mm crank (~330 N).
- **The gap is not the constraint's static softness.** Its regulariser
  (R = 7.8e-4, from dmax 0.9999 and the rod and paw's `invweight0`) gives
  11–16 µm at that force. The ends are *moving apart* at ~0.5 m/s: the
  loop is a critically damped spring-damper with a 4 ms time constant
  (two solver steps, the engine's equality `solref`), and a stance
  impulse opens it by about speed × τ before it pulls back.
- **The left loop opens with the carpus inside its stop** (0.01 past), so
  the soft stop is not what opens it.

## The solver levers, one by one

Rod gap per variant (`rod_gap.py`, 10 seeds, frames from 1 s), with the
gait the same policy then runs:

| variant | what changed | top 2 s m/s median | front loop max mm L / R | frames > 2 mm L / R | hind max L / R |
|---|---|---|---|---|---|
| base | – | 2.39 | 3.02 / 3.27 | 56 / 67 | 1.60 / 1.12 |
| carpus4 | `solreflimit` 0.004 on `j_carpus_*` (orun14's O1 plan) | 2.20 | 3.23 / 2.82 | 55 / 35 | 1.70 / 1.11 |
| stop4 | the same on `j_carpus_*` and `j_wrist_*` | 2.22 | 3.26 / 2.94 | 50 / 53 | 1.81 / 1.25 |
| iter | `iterations` 400, `tolerance` 1e-12 | 2.36 | 3.08 / 3.26 | 59 / 63 | 1.44 / 1.12 |
| eq2 | `refsafe` off, rod loops at 0.002 s (one step) | **blows up** at 0.028 s on 10/10 seeds | – | – | – |
| dt1keep | step 1 ms, every `solref` as built | **0.85** | 1.11 / 0.92 | 0 / 0 | 0.67 / 0.50 |
| dt1rod | step 1 ms, rod loops at 0.002 s | 0.85 | 0.45 / 0.53 | 0 / 0 | 0.29 / 0.23 |
| dt1 | step 1 ms, every equality at 0.002 s (a build at `solver_step_s` 0.001) | 0.83 | 0.39 / 0.47 | 0 / 0 | 0.28 / 0.24 |

- **Stiffer stops do not close the loop.** `carpus4`/`stop4`, the model
  change `orun14/wrist-peak.md` wrote up for Q2, leave the max at
  2.8–3.3 mm and cost 0.17–0.19 m/s on this policy. That plan is now a
  measured dead end for Q2.
- **The solver has converged.** 4× the iterations at 1e4× the tolerance
  moves the max by 0.06 mm.
- **The loop is already as stiff as a 2 ms step allows.** Below two steps
  MuJoCo's `refsafe` is what keeps it stable: off, it diverges in 14
  steps.
- **Only the step closes it.** At a 1 ms step with the loops at their two
  steps (2 ms) the front loops close to 0.45–0.53 mm, 2–2.5× under
  `dt1keep`'s 1 ms step with 4 ms loops at the same gait (median 0.06
  against 0.30 mm). **But the step is part of the plant:** the 2 ms-trained
  policy falls from a 2.39 m/s gallop to a 0.85 m/s shuffle on it, so the
  dt1 numbers are at a gait with the wrist off peak and do not show the
  gallop's gap. Taking the step needs a retrain, at twice the solver steps
  a control step (~2× the ~70–85 s an iteration).

## What follows

- No solver setting at the 2 ms step brings the front loop under 2 mm;
  the gap is the 4 ms loop dynamics under ~1 kN stance load at the
  saturated wrist.
- Two O1 candidates remain, neither built: (a) `solver_step_s` 0.001 in
  leo's `assembly.mjcf` (a sim change: retrain cold, ~2× GPU per
  iteration, judged against this table's base); (b) a linkage that does
  not carry the fore stance load through the rod (a crank/rod geometry
  change, which touches the owner's linkage leg and needs its own
  record). Neither is taken now: SG and RL rank above Q2 and hold the GPU.
- `rod_fight.py`'s loop force is the measure either candidate must move.
