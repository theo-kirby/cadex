# orun19 X1c: the training goal's ceiling 5000 → 7500 mm/s, warm from x1b-warm-150 (launch)

Verified against source: 2026-10-24. Charter X1, third screen: the launch.
Not judged yet. When it ends it is judged at 50 and 150 at S's commands
and up to 8.0 m/s, beside x1b-warm-150. That is X1's top: 5.72 m/s tracked
at 6.0 (Fr 8.42), and 5.84 m/s held at 6.5 (Fr 8.78), 0/100 falls
(`x1b-warm-150.md`). The streak without a new top is 0.

## The one change

`~/orun19-queue/leo_x1c.py` is `leo_x1b.py` (x1b-warm's script) with one
training change, plus the judged range:

- **The training goal's ceiling**: `SPEED_HIGH` 5000 → 7500 mm/s, so the
  goal is drawn from 700–7500 mm/s, held 12 s, ramped over 1 s. Its
  `nominal` (the range's midpoint) moves 2850 → 4100 with it.
- **`speed_spec`'s range** goes from 700–6500 to 700–8000 mm/s, with
  `sequence` 8000. That is judging, not training: `speed_judge.py` refuses
  a command outside it.
- **`track_speed` is X1b's one-sided term**, unchanged:
  `min(comv_x, cmd) / cmd` at weight 20.

X1a raised the ceiling under s2a-hold's two-sided tent, cold. This screen
raises it under X1b's one-sided reward, warm, so the ceiling's effect is
measured alone.

Built as leo revision **`9763fa37`** (project commit `2f9a776`) by
`queue_run.py --build` in ~3 min. Its bundle
`runs/x1c-ceil/train/speed-task.json` is **`ab9e023e`**. It differs from
x1b-warm's `f070a89b` in exactly five fields:

- in `goal/0`: `high` 5000 → 7500 and `nominal` 2850 → 4100;
- in `success/goal/0`: `high` 6500 → 8000, `nominal` 3600 → 4350, and
  `sequence` 6500 → 8000.

The model XML is byte-identical (`f9b8ab82`).

## Warm across the goal change: ADR-791

X1a's warm start was refused because `goal` is not one of ADR-161's
curriculum keys (`x1a-cold.md`). ADR-791 admits a goal change whose entries
are equal less `low`, `high`, `nominal` and `sequence`, and names it
`goal.range`. The actor reads the drawn command as it is, through the
running normaliser it carries, so 5000 mm/s means the same at either range.
The trainer logged `the task changed in ['goal.range', 'success']`, carried
the normaliser's 24,576,000 samples, and took `action_std 0.4112` from the
policy.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo x1c-ceil 3620 150 \
    "orun19 X1c: x1b's task with the training goal's ceiling 5000 -> 7500 mm/s, warm from x1b-warm-150 (10f197e1) by ADR-791" \
    --seed 0 --task speed --envs 4096 --init-from ~/orun19-queue/x1b-warm-150.cxpolicy \
    --parent-task ~/cadex-projects/leo/runs/x1b-warm/train/speed-task.json \
    --task-change "training goal ceiling 5000 -> 7500 mm/s (goal.range, ADR-791); judged range to 8000; nothing else" \
    --after x1b-warm --build ~/orun19-queue/leo_x1c.py
```

- **The run**: `x1c-ceil`, launched at 00:30:18 on `9763fa37`. Warm from
  `10f197e1`, seed 0, 4096 envs, 150 iterations, a checkpoint every 25, no
  critic warm-up, the default learning rate. Registered, view retained and
  launched through `cadex_cli.loop`.
- **Budget**: 3,620 s, as the critic set it.
- **Timed**: by the trainer's wall clock, iteration 8 came at 303 s and
  iteration 15 at 427 s, so ~17.7 s an iteration (x1b-warm ran ~17.9). The
  projection is 427 + 135 × 17.7 ≈ 2,815 s for 150; that plus 20% is
  ~3,380 s, inside the budget. Against x1b-warm's measured end (3,014 s,
  checkpoint rollouts included) the budget leaves 20% headroom.
- **Early curve**: reward per step 8.43 at iteration 0 (the critic is fresh),
  20.42 at 8 (the best so far), 20.29 at 15. σ rises from 0.411 to 0.436.

## What it can and cannot show

x1b-warm-150 already runs past its 5 m/s training goal: 5.72 m/s at 6.0
and 5.84 at 6.5, but under 6.0 at 6.5, so 6.5 is not tracked. If asking for
up to 7.5 m/s in training buys speed, the top tracked command rises past
6.0. If the hind hips (1.74–1.85× rated at 6.0–6.5) are the limit, the
held speed stays near 5.8 m/s whatever the command, which is what X1a's
ceiling showed at ~4.1 under the old reward. Commands up to 8.0 m/s are
judged to find out.
