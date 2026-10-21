# orun14: h1-meta at 25, stopped early (O8); p1-flat's build checked and launched

Verified against source: 2026-10-21. Follows `g1x-free-75.md` and
`p1-flat.md`.

## The run and the judging

- **The run:** h1-meta is g1-free's task with heel_pitch reshaped to
  `max(0, 1 - |_META - 6| / 16) ** 3` (`g1-free-50.md`), leo revision
  `e62efb91`, cold, 4096 envs, seed 0. Launched 07:15:57 and ran at about
  64 s an iteration. The trainer read 16.6 reward/step at iteration 24.
- **The checkpoint:** `gallop.000025.cxpolicy`, sha256 `39cc8865`.
- **The judging:** `orun11/judge.py` on `gallop_spec`, seeds 1001–1010, on
  the CPU, evaluation `h1-meta-25`. Then `orun12/legs.py`,
  `orun13/p2_lag.py`, `orun13/spine_foot.py` and `paw_floor.py`. The
  same-checkpoint comparison is g1-free-25 (the same task with the old
  heel_pitch).

| evaluation | pass | top 2 s m/s min / med / max | hock_down LH / RH (spec) | at toe-off LH / RH | no_tap | every_stride | overreach mm LH / RH (spec) | stride mm | touchdown Hz | flight stride share, s | worst RMS/rated | peak margin | loop gap max mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g1-free-25 | 0/10 | 0.43 / 0.53 / 0.66 | 0.02 / 0.02 (0/10, 0.015) | 0.00 / 0.00 | 0/10 (5.88) | 10/10 | −200 / −117 (0/10) | 397 / 393 | 2.67 / 2.56 | 0.06, 0.000 | 2.42 (j_tail1) | 0.00 | 2.2 |
| **h1-meta-25** | 0/10 | 0.61 / **0.73** / 0.85 | **0.07 / 0.04** (0/10, 0.039) | 0.04 / 0.00 | 0/10 (2.10) | 9/10 (1.54) | −222 / −177 (0/10, −222) | 173 / 192 | 2.78 / 3.00 | 0.10, 0.000 | 1.86 (j_tail1) | 0.00 | 2.1 |

- **Passing:** `no_fall` 10/10; `completes` and `upright` 9/10 (19.5°).
- **Failing medians:** `straight` 2/10 (26.4°, g1-free-25 passed 10/10 at
  21.3°), `top_speed` 0.73 m/s, `hock_down` 0.039, `hock_at_toeoff` 0,
  `no_tap` 2.10, `overreach` −222 mm.
- **Left and right (O5):** heels 0.07 / 0.04, stride 173 / 192 mm,
  touchdowns 2.78 / 3.00 Hz. The stride is a 17–19 cm shuffle.

## The hind paws: no flatter of the floor

`paw_floor.py`, medians over 10 seeds:

| evaluation | leg | on-ground F / R / T / U | floor pitch ° in stance | pin ° in stance | pin ° / floor pitch ° at lift | lifts toes-up of floor | pin rate p95 / max °/s | swing p95 °/s | flapping swings |
|---|---|---|---|---|---|---|---|---|---|
| g1-free-25 | LH | 0.02 / 0.96 / 0.00 / 0.02 | +0.7 | +10.7 | +12.9 / +0.3 | 0.00 | 230 / 727 | 114 | 0.00 |
| g1-free-25 | RH | 0.02 / 0.95 / 0.00 / 0.03 | +1.9 | +17.3 | +21.1 / +1.4 | 0.00 | 262 / 604 | 122 | 0.00 |
| **h1-meta-25** | LH | 0.05 / 0.79 / 0.01 / **0.13** | **+1.3** | +17.5 | +19.6 / +0.1 | 0.11 | 298 / 830 | 131 | 0.00 |
| **h1-meta-25** | RH | 0.04 / 0.79 / 0.00 / **0.15** | **+2.3** | +17.2 | +24.1 / +1.5 | 0.13 | 329 / 785 | 131 | 0.00 |

