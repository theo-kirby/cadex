---
node_id: b055d046-64ea-502c-8ac4-edba7c1f578a
slug: candid-delta-9314
title: 'Robin trains: default rate diverged and kept as failed, 1e-4 run completed, videos on the dashboard, final policy leans and drives over ten seeds'
created_at: '2026-09-14T03:19:28+00:00'
parents:
- odd-orchard-4978
summary: ''
---
## What

Ran Robin's bounded local GPU training lifecycle on the reopened revision
`5ad94d65…` and recorded it: two runs, `robin1` (trainer default learning rate
3e-4) which diverged to non-finite reward and loss at update 128 and stopped
itself, and `robin2` (`--learning-rate 1e-4`, the trainer's own suggestion,
nothing else changed) which completed 240 updates on 1024 environments in
620.8 s under `systemd-run` with `MemoryMax=20G` and a 3600 s timeout. Both
policies of `robin2` are evaluated over seeds 0–9 in fresh scratch projects;
both videos are on the persistent operator dashboard in the dark look. Receipts:
`docs/probes/ot6/robin/training.json` (15.8 KB), `TRAINING.md`, two decoded
frames, and Robin's own `train.py`, `evaluate.py`, `report_training.py` (the
Finch copies with Robin's facts); ADR-338; a test pinning the receipt; README
repointed; the project's `DECISIONS.md` carries the training entry.

## Why

Advances D7 (`ready-sand-2621`), whose remaining half after odd-orchard-4978 was
the bounded training run with checkpoint and final videos and measurements on
the dashboard. This is what the critic's message asked: episode and seed set
declared (400 steps at 50 Hz, fall below 46.2 mm, seeds 0–9), the two-hour and
20 GB limits enforced (3600 s timeout, `MemoryMax=20G`), checkpoint and final
videos published, balance, survival and falls reported, the dashboard verified at
experiment start and end, concurrent rendering bounded to one render and its
training impact measured. **Deviation:** the message said one lifecycle; the first
run diverged, so a second bounded run at the lower rate was made rather than
stopping at a failed run or retuning the reward (which would have changed what
was measured). The diverged run is kept as a failed run on the dashboard with its
checkpoint video, and the receipt carries it beside the completed run. The stale
clearance plan item was not taken.

## Method

Start: `operator_probe.py` at 1400×900 and touch 400×850 showed the persistent
unit serving Robin at `5ad94d65`, 24 components, 56 996 triangles, no overflow,
solids by default and nine proxy outlines under the toggle. `train.py`
(Finch's driver with 24 components, Robin's authorship, an `evidence/` mkdir
and an optional recorded learning rate) exported the model and task bundle,
wrote the run record, launched the trainer in a scoped unit, ran the shared
observer against the persistent URL, published checkpoint 20 while the trainer
was active (declare, rollout, render, video, browser check), waited for the
trainer, and published the final policy. `robin1` failed at update 128; its
record was rewritten `status: failed` with the trainer's error and a compact
failure receipt written beside it before `robin2` launched, so the driver's
preserved-records check covered both robin1 records. `evaluate.py` rolled each
`robin2` policy over seeds 0–9 through `rollout_seed` (seed 0 byte-identical to
the retained trace, source run unchanged), reading the fall threshold from the
retained task bundle, with a label-agnostic fall flag (Robin's termination rule
is unlabelled: the trace names it `termination`) and the chassis pitch from the
quaternion. `report_training.py` wrote the receipt, including the enclosing
checkpoint step for a render that overlapped no update interval, and copied
the scratch evidence into the project. End: fresh visits at both widths select
`robin2-final`, 24 components, 114 344 triangles, no overflow. Verification:
`cli/tests/test_review_design.py` 102 passed (browser tests at both widths, the
evidence caps and privacy scan over every ot6 file, the new Robin receipt
test); full CLI suite 588 passed, 1 skipped in 527 s (after the trainer had exited). No engine or product code changed, so the
engine suite and packaged gate were not rerun; the current-tree engine evidence
is kind-reef-3852's. No build, no new dependency.

## Result

`robin2`: exit 0, 240 updates, `done` on `gpu`, wall 620.8 s, host peak 7.41 GB,
GPU peak 15 139 MiB; plain update median 0.812 s (0.724–0.897), checkpoint
steps 33–35 s, compile 46.9 s; reward per step 0.127 → 0.688 (best 0.703 at
update 205). Over seeds 0–9: checkpoint 20 fell 10/10 at 0.40–0.58 s, pitch
64–74°; the final policy survived the full 8 s on 10/10 — by holding a +11.0 to
+11.2° lean and driving 1.8 m backward (seed 0 also 1.9 m sideways), the
equilibrium where the damped gearmotors' steady-speed torque balances
gravity's moment. It meets the task's bar and not the operator's: upright and
still is what a balancer should be measured against, and this fails it on
every seed, recorded as a measured result. A velocity or position term in the
reward is the open design decision for the next turn on Robin, left in the
project's `DECISIONS.md`, not taken here. `robin1`: failed at update 128 (reward
0.714, best 0.743 at 122), six checkpoints and `best` retained, checkpoint-20
video published while active, served as a failed historical run. The render's
impact: the enclosing checkpoint step 34.50 s against 33.3–34.5 s for the
others, plain medians 0.875 s before and 0.849 s after. Live: the observer's
fresh visit selected `RUN robin2`, seven page updates, six matched to their
commit within 0.95 s, one navigation. Dashboard at end: `ot6-robin` at
`8d727e18…`, five runs, a fresh visit selects `robin2-final`.

Concerns and assumptions: the learning-rate fix-forward is the trainer's
suggestion, not a diagnosis of the divergence; the two runs share one objective
identity by construction (same script, same task bundle digest per run record).
The robin1 run record was rewritten by hand (status, error, legs) with the same
base the driver wrote; its earlier `running` state was the driver dying at its
own assertion. The observer's first-seen count is six of seven page updates
because sub-second updates can reach the page before the file poll; the test
pins the observer's own guarantee. Scratch evaluations and all large artifacts
stay under `~/cadex-projects/`. The unreconciled tail is now three nodes:
reconcile is due next.

Dispatch closed: 1 unit — Robin's bounded training lifecycle run and recorded: the default rate diverged and is kept as a failed run, the 1e-4 run completed with checkpoint and final videos on the dashboard, and the final policy's full-episode survival is a leaning, driving equilibrium measured over ten seeds.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: e9ee039e057f64e96088b2fd47e1cda747af7c73

## State Impact

- target: ready-sand-2621 — Training half done: robin1 (default 3e-4) diverged at update 128 and is kept as a failed run with its checkpoint-20 video; robin2 (1e-4) completed 240 updates in 620.8 s under MemoryMax=20G/3600 s, host peak 7.41 GB, GPU 15 139 MiB. Over seeds 0–9: checkpoint 20 fell 10/10 at 0.40–0.58 s; the final policy survived 8 s on 10/10 by holding a +11° lean and driving 1.8 m backward — meets the task's bar, not upright-and-still. Both videos cadex-prototype-dark-v1 on the persistent dashboard, fresh visit selects robin2-final at 1400×900 and 400×850. Receipt docs/probes/ot6/robin/training.json + TRAINING.md (ADR-338), pinned by test; CLI suite 588 passed/1 skipped. Open: a velocity/position reward term for a stationary balance is the next design decision.
