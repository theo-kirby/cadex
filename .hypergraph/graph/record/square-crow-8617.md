---
node_id: 1b3ba3e9-4624-52ca-98d3-eb4c5b47a1b4
slug: square-crow-8617
title: 'ot11 C1: report cites 2a4169d1 receipts and coupled-gripper defect; done claimed'
created_at: '2026-10-01T21:03:58+00:00'
parents:
- zesty-bell-3977
summary: ''
---
## What
Brought `docs/probes/ot11/REPORT.md` up to the final revision `2a4169d1` and claimed done for critic review. The C1 receipt row now cites that revision's results: `pixi run test-engine` 2543 passed, 61 skipped; `cli/tests` run CPU-only, 1290 passed, 1 skipped; the packaged lifecycle gate 23 of 23 against the payload restaged after ADR-475. The row used to cite `d24016fc` and say no engine source had changed. The packaged-gate entry under *Remaining defects* now names ADR-473–475 as engine changes after which the gate was paid. A new Remaining-defects line covers two things: the coupled gripper is unstable when commanded closed, and MJX's support for `equality/joint` is unmeasured (ADR-475).

## Why
The critic's message asked for exactly this before the unit. The C1 row cited a stale revision, and golden-bay-4173 requires a later claim to cite the 2a4169d1 results. All criteria have evidence and #88 accepted done, so the exhaustion policy calls for closing. I did what the critic asked and nothing else.

## Method
- Edited the C1 row and the packaged-gate defect paragraph, and added one defect bullet. The numbers are copied from zesty-bell-3977's receipts at `2a4169d1`, and nothing was re-run.
- Ran `pixi run python -m pytest cli/tests/test_ot11_report.py`: 15 passed. This includes the check that every ADR cited under Remaining defects exists in DECISIONS.md.
- Searched for leftover `d24016fc` and "no engine source has changed" text and found none.

## Result
REPORT.md's C1 row cites the `2a4169d1` receipts. Remaining defects names the unstable coupled gripper and the unmeasured MJX `equality/joint`. Neither blocks an ot11 criterion, because no grip task is frozen and no gripper has been trained.

**Done is claimed for critic review**: P1–P4, R1–R3 and C1 each have evidence. No owner box is ticked.
- The suite numbers are carried over from `2a4169d1`. This commit changes only the report, so they still describe the code.
- The next rung, if the critic does not accept, is the long-term fourth behaviour (the grip). Its first step is to diagnose the soft `equality/joint` instability in the product, with a regression test, and to measure MJX's support for `equality/joint`.

Dispatch closed: 1 unit — C1 receipt row cites 2a4169d1 (2543/61, 1290/1, gate 23/23); coupled-gripper and MJX equality/joint defect added; done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 091cf0fccd3a9376515be276b2a69e7adf1bc853

## State Impact

- target: golden-bay-4173 — REPORT.md's C1 row now cites the final revision 2a4169d1 (test-engine 2543/61, cli/tests CPU-only 1290/1, packaged gate 23/23 after ADR-475), Remaining defects names the unstable coupled gripper and unmeasured MJX equality/joint (ADR-475), and done is claimed for critic review with no owner box ticked
