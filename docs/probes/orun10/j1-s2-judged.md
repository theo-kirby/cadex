# orun10 J1: j1-s2 judged at every checkpoint

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 13).

j1-s2 warm-starts from j1-s1's final on orun10-jump `6abd8390`. That bundle
adds world +x progress (weight 2) and an off-line price (weight 1) to the leap
reward and drops the shove (`j1-leap-check.md`). It ran at lr 3e-5 with a
10-iteration critic warm-up, for 100 iterations at about 45 s each, with a
checkpoint every 25. Its trainer reward per step was 3.8 → 6.5, and the
trainer's best is iteration 9 (8.21).

Each checkpoint is judged on the bundle's own `j1_spec`, seeds 1001–1010, on
the 6 m wide J1 course: a 300 mm ledge at x = 3 m, 1.5 m long, then a drop.
The judge is the engine's evaluation (`orun10-jump/evaluations/j1-s2-*`;
`s8/judge_j1.py` and `s8/summ_j1.py`). Seeds are classed by their chest path
(`s9/leap_paths.py`).

| checkpoint | pass | completes | up_across_down (median) | lands_running (6 m made good; median) | highest platform | best 2 s speed, median | stall / detour / over | worst RMS / rated, median (range) | peak margin |
|---|---|---|---|---|---|---|---|---|---|
| j1-s1 final (start) | 0/10 | 6/10 | 0/10 (0) | 0/10 (2.70 m) | 0 | 1.23 m/s | 7 / 3 / 0 | 1.06 (0.77–1.38) | 0 |
| 25 | 0/10 | 8/10 | 0/10 (0) | 2/10 (2.68 m) | 0 on all 10 | 1.245 m/s | 6 / 4 / 0 | 0.95 (0.78–1.08) | 0 |
| 50 | 0/10 | 10/10 | 0/10 (0) | 0/10 (2.71 m) | 0 on all 10 | 1.236 m/s | 9 / 1 / 0 | 0.83 (0.70–1.01) | 0 |
| 75 | 0/10 | 9/10 | 0/10 (0) | 0/10 (2.75 m) | 0 on all 10 | 1.243 m/s | 10 / 0 / 0 | 0.74 (0.62–1.10) | 0 |
| final (it 100) | 0/10 | 8/10 | 0/10 (0) | 1/10 (2.70 m) | 0 on all 10 | 1.233 m/s | 8 / 2 / 0 | 0.77 (0.60–0.98) | 0 |
| best (it 9) | 0/10 | 8/10 | 0/10 (0) | 1/10 (2.68 m) | 0 on all 10 | 1.232 m/s | 8 / 2 / 0 | 1.04 (0.92–1.28) | 0 |

`no_fall` passes 10/10 at every checkpoint. No seed leaves the ground at the
face, so no take-off speed or leap peak is measured. The model clamps drives
at peak (peak ratio 1.000, margin 0).

What it shows:

- **The progress term removed the detour, not the stall.** Detours fell from
  4 at it 25 to 0 at it 75. Every remaining seed stalls with the chest at
  x ≈ 2.70–2.83 m, at the face of the ledge. The stall still earns
  6.91 a step on the judged episodes (26 of them across 75, final and best),
  against a detour's 3.87.
- **It does not run at the commanded speed.** Its best 2 s speed is
  1.23–1.25 m/s against the spec's 2.5 m/s, unchanged from j1-s1 and from
  the zero-shot c1-c11b.
- This fits the open `leap-goal-draws-not-movable` finding: the task trains
  on C1's random goal draws, and the progress and off-line terms are gated
  off whenever a turn is asked. A warm start cannot move `goal`. Reward edits
  on this warm lineage are therefore spent on J1. The next J1 step is a task
  that trains on the spec's straight 2.5 m/s command. It is either a cold
  leap task on the J goals or a trainer change that lets a curriculum move
  the goal draws (an ADR). Of the two, the cold task touches no contract.
