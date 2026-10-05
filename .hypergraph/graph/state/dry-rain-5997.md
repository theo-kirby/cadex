---
node_id: 51b9e291-00a3-505a-b224-ed28984761ad
slug: dry-rain-5997
title: V2. Each checkpoint becomes motion in the viewport
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun3: **V2. Each checkpoint becomes motion in the viewport.** Each checkpoint landing in a training leg is rolled out through the engine while training continues, with the cost (< 5% iteration time) and disk measured. The viewport loops the newest one labelled with iteration and reward. A scrubber selects older ones and follows the newest unless pinned. A failed rollout shows its reason and never stops training. A browser test against a real engine shows a second checkpoint replacing the first while training runs. Traces are uncommitted run outputs [rec: golden-snow-6627]. The human owns the checkbox.

**Met on evidence; the live 5090 walk in a browser is W1's** [rec: forest-mist-3382]. Reconcile judgement: status `working`, because every V2 bullet now has evidence, following the precedent V1 set (`vast-ivy-6277`).

- **Write half (ADR-544, commit `025417e7`).** There is one watcher, `cli/cadex_cli/checkpoints.py` `CheckpointRollouts`, polled from `loop.supervise` and from `train.run_trainer` via an `on_poll` hook, so `cadex train` and `cadex walk`'s train leg both use it. `checkpoint_runner.py` runs on the engine interpreter, on the CPU, `nice`d, one checkpoint at a time, newest first. It writes `<out>.<tag>.rollout-trace.json` (`cadex-assembly-simulation-trace-v1` plus a `checkpoint` block: file, tag, iteration, reward_per_step, sha256), or `<out>.<tag>.rollout-failed.json` with the reason. `cadex train`/`walk` gain `--checkpoint-every N`. `test_checkpoint_rollouts.py` has 7 real-engine tests on a committed biped fixture [rec: snowy-water-3502].
- **Cost: none measurable.** Measured on the 5090 with 60 iterations, 256 envs and seed 7, run in the order off/on/off/on. The clean pair has median 0.9170 s/it off and 0.9169 on, a mean difference of +0.08%. The first pair (warm-up) is median +0.11%. The runs went through `run_trainer` under `machine_slot()` on a `/tmp` copy of orun3-biped's `reed_walk` bundle, not as a `cadex walk` leg, so nothing was written into the project [rec: snowy-water-3502].
- **Disk:** 38.7–329.5 KB per trace (it follows episode length), 224.7 KB mean, 2.47 MB for 11 checkpoints [rec: snowy-water-3502].
- **Page half (ADR-545, commit `802b265e`).** `/api/project` carries `stage.checkpoints`, and `/api/playback/checkpoint/<run>/<stem>` serves through `trace_playback`. The 3D viewport loops the newest checkpoint on the run's frozen model, labelled with iteration and reward. A scrubber pins an older checkpoint and follows the newest at its right end. A failed rollout shows its reason. A Chromium test against the real engine shows `walk.000040` replacing `walk.000020` while a stepped trainer runs [rec: forest-mist-3382].

**Open ends** [rec: snowy-water-3502]: a few iterations stall for tens of seconds whether rollouts are on or off, which pushes the mean to about 10× the median, and which iterations stall was not recorded. Same-seed GPU runs give different policy digests. Checkpoints synced from a remote run are not rolled out. The playback route is to enter P1's pinned API contract.

## Negative knowledge

- [scope: cadex walk / cadex train before ADR-543 | confidence: high | evidence: forest-jasper-1180, nimble-moss-4028] Neither `walk.py` nor `train.py` took the machine lock. Only MCP `train_start` did. ADR-543 closes the gap. Before timing anything on a training path, confirm that it holds the slot.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v2-each-checkpoint-becomes-motion)
- forest-jasper-1180 — baseline blocked by the owner's walk-r25 holding the slot; orun3-biped fixture prepared; found that the walk train leg bypassed the lock
- nimble-moss-4028 — cadex train/walk take the machine training slot (ADR-543); watcher call sites named
- snowy-water-3502 — ADR-544 watcher in both call sites; 5090 on/off cost not measurable; 224.7 KB/trace
- forest-mist-3382 — ADR-545 page half: playback route, viewport loop, scrubber, failure reason, Chromium test against the real engine
