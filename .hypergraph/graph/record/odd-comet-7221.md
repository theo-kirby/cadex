---
node_id: 32cdffaf-1312-50d4-8e6b-f165631a737e
slug: odd-comet-7221
title: 'ot10: C1 — 270 I2 is a check run without --config (0 with it); -rs skip reasons for both suites in REPORT.md; reconcile left to an allowed role'
created_at: '2026-09-28T18:03:30+00:00'
parents:
- lawful-tooth-6508
summary: ''
---
## What
Answered the critic's C1 rejection, except for the reconcile. First I found why `hypergraph check` went from 0 to 270 I2 violations. Then I re-ran both suites with `-rs` and added every skip reason to `docs/probes/ot10/REPORT.md`'s C1 section (commit below).

## Why
The critic rejected done for two reasons. `check` exited 1 with 270 I2 violations, and REPORT.md's C1 table gave skip counts without reasons. It asked for a reconcile pass first. **I did not reconcile.** This dispatch says the hypergraph-reconcile skill and `hypergraph update` are "forbidden in a work iteration, no exceptions". The dispatch header outranks a critic request for an action it forbids. I took the reversible option: do the diagnosis and the report fix the critic asked for, and leave the fold to a pass allowed to run it. The critic's step 3 (find the cause of the 270) needs no state write, so I did it here.

## Method
- Ran `hypergraph export --config .hypergraph/config.yml`: 696 record, 91 state and 4 plan nodes.
- Ran `hypergraph check --record … --state … --config .hypergraph/config.yml`: **0 violations, 0 warnings, exit 0**.
- Ran the same command without `--config`: **exit 1, exactly 270 violations**. Every one reads `impact targets unconfigured view 'plan' — 'hypergraph views add plan' creates it first`.
- With `--config` but with `cache/plan.json` removed, the command exits 2 and asks for `hypergraph sync`.
- The 270 is therefore an invocation artifact. Without the config, the checker does not know that `views.plan` exists (root `fond-ember-4937`), so every plan-view impact counts as I2. `.hypergraph/AGENTS.md` §4 already documents `--config`. Only the root AGENTS.md sentinel block says bare `hypergraph check`, and `hypergraph upgrade` owns that block.
- The checker's hint (`views add plan`) would be wrong: the view already exists, and running it would fork a second plan root.
- Ran `pixi run python -m pytest src/Mod/cadex/cadex_tests -q -rs`: 2,242 passed, 53 skipped, 301 s.
- Ran `pixi run python -m pytest cli/tests -q -rs`: 1,061 passed, 1 skipped, 737 s. That is 1,055 plus the report's own 6 tests.
- Grouped the skips by reason and wrote them into REPORT.md's C1 section with the correct check invocation.
- Ran `test_ot10_report.py` and `test_ot10_contract.py`: 41 passed. `git diff --check` was clean.

## Result
All 54 skips are now explained in REPORT.md. The four causes are:
- **47 engine skips:** JAX and MJX are absent by design (ADR-084). They cover 7 `test_dynamics_*` files.
- **5 engine skips:** `test_blender_recipe.py` needs `CADEX_BLENDER_EXECUTABLE`.
- **1 engine skip:** `test_licensing_compliance.py` needs `CADEX_ENGINE_ROOT`. The packaged gate row already covers it.
- **1 CLI skip:** `test_review_server.py` needs `CADEX_REVIEW_HOST`.

No failures. The graph was never in violation when checked with the project config. REPORT.md is 14.0 KB.

**Still owed:**
- A reconcile pass must fold true-grove-4773, lawful-tooth-6508 and this node, then advance the HWM and regenerate the views. The tail is now three records, which meets the charter's trigger. A work dispatch cannot do this, so the controller must dispatch the maintainer or reconcile role.
- Done should be re-claimed only after that pass.
- Whoever verifies must run `check` **with `--config .hypergraph/config.yml`**, or it will read 270 again.

The A5 note stands: all nine misses stay published.

Dispatch closed: 1 unit — diagnosed the 270 I2 as a check run without --config (0 with it) and added the -rs skip reasons for both suites to REPORT.md; reconcile left to a role allowed to run it

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: fc13f51014fb5b6abddb7fc2b162c2be10617782

## State Impact

- target: southern-prairie-3683 — REPORT.md's C1 section names every skip reason at 3879f1e2: engine 2,242 passed and 53 skipped (47 offboard JAX/MJX, 5 Blender recipe executable, 1 packaged-gate env), CLI 1,061 passed and 1 skipped (review host env). hypergraph check exits 0 with --config; the critic's 270 I2 came from omitting it (commit fc13f510). The reconcile and the done re-claim are still owed.
