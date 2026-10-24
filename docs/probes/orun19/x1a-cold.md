# orun19 X1a: the first top-speed screen, the command ceiling 5000 → 6500 mm/s (launch)

Verified against source: 2026-10-23. Charter X1, first screen: the launch.
Not judged yet. When it ends it is judged at 50 and 150 at S's commands,
up to 6.5 m/s, beside s2a-hold-150, X1's starting top (4.57 m/s held at 4.63,
Fr 5.38, 0/70 falls; `s2a-hold-150-top.md`).

## The one change

`~/orun19-queue/leo_x1a.py` is `leo_s2a.py` (s2a-hold's script) with one
literal changed: `SPEED_LOW, SPEED_HIGH = 700.0, 5000.0` → `700.0, 6500.0`.
That literal sets both the training goal's range and `speed_spec`'s judged
range. The spec is outside the task's digest, but `speed_judge.py` refuses a
command outside it, so it has to move for anything above 5 m/s to be judged.
`top_speed` stays a fixed 5000 mm/s. Why this change first: s2a-hold-150
holds ~4.55 m/s at every command from 4.23 to 5.0, and 5.0 was its highest
training draw. A policy never asked for more than 5 m/s has no reason to run
faster than its plateau.

- Built as leo revision **`9bc972a6`** by `queue_run.py --build` in ~3 min.
- Its bundle `runs/x1a-cold/train/speed-task.json` is **`1e513e8b`**. It
  differs from s2a-hold's `d5b25b15` in exactly five fields: `goal/0/high`
  5000 → 6500 and `goal/0/nominal` 2850 → 3600 (the range's midpoint), and
  the same two in `success/goal/0`, plus the spec's `sequence` 5000 → 6500.
  The model XML is byte-identical (`f9b8ab82`).

## Cold, not warm: the trainer refuses a goal change on a warm start

The first launch, `x1a-ceil`, was a warm start from s2a-hold-150
(`efe7f96b`), with s2a-hold's bundle as `--parent-task`. The trainer
refused it at 5.5 s, before iteration 0: `goal` is not among ADR-161's
`CURRICULUM_TASK_KEYS` (disturbance, episode, label, randomisation,
reset_variation, reward, success, termination), so `check_curriculum_change`
counts the goal as something the network reads. The goal's value is an
observation channel, so a new range is a new input distribution.

Allowing it would be a `training/` change, which needs an ADR and the
trainer's tests. So X1a trains cold, which O5 asks of a changed task
anyway. It also makes the comparison with s2a-hold exact: the same seed (0),
envs, iterations and budget, with one literal changed.

```
systemd-run --user --scope -p MemoryMax=30G env PYTHONPATH=cli pixi run python \
    docs/probes/orun13/queue_run.py ~/cadex-projects/leo x1a-cold 3600 150 \
    "orun19 X1a: s2a-hold's task with the command ceiling 5000 -> 6500 mm/s, cold (the trainer refuses a warm start across a goal change)" \
    --seed 0 --task speed --envs 4096 --expect-revision 9bc972a6
```

- **The run:** `x1a-cold`, launched 22:12:21 on `9bc972a6`. Cold, seed 0,
  4096 envs, 150 iterations, a checkpoint every 25.
- **Budget:** 3,600 s, s2a-hold's own. s2a-hold reached iteration 10 at
  372 s and ran ~18.7 s an iteration after that, about 2,990 s for 150.
  The budget is that plus 20% (O5).
