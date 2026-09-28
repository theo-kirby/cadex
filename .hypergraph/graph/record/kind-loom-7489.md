---
node_id: c0704f8e-0eb6-5eeb-bf85-784d325d2075
slug: kind-loom-7489
title: 'ot10: W2 run 2 on ot10-quadruped-3 — warm-started, walked 1.44 m upright, walked=false on a horizon-boundary survival artifact, diagnosed'
created_at: '2026-09-28T16:52:19+00:00'
parents:
- calm-mesa-1063
summary: ''
---
## What

W2 run 2 (`w2-2`) on `ot10-quadruped-3`. Pre-registered in `docs/probes/ot10/README.md` (commit `1c4600e1`) before launch, then run, then published with its verdict, curve, W1 video and diagnosis (commit `4bfe59e1`). It warm-starts the actor from `w2-1`'s policy (`d8b87d2e1215…`) on the unchanged ADR-410 task (bundle sha256 `b0913fa0fb93…`, byte-identical re-export). Budget: 1,000 iterations × 2,048 envs, training seed 0, `--timeout 10800`, `--stop-on-collapse`, grounding enforced, gait thresholds unchanged. The rollout seed is `null` in the script, not training's seed 0.

## Why

The critic's message named this unit: pre-register W2 run 2 with a warm start from w2-1 on the unchanged digest, a bounded budget and stop rule, and a null rollout seed; run it; publish the verdict, the W1 video and the curve; if `walked=false`, diagnose it without touching thresholds. All of that was done as asked. W2 is an open charter criterion (`golden-garden-8501`).

## Method

- Launched with `setsid nohup ./cadex walk --project ~/cadex-projects/ot10-quadruped-3-w2 --out …/runs/w2-2 --iterations 1000 --envs 2048 --seed 0 --init-from …/runs/w2-1/train/walk_task.cxpolicy --timeout 10800 --json` at 15:49:25Z. The engine/source comparison was `match` (57 files).
- Read `review.json`, `run.json` and `train/progress.json` from the run directory.
- Rendered W1 with `python -m cadex_cli.video --project <copy> --run w2-2`. Decoded frames 0/50/100 with the pixi env's ffmpeg into a committed 245 KB strip.
- Read foot heights from the trace: the foot STL's bbox centre, carried by each frame's placement.
- Checked the trainer's `episode_steps` against its source (`done = terminated or timeout`, `training/cadex_train.py:1497`, and `unroll × envs / endings` near line 1648). Checked it against horizon-boundary iterations in both runs' curves.

## Result

**`walked = false`, and it is an honest incomplete result. No threshold moved.**
- The walk exited 0 in 2,157.5 s: train 1,866.3 s, declare 59.7 s, roll-out 126.7 s.
- The trainer ran all 1,000 iterations on the GPU, and the collapse stop did not fire.
- Policy `7a4e8c233214…` (witness 1.3e-7) was stored and declared, then rolled out at revision `84ff4c98adab…`, digest `d67ac96c2fe0…`.
- Curve: reward per step went from 2.283 (iterations 0–99) to 2.662 (900–999). The best was 2.697 at iteration 998.

**Roll-out, the full 10 s episode with 501 frames:**
- It never tipped (maximum tilt 15.9°) and was upright in 100% of frames.
- It was not terminated.
- It travelled 1,443.8 mm forward and 297 mm sideways, at 147 mm/s planar against the 80 mm/s target.
- Heading stayed between −19.5° and +30.5°.
- Total reward was 614.4, against w2-1's 358.2.
- The feet lift and land repeatedly (48–124 crossings of a 3 mm line per foot), so it is stepping, not sliding.

**W1 video:** `rollout-e64ac61844fc….webm`, 322,440 bytes, 101 frames, rendered in 153.9 s against the 300 s bound. It lives in the copy's `runs/w2-2/`, not in git. I did not repeat the dashboard playback check in Chromium for this video.

**Diagnosis.** The only failing gait finding is `training_survival`: 32 of 500 steps, or 0.06 against the 0.90 bar. It is a measurement artifact:
- The trainer's `episode_steps` counts time-limit truncations as endings.
- With unroll 20 and horizon 500, every 25th iteration ends on a horizon boundary, where envs that have not fallen truncate together. Iteration 999 is always one of these.
- In w2-2, every sampled `(i+1) % 25 == 0` iteration reads 30.7–31.9, and every other one reads at least 787.7 (median 1,517). In w2-1 it is 204.8–213.3 on the boundary and at least 350.1 off it (median 525).
- `training_survival` reads only the last entry, so it reads this artifact every time. This names the mechanism behind w2-1's finding 3.

**Next unit (recorded, not done):**
- Fix `training_survival` to count true terminations only, or to read a trailing window that no horizon boundary dominates. It needs a regression test that fails on the current source. Keep the 0.90 bar.
- Then re-review w2-1 and w2-2 from their stored artifacts. That needs no retraining.
- Assumption: this is a measurement correction, not a weakened threshold. It still re-scores both runs, and the fix's record must say so.

**Other notes:**
- The reconcile tail is now 2 unreconciled records.
- No new dependency.
- Both suites: `cli/tests/test_ot10_contract.py` passes (21). The full CLI suite passed at `4bfe59e1`: 1,039 passed, 1 skipped. The engine suite was not re-run, because this unit changed only docs and a PNG.

Dispatch closed: 1 unit — W2 run 2 pre-registered, warm-started and run: 1.44 m forward upright over the full episode, walked=false only on a horizon-boundary survival artifact, diagnosed with the fix named

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4bfe59e12bbb9193708980dc8d15573051ea1887

## State Impact

- target: golden-garden-8501 — W2 run 2 (w2-2) pre-registered and run: warm start from w2-1 on the unchanged task, 1000x2048; the roll-out goes 1,443.8 mm forward over the full 10 s episode, never tips, upright 100%, stepping; walked=false solely because training_survival reads the trainer's episode_steps at iteration 999, a horizon-boundary batch where time-limit truncations count as endings (31.9 steps); W1 video rendered 153.9 s/300 s; next: fix the survival measurement with a regression, keep the 0.90 bar, re-review w2-1 and w2-2
