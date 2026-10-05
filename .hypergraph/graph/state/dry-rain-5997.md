---
node_id: 51b9e291-00a3-505a-b224-ed28984761ad
slug: dry-rain-5997
title: V2. Each checkpoint becomes motion in the viewport
created_at: '2026-10-05T08:57:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open orun3 charter criterion: **V2. Each checkpoint becomes motion in the viewport.** [rec: golden-snow-6627]

- When a new checkpoint lands during a `cadex walk` training leg, the CLI rolls it out through the engine. It writes a `cadex-assembly-simulation-trace-v1` trace beside the checkpoint, tagged with the checkpoint's iteration, reward and sha256. [rec: golden-snow-6627]
- The rollout runs while training continues. **Measured:** mean iteration wall time with rollouts on against off, on the same task and seed. The cost is under 5%, or an ADR explains why the owner should accept more. [rec: golden-snow-6627]
- The server serves each checkpoint's playback through the existing `trace_playback`. The viewport loops the newest one, labelled with its iteration and reward. A scrubber selects older ones, and the view moves to a newer checkpoint automatically unless the owner has picked one. [rec: golden-snow-6627]
- A browser test against a real engine shows a second checkpoint's playback replacing the first one while the run is still training. [rec: golden-snow-6627]
- A failed rollout is shown with its reason. It never stops or slows training. [rec: golden-snow-6627]
- Traces are run outputs. They are never committed, and their disk cost per checkpoint is measured. [rec: golden-snow-6627]

**Progress** [rec: forest-jasper-1180] [rec: nimble-moss-4028]:

- **Baseline unmeasured.** Two attempts found the 5090 slot (`~/.cache/cadex/training.lock`) held by the owner's `quad-qdd/runs/walk-r25`. The refusal receipt is kept, and `runs/baseline-probe` was never created [rec: forest-jasper-1180] [rec: nimble-moss-4028].
- Fixture ready: `~/cadex-projects/orun3-biped` is an untouched `cp -a` of `ot5-biped`. `loop.retained_task` resolves `reed_walk` at revision `0596013572c6…` with `evaluation_seeds: []`, so seed 7 is legal. Planned settings: 120 iterations, `checkpoint_every` 10, timing from `progress.json` rewrite timestamps [rec: forest-jasper-1180].
- The walk's train leg previously bypassed the machine lock [rec: forest-jasper-1180]. It is now fixed (ADR-543, commit `0c1b9cb8`). `cadex train` holds the slot around a local trainer, and `cadex walk` refuses before its first leg while the slot is held, so a walk leg can host the baseline without sharing the 5090. Tests use private slots, so the CLI suite neither refuses on nor holds the owner's run [rec: nimble-moss-4028].
- **Watcher design constraint:** one implementation with two call sites: `loop.supervise`'s 0.25 s poll loop (`loop.py:712`), and `train.run_trainer` (`train.py:483`). `run_trainer` currently blocks in `process.wait(timeout)` and must wait by polling [rec: forest-jasper-1180] [rec: nimble-moss-4028].

Declared target: `gap-v2-each-checkpoint-becomes-motion`. This node becomes working only with measured evidence that the criterion is met. The owner ticks the charter box [rec: golden-snow-6627].

## Negative knowledge

- [scope: cadex walk / cadex train before ADR-543 | confidence: high | evidence: forest-jasper-1180, nimble-moss-4028] Neither `walk.py` nor `train.py` took the machine lock. Only MCP `train_start` did, via `loop.register` → `loop.launch` → supervise. ADR-543 closes the gap; before timing anything on a training path, confirm that it holds the slot.

## Provenance

- golden-snow-6627 — operator-declared orun3 charter gap (gap-v2-each-checkpoint-becomes-motion)
- forest-jasper-1180 — baseline blocked by the owner's walk-r25 holding the slot; orun3-biped fixture prepared; found the walk train leg bypassed the lock
- nimble-moss-4028 — cadex train/walk take the machine training slot (ADR-543); baseline still blocked; watcher call sites named
