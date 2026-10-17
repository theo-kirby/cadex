# orun9 O8: the sprint allowance, set up and launched

Verified against source: 2026-10-17. Frozen evidence (orun9, iteration 7).

The hinge screen (`hinge-screen.md`) priced each drive's excess over rated
at weights 2, 4 and 8. Every weight passed `within_rated` on every spec, and
none ran the 3 m/s segments faster than 2.4 m/s (c1-t7 with no price:
2.56/2.42). O8 lets a sprint exceed rated but never peak (orun7 O3). This
screen takes that allowance in full: above a 2.5 m/s command both rated
prices step off, and only the peak price stays.

## The change (reward only)

On `~/cadex-projects/orun8-cat`, revision `c56eaf1a` (project commit
`34d0cf8`), task `run` sha256 `d71cc895`. The model is unchanged
(`f321f89c`). There is a new parameter, `sprint_from` = 2500 mm/s.

- `RATED_ON = exp(-exp((cmd - 2500) / 100))`: 0.95 at 2.2 m/s, 0.37 at
  2.5, 0.0006 at 2.7. It reads raw `cmd`, so a reverse keeps the factor at 1.
- `effort`'s rated mean was `(1 + DRV*STILL) * mean (tau/rated)^2`. It is
  now `(1 + DRV*(STILL + RATED_ON - 1)) * ...`. In cmd mode this is the
  old price below 2.2 m/s and zero above 2.7. The nav (waypoint) mode is
  unchanged, because its wanted speed is capped at 2.5 m/s. The
  `(tau/peak)^10` price is unchanged.
- `over_rated_fore/hind`: the cmd-mode gate `exp(-(CMD/2000)^2)` gains
  `- exp((cmd - 2500)/100)` in its exponent. That gives the same
  `RATED_ON` factor in fewer syntax nodes.
- To fit the engine's 512-node cap (the fore term was 517 nodes), each
  drive's `((x + |x|)/2)^2` became `(x + |x|)^2` and the term's weight
  became `-hinge_w / 4`. These are equal.

## Per-step reward check, before launch

`~/orun9-progress/c1s1/stepcheck.py` evaluates both bundles' `speed`,
`stand`, `effort` and `over_rated_*` terms with the engine's reward
evaluator. The robot is upright, in cmd mode, at forward speed v, with
every one of the 21 priced drives at k× its rating. The old bundle is
c1-h2's (`1673469d`). Tracking, posture and the other terms are left out:
they do not move with torque.

| cmd (m/s) | v (m/s) | k | old | new |
|---|---|---|---|---|
| 0 | 0 | 0.77 | +4.81 | +4.81 |
| 0 | 0 | 1.20 | +1.43 | +1.43 |
| 2.5 | 2.0 | 1.00 | +4.05 | +4.68 |
| 2.5 | 2.5 | 1.40 | +4.61 | +6.74 |
| 3.0 | 0 | 0.77 | −0.52 | +0.07 |
| 3.0 | 2.4 | 1.00 | +4.00 | +5.00 |
| 3.0 | 3.0 | 1.00 | +7.00 | +8.00 |
| 3.0 | 3.0 | 1.40 | +5.31 | +7.97 |

- **Standing is unchanged.** At command 0 every row is equal, so the stand
  price, including the doubled rated price at a stand, is untouched.
- **Moving always pays more than standing.** Standing at a 3 m/s command
  pays +0.07; running pays +5.00 to +8.00.
- **The sprint now pays for its torque.** At a 3 m/s command, the gain for
  running 3.0 m/s at 1.4× rated over 2.4 m/s at rated was +1.31 a step.
  It is now +2.97.
- **Risk:** the `run` spec judges `within_rated` over the whole episode,
  and two of its five segments ask 3 m/s. If those segments go well over
  rated, `run` can fail `within_rated` even though the sprint is allowed.
  Judging will show it.

## The run

- **Name:** `c1-sp2`. A 100-iteration warm start from c1-h2 at iteration
  100 (`runs/c1-h2/train/run.cxpolicy`), the only full turn2 pass.
  Settings: ADR-753 normaliser carried, critic warm-up 10, 8192 envs,
  seed 0, unroll 20, command slew 15°, checkpoints every 50. It was
  registered through `cadex_cli.loop` with its training view retained, in
  scope `orun9-c1-sp2` (MemoryMax 30G), on the GPU.
- **c1-sp1 is void.** It was registered and launched with
  `CUDA_VISIBLE_DEVICES=` inherited, so the trainer saw no GPU, and it ran
  in the loop's own scope. It was stopped by request after about a minute
  and trained nothing to judge.
- **Iteration time:** 13.9 s an iteration in steady state (iterations
  11 to 18 took 97 s). Iteration 11 came at 265 s of wall time, including
  the compile. c1-h2 and c1-h2x averaged 15.9 s/it over 100 iterations,
  compile included. Reward per step was 6.0 at iteration 18 (best 6.39 at
  iteration 6). Not judged yet.

## Judged (iteration 8)

c1-sp2, warm from c1-h2 at 100, finished 100 iterations (exit 0; the
witness agrees to 1.5e-7). Both checkpoints were judged on the six specs on
the 10 frozen seeds (`judge2.py --reward-may-differ`, CPU only).

| spec | it 50 | it 100 | failing predicate, median (it 100) |
|---|---|---|---|
| run | 0/10 | 0/10 | tracks_speed 781 mm/s RMS (713 at 50); within_rated passes, worst drive 0.82–0.91 |
| stand | 0/10 | 0/10 | still 559 mm (532 at 50) |
| shove | 10/10 | 10/10 | — |
| turn2 | 10/10 | 5/10 | tracks_yaw 7/10 (median 18.9), tracks_speed 8/10 (261 mm/s), tail_clear 7/10 |
| reverse | 0/10 | 0/10 | reverses 78° (64° at 50) |
| points | 0/10 | 0/10 | reaches 0, close 5790 mm |

**Speed per command segment** on `run` at iteration 100 (commands 0.5, 3.0,
1.5, 0.5 and 3.0 m/s, 2.4 s each; `segspeed.py`, mm/s across the 10 seeds):
0.54–0.63, 2.20–2.35, 2.04–2.17, 0.65–0.76 and 1.66–2.16. At iteration 50
the figures were 2.16–2.25 in the first 3 m/s segment and 1.86–2.23 in the
second.

**Finding.** The sprint allowance bought no speed. With the rated prices
switched off above 2.5 m/s, the cat ran no faster than c1-h2, and every
drive stayed within rated over the whole episode (worst 0.91). So `run` does
not fail `within_rated` in its 3 m/s segments: it fails on speed while the
drives have rated margin left. This agrees with `frosty-trail-8831` (the run
binds on speed, not torque). The rated price is not what holds the cat below
3 m/s at this weighting. c1-sp2 passes no clause c1-h2 did not, and it lost
turn2 by iteration 100. Under O1, c1-h2x and c1-sp2 are two consecutive
judged cat runs with no new clause, so the next GPU run is a B run.
