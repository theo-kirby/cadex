# T2: the Go1 go-to-point actor given a height scan

Verified against source: 2026-10-29 (this commit). Frozen run evidence; read it, never cite
it as current.

This tests T2-JUDGE.md's hypothesis directly: the blind actor stops at step faces it
cannot see (ADR-859).

## How

- **Bundle.** `t2_scan.py bundle go1-around go1-scan` is the same model and task as
  `go1-around`, plus one `scans` row: `height_scan` on the trunk, `role: policy`, on the
  engine's 5 × 3 grid (−100 to +300 mm ahead, ±100 mm across). Nothing else moves.
- **Warm start.** From `go1-around/run1/go1.000200.cxpolicy`, the checkpoint that
  passed flat 10/10, across `--init-from-task-change`. The trainer gives the 15 new
  actor inputs zero weights, so the warmed actor starts as the source's policy (ADR-859).
  The critic starts cold, as on every warm start.
- **Screen.** `~/cadex-projects/orun21-lab/go1-scan/run1`: 300 × 8192 × 20 = 49.2 M env
  steps, wall time 512 s, the same flags as `go1-around/run1`, seed 3. The curriculum's
  batch mean level was 0.96 at iteration 100, 1.86 at 200 and 2.68 at 299, and still
  climbing.
- **Judge.** `g2_judge.py` as T2-JUDGE.md ran it: ten held-out sequences per row, the
  held-out course stream, and G2's bar with no widening. The player reads the scan over
  the course stood (`cadex_goto.Player`). On 300 random poses over the pool's course 0,
  its reading matched `CadexDynamics.height_scan_values` to within 6e-14 mm.

## Ten held-out seeds per row

| policy | ground | pass | reach | speed | falls | unreached /80 |
|---|---|---|---|---|---|---|
| `go1-around/run1` it 200 (blind) | flat | 10 | 10 | 10 | 0 | 0 |
| | level 2 | 1 | 2 | 6 | 2 | 34 |
| | level 4 | 0 | 0 | 3 | 6 | 58 |
| `go1-scan/run1` it 100 | level 2 | 1 | 2 | 5 | 4 | 43 |
| `go1-scan/run1` it 200 | flat | **10** | 10 | 10 | 0 | 0 |
| | level 0 | 10 | 10 | 10 | 0 | 0 |
| | level 2 | **6** | 6 | 7 | 2 | 15 |
| | level 4 | 0 | 0 | 2 | 4 | 56 |
| | level 6 | 0 | 0 | 2 | 6 | 63 |
| `go1-scan/run1` final (it 299) | flat | **10** | 10 | 10 | 0 | 0 |
| | level 0 | 10 | 10 | 10 | 0 | 0 |
| | level 2 | **5** | 5 | 6 | 0 | 18 |
| | level 4 | 1 | 1 | 3 | 1 | 50 |
| | level 6 | 0 | 0 | 3 | 3 | 62 |

## What it shows

- **The scan moves level 2, and flat holds.** Level 2 rose from 1/10 to 6/10 at
  iteration 200 and 5/10 at the end. Unreached points fell from 34 to 15–18 of 80.
  Flat ground and level 0 pass 10/10 at both checkpoints. The blind run had lost
  flat (3/10) by its own final checkpoint.
- **Level 4 is not moved yet.** It passes 0–1 of 10, with 50–56 points unreached. By the
  end the robot falls less often (1 fall against the blind policy's 6) but stops more,
  at the 70–85 mm faces. The curriculum reached a batch mean level of 2.68, and only
  424 of 8,192 environments trained at level 5 or higher. So level 4 was barely trained
  when the screen stopped.
- **Iteration 100 is not better than blind.** The scan inputs start at zero weight, and
  the climb shows only between iterations 100 and 200.

T2 is not met: level 4 and above still fail, and no wall or maze sequence has been played.
The blind-actor hypothesis holds at level 2.

## Extended: more exposure at the higher levels

**Hypothesis.** Level 4 failed because the curriculum barely reached it (424 of 8,192
environments at level 5 or higher when run1 stopped). More iterations at the high levels
should move level 4.

- **Screen.** `go1-scan/run2`: the same bundle and flags, warm from run1's final policy
  (`--init-from run1/go1.cxpolicy`, no task change), seed 4, 450 × 8192 × 20 = 73.7 M env
  steps in 741 s. The curriculum restarts every environment at level 0, because levels are
  not carried in a checkpoint. The batch mean level was 0.99 at iteration 112, 1.92 at 225,
  2.81 at 337 and 3.85 at 449, still climbing. At the end, 2,478 environments were at level
  5 or higher, against run1's 424.
- **Judge.** The same `g2_judge.py` rows on the same held-out seeds (`go1-scan/judge2/`).

| policy | ground | pass | reach | hold | speed | falls | unreached /80 |
|---|---|---|---|---|---|---|---|
| run1 final (it 299) | flat | 10 | 10 | 10 | 10 | 0 | 0 |
| | level 2 | 5 | 5 | | 6 | 0 | 18 |
| | level 4 | 1 | 1 | | 3 | 1 | 50 |
| | level 6 | 0 | 0 | | 3 | 3 | 62 |
| `run2` it 300 | level 2 | **6** | 8 | 10 | 7 | 1 | **7** |
| | level 4 | 1 | 2 | 10 | 5 | 5 | 34 |
| `run2` final (it 449) | flat | 6 | 10 | 10 | **6** | 0 | 0 |
| | level 0 | 6 | 10 | 10 | 6 | 0 | 0 |
| | level 2 | 4 | 7 | 10 | 4 | 3 | 7 |
| | level 4 | 1 | 2 | 9 | 3 | 3 | **24** |
| | level 6 | 0 | 0 | 10 | 2 | 4 | 54 |

(The hold column was not tabulated for run1. Every run1 row above passed hold wherever it
reached a point.)

**What it shows.**
- **Exposure moves reach, not passes.** Unreached points at level 4 fell from 50 to 34 at
  iteration 300 and to 24 at the end. At level 2 they fell from 18 to 7. Passes at level 4
  stayed at 1/10, because the seeds that now get further either fall (3–5 seeds against
  run1's 1) or stall on one leg (speed ratios 0.06–0.34 on the stalled legs).
- **It costs flat speed.** The final checkpoint is slower on flat ground. Six of ten seeds
  pass speed against run1's ten, and the slow legs run at 0.78–0.82 of the command. Its run
  legs take 7.26 s against 6.84 s, and its walk legs ahead 13.72 s against 12.60 s. This is
  the same trade that `kind-ridge-3238` records for go-to-point share.
- **So the binding limit is not exposure.** More steps at level 4 and above turned stops
  into attempts and attempts into falls. They did not give the Go1 a gait that clears 70–90
  mm faces. Following the critic's rule, the next step is a foot-swing or clearance term
  (Rudin et al. 2022's feet-air-time, legged_gym's `feet_air_time` with a swing-height
  target), not more steps. The trainer already pays both through a task's `feet` block
  (`air_time`, `swing_height`, ADR-769). The Go1 bundle carries no `feet` block, so the
  next screen needs only a bundle change. The maze or wall sequence is still unplayed. `g2_judge.py` and
  `cadex_goto play` draw random held-out points, and they cannot yet place points through a
  maze's corridor.
