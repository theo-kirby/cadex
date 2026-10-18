# orun10 J1: does a world +x progress term pay the leap over the stall and the detour? (per-step check)

Verified against source: 2026-10-18. Frozen evidence (orun10, iteration 12).

j1-s1 judged 0/10 at every checkpoint (`j1-s1-judged.md`). Its chest
stalls at the ledge face, or it turns round the 6 m ledge. Before training
again, this check asks j1-s1's own judged episodes whether a world-frame
+x progress term, or a price on leaving the course line, would make
leaping out-earn stalling and detouring.

**Method.** `leap_check.py` is in the run's progress folder, `s9/`. It
reads the 40 judged j1-s1 episodes (checkpoints 25, 50, 75 and final, seeds
1001–1010, all on `j1_spec`). It classifies each seed by its chest path in
the trace (50 Hz chest placement):

- **over** if the chest is more than 150 mm up while over the platform
  (none are);
- **detour** if |y| passes the ledge's 3 m half-width;
- **stall** otherwise.

Returns are each term's total over the 600-step horizon, so an early
termination earns nothing after it. Reward terms are linear in their
weights, so they re-weight exactly. Two candidates are read from the chest
path, with the spec's own gates (cmd mode, turn 0, cmd 2500 mm/s):

- `progress_x = min(max(comv_x, 0), cmd) / 1000`: world +x speed, capped at
  the command;
- `off_line = |com_y| / 1000`: metres off the course line.

**The leap is an estimate.** No judged episode leaps. It is a straight
run at 95 % of the command for the whole 12 s. It earns the detours' median
total, with track_yaw and sideways swapped for the stalls' medians, and the
stalls' median |y|.

## The judged classes (median per step, over 600 steps)

| class | n | return | speed | track_yaw | sideways | progress_x | off_line (m) | ended early |
|---|---|---|---|---|---|---|---|---|
| stall | 29 | 6.61 | 0.56 | 1.89 | −0.04 | 0.27 | 0.21 | 8 |
| detour | 11 | 8.98 | 3.73 | 1.50 | −0.11 | 0.47 | 5.22 | 1 |
| leap (estimate) | — | 9.48 | — | — | — | 2.38 | 0.21 | — |

Detours run up to 20.8 m off the line. The body-frame `speed` term pays
them as it would pay a leap (3.73 against a stall's 0.56).

## Re-weighted (median return per step)

| w progress_x | w off_line | stall | detour | leap | leap − stall | leap − detour | detour − stall |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 6.61 | 8.98 | 9.48 | +2.86 | +0.50 | +2.36 |
| 0 | 1 | 5.93 | 3.15 | 9.26 | +3.34 | +6.11 | −2.77 |
| 1 | 0 | 6.93 | 10.04 | 11.85 | +4.92 | +1.81 | +3.11 |
| 1 | 0.5 | 6.56 | 6.41 | 11.75 | +5.18 | +5.33 | −0.15 |
| **2** | **1** | **6.49** | **4.42** | **14.01** | **+7.52** | **+9.60** | **−2.07** |
| 4 | 0 | 7.88 | 11.44 | 18.98 | +11.10 | +7.54 | +3.56 |
| 4 | 1 | 7.05 | 5.94 | 18.76 | +11.71 | +12.82 | −1.11 |

## Reading

- **The C1 reward already ranks a straight run first, by a thin margin over
  a detour** (+0.50 per step). A detour is the cheapest gain from a stall
  (+2.36), and j1-s1 took it on 3–4 seeds per checkpoint from 50.
- **Progress alone does not stop detours.** At w = 4 a detour still beats a
  stall by +3.56. The `off_line` price is what puts detours under stalls.
- **At weights 2 and 1** the run leads the stall by 7.52 and the detour by
  9.60, and a detour pays 2.07 less than a stall. These go into j1-s2.

## A limit this check does not move

The leap task trains on C1's goal draws: cmd −0.8 to 3.5 m/s resampled
every 3 s, turn ±60°/s, and a random nav mode with waypoints. Only a
minority of training episodes meet the ledge head-on at speed. The trainer
refuses a warm start that moves the goal draws: `goal` is not in
`CURRICULUM_TASK_KEYS` (ADR-161). So both new terms are gated off with the
yaw rate asked (`exp(-|turn|/15)`) and by the cmd mode. If j1-s2 still
stalls, the goal draws are the next lever: either a trainer change that
lets the draw ranges move (they change the distribution the actor reads,
not its channels), with an ADR, or a cold leap task on the J goals.

## The j1-s2 task (orun10-jump 6abd8390)

- `progress_x`, weight 2:
  `DRV · exp(−|turn|/15) · UP · max(min(comv_x, CMD), 0) / 1000`.
- `off_line`, weight −1: `DRV · exp(−|turn|/15) · |com_y| / 1000`.
- The leap task's training shove is dropped (no J spec judges one).
  Every other task in the script is unchanged.
- That makes 15 reward terms (the limit is 16).
- The trainer's own `check_policy_fits` (`s9/dry_check.py`) moves only
  `disturbance` and `reward` from j1-s1.
