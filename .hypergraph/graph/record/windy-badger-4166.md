---
node_id: 0f4c81fa-ee1e-5dff-90dd-fc062defb6ed
slug: windy-badger-4166
title: 'orun4 report: smoke defect fixed, done claimed for critic review'
created_at: '2026-10-07T01:51:16+00:00'
parents:
- smooth-pond-6955
summary: ''
---
## What
Brought `docs/probes/orun4/REPORT.md` up to date after ADR-581, ADR-582 and ADR-583 (commit `cc9a77a3`), and claimed done for critic review.

## Why
The critic's message asked for exactly this unit: list ADR-581..583, move the smoke defect from remaining to fixed with its two caveats, then claim done. Target: C1 (`grand-ember-8938`). No new engine work was started.

## Method
- The ADR table already carried ADR-581, ADR-582 and ADR-583 (added with the ADR commits); checked, left as is.
- §7 item 2 is now headed **Fixed: `cadex smoke` false positives**, keeps the measured facts (186.7 s / 186.5 s, 33 threaded pairs at most 83% of allowance), and states the two caveats from ADR-582 and ADR-583 text: moving pairs whose boxes overlap still cost one boolean per pair per frame; only a catalog bolt into a printed part carries a thread allowance.
- The done claim now says defect 2 is fixed (folded at `152635da`), defect 5 is an owner-revisable assumption, and only this claim's record is left to fold. The `Verified against source` line names the retake.
- Doc-only: no test pins REPORT.md's prose; the doc/report test files (96 tests) and `test_agent_guidance.py` (11) pass.

## Result
REPORT.md lists every orun4 ADR (558–583), carries no open defect other than ADR-559's owner-revisable assumption, and claims done for critic review. No owner box is ticked. The full suites were not rerun: the change is a single markdown file that no test reads. This record is the only unreconciled one.

Dispatch closed: 1 unit — orun4 report updated for ADR-581..583 (smoke fixed, two caveats kept); done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: cc9a77a391b93ad6fe08b338cde4f44ec9b204ec

## State Impact

- target: grand-ember-8938 — REPORT.md §7 marks cadex smoke fixed by ADR-581..583 with two caveats (moving box-overlapping pairs still cost a boolean per frame; only catalog bolts get a thread allowance); done re-claimed for critic review at cc9a77a3
