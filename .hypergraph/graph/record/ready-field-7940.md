---
node_id: 0f730ae3-ddfa-5c7f-9252-eee22d477f42
slug: ready-field-7940
title: 'ot11 P2: the behaviour metrics are engine code, with reach and the w2-2 failing fixture (ADR-455)'
created_at: '2026-09-30T08:02:51+00:00'
parents:
- proud-lantern-5203
summary: ''
---
## What

The first unit of P2: the behaviour metrics now live in the product, for all three families, and a success predicate is data (ADR-455, commit `3014ee62`).

- **`src/Mod/cadex/CadexEvaluation.py`** (new, pure standard library) reads a rollout trace into metrics: **posture** (tilt, heading, drift, recovery time from each shove), **gait** (steps, step share, foot clearance, stance slip, duty factor, foot depth, commanded-speed tracking) and **reach** (final error, time to target, overshoot, per target). `check()` holds a flat metric table against `{id, metric, min, max}` predicates.
- **`CadexDynamics.evaluation_rig`** (new) reads the model's half in millimetres: base, floor, mass, COM height, each foot's collision geoms and hip height, and a tip with its arm length. A grounded arm has no base and is still measured.
- **`docs/probes/ot11/runner/measure.py`** lost its own reader (numpy, mujoco, about 330 lines) and is now only the contract's binding: which product metric each frozen predicate bounds. It gained the reach predicates Q1–Q4.
- **ot10's `w2-2` shuffle is a failing fixture** in both suites: `cadex_tests/fixtures/ot10_w2_2_feet.json`.

## Why

Target: P2 (`damp-flame-5523`), the highest-ranked open criterion after P1's record. The critic asked first for the missing P1 record (done: `proud-lantern-5203`, with the `cli/tests` output), then for P2: the spec in xscript, the evaluation command, the readers moved into the product, w2-2 as a failing fixture, and the reach metrics.

**Deviation, stated.** That is more than one unit. This iteration did the last three (readers moved, w2-2 fixture, reach metrics) and did **not** declare the spec in xscript or add the evaluation command. The order is a dependency: a spec declared in xscript has to name metrics, and the command has to call a reader, so the metric vocabulary and the reader come first. The predicate shape `check()` takes is the shape the xscript spec will carry.

## Method

- Ported the probe's numpy reader to plain Python in the engine, on `CadexStudio`'s terms (ADR-445): outside the service's closure, loadable by path with no engine built. The model read went into `CadexDynamics`, the one module that imports `mujoco` and converts units.
- **Agreement gate for the port.** Re-ran `measure.py` through the product reader on the stored `w2-2` trace and on Robin's ten ot9 traces and diffed every number against the retained P1 receipts: worst relative difference **1.3e-15** (201 numbers for Robin). The only differences are `why` strings that now name the metric.
- `cadex_tests/test_evaluation_metrics.py` (46 tests) pins each metric on a motion that passes it and one that fails it; a foot's height from a trace is checked against MuJoCo's own geom position on a tumbling model; nine rig refusals are pinned by reason. `cli/tests/test_ot11_measure.py` (now 28 tests) pins every frozen predicate through the binding, including Q1–Q4, and asserts every contract predicate is bound to a metric the product measures.
- The w2-2 fixture is the base and four feet of the stored rollout, 5 of 62 components, no commands, positions to 0.001 mm, 153 KB. Its metrics match the full trace to five figures.
- Payload change (one module added to CMake), so: `pixi run build-engine`, `pixi run stage-engine`, then the packaged gate.

Test evidence at `3014ee62`:

```
pixi run test-engine
  2342 passed, 53 skipped in 436.72s (0:07:16)
pixi run python -m pytest cli/tests -q
  1125 passed, 1 skipped in 828.97s (0:13:48)
CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
  23 passed in 19.90s
```

The staged payload's own Python imports `CadexEvaluation`, reads the arm rig and reproduces w2-2's numbers. The engine suite's 53 skips and the CLI suite's 1 skip were not inspected this iteration; the CLI count was 1118 passed, 1 skipped before the unit.

## Result

What is true now:

- The product has one reader for gait, reach and balance metrics, and the ot11 contract is read through it. There is no second reader.
- `w2-2` fails a walk spec in the product's own tests on speed (1.907×), step share (0.140), slip (0.666), leg balance (4.2×) and floor depth (−0.220 hip heights), and passes on tilt, heading, clearance and duty factor. Through the contract binding it fails exactly W3, W5, W7, W9, W10, which is what `contract.json` records.
- Reach metrics exist and are pinned on synthetic reaches (direct, overshoot, slow, short, arrives-then-leaves). **No real arm has been measured.**

What P2 still lacks:

- The success spec is not declared in xscript, and `docs/XSCRIPT.md` is untouched.
- No command rolls a policy on the ten seeds under the contract's conditions, and no report is written (per-seed, per-predicate, reward by term, termination causes, video, filmstrip).
- The review dashboard shows nothing of this.

Concerns and assumptions for the next iteration:

- **The w2-2 fixture is an assumption about the charter.** The charter forbids committing rollout traces and P2 requires w2-2 as a failing fixture. I read that as: a five-body pose extract is a test fixture, not the trace. If the critic reads it otherwise, the fixture goes and the w2-2 tests must skip without the read-only project.
- The commanded speed and reach targets are passed in by the caller. Until P3 puts the goal in the trace, the evaluation command has to supply them from the spec.
- `evaluation_rig` refuses a foot whose collision geom is a mesh or cylinder. The accepted ot10 quadruped has sphere feet; Robin has no feet.
- `measure.py` still exists as the contract binding. When the spec is in xscript, the contract can be written in that form and the probe runner can go.
- The floor-penetration cause (P1) is still unmeasured, and the judge has still not run.
- No new dependency.

Next unit, in order: declare the success spec in xscript beside the task (predicates in `check()`'s shape, plus feet, tip, evaluation conditions and seeds), document it in `docs/XSCRIPT.md`, then the evaluation command and report.

Dispatch closed: 1 unit — behaviour metrics (gait, reach, balance) moved into the engine with w2-2 as a failing fixture; spec-in-xscript and the evaluation command not started.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 3014ee626a48387747772105c0f1ef1844b8fde1

## State Impact

- target: damp-flame-5523 — still open. The three metric families (gait, reach, balance) are engine code in CadexEvaluation.py with CadexDynamics.evaluation_rig, pinned on passing and failing fixtures including ot10's w2-2 shuffle; the probe's measure.py is only the contract binding and reproduces both P1 receipts to 1.3e-15 (commit 3014ee62, ADR-455). Missing: the success spec in xscript and docs/XSCRIPT.md, the one evaluation command and its report, reward decomposition and termination causes in that report, video and filmstrip, and the dashboard view.
- target: rough-shore-6557 — no status change. The contract's predicates are now read through the product's metrics, and the reach predicates Q1–Q4 have a reader, pinned on synthetic reaches only. Judge still not run; floor-penetration cause still unmeasured.
