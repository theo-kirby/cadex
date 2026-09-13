---
node_id: 15b58a5b-3a9d-5b54-bae4-f830d662bc95
slug: dusty-otter-7562
title: D6. The real biped trains, is measured and is recorded in the new look
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: blocked

## Current

**Blocked on an engine unit: a free-base solve.** `assembly.solve` and the dynamics export both refuse an assembly with no grounded component (`no_grounded_component`, in both `cadex_assembly_worker.py` and `CadexDynamics.py`), and the charter forbids a floor in the design, so Finch's pelvis is grounded for the solver and its accepted MJCF has a static base — a biped that cannot fall cannot be trained to stand. The prerequisite is a free-base solve: the first component held for the solver, a free joint in the export (the exporter's island path already gives an unreached component a free joint), and the ground supplied by the environment (the reset-variation floor checks must find an environment plane). That unit changes the xscript surface and needs the engine suite and the packaged gate; after it, the Finch script drops `grounded=True`, declares the task, and trains as a new accepted revision [rec: sleepy-rain-9945]. The criterion's other inputs are in place: D5 is evidenced (`cool-hill-9617`) and the D3 look is in place (`silver-ledge-4640`).

Charter criterion: **D6. The real biped trains, is measured and is recorded in the new look.** One bounded real GPU training run on the redesigned biped, a checkpoint video and a final video in the D3 look on the operator dashboard, and the measured displacement, survival and falls over a declared episode and seed set. Standing for the full episode is the bar the report measures against; failing it is a valid measured result. Declared target `gap-d6-real-biped-trains-measured`; the human owns the checkbox edit [rec: brisk-ledge-9638].

Reconcile judgement: `blocked` rather than `open` — the record names the prerequisite explicitly and it lies in the engine, outside this criterion's own scope; nothing is implemented or claimed for D6 itself [rec: sleepy-rain-9945].

## Negative knowledge

None yet.

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d6-real-biped-trains-measured`
- sleepy-rain-9945 — ADR-334's carried concern: the engine's `no_grounded_component` refusal leaves Finch's accepted MJCF with a static base; the free-base solve with the ground from the environment is D6's prerequisite
