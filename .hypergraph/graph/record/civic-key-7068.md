---
node_id: 7d88a5e5-a09c-559c-bf0d-66f8b03ec3f8
slug: civic-key-7068
title: 'ADR-470: cadex evaluate voids models with a contact margin or gap; ADR-469 (0.004 s contact spring) recorded; lifecycle gate paid 23/23 twice; suites green'
created_at: '2026-10-01T09:25:10+00:00'
parents:
- glad-oak-7013
summary: ''
---
## What

Two things. First, what iteration #57 left unpaid. Its commit (`22d30e7e`, ADR-469: the 0.004 s contact spring) had no record, and it owed the packaged lifecycle gate. This record covers ADR-469 too. Second, one unit: ADR-470. `cadex evaluate` now voids every seed of a model whose contact is held off its geometry by a `margin` or `gap`, and lists the geoms in the report. Before this, that void was applied by hand at publication.

## Why

The critic's fix_first: (a) record ADR-469 with its State Impact on R1 and C1, giving both suites' counts; (b) rebuild and stage the payload, then rerun `test_cadexd_lifecycle.py`. Both are done here. ADR-469 is recorded in this node rather than in a separate one, so the iteration stays one record. The critic's ordered next step was item 2: the product should report a margin or gap as void, with a test that fails before the change. That is this unit. It serves R1 (smooth-fountain-9832), because the owner's clause voids margin models for R1. It also serves P1/P2 trust: an evaluation must not read a held-off surface as stance. The critic's item 3 (publish r14 as void and pre-register walk session 5) is not done. It is the next unit.

## Method

- **ADR-469 (commit `22d30e7e`, iteration #57).** `CONTACT_TIMECONST_S` went from 0.02 s to 0.004 s. The environment floor is written with `solref (0.004, 1)`. Restitution shapes keep the 0.02 s spring as `BOUNCE_TIMECONST_S`. Receipt: `docs/probes/ot11/retained/p4-quad-1-contact-depth.json`. On r12-convex-sym's model over seeds 1101–1110, the deepest foot point after the settle was −6.18 to −7.62 mm before and −0.66 to −2.50 mm after. Seed 1104 tipped inside the settle in the after run and has no reading. Regression `test_a_foot_under_a_stepping_load_stays_on_the_floor_rather_than_in_it` sinks 2.60 mm on the old source and 0.46 mm on the new. The MJX agreement suites passed 17/17 from the training venv (per ADR-469).
- **Gate.** Ran `pixi run build-engine` and `pixi run stage-engine` from `22d30e7e`; the staged `CadexDynamics.py` carries `CONTACT_TIMECONST_S = 0.004`. `CADEX_ENGINE_ROOT=<payload> pytest test_cadexd_lifecycle.py`: 23 passed. Repeated after ADR-470 on a restaged payload: 23 passed.
- **ADR-470.** `CadexDynamics.contact_offsets(model)` lists every contact geom (nonzero contype or conaffinity) whose compiled margin or gap is not zero, plus `option` for an override `o_margin`. `evaluate_success` compiles the model once, reads it, and joins `contact_offset_void` into each seed's `void` reason. The report carries `contact_offsets`. In the CLI (`cli/cadex_cli/evaluate.py`), `failing_predicates`, `evaluation_cell` and `human_lines` lead with the geoms, and `agent_view` carries `contact_offsets`. Docs updated: docs/CLI.md (void section, date), docs/XSCRIPT.md (`margin_mm`), DECISIONS ADR-470, and REPORT.md (the margin bullet and the gate bullet).
- Tests: `test_a_contact_margin_or_gap_voids_every_seed_and_names_the_geom` (engine) and `test_a_contact_margin_voids_the_report_and_names_its_geoms` (cli). With the engine and CLI source stashed, both fail; with them restored, both pass.
- Measured on real models with `contact_offsets`. r13-hovercost-margin: four `c_foot_*/collision0` at 3.0 mm. r14-margin15-lift: the same four at 1.5 mm. Every other ot11-quad-1 run model (r1–r12, w2-1, w2-2) and both negatives list none. Of the 36 MJCF files under ot11-robin-1 and ot11-heron-*, none lists an offset, so no published R2 or R3 evaluation moves.

## Result

What is true now: `cadex evaluate` voids every seed of a model with a contact margin or gap, names the geoms, and leads every reading of the report with them (ADR-470). ADR-469's 0.004 s spring is recorded. The packaged lifecycle gate is paid for both. It ran on a payload rebuilt and restaged from source carrying ADR-469 and ADR-470 (`def contact_offsets` is present in the staged CadexDynamics.py), and `test_cadexd_lifecycle.py` passed 23 of 23, none skipped. It also passed 23 of 23 earlier this iteration on the payload staged from `22d30e7e`. Suites at this revision: `pixi run test-engine` 2523 passed, 60 skipped; `pixi run python -m pytest cli/tests` 1271 passed, 1 skipped. ADR-470 adds no trainer change, so there was no training-venv rerun this iteration. ADR-469's 17/17 MJX agreement run stands as recorded in that ADR.

Concerns for the next iteration:
- `r14-margin15-lift` has finished training (its policy is at `assets/walk_r14.cxpolicy`) and is neither published nor evaluated. Evaluating it now voids it automatically on its 1.5 mm foot margin. Publish it as void (critic item 3). Then pre-register walk session 5 on a revision rebuilt from current source (0.004 s spring, no margin). A rebuild moves the task digest, so earlier policies do not verify against it (ADR-469).
- Row 25 (r13) was evaluated before ADR-470 and keeps its published verdict, with the hand-applied void. It was not re-evaluated.
- Assumption: the void covers every contact geom, not only feet and floor. It is task-agnostic, and none of the ot11 Robin or Heron models trips it. `margin_mm` stays legal for export and training.

Dispatch closed: 1 unit — ADR-470: `cadex evaluate` voids margin/gap models; ADR-469 recorded and its lifecycle gate paid

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 22d30e7e32e9138c6ff29d6cf9008af689d975f6

## State Impact

- target: smooth-fountain-9832 — ADR-469 (commit 22d30e7e) exports non-bouncing contacts and the environment floor on a 0.004 s spring: r12's feet sink -0.66..-2.50 mm, against -6.18..-7.62 mm before, over seeds 1101-1110 (seed 1104 has no after reading); regression test fails on old source. ADR-470 makes cadex evaluate void every seed of a model with a contact margin or gap and list the geoms (r13 3.0 mm, r14 1.5 mm feet; no other ot11 model), so the owner's margin-void clause is applied by the product, not by hand. r14-margin15-lift has finished training and is unpublished; walk session 5 is not yet registered on a rebuilt no-margin revision
- target: golden-bay-4173 — Packaged lifecycle gate paid for ADR-469 and ADR-470: 23/23 on a payload staged from each. Suites at this revision: test-engine 2523 passed / 60 skipped; cli/tests 1271 passed / 1 skipped. REPORT.md's margin and gate bullets are updated
