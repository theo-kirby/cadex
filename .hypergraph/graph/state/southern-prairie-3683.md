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

**Where it stands:** every item has evidence. The closing run at `f2b97e01` is green and done is re-claimed for critic review with A5 stated **not met** (7 of 18 meet the bar, 11 miss); no owner box is ticked. Status is `working`; the human owns the checkbox [rec: rich-path-1948] [rec: copper-dusk-1149].

- **Suites and gate** at `31de992c`: `pixi run test-engine` 2242 passed / 53 skipped; `cli/tests` 1055 passed / 1 skipped; packaged lifecycle gate 23 passed, on a payload matching source on 57 files [rec: lawful-tooth-6508]. At `3879f1e2`, CLI 1061 passed / 1 skipped [rec: odd-comet-7221]. Re-run at `18eb0a70` green [rec: soft-cliff-8778]. **Closing run at `f2b97e01`:** engine 2,263 passed / 53 skipped, CLI 1,075 passed / 1 skipped, packaged lifecycle gate 23/23 against a staged payload identical to source (57 of 57 files; no engine commit since ADR-438) [rec: rich-path-1948]. `hypergraph export` and `check --config` exit 0 at `ac79da1d` [rec: copper-dusk-1149].
- **Every skip has a named reason** (REPORT.md C1 section, commit `fc13f510`). Engine, 53: 47 offboard JAX/MJX, 5 need the Blender recipe executable, 1 packaged-gate environment. CLI, 1: the review host environment [rec: odd-comet-7221].
- **Closing report** `docs/probes/ot10/REPORT.md` (commit `26bc9ef0`; closing C1 section at `595f49ff`). Its verdict now opens on the final count — 18 counted, 11 missed, 7 of 18 the highest bar reached. It lists all 18 counted attempts plus hex3 with hero, five look views and score file each, all 20 transcripts in the refusal census, both W2 runs with all five W1/W2 rollout images, and the remaining defects; the three previously unlinked sheets are now linked. `test_ot10_report.py` and `test_ot10_contract.py` pin it (48 of 48) [rec: lawful-tooth-6508] [rec: rich-path-1948].
- **`hypergraph check` exits 0 when run with `--config .hypergraph/config.yml`.** The critic's 270 I2 violations came from a bare `check` without `--config`, not from the graph [rec: odd-comet-7221].
- **Reconcile and claim:** the confirmation round and later A5 turns are now carried in REPORT.md [rec: rich-path-1948]. The final claim came from a work iteration that may not reconcile; this housekeeping pass folds its tail (morning-tooth-4242, rich-path-1948, copper-dusk-1149), which satisfies the charter's "reconcile, then claim" order only if the critic accepts the claim against the reconciled state — judgement, noted here [rec: copper-dusk-1149].

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
