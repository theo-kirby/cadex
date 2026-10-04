---
node_id: addf844e-ac42-5dc7-9852-8d5c4ffebdd1
slug: clever-sky-3211
title: 'orun2 C1: a preview skips static and swept fit (ADR-527); defect 4 closed with suites and packaged gate'
created_at: '2026-10-04T07:01:27+00:00'
parents:
- lively-beacon-5538
summary: ''
---
## What

Recorded and evidenced ADR-527. It landed without a record in commit `5bc0b6de` (iteration 57). `validate_and_solve_assembly(..., skip_derived=True)` is called only by a pose-only preview. It now skips the static fit, the fit and attachment checks and the swept fit (`src/Mod/cadex/cadex_assembly_worker.py`), the same way it already skipped traces, exports and exploded views. The accepting run measures all of them as before. `src/Mod/cadex/cadex_tests/test_preview_skips_fit.py` runs a real preview under FreeCADCmd with every fit stage made to raise, and asserts that the revolute placement is still solved. `docs/probes/orun2/REPORT.md` §6 item 4 already reads "fixed (ADR-527)". No code changed this iteration.

## Why

The critic's fix-first was to write the ADR-527 record with State Impact on C1. It had to include measured `pixi run test-engine` and CPU-only CLI suite results. Because `cadex_assembly_worker.py` ships in the payload, it also needed a rebuilt, staged packaged lifecycle gate, with skips reported as skips. That is this iteration's whole unit.

Deviations, both deliberate:
- **No reconcile.** The critic asked for one after the record. The work-iteration dispatch forbids the reconcile skill without exception, so it is left to the reconcile pass. The tail is now two records past the mark (`lively-beacon-5538` and this one), which meets the charter's three-record trigger on the next one.
- **No second unit.** The budget is one unit. The critic's "next open REPORT defect" does not exist as fixable work: defect 5 (the 5090 leg) waits on the owner, who has to load the `nvidia` kernel module, and defect 6 (the pixi footprint audit) was deferred by the owner to the next run. So the next unit is the long-term subtraction rung: the shell-only bridge answers, then bundle payload staging, each with an ADR.

## Method

- `pixi run build-engine` (exit 0), then `pixi run stage-engine` (exit 0), producing `build/engine/cadex-engine-0.0.0-linux-x64`.
- `pixi run test-engine`: **2608 passed, 56 skipped** in 405 s, exit 0. That is one more pass than at `lively-beacon-5538`, which is the new test.
- `CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q`: **1420 passed, 1 skipped** in 1271 s, exit 0. The skip is the same private-network-host test as before, which the charter bars from binding.
- Packaged gate: `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py -rs`: **24 passed, 0 skipped**, 21.4 s.
- `test_preview_skips_fit.py` passed against the payload root (1 passed, 0 skipped). With `-v`, the call took 0.17 s and asserted the driver's `PREVIEW-FIT` marker, so FreeCADCmd really ran it.
- I re-ran `cadexd_latency_integration.py` on the dev tree after the suites, on a quiet machine. Preview median **0.0435 s** against the 0.10 s bar, first preview 0.28 s, `set_params` median 0.381 s, display 0.432 s against the 0.65 s parity bar. Assembly `set_params` with display was 1.337 s (not barred). `ok: true`. The live lane skipped because it needs `CADEX_LIVE_PROJECT` with a policy.

## Result

True now: REPORT.md defect 4 is closed. It has ADR-527, a test that fails on the old tree, and measured evidence that reproduces the ADR's numbers. Both suites and the rebuilt, staged packaged gate are green at this tree, with no skips in the gate. The open report defects are 5 (owner-blocked 5090 leg) and 6 (deferred pixi audit), and neither can be fixed without the owner.

Concern: the reconcile is due. Two unreconciled records sit past the mark, so the reconcile pass should fold them before the next work unit adds a third.

Next unit: the long-term subtraction rung, starting with the shell-only bridge answers in `cli/`/`src/Mod/cadex` (ADR, tests).

Dispatch closed: 1 unit — ADR-527 recorded with engine 2608/56, CLI 1420/1 (CPU) and packaged gate 24/0 evidence; defect 4 closed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 5bc0b6deb88915db84dd65ce1550554f9ee457d8

## State Impact

- target: wild-ocean-3878 — REPORT.md defect 4 closed by ADR-527 (preview median 0.0435 s vs 0.10 s bar, ok true; test_preview_skips_fit.py); engine 2608 passed/56 skipped, cli 1420 passed/1 skipped GPU hidden, packaged gate 24 passed/0 skipped; open defects 5 (owner) and 6 (deferred)
- target: twilight-aspen-1541 — D2.2 raw-NDJSON bar now fully within bar: preview 0.0435 s, set_params 0.381 s, display 0.432 s (ADR-527)
