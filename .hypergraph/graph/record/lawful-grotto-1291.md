---
node_id: 8296f51d-21ab-591b-9b82-d3f173107474
slug: lawful-grotto-1291
title: Every build reply carries the published catalog identity as an advisory inventory block beside the fit summary (ADR-362); F6 and F7 run on this product version, F5 stays as measured
created_at: '2026-09-16T14:18:18+00:00'
parents:
- sunny-chart-5873
summary: ''
---
## What

Every successful build reply from the headless CLI's bridge (`write_script`, `edit_script`, `set_params`, `rebuild`) now carries an advisory `inventory` block beside the ADR-346 `fit` block, read from `inspect scope=inventory` under the same lock so it describes the revision the reply accepted: `component_count`, `catalogued_count`, `uncatalogued_count`, the `catalog_counts` roll-up by `family/part_number`, and every `uncatalogued_sources` name, plus a `source` line saying it is the published inventory and not stdout, and a `note` saying a purchased part listed there has lost its catalog identity. Counts are per component and names per source output, so one drilled servo body placed twice is two uncatalogued components and one name. It has no verdict and refuses nothing; `available: false` with the reason when the revision places no assembly or the inventory cannot be read. The progress line, `ToolCall`, `BridgeState.last_inventory`, the turn report's `--json` envelope (`inventory`) and its prose report (one line per uncatalogued source) all carry it. The system prompt gains a bullet, `CATALOG IDENTITY IS MEASURED TOO`, beside the fit bullet: read the block before saying hardware comes from the catalog; if a purchased part is listed, place the untouched catalog body and put the cut in the printed part. ADR-362 records it; `docs/CLI.md` gains a section beside the ADR-346 one, the envelope paragraph and an overlay bullet; `docs/probes/ot7/REPORT.md` gains a "Product version" paragraph in the F10 section saying F6 and F7 run one product change newer than F5, F5 is not re-run, and no frozen prompt changed.

Tests: `cli/tests/fake_cadexd.py` gains `inventory_value` and the unconfigured fake serves the inventory scope as unavailable; `test_mcp_protocol.py` gains a known-answer fixture in Heron's shape (six components, three catalogued, three uncatalogued over two sources) pinning every count, name and the progress line on the text the model receives, plus the partless, advisory-not-refusing, unreadable and refused-build cases, and the read count moves from five to nine; `test_inventory.py` gains a unit test on `inventory_summary`; `test_turn_loop.py` pins the prompt bullet; `test_clearance.py`'s paged fixture serves the inventory scope; `test_project_tool_surface.py` pins `inventory` as a served scope the CLI offers, with the ADR. No protocol op, arg or response shape changed; no engine source changed; no `shell/` change; no new dependency.

## Why

The critic's message: F5's bounded experiment is complete, spend no further prompt on it; before F6, surface the published inventory's catalog counts and uncatalogued sources alongside the design-turn fit summary, advisory only, with a known-answer fixture, the tool-surface contract and documentation updated, an ADR, the required gates, and the product-version difference for F6/F7 recorded without changing frozen prompts or revisiting F5. This is that unit, as asked. It advances F6 and F7 (`narrow-dune-9454`, `rapid-grove-9687`) by changing what their agent sees before their first design turn, and F10 (`first-snow-5587`) through the report paragraph. The evidence for the blind spot is `sunny-chart-5873`: four F5 turns in which the agent claimed all twelve purchased parts catalog while the published inventory listed both servos and both horns uncatalogued, because nothing in its reply carried catalog identity. The critic also said to reconcile after this third unreconciled record and then dispatch F6 in `ot7-robin-b` when Claude has room; a reconcile is forbidden inside a work iteration, so the tail is now three (`restless-gate-7062`, `sunny-chart-5873`, this) and the next iteration is the reconcile pass. No design turn was dispatched and no `ot7-*` project was touched.

## Method

