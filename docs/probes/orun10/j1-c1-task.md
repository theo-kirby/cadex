# orun10 J1: j1-c1, the leap task trained cold on its own straight goals

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 14).

## Why

j1-s1 and j1-s2 both started warm from C1. Both were judged 0/10 at every
checkpoint (`j1-s1-judged.md`, `j1-s2-judged.md`). In j1-s2 every seed
stalls at the ledge face, at a best 2 s speed of 1.23 m/s against the
spec's 2.5 m/s command. Both trained on C1's goal draws:

- cmd −0.8 to 3.5 m/s, redrawn every 3 s;
- turns of ±60°/s;
- a random nav mode.

So few training episodes met the ledge head-on at speed. A warm start may
not move `goal`.

## The task (orun10-jump `07e833fb`)

The script (`~/orun10-progress/s11/leap3-script.py`, project commits
`966a2f2` and `d0eddb0`) adds the parameter `leap_straight`. Its default is
0, which leaves every task as it was. At 1, the leap task trains on
`J_GOALS`, the goals `j1_spec` judges with:

- cmd held at 2500 mm/s for the whole 12 s;
- turn held at 0;
- nav held at −1, the cmd mode.

It keeps C1's channels and draw ranges. `check_bundle.py` compared the
rebuilt bundle against j1-s2's trained bundle:

- **only `goal` and `goal_algorithm` differ;**
- the reward is j1-s2's, term for term (15 terms, with `progress_x` at
  weight 2 and `off_line` at weight 1);
- the trainer loads the bundle;
- the trainer refuses a warm start from j1-s2, naming `['goal', 'goal_algorithm']`.

So the task trains cold.

## Per-step check (`leap_check3.py`)

All 90 judged j1-s1 and j1-s2 episodes ran on `j1_spec`'s goals, the goals
this task now trains on. Their returns were re-scored on the j1-c1 reward:

- the C1 terms come from `evaluation.json`;
- `progress_x` and `off_line` are re-read from the chest path.

No judged episode leaps, so the leap row is the same estimate as
`j1-leap-check.md`.

| class | n | return per step | `speed` term | progress_x | off_line (m) |
|---|---|---|---|---|---|
| stall | 70 | 6.73 | 0.56 | 0.26 | 0.36 |
| detour | 20 | 4.19 | 3.23 | 0.45 | 5.30 |
| leap (estimate) | — | 13.94 | — | 2.38 | 0.36 |

A leap out-earns a stall by 7.21 a step and a detour by 9.75. A detour
earns 2.54 less than a stall.

## The run

j1-c1 is a 150-iteration cold screen (`training/RECIPE.md`: screen at 100–150), with
8192 envs and a checkpoint every 25. It was registered through
`cadex_cli.loop` with `retain_training_view`. It launched in its own
`systemd-run --user --scope -p MemoryMax=30G` when s3-h1 freed the GPU,
at 02:33 on 2026-10-18, through `launch_c1_when_free.sh`. Its first
iterations are a cold start: reward per step 1.36–1.54, episodes of 40–54
steps, and σ falling from its first-update value. It is not judged yet.
