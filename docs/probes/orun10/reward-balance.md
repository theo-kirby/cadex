# orun10 S1: does the gallop reward pay the clip over speed? (per-step bundle check)

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 11).

Three gallop screens topped out between 4.07 and 4.50 m/s (s1-g1, s1-g4/g5,
s1-g6). `s1-g6-judged.md` read the fall after iteration 100 as the reward
paying the slow 2.1 m/s clip over speed. Before re-weighting anything, this
check asks the engine's own judged episodes whether a lighter clip changes
which behaviour the task pays most (the "going against not going" check on
the accepted bundle).

**Method.** Every reward term is linear in its weight, so a judged
episode's per-term totals re-weight exactly. `reweight.py` (in the run's
progress folder, `s8/`) reads every `gallop_spec` `evaluation.json` under
`orun10-cat/evaluations`. It groups them by the judged task's semantic digest
(one reward per group) and drops policies judged twice. For each seed it
divides each term by the 500-step horizon, so a fall earns nothing after it.
It scales the three clip terms (`track_pose`, `track_lift`, `track_contact`)
by k ∈ {1, 0.5, 0.25, 0}, leaves `track_speed` and the penalties alone, and
takes the median over seeds 1001–1010.

`track_speed` is 14 × v / 7 m/s (upright-scaled, saturating at 7 m/s), so
it pays 2.0 per step per m/s. The clip terms together pay at most 7.

## s1-g6's task (3.0 Hz, 0.7 m clip)

| checkpoint | 2 s top, m/s | completes | track_speed /step | clip /step | k = 1 | k = 0.5 | k = 0.25 | k = 0 |
|---|---|---|---|---|---|---|---|---|
| 50 | 3.035 | 10 | 5.76 | 5.41 | 13.90 | 11.19 | 9.84 | 8.49 |
| **100** | **4.072** | 10 | **7.77** | **6.05** | **16.66** | **13.63** | **12.12** | **10.60** |
| 150 | 3.761 | 10 | 7.15 | 5.85 | 15.97 | 13.05 | 11.59 | 10.12 |
| best 142 | 3.545 | 0 | 3.14 | 2.71 | 7.03 | 5.67 | 5.00 | 4.32 |
| best 193 | 3.003 | 10 | 5.80 | 5.72 | 14.19 | 11.33 | 9.90 | 8.46 |
| final 200 | 3.425 | 10 | 6.58 | 5.91 | 15.39 | 12.43 | 10.95 | 9.47 |

The fastest checkpoint (100) is paid most at every k. Its margin over the
next shrinks as the clip lightens: +0.69, +0.58, +0.52, +0.48 per step.

## The other two tasks

| judged task | fastest (2 s top) | paid most at k = 1 / 0.5 / 0.25 / 0 | its margin per step at k = 1 → 0 |
|---|---|---|---|
| s1-g1's (2.4 Hz clip, speed paid to a lower ceiling) | best 280 (4.248) | best 280 at every k | +0.72 → +0.65 |
| s1-g4/g5's (2.4 Hz clip, speed paid to 7 m/s at 14) | s1-g4 final (4.486) | s1-g4 final at every k | +0.05 → +0.08 |

## What it shows

- **On judged episodes the reward already pays speed first.** Among 23
  distinct judged policies across three tasks, the fastest is paid most
  under every re-weighting, including k = 1. The fastest checkpoint also
  tracks the clip best (s1-g6 at 100: clip 6.05 per step, the highest in its
  group), so speed and clip tracking go together here.
- **Down-weighting the clip is not the lever its last reading suggested.**
  On s1-g6 and s1-g1 a lighter clip narrows the fastest policy's lead. On
  s1-g4/g5 the lead is 0.05–0.09 per step at every k, against 2.0 per step
  that each extra m/s pays, so the weights barely separate those five
  4.26–4.49 m/s policies at all.
- **The inversion is the trainer's, not the engine's.** The trainer's reward
  per step ranks s1-g6's iteration 193 first (16.89, σ 0.39) and iteration
  100 below it (15.87, σ 0.51). Judged deterministically on the frozen seeds,
  the engine's reward has 100 at 16.66 and 193 at 14.19. So the ranking flips
  between the trainer's sampled returns and the engine's mean-action returns.
  The slowing after 100 is what the stochastic return pays, not what the
  task's terms prefer on a judged run.
- So `s1-g6-judged.md`'s line that "the reward pays the clip, not the speed"
  holds for the trainer's sampled return, not for the task's terms on judged
  episodes.

Not measured here: why the sampled return prefers the slower gait (σ, the
mass randomisation and the reset variation are the candidates), and what a
re-weighted task would train to. This check scores behaviours that already
exist. It says no re-weighting of the clip terms would make the judged
reward prefer any existing faster behaviour, since it already does.

## s1-g7 stays cold

s1-g7 changes only the clip (750 mm at duty 0.20). `warm_check.py` copies
s1-g6's bundle, moves only its `reference` key and asks the trainer's own
`check_policy_fits` to take s1-g6 at 100 across it. It refuses:
`these keys moved and may not: ['reference']` (ADR-161: a curriculum may
move `body`, `disturbance`, `episode`, `label`, `randomisation`,
`reset_variation`, `reward`, `success`, `termination`). So s1-g7 runs cold,
as its launcher says, and is compared with s1-g6 at 100.
