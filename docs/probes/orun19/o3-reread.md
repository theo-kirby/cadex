# orun19 S2: the judged speed policies re-read under the revised O3

Verified against source: 2026-10-23. Frozen evidence (orun19, iteration 14).
The owner rewrote O3 (2026-10-23): running over the command is never a miss;
a policy tracks when its speed over the last 2 s of each judged seed is no
more than 10% under the command at every judged command up to its top, with
0 falls; judgements already made are re-read, not re-run. This re-reads
every judged v06 speed policy and v05's b1-s2-180 from their evaluations.
Nothing was trained or evaluated again.

```
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun19/o3_reread.py ~/cadex-projects/leo/evaluations \
    s2a-hold-150 s2a-hold-50 s2b-tent-150 s2b-tent-50 s1-v06-180 s1-v06-50 b1-s2-180
```

`o3_reread.py` reads each `evaluation.json` (commands 700–5000 mm/s, seeds
1001–1010), takes each seed's last-2 s speed by orun18's
`b1_summary.last_window_speed` (the speed every earlier note used), counts a
fall from the engine's `falls` / `completed`, and calls the top the highest
command with every judged command up to it tracked.

## S2 is met: s2a-hold-150 tracks 0.7–3.5 m/s

**s2a-hold-150** (`efe7f96b`), 0 falls on 50 seeds:

| command m/s | last 2 s m/s, median (min / max) | slowest seed / command | seeds ≥ 0.9 × command | tracks |
|---|---|---|---|---|
| 0.7 | 0.86 (0.84 / 0.87) | 1.204 | 10/10 | yes |
| 1.5 | 1.80 (1.77 / 1.83) | 1.181 | 10/10 | yes |
| 2.4 | 2.95 (2.93 / 2.98) | 1.223 | 10/10 | yes |
| 3.5 | **4.08** (4.00 / 4.21) | 1.144 | 10/10 | yes |
| 5.0 | 4.53 (4.49 / 4.59) | 0.898 | 9/10 | no (seed 1003, 4.49, is 10.2% under) |

**Four commands, 0.7 to 3.5 m/s, 0 falls: S2's bar.** The top tracked
command is 3.5 m/s, held at **4.08 m/s median (4.00 the slowest seed), Fr
4.29** (4.12 on the slowest seed; hip height 0.396 m as in `s1-v06-180.md`,
Fr = v²/(g h)). Beside it: v05's B1 (b1-s2-180) tracks 0.7 and 1.5 only and
its top held speed is 2.59 m/s (Fr 1.73); Go1's tracked speed is 1.53 m/s
(Fr 0.80, `../orun18/b2-ceiling.md`). The fastest v06 has held on a
command is still 4.53 m/s (Fr 5.28) at 5.0, which misses by one seed.

O6 for this policy is unchanged from `s2a-hold-150.md`: worst RMS 1.03×
rated at 0.7 rising to 1.34× (`j_elbow_l`) at 3.5 and 1.43× at 5.0; peak
margin 0.00 at every command; fores lean left, hinds right at the knee; no
NaN; hind rod loops 1.0–1.5 mm.

## Every judged policy, re-read

| policy | 0.7 | 1.5 | 2.4 | 3.5 | 5.0 | falls | tracks up to | held there, median (Fr) |
|---|---|---|---|---|---|---|---|---|
| **s2a-hold-150** (`efe7f96b`) | 0.86 ✓ | 1.80 ✓ | 2.95 ✓ | 4.08 ✓ | 4.53 (9/10) | 0/50 | **3.5 (4 commands)** | **4.08 (4.29)** |
| s1-v06-180 (`bd32a42c`) | 0.75 ✓ | 2.17 ✓ | 3.07 ✓ | 3.77 ✓ | 4.24 (0/10) | 0/50 | 3.5 (4 commands) | 3.77 (3.66) |
| s2b-tent-150 (`f971c970`) | 0.97 ✓ | 1.89 ✓ | 3.09 ✓ | 3.82 ✓ | 4.01 (0/10) | 0/50 | 3.5 (4 commands) | 3.82 (3.76) |
| s2a-hold-50 (`80f97755`) | 1.80 ✓ | 1.95 ✓ | 1.63 (1/10) | 2.23 (0/10) | 1.05 (0/10) | 0/50 | 1.5 | 1.95 |
| s1-v06-50 (`a3296704`) | 1.62 ✓ | 1.70 ✓ | 1.76 (0/10) | 1.82 (0/10) | 1.04 (0/10) | 0/50 | 1.5 | 1.70 |
| s2b-tent-50 (`43cbe2ef`) | 1.27 ✓ | 1.43 (8/10) | 1.49 (0/10) | 1.23 (0/10) | 1.16 (0/10) | 0/50 | 0.7 | 1.27 |
| v05 b1-s2-180 (`8adbb84f`) | 1.84 ✓ | 2.59 ✓ | 1.85 (0/10) | 1.80 (0/10) | 1.62 (0/10) | 0/50 | 1.5 | 2.59 (1.73) |

Medians, m/s; ✓ = every seed at least 0.9 × the command; otherwise the
seeds that made it.

- **Three v06 policies now track four commands**, S1's own s1-v06-180
  included: the old rule failed them on overshoot, which no longer counts.
  The slowest seed of s1-v06-180 at 0.7 is 0.66 (0.943), so it passes on
  that command too.
- **Ranked faster first (O3)**, s2a-hold-150 is the best: fastest at the
  top tracked command (4.08 against 3.82 and 3.77) and at 5.0 (4.53 against
  4.24 and 4.01), the only one within one seed of a fifth command. It is
  S2's policy, the base for L1's comparison and X1's start.
- **None tracks 5.0.** v06's speed policies top out at 4.0–4.6 m/s on a
  5.0 command; at 5.0, s2a-hold-150 has the left elbow, left hock, right
  knee and left shoulder at their clamp on 0.13–0.17 of frames
  (`s2a-hold-150.md`). Raising that is X1's work.
- **What O3's levers moved, re-read.** Lever 1 (hold the command) took the
  speed policy from 3.77 to 4.08 at 3.5 and 4.24 to 4.53 at 5.0 and
  tightened the seed spread; lever 2 (symmetric tent) slowed the top end
  (4.01 at 5.0) and is still rejected, now for speed, not for overshoot.
