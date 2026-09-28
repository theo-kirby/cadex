---
node_id: c50ff40b-a316-59e4-a879-777630a499e4
slug: southern-prairie-3683
title: C1. Regressions and a closing report are complete
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **C1. Regressions and a closing report are complete.** - Both full suites pass at the final revision, plus the packaged lifecycle gate for any engine or payload change. - `docs/probes/ot10/REPORT.md` lists every probe, score, render, training run, failed attempt and remaining defect, with the before/after comparison against hex3. - Reconcile, then claim done for critic review without ticking the owner boxes. [rec: damp-dusk-8045]

**Where it stands:** every item has evidence and done has been re-claimed for critic review at `18eb0a70`. Status is `working`; the human owns the checkbox [rec: soft-cliff-8778].

- **Suites and gate** at `31de992c`: `pixi run test-engine` 2242 passed / 53 skipped; `cli/tests` 1055 passed / 1 skipped; packaged lifecycle gate 23 passed, on a payload matching source on 57 files [rec: lawful-tooth-6508]. At `3879f1e2`, CLI 1061 passed / 1 skipped [rec: odd-comet-7221]. **Final re-run at `18eb0a70`:** engine 2242 passed / 53 skipped, CLI 1061 passed / 1 skipped, `hypergraph check --config` 0 violations [rec: soft-cliff-8778].
- **Every skip has a named reason** (REPORT.md C1 section, commit `fc13f510`). Engine, 53: 47 offboard JAX/MJX, 5 need the Blender recipe executable, 1 packaged-gate environment. CLI, 1: the review host environment [rec: odd-comet-7221].
- **Closing report** `docs/probes/ot10/REPORT.md` (commit `26bc9ef0`; A5 verdict at `f9763c6e`). It states the A5 verdict (not met by its letter) and lists every A5 attempt with its score and render, both W2 runs, the A4 refusal census and the remaining defects. `cli/tests/test_ot10_report.py` pins it to the score files [rec: lawful-tooth-6508] [rec: soft-cliff-8778].
- **`hypergraph check` exits 0 when run with `--config .hypergraph/config.yml`.** The critic's 270 I2 violations came from a bare `check` without `--config`, not from the graph [rec: odd-comet-7221].
- **Reconcile and claim:** reconciled through odd-comet-7221, then done re-claimed for critic review [rec: soft-cliff-8778]. A5's confirmation round, pre-registered after the claim, adds turns REPORT.md will need to carry [rec: honest-dawn-9522] [rec: wise-sea-0110] — noted as a judgement, not a declared impact on this node.

## Negative knowledge

- [scope: this repo's hypergraph check | confidence: high | evidence: odd-comet-7221] A bare `hypergraph check` without `--config .hypergraph/config.yml` reports spurious I2 violations (270 here). Judge graph health only with `--config`.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- lawful-tooth-6508 — C1 evidence: suites and packaged gate green at 31de992c; REPORT.md lists every attempt, pinned by test_ot10_report.py
- odd-comet-7221 — REPORT.md names every skip reason; 270 I2 was a check without --config (0 with it)
- soft-cliff-8778 — final re-run at 18eb0a70 green, check 0 violations, REPORT.md states the A5 verdict, done re-claimed
- honest-dawn-9522 — A5 confirmation round pre-registered after the C1 claim (context only)
- wise-sea-0110 — A5 confirmation turn 1 run after the C1 claim (context only)