- **No flatter, and the toes-up share already growing.** The stance floor
  pitch is +1.3 / +2.3° against g1-free-25's +0.7 / +1.9°. The share of
  ground frames toes-up of the floor (U) is 0.13 / 0.15 against 0.02 /
  0.03, five times as large. A paw lifts toes-up of the floor on 0.11 /
  0.13 of toe-offs, where g1-free-25 had none.
- **The heel moved little.** 0.07 / 0.04 against 0.02 / 0.02, on a
  shuffle. In g1-free the heel share came with the toes-up landing
  (25 → 50: heels 0.02 → 0.30, U 0.02 → 0.76). h1-meta shows that start
  sooner, not a flat-footed heel.
- **Pin speed (O9):** 298 / 329°/s p95, swing 131°/s p95, no swing frame
  over 900°/s, no flapping.

## Gait, spine, torque

- **Pair lag (`p2_lag.py`):** fore 0.355 of the stride, hind 0.342;
  rotary on 1/10 seeds; no flight (0.000 s, a share of 0.10). Seed 1003
  reads no ordered stride.
- **Spine (`spine_foot.py`):** 31.1° a stride (the sum of the two
  joints), 0.15 of frames at a stop, the cable gap at most 0.17° (O9: 1°).
- **Torque:** the worst RMS drive is `j_tail1` at 1.86× rated; the peak
  margin is 0.00. The rod loops are open to 2.1 mm (O9: 2 mm).

## The decision: stop at 25

The critic's rule for this checkpoint was to stop h1-meta if it was no
flatter of the floor. Its floor pitch is no better than g1-free-25's, and
its U share is five times larger. The reshaped heel_pitch reads only the
metatarsus, so it cannot see the paw on its pin (`g1-free-50.md`). It was
stopped through `loop.request_stop` at 07:52:46, with the reason in the
ledger, and its state read back `stopped`. It wrote no final policy, only
the 25 checkpoint and `gallop.best`. Recorded as a dead end for P1: the
reshaped metatarsus term alone does not flatten the paw.

## p1-flat: build verdicts and launch

- **The revision:** `orun14-p1.py` built `4c9de98d` (project git
  `18afa79`, digest `85419986`), and the project's accepted revision is
  `4c9de98d`. The queue's `--expect-revision` is the revision that build
  accepted, so p1-flat trains on exactly it.
- **Static clearance** (`cadex clearance`, published measurements at the
  initial pose, no rebuild): 8,911 pairs checked, 14 failing, the same as
  `bc287c9c` (`b1-ready.md`):
  - heel/metatarsus intersections, 168.2 / 154.2 mm³ (welded);
  - eight front and hind crank/rod/paw/metatarsus pairs below clearance
    at 0 mm;
  - four declared contacts that miss: elbow drive/forearm 2.9 mm, knee
    drive/shin 9.5 mm, each side.
- **Joint sweep** (`cadex clearance --sweep`, complete coverage): 12
  failing pair-through-joint rows, 8 distinct pairs, all front-leg parts
  against the chest through `j_shoulder_*` and `j_scap_*` (wrist drive up
  to 11,270 mm³, crank 1,092, forearm 1,027, rod 290). This is the
  baseline's 12. No new pair.
- **The bundle** (`runs/p1-flat/train/gallop-task.json`): 19 reward terms
  with `paw_flat`. It has `q_pawpin_l`, `dq_pawpin_l`, `q_pawpin_r` and
  `dq_pawpin_r` as observations. `ohl` / `ohr` are gone. h1-meta's bundle
  had 18 terms and `ohl` / `ohr`.
- **Launched** at 07:52:52 on `4c9de98d`, cold, 50 iterations, 4096 envs,
  budget 4,800 s. Judge it at 25 and 50 under `p1-flat.md`'s keep rule.
  The same-checkpoint comparisons are g1-free-25 and h1-meta-25 (U 0.02–0.15,
  floor pitch +0.7 to +2.3°).
