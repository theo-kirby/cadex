---
node_id: a9c349cb-368f-55a4-9ec6-4afcffe97cde
slug: dusty-bramble-8099
title: 'orun2 W1: walk steps 7-8 (training on CPU, evaluate) on orun2-w1-robin, seen in the dashboard; 5090 driver not loaded'
created_at: '2026-10-04T02:35:08+00:00'
parents:
- icy-tooth-7719
summary: ''
artifacts:
- docs/probes/orun2/w1/README.md
- docs/probes/orun2/w1/walk-train-steps.json
- docs/probes/orun2/w1/walk_train_dashboard.py
---
## What

orun2 W1 walk steps 7 and 8 on `~/cadex-projects/orun2-w1-robin`, a whole
copy of `ot11-robin-1` that ADR-520 unlocked. Step 7 is a short training run
and step 8 is `cadex evaluate`. Each step was seen in the dashboard through
headless Chromium. With steps 1–6 [rec: red-loom-2239], every step of the
W1 walk has now run on a real robot project and is visible in the dashboard.
**The deviation: the training ran on the CPU, not the 5090.**

## Why

The critic named this as the next unit: W1 steps 7–8 on `orun2-w1-robin`.
It is the last open part of the W1 walk, and W1 ranks above C1. The
critic's fix-first item, the ADR-520 record with the packaged gate, is the
parent record `icy-tooth-7719`.

**Deviation from the critic and the charter: "on the 5090" was not
possible.** The running kernel, `7.0.0-34-generic`, has no `nvidia` module.
`modinfo nvidia` reports it missing, `/lib/modules/7.0.0-34-generic` has no
`updates/dkms`, and `nvidia-smi` cannot reach the driver. `lspci` still shows
the card (`10de:2b85`). Fixing it needs root and a DKMS rebuild or a reboot
into a kernel with the module, and an unattended role has neither.
`training/SETUP.md` §b names CPU training as the path for lifecycle
verification. I took that path, which is the reversible option: it proves
every leg of the walk, and the 5090 run can replace it whenever the driver is
back. Iteration 41's record had already warned that `nvidia-smi` could not
reach the driver.

## Method

1. **First walk attempt, refused.** `JAX_PLATFORMS=cpu cadex walk
   --iterations 3 --envs 8 --name w1-cpu-1.cxpolicy` stopped at its train leg
   with exit 3. The project's accepted revision still had `policy_on=1`,
   because iteration 42 proved ADR-520 on a scratch copy and not on this
   project. The train leg's export built the stale policy, which refused with
   task digest `ca60b4ce…` against `d50e953b…`. That refusal is correct, and
   the run directory `runs/w1-cpu-1` is kept.
2. **Set the stale policy aside.** `cadex params --set policy_on=0` returned
   `ok: true` and accepted `bab6fa28`.
3. **Step 7.** `JAX_PLATFORMS=cpu CUDA_VISIBLE_DEVICES= cadex walk --out
   runs/w1-cpu-2 --name w1-cpu-2.cxpolicy --iterations 3 --envs 8 --seed 0
   --timeout 1800 --json` ran export, training, storage, the digest edit,
   declaration, rollout and reviews.
4. **Step 8.** `cadex evaluate --out evaluations/w1-cpu-2 --json`.
5. **Dashboard.** `docs/probes/orun2/w1/walk_train_dashboard.py` is new and
   only reads. It serves `cadex app` over `~/cadex-projects` on 127.0.0.1 on
   a random port, selects run `w1-cpu-2` on the Curves tab, then shows the
   accepted design on the Evaluation tab. It saves a screenshot of each and
   `walk-train-steps.json`.
6. The commit `fbdf9d88` adds only `docs/probes/orun2/w1/` (two PNGs of 183
   and 250 KB, the JSON, the driver and README rows 7–8). On it I ran
   `test_project_docs.py` and `test_licensing_compliance.py`: 50 passed, 1
   skipped. The full suites ran this iteration on the code tree, which
   `fbdf9d88` does not touch: engine 2606 passed, CLI 1400 passed, packaged
   gate 24 passed (see `icy-tooth-7719`).

## Result

**True now: every step of the W1 walk has run on a copy of a real robot
project and is visible in the dashboard. Step 7 ran on the CPU, not the
5090.**

| Step | Measured | Seen in the dashboard |
|---|---|---|
| 7. Training | walk exit 0. Legs: train 81.3 s, declare 9.1 s, rollout 18.8 s. Receipt: `device: cpu`, 5058 parameters, wall time 13.2 s, policy `d2556f70`, task `d50e953b`. The policy is stored with its digest. The digest edit was accepted as `bda7c1c9` (`policy_on=1`). The rollout tipped at step 19 with total reward 8.82. Clearance: 378 pairs, 0 offending. | Run `w1-cpu-2` is listed and marked **current**. Curves tab: iteration 2 of 3, and 3 retained samples in each of reward, loss and episode length. Checkpoints come from the run's own `train/`. Policy store: "stored — the project store holds this policy with the recorded digest". Screenshot: `w1-7-training.png`. |
| 8. `evaluate` | exit 0. **Fail, 0 of 10 seeds.** B1 (completed), B2 (tilt ≤ 30°, measured 32.4–36.1°) and B5 (recovery) fail on all 10. B3 (drift) and B4 (heading) pass on all 10. Seed 1101 is filmed with 2 filmstrips and a webm. | Evaluation tab shows: "fail: 0 of 10 seeds pass · policy (d2556f70a25c) on task balance_task · revision bda7c1c9c31f, the accepted design". The predicate and seed tables are there, and the film shows 2 images and 1 video. The earlier 10/10 evaluations are listed as historical. Screenshot: `w1-8-evaluate.png`. |

`PROGRESS.md` gained these rows: params `policy_on=0`, script (the digest
edit), params `policy_on=1`, walk, and evaluate.

**What is still open for W1:**
- The 5090 leg. When `nvidia-smi` works again, rerun step 7 on the GPU with
  `cadex walk` at a real budget (the r3 recipe got 10/10). Then rerun
  `evaluate`, and use the same driver to replace the two screenshots.
- The row-by-row audit of the parity ledger: no "ported" row without a test.
- Both full suites and the packaged gate at W1's close. All three are green
  as of this iteration.

**Concerns:**
- The project's accepted design now declares a 3-iteration policy that
  fails. That is fine on an `orun2-*` copy, but the next design turn on it
  will see the failing evaluation.
- The GPU driver fault is on the host, and only the owner can fix it. Every
  training unit until then is CPU-only.

The unreconciled tail is now two records (`icy-tooth-7719` and this one).

Dispatch closed: 1 unit — W1 steps 7–8 (CPU training because the 5090 driver is not loaded, then evaluate) on orun2-w1-robin, each seen in the dashboard

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: fbdf9d88f6d1d3d6ecbe4022028cf47363538da9

## State Impact

- target: shady-clover-5534 — all eight walk steps have run on copies of real robot projects and are visible in the dashboard (steps 7-8 on orun2-w1-robin, fbdf9d88); step 7 ran on CPU because the 5090's nvidia module is not loaded on kernel 7.0.0-34, so the 5090 leg, the parity-ledger audit and the closing suite run remain