1. Read `.ouroboros/AGENTS.md`, the two unreconciled records, the bridge's fit path (`bridge.py`, `clearance.py`), the inventory module and the engine's inventory scope value (`CadexInspection.py`), the report and envelope wiring, the existing ADR-346 tests and docs.
2. Added `INVENTORY_SOURCE`, `inventory_summary` and `read_inventory_summary` to `cli/cadex_cli/inventory.py`; wired `_read_inventory`, `_inventory_line`, `ToolCall.inventory` and `BridgeState.last_inventory` into `bridge.py`; added the `inventory` field, JSON and prose to `report.py`; set it from the bridge in `__main__.py`; added the prompt bullet in `agent.py`.
3. Wrote the tests above; the three older assertions that pinned the fit phrase as the progress line's end now pin it as contained, since the line continues with the inventory phrase.
4. Ran the touched CLI files (210 passed), the engine tool-surface test (13 passed), then the full CLI suite and `pixi run test-engine`; results in `## Result`.
5. Wrote ADR-362, the `docs/CLI.md` sections and the REPORT.md paragraph; scanned the diff for machine paths (none); committed.

## Result

**True now.** Commit `fd3b3643`. Every build reply from the headless CLI carries an advisory `inventory` block beside `fit`, the envelope carries it as `inventory`, and the system prompt tells the agent to read it before claiming catalog hardware. Gates: the full CLI suite 768 passed, 1 skipped (545 s); `pixi run test-engine` 2142 passed, 53 skipped (300 s); the touched CLI files 210 passed; the tool-surface test 13 passed. No protocol op or response shape changed, so the packaged gate is not owed. No `ot7-*` project, frozen prompt or design changed; no design turn dispatched; no new dependency.

**Product version.** F5's four completed turns ran on the product before this change and F5 stays exhausted as measured; F6 and F7 will run with the block, on unchanged frozen prompts, so a difference from F5 on the catalog count is a difference across this one change. REPORT.md says so in its F10 section.

**Assumption.** Whether a cut catalog body counts as catalog hardware remains the owner's call on the F5 tick; the block reports the fact and takes no side, which is why it is advisory and has no verdict.

**Concern.** The unreconciled tail is three records (`restless-gate-7062`, `sunny-chart-5873`, this), so the next iteration is the reconcile pass; after it, F6's create on `ot7-robin-b` is the next design turn, dispatched only when `run.py window` reads under 45 %.

Dispatch closed: 1 unit — every build reply carries the published catalog identity as an advisory `inventory` block beside the fit summary (ADR-362), with a Heron-shaped known-answer fixture, the tool-surface pin, docs and the F6/F7 product-version note; commit fd3b3643.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: fd3b3643cb6b117d39a0028cdb015dc7ad17a9af

## State Impact

- target: chilly-union-8972 — every successful build reply from the bridge carries an advisory inventory block beside fit (ADR-362): component, catalogued and uncatalogued counts, the catalog roll-up and every uncatalogued source by name, read from inspect scope=inventory under the build's lock, never from stdout; no verdict and nothing refused; the --json envelope and prose report carry it as inventory; the system prompt says catalog identity is measured too; test_project_tool_surface.py pins inventory as a served scope the CLI offers; commit fd3b3643
- target: narrow-dune-9454 — F6's create on ot7-robin-b will run on a product whose build replies carry the advisory inventory block (ADR-362, commit fd3b3643), one change newer than F5's product; frozen prompts unchanged; dispatch waits for the reconcile pass and a window reading under 45 %
- target: rapid-grove-9687 — F7's create on ot7-plover-b will run on the same product version as F6 (ADR-362, commit fd3b3643): build replies carry the advisory inventory block; frozen prompts unchanged
- target: first-snow-5587 — REPORT.md's F10 section carries a Product version paragraph: F6 and F7 run one product change newer than F5 (ADR-362, the inventory block), F5 is not re-run, no frozen prompt changed, and a catalog-count difference from F5 is a difference across that one change
- target: mild-ledge-7157 — the critic's pre-F6 product unit landed (ADR-362, commit fd3b3643): catalog identity reaches the agent on every build reply; the unreconciled tail is three records, so the next iteration is the reconcile pass, then F6's create on ot7-robin-b when the window reads under 45 %
