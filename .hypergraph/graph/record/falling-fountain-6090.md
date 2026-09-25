---
node_id: c2a362d6-0587-5920-aac7-ebaefea036c4
slug: falling-fountain-6090
title: 'ot9 B5: final fresh reopen, both suites green, closing REPORT.md; done claimed'
created_at: '2026-09-22T20:07:25+00:00'
parents:
- long-glacier-5252
summary: ''
---
## What

ot9 B5, everything except the reconcile. In a fresh process I reopened `ot9-robin` at its final accepted revision, ran both full suites at the final revision, and wrote the closing report `docs/probes/ot9/REPORT.md`. The receipt is `retained/r6-robin-final.json`, and `cli/tests/test_ot9_report.py` holds the report equal to the r3–r6 receipts.

## Why

The target is B5 (`true-anchor-9584`) under the ot9 root (`open-cabin-5892`). The critic's message asked for five things.

- **Items 1, 2, 3 and 5 are done.**
- **Items 4 and 0 are not done.** The critic's "fix first" (reconcile candid-wood-6113 and long-glacier-5252) and its item 4 (reconcile again) were both left undone. This dispatch forbids the hypergraph-reconcile skill in a work iteration, "no exceptions", so I did not run it.
- The tail is now 3 unreconciled records. Under the charter's rule a reconcile is due, and the loop's reconcile iteration should take it next. The report's own Claim section says so.

## Method

1. **Fresh reopen.** Ran `./cadex export --project $PROJECTS/ot9-robin --out $PROJECTS/ot9-robin/reopen/b5-final --json` in a new process after every earlier chain had exited. It took 274.9 s and made project commit `46ad96c`.
   - I hashed the exported trace, the policy receipt, the MJCF and the task, and compared them with the r4 receipt's seed-9 row and its r4 reopen.
   - I read the trace with `runner/balance_eval.py` using the pins.
2. **Suites.** Ran `pixi run test-engine` and `pixi run python -m pytest cli/tests` at the final revision. The CLI run includes the new test.
3. **Packaged gate.** Not run. `git diff` from the run's merge base shows no change under `src/`, `package/`, `shell/` or `pixi.toml`, so the gate is not required.
4. **Report.** Built the seed table from `r4-robin-eval-1.json` with the same format string the test uses.

## Result

- **Final reopen:** `ae889a9b…` rebuilt to digest `078ebe87…`, as the critic expected.
  - Policy receipt `8df0c267`, byte-identical to r4's.
  - Policy `ef71f370`, MJCF `933b1ac6`, task `1f8c1040`; witness error 6.9e-8.
  - The trace `5d64a9ee` is byte-identical to evaluation seed 9, and the reader passes it (8.0 s, truncated, peak 2.783°, minimum height 105.83 mm).
- **Suites:**
  - `pixi run test-engine`: 2196 passed, 53 skipped, 0 failed.
  - `cli/tests`: 938 passed, 1 skipped, 0 failed.
  - The packaged gate was not required: there was no engine or payload change in ot9.
- **REPORT.md** covers:
  - the accepted identity and every run with its accounting class: r2 no-policy fall, r3-ppo-1 training, the interrupted iteration 6, the r3-ppo-1 ten-seed evaluation (pass 10/10), the r4 reopen, the B4 measurement and the B5 reopen;
  - the checkpoint choice: the final iteration 299 was installed, not the best checkpoint `dc4d392e` from iteration 255, and it was chosen before evaluation;
  - all ten seed rows;
  - no design, task or reward change;
  - contact compression, reported apart from intersections;
  - remaining defects: the ~0.84 m systematic drift, robustness left unmeasured, and the stale `accepted_geometry` in script.json.
- It claims done for critic review and ticks no boxes.
- **Owed:** a reconcile folding candid-wood-6113, long-glacier-5252 and this record. That is B5's last step, and it is forbidden in this dispatch.
- No new dependency. No trace, policy binary or machine path is committed.

Dispatch closed: 1 unit — B5 final fresh reopen (ae889a9b→078ebe87, trace = seed 9), engine 2196/53 skipped and cli 938/1 skipped green, closing REPORT.md pinned by test_ot9_report.py; done claimed for critic review, reconcile left to the reconcile iteration.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: aecab84e48a43055eef11f966a18218b3ce835a1

## State Impact

- target: true-anchor-9584 — B5 evidence at the final revision: fresh-process reopen rebuilt accepted ae889a9b to 078ebe87 with policy ef71f370 / model 933b1ac6 / task 1f8c1040, trace byte-identical to seed 9; pixi run test-engine 2196 passed 53 skipped, cli/tests 938 passed 1 skipped; packaged gate not required (no src/package/shell change in ot9); docs/probes/ot9/REPORT.md lists every run, the ten seeds, checkpoint choice, interrupted iteration 6, drift, compression and no design change, pinned by cli/tests/test_ot9_report.py (commit aecab84e); final reconcile still owed
- target: open-cabin-5892 — closing report written and done claimed for critic review; B1-B5 all have measured evidence, owner boxes unticked
