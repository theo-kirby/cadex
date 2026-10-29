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
