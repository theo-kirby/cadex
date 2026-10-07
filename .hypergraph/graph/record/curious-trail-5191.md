---
node_id: cfcd9936-724e-55c3-8189-28a167475328
slug: curious-trail-5191
title: 'C1: REPORT.md updated for ADR-580''s 474 s; done claimed for critic review'
created_at: '2026-10-07T00:26:55+00:00'
parents:
- modest-ivy-6616
summary: ''
---
## What
Updated `docs/probes/orun4/REPORT.md` for ADR-580 and made the done claim for critic review. §6 now gives the suite as 474.4 s as one foreground command (1211 passed, 1 skipped), under the owner's 480 s target with about 5 s of margin, and names ADR-580's two changes. The ADR table gains ADR-580. Defect 3 now reads fixed. The done claim no longer withdraws done: it claims done for critic review and ticks no owner box.

## Why
This is the critic's fix_first: four stale places in REPORT.md (§6 "The target is not met", defect 3 at 566 s, the ADR table ending at ADR-579, and the done claim withdrawing over defect 3). The critic asked for this after the reconcile. Work iterations may not reconcile, so the reconcile has not run yet. The report's content does not depend on the fold, so I updated it now. The claim says plainly that tender-sun-8957, modest-ivy-6616 and this record are still unfolded.

## Method
Read the stale sections and took ADR-580's measured figures from `docs/DECISIONS.md`: 474.4 s, 1211 passed, the slowest tests left, and the 0.05 s shutdown poll. Edited the four places plus the report's Verified line, and grepped for leftover "566", "not met" and "withdrawn". No test pins REPORT.md, and no code changed, so no suite was rerun. 474.4 s is ADR-580's measurement, not a new one.

## Result
REPORT.md is current through ADR-580. Done is claimed for critic review, and no owner box is ticked. Defects 2 (`cadex smoke` false positives) and 5 (ADR-559's interrupted-reads-failed assumption) stay listed as open. Neither is a done criterion. The suite's margin under 480 s is about 5 s. A later run over 480 s must be reported, not trimmed from the keep list. The tail is now three unreconciled records (tender-sun-8957, modest-ivy-6616 and this one), so a reconcile pass is owed before the second critic acceptance.

Dispatch closed: 1 unit — REPORT.md updated for ADR-580; done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: a4c5d5c6fc075a7ef83dd2d2ff278d753f2cf179

## State Impact

none: report text only; the CLI suite's state was declared by modest-ivy-6616
