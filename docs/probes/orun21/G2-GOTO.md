# G2: the Go1 trained with the go-to-point layer in the loop

Verified against source: 2026-10-28 (this commit). Frozen run evidence; read it, never cite
it as current.

The first G2 training (ADR-840). Route A (ADR-839): a velocity-command policy
under `cadex_goto`'s layer. This time the layer also commands a share of the
training episodes. The Go1 bundle already has a lateral goal (`cy`, ±0.8 m/s),
so C-1 holds on the Go1 with no change.

## How

- **Trainer.** `cadex_train.py --goto walk:0.4-0.7,run:1.0-1.5 --goto-share S`.
  Each episode on the layer (chance S) draws one of 1024 `train`-split
  sequences, turned to a uniform heading about where the base starts (C-13:
  the actor sees no world yaw, so this is the yaw-uniform start it needs).
  `cx, cy, cw` are then the layer's command from the base pose at every step,
  for both the observation and the tracking reward.
- **Runs.** `orun21-lab/go1/runs/g2-goto{,-s20}/launch.sh` is run1's
  reference command (1260 × 8192 × 20 = **206.4 M env steps**, Playground's
  PPO settings, seed 1, cold, under the 30G scope) plus `--goto`.
- **Sequences.** Legs now carry `lead_s` = 2.5 s at their speed. Before this,
  only 17 of 37 run legs had a straight second to read; now all 37 do, and
  all 43 walk legs still do.
- **Judge.** `g2_judge.py POLICY TASK OUT` runs `cadex_goto.py play` on
  `heldout:0`–`9` (8 points each, 3–5 behind) and sums up the `goto.json`
  files. `leg_s` is the time from a point lighting to reaching it.
  `docs/probes/orun18/go1_judge.py` runs the plain joystick check.

## Budget against Playground (C-19)

| | env steps | trainer `wall_time_s` | launch → done |
|---|---|---|---|
| Playground Go1 joystick (orun18 A1, this 5090) | 200 M | 385 s | |
| run1, no layer (GO1-BASELINE.md) | 206.4 M | 324.7 s | 372 s |
| g2-goto, share 0.5 | 206.4 M | 334.9 s | 389 s |
| g2-goto-s20, share 0.2 | 206.4 M | 332.9 s | 387 s |

The layer costs about 3% of training time.

## Ten held-out sequences

| policy | pass (all) | falls | closest ≤ m | worst hold m | walk ratio min / mean | run ratio min / mean | total s (10 episodes) |
|---|---|---|---|---|---|---|---|
| run1, untouched | **10/10** | 0 | 0.256 | 0.100 | 0.924 / 0.941 | 0.947 / 0.954 | **870.3** |
| g2-goto-s20 (0.2) | **10/10** | 0 | 0.255 | 0.100 | 0.873 / 0.922 | 0.971 / 0.980 | 884.1 |
| g2-goto (0.5) | 3/10 (speed) | 0 | 0.253 | 0.100 | 0.767 / 0.902 | 0.977 / 0.984 | 916.2 |

Mean time to a point (`leg_s`, s) by band and bearing:

| policy | walk ahead | walk side | walk behind | run ahead | run side | run behind |
|---|---|---|---|---|---|---|
| run1 | 12.30 | 10.46 | 11.69 | 6.88 | 7.17 | 8.08 |
| s20 | 12.89 | 10.78 | 11.82 | 6.94 | 7.27 | 8.11 |
| 0.5 | 13.92 | 11.28 | 12.21 | 7.27 | 7.56 | 8.27 |

The plain joystick check (last 2 s, 10 seeds, 0 falls each):

| command m/s | run1 | s20 | 0.5 |
|---|---|---|---|
| 0.5 | 0.470 | 0.458 | 0.443 |
| 1.0 | 0.958 | 0.977 | 0.993 |
| 1.5 | 1.431 | 1.466 | 1.473 |

## What it shows

- **G2's bar is met by g2-goto-s20**: 10/10 held-out sequences, every point
  reached within 0.3 m, every hold within 0.15 m, no fall, straight-leg speed
  0.873–0.987 of the command. The untouched reference also meets it.
- **The layer in the loop does not make the robot faster to its points yet.**
  s20 takes 1.6% longer in total and 0.5 takes 5.3% longer. Run legs track
  better (0.98 against 0.95), and the plain check agrees at 1.0 and 1.5 m/s.
  Slow walking gets worse, and the loss grows with the share: 0.470, 0.458,
  0.443 at 0.5 m/s. Walk legs are slow and long, so they set the time.
- **What is binding, as a hypothesis.** The layer's episodes add many slow
  commands: the approach slow-down, the 0.25 m/s floor, and hold corrections
  of at most 0.3 m/s. Under the tracking kernel `exp(-err²/0.25)`, missing a
  0.45 m/s command by 0.05 m/s pays 0.99 of the term. So the policy trades
  slow-speed tracking for the posture and energy terms. The next step changes
  what the layer asks or what the reward pays at low speed. It does not tune
  the share again.
- Reach is close to guaranteed by the layer's arrival rule (0.25 m, or
  0.1 m for a hold), so the time per point is the reading that can show
  whether training helps.
