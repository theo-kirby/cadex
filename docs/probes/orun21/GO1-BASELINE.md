# orun21: the Go1 reference, reproduced on this checkout

Verified against source: 2026-10-28. Frozen run evidence; read it, never cite
it as current.

The charter's fixed reference (horizon step 1): orun18 A2's Go1 joystick
bundle through `training/cadex_train.py`, re-run unchanged at `d6e3681a`
(orun21's charter commit, on `main` 9ebef99a + ADR-900). Every recipe change
in orun21 is first measured against this number.

## Setup

- **Lab.** `~/cadex-projects/orun21-lab/` holds `cp -a` copies of
  `leon-v` (main `4d67e21`, its untracked `runs/` too) and `orun9-biped`
  (`48f9508`, with its uncommitted ledger and runs). The originals stay
  read-only.
- **Bundle.** `orun21-lab/go1/outputs/`, rebuilt with
  `docs/probes/orun18/a2_bundle.py` from Playground 0.2.0's Go1 XMLs (the
  same command as orun18). It is **byte-identical** to orun18's: task
  `6bc7869f…`, model `1d03aaeb…`, gaps `8f354f56…`. Not committed (it
  embeds the BSD-3 Menagerie model).
- **Training.** `orun21-lab/go1/run1/launch.sh` is orun18's
  `run1/launch.sh` with only the paths and label changed: 1260 iterations
  × 8192 envs × 20 steps = 206.4 M steps, Playground's PPO settings, seed 1,
  under `systemd-run --user --scope -p MemoryMax=30G`, alone on the RTX
  5090 (driver 580.178.04; jax 0.7.2, brax 0.14.2, mujoco 3.10.0).
- **Judge.** `docs/probes/orun18/go1_judge.py cadex` with the same seeds
  (0–9), commands and 8 s episodes as orun18 D3.

## Result: reproduced

| | orun18 A2 | orun21 | ratio |
|---|---|---|---|
| trainer `wall_time_s` | 326.4 s | **324.7 s** | 0.99 |
| launch → first iteration | — | 54.6 s (`progress.json` `starting` until then) | |
| launch → checkpoint 300 | 141.1 s | 139.2 s | 0.99 |
| checkpoint 1200 → final policy written | 14.0 s | **38.5 s** | 2.75 |
| launch → done (`updated_at − started_at`) | 350.1 s | **372.1 s** | 1.06 |
| final reward per step | 0.0293 | 0.0286 | |
| best reward per step (iteration) | 0.0302 (1243) | 0.0303 (1141) | |
| witness error | 2.1e-7 | 1.6e-7 | |
| policy sha256 | `05b9ba53…` | `9ec81e8a…` | |

The judge (`run1/judge.json` `2fc5fa7c…`, `judge-beyond.json` `6b933c1c…`):

| command m/s | falls | orun21 last 2 s | orun18 A2 | A1 Playground | orun21 / A1 |
|---|---|---|---|---|---|
| 0.5 | 0/10 | **0.470** (min 0.465) | 0.477 | 0.486 | 0.966 |
| 1.0 | 0/10 | **0.958** (min 0.950) | 0.973 | 1.008 | 0.950 |
| 1.5 | 0/10 | **1.431** (min 1.424) | 1.436 | 1.526 | 0.938 |
| *2.0, beyond* | 0/10 | 1.921 | 1.913 | — | |
| *2.5, beyond* | 0/10 | 2.416 | 2.389 | — | |

Worst RMS torque over its limit is 0.24–0.34 (FR_calf), worst peak 0.52–0.92,
and no frame is at the clamp. orun18's A3 bar (within 10% of A1 at every
judged command, no more falls) still holds: 0.94–0.97 of A1, 0/30 falls.
The judge's forward pass matches the container's witness samples to 9.1e-6.

**The reference number for orun21:** 0.470 / 0.958 / 1.431 m/s at
0.5 / 1.0 / 1.5 m/s, 0/30 falls, 324.7 s of training and 372 s end to end
for 206.4 M steps. It is one training seed; the 1–1.5% drop against orun18
at the same seed is within what a re-run on a GPU varies by, and is not
treated as a change.

## What it shows for M0 and D1

- **The end of a run costs 24 s more than in orun18.** Training itself is
  unchanged (324.7 vs 326.4 s, and the same time to checkpoint 300), but the
  final policy is written 38.5 s after checkpoint 1200 rather than 14 s. The
  likeliest cause is ADR-835's closing view: since orun18 the trainer
  JIT-compiles and runs a 10 s (`--view-seconds`, 500-step) deterministic
  rollout of the witness batch before it writes the policy (`view_rollout`,
  `training/cadex_train.py:4342`). That is 7% of a Playground-sized run,
  and a fixed cost a screen pays in full. Not timed on its own yet: M0
  times it.
- **For 55 s after launch the run says only `starting`.** `progress.json`
  is written once at launch (`iteration` −1, `device` empty) and not again
  until the first iteration, through the whole compile. That is D1's
  "heartbeat that stays live through a long compile", seen on the
  reference.
