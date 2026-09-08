---
node_id: f610db62-9354-57c3-8955-f9f5da6574c7
slug: narrow-wing-0418
title: Walk reports bounded engine/source differences without refusing
created_at: '2026-09-08T14:58:02+00:00'
parents:
- western-reef-4119
summary: ''
---
## What

Added the walk's engine/source comparison to its JSON envelope and stderr before the first leg. The report separates match, measured difference and unavailable evidence, caps each name list at ten, and carries full counts. Updated CLI documentation, project architecture scaffold, ADR-251 and the ROADMAP checkbox.

## Why

Advances the charter criterion **The walk exists and is tested headlessly** (`crisp-reef-5607`) by exposing the installed/source mismatch that previously needed a manual prerequisite check. Follows the selected reporting unit in `western-reef-4119` and the overseer's explicit dispatch. The reversible choice is reporting only: no refusal, rebuild, changed engine selection or payload change. Dev runs compare binary-prefix Mod/cadex; explicit/environment payloads compare their declared module directory. This only measures top-level Python bytes, never age ordering, binary provenance or the loaded-module closure.

## Method

Added offline walk regressions for matching, differing and unavailable evidence while train/declare/rollout/review still succeed; asserted the same report in JSON and stderr. Additional helper tests cover external payload differences, missing/extra files, truncated lists with complete counts, absent source and unreadable evidence. Executed the new walk regression against the previous committed __main__.py in an isolated Python module namespace: all three cases fail with KeyError: engine_source_comparison, without altering the checkout. The first focused run exposed a missing json import; fixed before the final gate.

## Result

`pixi run python -m pytest cli/tests -q`: **223 passed in 228.14 seconds**, no skips or failures. The gate included its existing bounded real-engine/local-trainer lifecycle tests. Old-source regression: **3 failed as expected** at the missing report key. `git diff --check` passed.

A direct read-only comparison on this machine found all 56 top-level Python files matching, with zero changed/missing/extra files. This does not prove binary currency. Logs remain outside git at /tmp/ot4-engine-report-cli.log and /tmp/ot4-engine-report-old.log; no generated probes or review dumps are committed. No GUI, remote dispatch, full build or new training experiment was run. Existing walk evidence remains intact; this unit does not independently re-prove the full lifecycle criterion. Next, per the overseer: the local three-mode artifact-parity test, with GUI and remote execution still excluded by the charter. The plan's model-free iterate comparison also remains unspent.

Dispatch closed: 1 unit — report bounded engine/source comparison evidence without refusing the walk.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: d6e3fe2174bed28f177a108a54ae23548f5b6829

## State Impact

- target: crisp-reef-5607 — Walk reports match/different/unavailable installed or payload Python comparison in JSON and stderr before its first leg; CLI gate 223 passed, old-source regression fails; no binary provenance claim.
- target: chilly-union-8972 — Added bounded engine/source comparison reporting to cadex walk, documented in CLI and scaffold; selection and refusal unchanged.
