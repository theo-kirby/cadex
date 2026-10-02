---
node_id: de728b52-2f5a-5b5b-b240-a15de6bdd1a6
slug: silver-light-9977
title: 'ot11 C1: stale walk claim removed and test-pinned; suites green at d24016fc; done claimed for critic review'
created_at: '2026-10-01T19:56:52+00:00'
parents:
- misty-star-3641
summary: ''
---
## What
Records iteration 87's unrecorded fix (commit `d24016fc`) and refreshes C1's suite receipts.
- `d24016fc`: `docs/probes/ot11/REPORT.md` no longer says "No walk evaluation has passed a seed" beside rows 35 and 36 (both 10 of 10); the bullet now names walk rows 1–2 and 13–28 as passing no seed, rows 29–34 as partial (1, 2, 9, 0, 2, 6 of 10), and rows 35–36 as 10 of 10. The *Remaining defects* W10 bullet now says W10 held under a stepping gait with no contact offset on ADR-469's spring (row 36 lowest foot −0.019 to −0.012 hip heights). `docs/probes/ot11/README.md`'s "R1 stands at 0 of 10" is rescoped to "when session 3 closed".
- New test `test_no_stale_walk_claim_beside_a_passing_walk_row` (`cli/tests/test_ot11_report.py`): once any walk evaluation passes, no line of REPORT.md may match a stale "no walk has passed" claim, and the replacement bullet must name rows 35 and 36, which the evaluation ledger must show as 10 and 10.
- This iteration: both full suites at `d24016fc`; REPORT.md's C1 receipt row moved from `4d2baa7d` to `d24016fc` with the new counts.

## Why
The critic's message: record the REPORT.md fix and its test with C1 (golden-bay-4173) as State Impact, run both suites at this revision, update the closing report's suite receipts to the final commit, and put done up for critic review without ticking owner boxes. Deviation: the critic also said "then fold it" / "run the reconcile". This dispatch forbids the reconcile skill and `hypergraph update` in a work iteration, so I did not fold; I ran export + check only. The tail is now one record.

## Method
`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu` for cli/tests (one-GPU-job rule), `pixi run test-engine` in parallel. Confirmed no `src/Mod/cadex` or `package/` change since `4d2baa7d` (`git log 4d2baa7d..HEAD -- src/Mod/cadex package` empty), so the packaged gate's last 23/23 after ADR-470 still stands. Reran `cli/tests/test_ot11_report.py` after the receipt edit: 15 passed.

## Result
At `d24016fc`: `pixi run test-engine` **2529 passed, 61 skipped**; `cli/tests` CPU-only **1290 passed, 1 skipped** (`test_review_server.py:851`, needs `CADEX_REVIEW_HOST`). No failures. REPORT.md's C1 row cites these. The receipt edit itself is docs-only and the report tests pass on it.
**Done is claimed for critic review** again: P1–P4, R1–R3 and C1 each carry evidence and a receipt row; no owner box is ticked. Remaining defects stay listed in REPORT.md.
- Not done: the fold. A reconcile pass must fold this node.
- Next if the critic does not accept: the long-term rung (a fourth behaviour through the same loop with no new code path).

Dispatch closed: 1 unit — recorded the stale walk-claim fix and its test; both suites green at d24016fc; C1 receipts updated; done claimed for critic review

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 8ee9c95b14b0b7bc5faa5564e643c438490e382c

## State Impact

- target: golden-bay-4173 — REPORT.md no longer claims no walk evaluation passed beside rows 35-36 (10/10), pinned by test_no_stale_walk_claim_beside_a_passing_walk_row; at d24016fc test-engine 2529 passed / 61 skipped and cli/tests CPU-only 1290 passed / 1 skipped, cited in the C1 receipt row; no engine change since the 23/23 packaged gate; done claimed for critic review, owner boxes unticked
