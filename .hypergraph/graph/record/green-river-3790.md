---
node_id: 2d2f16c5-797a-5863-82e5-e6b7a38da90c
slug: green-river-3790
title: 'F3: expose published joint sweeps through clearance inspection and CLI (ADR-350)'
created_at: '2026-09-14T19:24:38+00:00'
parents:
- misty-spark-6372
summary: ''
---
## What

Exposed the accepted assembly's published clearance_sweep through the existing
agent clearance inspect scope and cadex clearance --sweep (ADR-350). The CLI
writes docs/clearance-sweep.md with the accepted revision, coverage and the
unchanged measurements. Missing sweeps are explicitly unavailable.

## Why

Advances F3 (curious-quill-9036), following the producer in misty-spark-6372 and
the critic's requested read-only consumer unit. The measurements already existed
but the clearance tool did not expose them. No deviation from the critic request.

## Method

Added the published side table to clearance inspection; generic JSON Pointer
paging and existing op arguments remain unchanged. Updated the CLI command,
agent instructions, CLI and integration docs, and the tool-surface contract test.
Known-result and incomplete fixtures retain pair names, extrema, first-contact
angles and timings; a 60-pair fixture crosses real pager boundaries. Missing
legacy data stays unavailable. Fabricated-store tests compare every file before
and after reads. The packaged lifecycle test restarts and compares the sweep
and pair inspection with the retained result, preserving accepted identity.
A real CLI legacy-project fixture verifies --sweep writes a report without
changing script.json or adding/replacing accepted result files.

## Result

Sweep coverage and every published measurement now reach the agent and CLI.
Complete coverage is explicitly not a fit verdict: minimum distance alone cannot
prove that intended contact holds throughout a range. Static thresholds do not
reinterpret the sweep. Exit 0 reports successful report writing, including for
missing/incomplete coverage. No dependencies, design edits, or dashboard edits.
Existing inspect arguments and generic shell pass-through require no shell edit.
The roadmap/state views were not hand-edited, per the unattended-role contract.

Validation: focused suites 51 passed; pixi run test-engine 2,124 passed and
53 skipped (313.50 s); pixi run python -m pytest cli/tests 641 passed and
1 skipped (539.35 s). One pixi run build-engine and pixi run stage-engine
succeeded. The staged-payload test_cadexd_lifecycle.py gate passed all 17 tests
(11.16 s). git diff --check passed. Initial focused test failures were fixture
requests exceeding the inspect limit (100 vs 50); corrected to the actual paged
contract before the green runs. No product failure remains.

F3 remains open for product Finch evidence and unsupported limited joints.
The negative Finch result in ADR-348 and docs/probes/ot7/sweep/README.md is
preserved; no contact angle is invented. No claim closes F9's retained-design
comparison or the full charter.
Dispatch closed: 1 unit — expose retained joint sweeps through inspection and CLI.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: d096c0c9151f9e9f330182b6df5698068b00b4a0

## State Impact

- target: curious-quill-9036 — Published sweep measurements, first-contact angles, timings and incomplete coverage now reach clearance inspection and cadex clearance --sweep without rebuild or acceptance changes. F3 remains open for product Finch evidence and unsupported limited joints; negative Finch result preserved.
- target: eager-summit-3153 — Consumer unit verified with 2124 engine passes (53 skips), 641 CLI passes (1 skip), one build and staging, and 17 staged-payload gate passes; retained-design comparison remains open.
