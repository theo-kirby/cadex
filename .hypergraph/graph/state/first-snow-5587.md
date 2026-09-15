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

**The closing report at `docs/probes/ot7/REPORT.md` is rewritten forward under ADR-355 and carries F4's first measured result; critic acceptance of done remains unmet.** The report now opens with the amendment section: a per-design table of void calls, attempts, unspent slots and retry project, F4–F7 rows, and a closing section; the 2026-09-14 "exhausted" and "terminal incomplete" wording is kept and marked superseded, not deleted. The runner README gained a "Void calls (ADR-355)" section and the attempts README was rewritten the same way; the six pre-restart calls are listed apart from design attempts as void by code (`docs/probes/ot7/attempts/void-calls.json`) [rec: narrow-wave-7452]. After the F4 repair turn on `ot7-heron-repair-b` timed out at the runner's 30-minute bound with no submission, the report, the retained index and the runner README were written forward again with that receipt (`docs/probes/ot7/retained/repair-timeout-b.json`, 11,180 bytes, under the 16 KB cap), leaving the slot ruling to the owner [rec: rare-birch-0755]. Reconcile judgement: the report's stale outcome paragraph is fixed forward as the charter directed; the document half of F10 is current, and done acceptance is not claimable while F4–F7 have unspent slots. Retain `open`.

**What the report carries [rec: windy-otter-5423] [rec: blue-slope-0916] [rec: slender-spring-1027].** It links F1–F9 evidence, frozen prompts and transcript digests, fit availability, smoke outcomes and ot6 comparisons. Validation checked its links, seven frozen prompt hashes and transcript digests, and held it under the 16 KB cap after the iteration-40 rewrite condensed prose. The three creates have no accepted geometry or simulation; the seed's 21-to-15 failure correction is threshold slack, not agent repair. Iteration 40's "terminal incomplete" outcome, stating all authorized experiments exhausted, is the wording the amendment superseded: the six refused calls are void, no model saw a prompt, nothing is exhausted [rec: keen-wing-6569].

Charter criterion: **F10. A closing report exists and the critic accepted done.** One row per design: prompts, turns, continuation prompts used, fit failures per turn, final static and swept checks, smoke result, and the ot6 comparison; it links the evidence for F1–F9 and names what remains open, claiming nothing a record does not carry. This is the run's last unit; declared target `gap-f10-closing-report-exists-critic`, and the human owns the checkbox edit [rec: kind-dusk-1609] [rec: keen-wing-6569]. The ot6 precedent (`chilly-road-8573`) test-pinned the report in `cli/tests/test_review_design.py` and needed one more unit for the critic's acceptance. Exhaustion policy is `report_done`: a design that failed after its allowed continuation prompts is evidence, but void calls never exhaust a design, and "no authorized experiment remaining" may not be claimed while any design has an unspent slot [rec: keen-wing-6569].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f10-closing-report-exists-critic`
- windy-otter-5423 — closing evidence report exists; agent outcomes and critic done acceptance remain unproven
- blue-slope-0916 — report updated with the iteration-39 collector outcome, the sixth provider refusal
- slender-spring-1027 — report rewritten to a terminal incomplete outcome, condensed under 16 KB; reconcile forbidden in that dispatch
- keen-wing-6569 — the ot7 restart directive (ADR-355): the six calls are void, the exhausted handoff is superseded and is fixed forward
- narrow-wave-7452 — REPORT.md, runner README and attempts README rewritten forward with void calls tabled apart from attempts; superseded wording kept
- rare-birch-0755 — report, retained index and runner README written forward with the F4 timeout receipt
