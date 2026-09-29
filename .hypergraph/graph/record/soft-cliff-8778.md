---
node_id: 4994ed36-71a7-5b98-a850-8cb86755ae30
slug: soft-cliff-8778
title: 'ot10: C1 re-claim — suites green at HEAD, A5 not met by its letter, highest bar published'
created_at: '2026-09-28T18:19:16+00:00'
parents:
- odd-comet-7221
summary: ''
---
## What
Took the done re-claim C1 still owed and stated A5's verdict by its letter. REPORT.md (commit `f9763c6e`) now says A5 is **not met**. Its Result paragraph and its A5 section both say this, and the earlier line leaving the reading to the owner is gone. The report names `ot10-biped-1` (15/21), `ot10-quadruped-3` (15) and `ot10-hexapod-10` (14) as the highest bar reached, and says they are not a redefinition of success. Both full suites and `hypergraph check --config` were re-run at HEAD. Done is claimed again for critic review.

## Why
The critic named this unit: re-run the suites and the checker at HEAD, claim done, and stop leaving A5's clause to the owner as an open question. The charter allows one turn per body plan and says "one failing design fails this criterion". Twelve turns were counted and nine missed, so A5 fails by its letter. I did what the critic asked, with no deviation.

## Method
- Edited two paragraphs of `docs/probes/ot10/REPORT.md` and added a final-run paragraph to its C1 section. The score and proxy tables were not touched.
- Ran `pixi run test-engine` and `pixi run python -m pytest cli/tests -q -rs` at `18eb0a70`. The edit touched only prose in the report.
- Re-ran `test_ot10_report.py` and `test_ot10_contract.py` on the edited page.
- Ran `hypergraph export` and then `hypergraph check --record … --state … --config .hypergraph/config.yml`.

## Result
- Engine suite: 2,242 passed, 53 skipped, 0 failed (397 s).
- CLI suite: 1,061 passed, 1 skipped, 0 failed (785 s). The skip is `test_review_server.py:851`, which needs `CADEX_REVIEW_HOST`.
- The ot10 report and contract tests pass: 41 of 41.
- `hypergraph check --config`: 0 violations, 0 warnings.
- No engine or payload file changed, so the packaged gate was not re-run. Its last run passed 23 of 23 (see REPORT.md).
- A5 is recorded as not met. Its highest bar is one design per body plan that meets the frozen bar. Everything else in the charter has evidence, and done is claimed for critic review with no owner box ticked.
- The unreconciled tail is this one node.

Dispatch closed: 1 unit — C1 re-claim: suites green at HEAD, check 0 violations, and REPORT.md states A5 is not met by its letter, with biped-1, quadruped-3 and hexapod-10 as the highest bar reached

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: f9763c6eb2e85d4f197b5572b4fc7fc12944f67d

## State Impact

- target: loyal-fountain-8709 — A5 is not met by its letter: 12 counted turns and 9 misses, where the charter allows one turn per body plan (REPORT.md, f9763c6e). Highest bar reached: ot10-biped-1 (15), ot10-quadruped-3 (15) and ot10-hexapod-10 (14) each meet the frozen bar. No success redefined.
- target: southern-prairie-3683 — Final re-run at 18eb0a70: engine 2242 passed/53 skipped, CLI 1061 passed/1 skipped, hypergraph check --config 0 violations. REPORT.md states the A5 verdict. Done re-claimed for critic review.
