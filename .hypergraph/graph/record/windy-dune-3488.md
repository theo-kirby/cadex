---
node_id: b44906fb-e000-50a3-9dc4-50248438ab23
slug: windy-dune-3488
title: Remove unsupported catalog purchase tally; preserve placed inventory
created_at: '2026-09-08T03:44:12+00:00'
parents:
- snowy-cove-0032
summary: ''
---
## What

Remove the unsupported catalog generator tally in one subtractive fix-forward correction to 997293b8. Preserve ADR-236 catalog identity and inventory of placed components. Add ADR-243, retire its dangling source references, correct CLI/integration and lifecycle scaffold documentation, and tick the removal item in ROADMAP. No earlier commit is reverted or rewritten.

## Why

Advances missions 6 and 2 and charter criterion **The agent can see its work without a screen** (damp-moon-9297), preserving its already-working baseline while removing an unqualified claim. Follows snowy-cove-0032 and the overseer's explicit rank-1 instruction. Calls can create cutters or unused values, while one generated body can be placed several times; subtracting placed instances cannot establish purchases, missing hardware or fused-part identity. The reversible choice is the existing placed-instance inventory, with its limits documented. No new diagnostic is inferred from absent catalog rows.

## Method

Read actor and hypergraph-record skills, STATE, graph contract, VISION, the prior audit and all eight changed files in 997293b8. Remove its registry, worker report field, inspection arithmetic/fields, inventory prose and walk counts, plus tests solely asserting that discarded contract. Keep the catalog identity map and published-output stamp. Add one real-kernel test that publishes one catalog bolt body and links it twice: two components, two catalogued instances, both source names and family/id preserved, no generated/unplaced fields. Use inspect leaf paths so the test respects preview bounds.

Run one supported `pixi run build-engine` (configure/build/install), then `pixi run stage-engine`. Compare the three changed engine modules byte-for-byte with the fresh payload. Run full engine and CLI suites and the packaged lifecycle plus inventory suites. No shell edits, GUI launch, remote work, provider dispatch or independent training experiment. The CLI suite includes its existing toy local trainer/walk tests.

## Result

Final verification: full engine suite 2078 passed, 52 skipped (318.16 s, exit 0); full CLI suite 195 passed, no skips (245.39 s, exit 0); fresh packaged lifecycle and inventory suites 24 passed (14.82 s, exit 0). Commands: `pixi run python -m pytest src/Mod/cadex/cadex_tests`; `pixi run python -m pytest cli/tests`; `CADEX_ENGINE_ROOT=<fresh payload> pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_inventory_scope.py`. Build and stage logs, initial failures and final suite output remain in local `/tmp/cadex-39-*.log`, not versioned artifacts. `git diff --check` passes. Hypergraph export/check run before committing the node.

The first CLI suite reported 22 failed, 148 passed, 25 errors; the focused diagnosis showed `cannot import name 'library_catalog_calls'`. A temporary content-addressed worker bundle at project-b816c82c107e41400932d3a4 contained the old worker (SHA256 8312536e77dc2b59fe0b16a7ce210c0b9284901b9a14d8d5aa16cffc499d91fb), unlike corrected source (20544c5135fffb8829be634a1db4a1f7e9a7e3a39570743c9c372ac2239fa571). Quarantined that one disposable bundle by renaming it; no cache product code changed. The existing hardlink cache can hold bytes inconsistent with its content-addressed name; a later maintenance unit should investigate invalidation rather than assume this correction fixed it.

The first full engine run reported 3 failed, 2068 passed, 59 skipped: the same stale worker affected the real skeleton test; the payload-isolation check saw ccx while staging was still copying the environment; and my new test assumed a preview was a full component list. The initial packaged run passed all 15 lifecycle checks but hit that test assertion (23 passed, 1 failed overall). Corrected the test to read leaf paths. Staging and the full suite should be sequential because the suite inspects the staged tree; the final run obeys that dependency. The finished payload has no bin/ccx.

Build/install and staging exit 0. Staging is local-only, 2.4 GB, with external LC_RPATH warnings from the stage-only audit; it is not a relocatable release. The installed application bundle remains stale and was not rebuilt or launched. Existing accepted reports with historical tally fields are read without using those fields, with no reacceptance or digest migration.

Next: rank 2 hardware-placement guidance in the walk prompt and project scaffold, then the quota-gated two-servo rehearsal under its existing bounds. This unit is not evidence that an agent followed that guidance, nor that catalog geometry inside boolean results can be identified. The baseline headless-review criterion stays working; no additional charter box is claimed. The harder fused-part finding remains a review limit until a future rehearsal and any separately justified experiment establish more. This adds the third unreconciled record; reconciliation remains the maintainer's work, not this actor's.

Dispatch closed: 1 unit — remove unsupported inventory purchase inference while preserving and verifying placed catalog instances.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 66f3740e4a17e04c47bf58299eba9551acad57c3

## State Impact

- target: damp-moon-9297 — Remove unqualified generator-minus-placement claims; retain catalog identity and two-links-per-body inventory, verified by full engine/CLI suites and fresh packaged gates. Fused catalog identity remains unsupported.
