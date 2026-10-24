# orun19 X1b: track_speed one-sided, warm from s2a-hold-150 (launch)

Verified against source: 2026-10-23. Charter X1, second screen: the launch.
Not judged yet. When it ends it is judged at 50 and 150 at S's commands and
up to 6.5 m/s, beside s2a-hold-150. That is X1's top: 4.57 m/s held at
4.63, Fr 5.38, 0/70 falls (`s2a-hold-150-top.md`). X1a did not raise it
(`x1a-cold-150.md`, ~4.1 m/s ceiling): it was the first X1 screen in a row
without a new top.

## The one change

`~/orun19-queue/leo_x1b.py` is `leo_s2a.py` (s2a-hold's script) with one
change to the reward, plus the judged range:

- **`track_speed`**: `UP * (comv_x - 0.75 * (comv_x - cmd + |comv_x - cmd|)) / cmd`
  → `UP * (comv_x - 0.5 * (comv_x - cmd + |comv_x - cmd|)) / cmd`.
  - Below the command it is unchanged: linear, `comv_x / cmd`.
  - At and above the command it now pays the full weight (20), so
    `min(comv_x, cmd) / cmd`.
  - Before, the tent gave back half its slope past the command: it paid
    `(1.5 cmd - 0.5 comv_x) / cmd`, so 0.9 of the weight at 1.2× the
    command. Running over the command now costs nothing, as O3 reads it.
- **`speed_spec`'s range** goes from 700–5000 to 700–6500 mm/s, with
  `sequence` 6500. Without that, `speed_judge.py` refuses commands above
  5 m/s. The spec is the task's `success`, which a curriculum step may
  change.
- **The training goal is unchanged**: s2a-hold's 700–5000 mm/s, held 12 s,
  ramped over 1 s. The goal is an observation channel, so changing it is what
  stopped X1a's warm start (`x1a-cold.md`). With it kept, the warm start is
  allowed.

Built as leo revision **`6f4bbe78`** (project commit `9ae865f`) by
`queue_run.py --build` in ~3 min. Its bundle
`runs/x1b-warm/train/speed-task.json` is **`f070a89b`**. It differs from
s2a-hold's `d5b25b15` in exactly four fields:

- `reward/1/expression`: 0.75 → 0.5;
- in `success/goal/0`: `high` 5000 → 6500, `nominal` 2850 → 3600, and
  `sequence` 5000 → 6500.

The model XML is byte-identical (`f9b8ab82`). The trainer logged `the task
changed in ['reward', 'success']` and accepted the warm start, with
`action_std 0.5096` taken from the policy.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo x1b-warm 3600 150 \
    "orun19 X1b: s2a-hold's task with track_speed paying in full at and above the command (0.75 -> 0.5), warm from s2a-hold-150 (efe7f96b)" \
    --seed 0 --task speed --envs 4096 --init-from ~/orun19-queue/s2a-hold-150.cxpolicy \
    --parent-task ~/cadex-projects/leo/runs/s2a-hold/train/speed-task.json \
    --task-change "track_speed one-sided: no give-back past the command (0.75 -> 0.5); judged range to 6500; nothing else" \
    --after x1a-cold --build ~/orun19-queue/leo_x1b.py
```

- **The run**: `x1b-warm`, launched at 23:20:20 on `6f4bbe78`. Warm from
  `efe7f96b`, seed 0, 4096 envs, 150 iterations, a checkpoint every 25, no
  critic warm-up, the default learning rate. Registered, view retained and
  launched through `cadex_cli.loop`.
- **Budget**: 3,600 s.
- **Timed**: by the trainer's own wall clock, iteration 10 came at 342 s
  and iteration 15 at 432 s, so ~17.9 s an iteration (s2a-hold ran
  ~18.7). The projection is 342 + 140 × 17.9 ≈ 2,850 s for 150, and that
  plus 20% is ~3,420 s, so the 3,600 s budget covers it. Measured against
  the end instead: s2a-hold and x1a-cold each finished their 150 at
  ~3,118 s, checkpoint rollouts included, which leaves 15% headroom in
  3,600 s, not 20%. The budget was set before the timing, because
  `queue_run.py` takes it at registration.
- **Early curve**: reward per step 9.18 at iteration 0 (the critic is fresh
  on the new reward), 20.29 at 5 (the best so far), 19.34 at 10 and 19.15 at
  15. σ rises from 0.510 to 0.539.

## Why this change

s2a-hold-150 holds ~4.55 m/s at every command from 4.23 to 5.0 in one
fixed gait (`s2a-hold-150-top.md`). X1a showed that raising the ceiling
alone, cold, gives a slower policy (~4.1 m/s). The tent's give-back is the
one term that pays the policy to stay under the command once it reaches it.
Taking it out is the smallest change that stops penalising speed, and it
leaves the network's inputs as they were.

What it cannot do: the goal still stops at 5 m/s and the reward stops rising
at the command. So a new top needs the policy to run faster than s2a-hold's
plateau at commands of 4.23–5.0, not more than 5.0 to be asked for. If X1b
does not raise the top, the next lever is a reward that keeps rising past
the command, which is open to X1.
