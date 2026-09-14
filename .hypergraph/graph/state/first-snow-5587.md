---
node_id: 5ec2905b-5ee7-54e2-b0bc-2bdba67648ce
slug: first-snow-5587
title: F10. A closing report exists and the critic accepted done
created_at: '2026-09-14T17:28:06+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

Charter criterion: **F10. A closing report exists and the critic accepted done.** `docs/probes/ot7/REPORT.md` has one row per design: prompts, turns, continuation prompts used, fit failures per turn, final static and swept checks, smoke result, and the ot6 comparison. It links the evidence for F1–F9 and names what remains open, claiming nothing a record does not carry. This is the run's last unit. Declared target `gap-f10-closing-report-exists-critic`; a record may say "ticks F10" when its evidence exists, and the human owns the checkbox edit [rec: kind-dusk-1609].

The ot6 precedent (`chilly-road-8573`): the report was test-pinned in `cli/tests/test_review_design.py` (a section per criterion, every link resolving, every `[rec: …]` slug existing, every named ADR present, no private address, under the 16 KB cap), and the criterion's second half — the critic's acceptance — needed one more unit to write into the report. Exhaustion policy is `report_done`: a design that failed after its allowed continuation prompts is evidence, not a reason to keep prompting, and no fourth design or long-term rung fills the run. [rec: kind-dusk-1609]

Reconcile judgement: `open` — declared by the ot7 directive with no evidence yet; flips to `working` only when a record carries the criterion's evidence, on the reading ot5 and ot6 used (evidenced pending the owner's tick) [rec: kind-dusk-1609].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f10-closing-report-exists-critic`
