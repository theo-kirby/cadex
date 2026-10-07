---
node_id: 12be4bae-08b3-520a-a085-2b085193ef6a
slug: grand-ember-8938
title: C1. Closing report
created_at: '2026-10-06T07:42:23+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **C1. Closing report.** `docs/probes/orun4/REPORT.md` covers F1's before/after on a filtered policy; the G2 ledger summary and fresh-session check; H1's before/after images; one example each of H2's heroes and H3's shove video (a still); D3's presets as one screenshot each (PNG, ≤300 KB, dark floor); every ADR the run added; the remaining defects. Then reconcile and claim done for critic review without ticking the owner boxes. The human owns the checkbox [rec: light-mist-9160].

**Report written; done not yet claimed** (commit `89e4cadd`) [rec: eager-sage-0150]. Reconcile judgement: status `working` — the report exists, but the criterion's last step (reconcile, then the done claim for critic review) was outstanding when it was recorded. This pass is that reconcile.

- REPORT.md covers F1's before/after on the alpha-0.5 policy; the G2 ledger (25 rows: 16 base, 7 style, 1 tool, 1 not adopted; L4, W1 and L5's reading left for the owner); both fresh-session checks; H1's six before/after images; the H2 hero and print-bed stills and the H3 shove still with push numbers; D3's eight screenshots (187–274 KB, dark floor, scripted through View → Layout at 1280×800); ADR-558 to ADR-573; remaining defects [rec: eager-sage-0150].
- It claims no criterion. Docs-only change: `test_project_docs.py`, `test_agent_guidance.py` and licensing tests 53 passed / 1 skipped; full suites not required [rec: eager-sage-0150].
- **Open defect named by the report (§7, defect 1):** a run recorded before ADR-559 still reads **failed** — `orun4-biped-sts/runs/walk-r13` has `training-status.json` `state: stopped` but a legacy `run.json` `status: failed`, so Status shows `failed` plus a stale "no telemetry update for over 30 s" warning; visible in every D3 screenshot. Candidate fix: the reader prefers a `stopped` `training-status.json` over a legacy `failed` `run.json`, with a test that fails without it [rec: eager-sage-0150]. Reconcile note: this bears on F2 (`lucky-shade-9428`) but was declared only here; F2's status is unchanged.

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-c1-closing-report-docs-probes)
- eager-sage-0150 — REPORT.md and eight preset screenshots written; done not claimed; legacy failed-run defect named
