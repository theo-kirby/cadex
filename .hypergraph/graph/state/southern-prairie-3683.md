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

**Where it stands:** every item has evidence and the reconcile the charter orders ran (`a4304da6`, folding `keen-comet-6140`, `glad-oak-4897`, `glad-ridge-1079`). Done was re-claimed after it in REPORT.md (commit `8daeb814`), with final gates engine 2,282/53, CLI 1,085/1, packaged 23 and `check` at 0 violations; no box is ticked [rec: clever-ocean-2380]. REPORT.md claims done for critic review on A1–A4, A6, A8, W1, W2 and C1, leaves A5 to the owner (by its letter not met, 7 of 18 meet the bar), carries A7 forward open, and presents W2 with the owner's shuffle verdict [rec: glad-oak-4897] [rec: glad-ridge-1079]. Status is `working`; the human owns the checkbox.

- **Final gates** at `fc279bfe` plus the report edit: `pixi run test-engine` 2,282 passed / 53 skipped; `cli/tests` 1,085 passed / 1 skipped; packaged lifecycle gate 23 passed against a staged payload equal to source on 57 of 57 files (the engine changed since the previous closing run, ADR-441–443); `test_ot10_report.py` and `test_ot10_contract.py` 48 of 48 [rec: glad-oak-4897]. `glad-ridge-1079` changed no engine, `cli/` code or payload, so those results stand at the final revision [rec: glad-ridge-1079]. Earlier closing runs (`31de992c`, `f2b97e01`) were also green [rec: lawful-tooth-6508] [rec: rich-path-1948].
- **Every skip has a named reason** (REPORT.md C1 section): JAX/MJX offboard, no Blender recipe runtime, the packaged-gate env var, the private review host [rec: odd-comet-7221] [rec: glad-oak-4897].
- **Closing report** `docs/probes/ot10/REPORT.md` (commits `26bc9ef0`, `c1cdd2c0`, `a5fc93e7`): all 18 counted attempts plus hex3 with hero, look views and scores; the refusal census; both W2 runs; a per-criterion status list; an A7 section (open, carried forward, highest total 16, T4 at most 2, no confirmation turn run); an A8 section; a final gates table; the W2 section *What the gait check cannot see* [rec: lawful-tooth-6508] [rec: glad-oak-4897]. The old "Reconcile before done" paragraph is marked history and the closing paragraph names every record the last reconcile must fold [rec: glad-ridge-1079].
- **Graph health** is judged with `hypergraph check --config .hypergraph/config.yml` only [rec: odd-comet-7221].

## Negative knowledge

- [scope: this repo's hypergraph check | confidence: high | evidence: odd-comet-7221] A bare `hypergraph check` without `--config .hypergraph/config.yml` reports spurious I2 violations (270 here). Judge graph health only with `--config`.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- lawful-tooth-6508 — C1 evidence: suites and packaged gate green at 31de992c; REPORT.md lists every attempt, pinned by test_ot10_report.py
- odd-comet-7221 — REPORT.md names every skip reason; 270 I2 was a check without --config (0 with it)
- soft-cliff-8778 — final re-run at 18eb0a70 green, check 0 violations, REPORT.md states the A5 verdict, done re-claimed
- honest-dawn-9522 — A5 confirmation round pre-registered after the C1 claim (context only)
- wise-sea-0110 — A5 confirmation turn 1 run after the C1 claim (context only)
- rich-path-1948 — C1 closing run at f2b97e01 green (engine 2263/53, CLI 1075/1, gate 23); REPORT claims done with A5 unmet
- copper-dusk-1149 — done re-claimed with A5 unmet at 7 of 18; export and check exit 0; reconcile left to housekeeping
- glad-oak-4897 — closing report finished (A7 carried forward, A8 section, W2 shuffle verdict); final gates engine 2282/53, CLI 1085/1, packaged gate 23
- glad-ridge-1079 — REPORT's stale reconcile paragraph marked history; no code change, final gates stand; reconcile owed to this pass
- clever-ocean-2380 — done re-claimed after reconcile a4304da6 (REPORT.md 8daeb814); gates engine 2282/53, CLI 1085/1, packaged 23; no box ticked
