---
node_id: ffb04a33-0a2c-5e33-84ec-c445476179e4
slug: rough-bell-4055
title: 'orun2 W1 step 7 on the 5090: GPU walk and evaluate 10/10, defect 5 cleared'
created_at: '2026-10-04T10:05:51+00:00'
parents:
- fresh-dusk-5774
summary: ''
---
## What

W1 step 7's GPU leg, the owner's iteration-67 note. `cadex walk` trained
Robin's balance policy on the RTX 5090 at the budget of Robin's earlier
passing policy. `cadex evaluate` then held it to the task's success spec.
Both were seen in the dashboard, and the W1 README and REPORT (defect 5) now
carry the measured result. Commit `a320a489`.

## Why

The critic named this unit, and so did the owner's 2026-10-04 note: "W1
step 7's GPU leg comes next, before more subtraction." W1 was the only
criterion whose evidence still had a named gap (solemn-birch-8260). I did
what the critic asked, with no deviation.

## Method

1. **Preconditions.** `nvidia-smi` showed NVIDIA GeForce RTX 5090, driver
   580.178.04, 2 MiB used. `~/cadex-train-venv/bin/python -c "import jax;
   jax.default_backend()"` returned `gpu [CudaDevice(id=0)]`.
2. **Step 7**, on the existing copy `~/cadex-projects/orun2-w1-robin`. The
   accepted design was `bda7c1c9`, which declared the CPU policy on the
   current task `d50e953b`, so no stale-policy step was needed. The command
   ran with `JAX_PLATFORMS` unset and the GPU visible:
   `cadex walk --project . --out runs/w1-gpu-1 --name w1-gpu-1.cxpolicy
   --iterations 300 --envs 1024 --seed 1001 --timeout 3600 --json`, under
   `/usr/bin/time -v`. The budget was r3-ppo-1's recipe (300 it × 1024
   envs, seed 1001), from the project's `PROGRESS.md`. The trainer process
   held 24,612 MiB on the 5090.
3. **CLI suite while training was live.** `CUDA_VISIBLE_DEVICES=""
   JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` ran at the same
   time as step 7.
4. **Step 8:** `cadex evaluate --project . --out evaluations/w1-gpu-1 --json`.
5. **Dashboard:** `PYTHONPATH=cli pixi run python
   docs/probes/orun2/w1/walk_train_dashboard.py --run w1-gpu-1`. It is
   read-only, serves on 127.0.0.1 and drives headless Chromium. I replaced
   `w1-7-training.png` (202 KB) and `w1-8-evaluate.png` (239 KB) and
   `walk-train-steps.json`. The CPU versions stay in git history at
   `fbdf9d88`.
6. **Docs:** the W1 README's training paragraph and rows 7–8; REPORT's W1
   row, defect 5, §7 and its header line. `test_project_docs.py` +
   `test_licensing_compliance.py`: 50 passed, 1 skipped.

## Result

**True now: W1 step 7 trained on the 5090, and the policy passes 10 of 10
seeds.**

| | measured |
|---|---|
| walk | exit 0; 517.5 s wall (8:37.5), peak RSS 6.2 GB |
| legs | train 465.86 s (trainer wall time 331.13 s), declare 10.39 s, rollout 19.94 s |
| receipt | `device: gpu`, 5058 parameters, policy `dbd3913e`, task `d50e953b`, witness error 6.0e-8 |
| reward curve | 300 samples; reward/step rose from 0.167 to 0.950 at iteration 299, best 1.049 at 222; loss 21.6 peak → 7.91; median episode length 500 of 500 over iterations 250–299 |
| accepted | `bf914476` (digest edit plus `policy_on=1`), stored with its digest |
| rollout (seed 0) | upright over all 501 frames, max tilt 6.79°, travel 27.4 mm, total reward 672.6; clearance 378 pairs, 0 offending (initial solved pose) |
| evaluate | exit 0 in 194.9 s; **pass, 10/10 seeds**. B1–B5 all 10/10: tilt ≤ 6.35° (bound 30°), drift ≤ 1.64 COM heights (bound 2), heading ≤ 0.77° (bound 20°), recovery ≤ 1.80 s (bound 2 s); seed 1101 filmed |
| dashboard | Curves tab: run `w1-gpu-1` marked current and completed, iteration 299 of 300, 300 samples in each history. Evaluation tab: "pass: 10 of 10 seeds", with the CPU run's 0/10 listed as historical |
| CLI suite (GPU hidden, during training) | 1420 passed, 1 skipped, exit 0, 1233.75 s |

The engine suite was not run. This commit touches only
`docs/probes/orun2/` (docs, PNGs, JSON and a probe driver's usage
line), and no engine code.

**Concerns:**
- The packaged gate was not re-run, because nothing in the payload changed.
- The policy binary and rollout trace stay in the project copy. Neither is
  committed.
- With W1's gap closed, every criterion now has recorded evidence.
  REPORT §7 says so and claims done for critic review. Per the charter, the
  next unit is a long-term rung: the dashboard design pass, or further
  subtraction.

Dispatch closed: 1 unit — W1 step 7 on the 5090 (300 it × 1024 envs, 331 s, device gpu) and evaluate 10/10, seen in the dashboard; REPORT defect 5 cleared

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: a320a489f022286400160c574e13b559bab20982

## State Impact

- target: shady-clover-5534 — GPU leg closed: cadex walk on orun2-w1-robin trained on the RTX 5090 (300 it × 1024 envs, 331.1 s, device gpu, reward/step 0.950), rollout upright 501/501 frames, evaluate pass 10/10 seeds, both seen in the dashboard; REPORT defect 5 cleared; CLI suite GPU-hidden 1420 passed/1 skipped
