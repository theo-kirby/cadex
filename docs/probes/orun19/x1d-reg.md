# orun19 X1d: the regularisers to a quarter, warm from x1b-warm-150 (launch)

Verified against source: 2026-10-24. Charter X1, fourth screen: the launch.
Not judged yet. When it ends it is judged at 50 and 150 at S's commands
and up to 8.0 m/s, beside x1b-warm-150. That is X1's top: 5.72 m/s tracked
at 6.0 (Fr 8.42), and 5.84 m/s held at 6.5 (Fr 8.78), 0/100 falls
(`x1b-warm-150.md`). The streak without a new top is 1 (X1c,
`x1c-ceil-150.md`). If X1d fails too, R1 is written under the exhaustion
policy.

## The one change

`~/orun19-queue/leo_x1d.py` is `leo_x1b.py` (x1b-warm's script) with one
training change, O3's third lever, plus the judged range:

- **The regularisers' weights to a quarter**:
  - `torque`, each drive's (τ / rated)² averaged: −0.2 → −0.05;
  - `energy`, mechanical power in kW: −0.2 → −0.05;
  - `action_rate`, each command's rate over 600 °/s, squared: −0.002 →
    −0.0005.

  `near_peak` (the (τ / peak)¹⁰ guard carried from the gallop reward) is
  not one of the three and is unchanged. X1b and X1c are bound at the hind
  hips (1.74–1.85× rated at 6.0–6.5 m/s in X1b), so this asks whether
  pricing torque and power less buys speed.
- **`speed_spec`'s range** goes from 700–6500 to 700–8000 mm/s, with
  `sequence` 8000, as in X1c. That is judging, not training.
- **The training goal stays X1b's** 700–5000 mm/s, and `track_speed` is
  X1b's one-sided term at weight 20.

A quarter, not a half, because the terms are small beside `track_speed`'s
20: at x1b-warm-150's policy, quartering them raised the reward per step
from x1b's last 22.75 to 22.87 by iteration 7, so all three together
cost ~0.2 a step there. Halving them would move about 0.1 of ~22.

Built as leo revision **`0f11e624`** (project commit `724f942`) by
`queue_run.py --build` in ~3 min. Its bundle
`runs/x1d-reg/train/speed-task.json` is **`3ced6ed6`**. It differs from
x1b-warm's `f070a89b` in exactly six fields:

- `reward/7/weight` (torque) −0.2 → −0.05, `reward/8/weight` (energy)
  −0.2 → −0.05, `reward/9/weight` (action_rate) −0.002 → −0.0005;
- in `success/goal/0`: `high` 6500 → 8000, `nominal` 3600 → 4350, and
  `sequence` 6500 → 8000.

The model XML is byte-identical (`f9b8ab82`). The training goal is
unchanged, so the warm start needs only ADR-161's `reward` key; the trainer
logged `the task changed in ['reward', 'success']`, carried the
normaliser's 24,576,000 samples and took `action_std 0.4112` from the
policy.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo x1d-reg 3620 150 \
    "orun19 X1d: x1b's task with the torque, energy and action-rate weights to a quarter, warm from x1b-warm-150 (10f197e1)" \
    --seed 0 --task speed --envs 4096 --init-from ~/orun19-queue/x1b-warm-150.cxpolicy \
    --parent-task ~/cadex-projects/leo/runs/x1b-warm/train/speed-task.json \
    --task-change "torque -0.2 -> -0.05, energy -0.2 -> -0.05, action_rate -0.002 -> -0.0005 (O3 third lever); judged range to 8000; nothing else" \
    --after x1b-warm --build ~/orun19-queue/leo_x1d.py
```

- **The run**: `x1d-reg`, launched at 01:47:50 on `0f11e624`. Warm from
  `10f197e1`, seed 0, 4096 envs, 150 iterations, a checkpoint every 25, no
  critic warm-up, the default learning rate. Registered, view retained and
  launched through `cadex_cli.loop`.
- **Budget**: 3,620 s.
- **Timed**: by the trainer's wall clock (`progress.json`), iteration 15
  came at 428.5 s and iteration 23 at 574.3 s, so ~18.2 s an iteration
  (x1b-warm ~17.9, x1c ~17.7). The projection is 574 + 126 × 18.2 ≈
  2,870 s for 150; 150 iterations at 18.2 s plus 20% is ~3,280 s, inside
  the budget, and the budget is x1b-warm's measured end (3,014 s, checkpoint
  rollouts included) plus 20%.
- **Early curve**: reward per step 10.77 at iteration 0 (the critic is
  fresh), 22.87 at 7 (the best so far), 22.57 at 23. σ rises from 0.411 to
  0.454.

## What it can and cannot show

If the drives' price is what holds the policy near 5.8 m/s, the top tracked
command rises past 6.0 and the hips run further over rated. If the hips'
peak torque binds (X1c's peak margin was 0.00), the held speed stays near
5.8 m/s whatever the price, and the body is the limit, which R1 then
reports as a recommendation for the next model. Commands up to 8.0 m/s are
judged to find out.
