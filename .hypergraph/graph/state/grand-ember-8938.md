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

**Report complete; done claimed for critic review at `cc9a77a3`; the owner's box is untouched** [rec: windy-badger-4166]. Reconcile judgement: status stays `working` — the status vocabulary has no `met`, and the human owns the checkbox.

- REPORT.md covers F1's before/after on the alpha-0.5 policy; the G2 ledger (25 rows: 16 base, 7 style, 1 tool, 1 not adopted; L4, W1 and L5's reading left for the owner); both fresh-session checks; H1's six before/after images; the H2 hero and print-bed stills and the H3 shove still with push numbers; D3's eight screenshots (187–274 KB, dark floor, scripted through View → Layout at 1280×800); remaining defects [rec: eager-sage-0150]. Its ADR table lists every orun4 ADR, 558–583 [rec: windy-badger-4166].
- §7 item 2 is now **Fixed: `cadex smoke` false positives** (ADR-581..583; 186.7 s / 186.5 s; 33 threaded pairs at most 83% of allowance), with two caveats kept: moving pairs whose boxes overlap still cost one boolean per pair per frame; only a catalog bolt into a printed part carries a thread allowance (detail on `salty-isle-4063`) [rec: windy-badger-4166].
- REPORT.md now carries no open defect other than ADR-559's owner-revisable assumption (its defect 5); the legacy-`failed` reading of `walk-r13` named earlier is not listed as open [rec: windy-badger-4166]. Reconcile note: that judgement is the report's; F2 (`lucky-shade-9428`) was not declared and is unchanged.
- Docs-only: the doc/report tests (96) and `test_agent_guidance.py` (11) pass; full suites not rerun because no test reads REPORT.md's prose [rec: windy-badger-4166].

## Negative knowledge

None yet.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-c1-closing-report-docs-probes)
- eager-sage-0150 — REPORT.md and eight preset screenshots written; done not claimed; legacy failed-run defect named
- windy-badger-4166 — REPORT.md lists ADR-558..583, marks smoke fixed with two caveats, and claims done for critic review
