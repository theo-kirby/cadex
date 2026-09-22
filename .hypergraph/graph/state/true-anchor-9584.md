---
node_id: 8897d1c8-a583-5380-a009-a622dfe0755b
slug: true-anchor-9584
title: B5. Regressions and a closing report are complete.
created_at: '2026-09-22T17:39:47+00:00'
parents:
- open-cabin-5892
summary: ''
---
Status: working

## Current

**B5. Regressions and a closing report are complete.** Both full suites, the packaged lifecycle gate for any engine/payload change, and a fresh reopen of the final ot9 project pass at the final revision. The report at `docs/probes/ot9/REPORT.md` lists every training and evaluation run, checkpoint choice, accepted identity, changed design/task/reward, failed attempt, achieved bar and remaining defect. Reconcile, then claim done for critic review without ticking owner boxes. [rec: curious-branch-9704]

**Final fresh reopen [rec: falling-fountain-6090].** A new process rebuilt accepted ae889a9b to digest 078ebe87 with policy ef71f370, model 933b1ac6, task 1f8c1040 (witness 6.9e-8); its trace is byte-identical to evaluation seed 9 and passes the reader (8.0 s, truncated, peak 2.783 deg, min height 105.83 mm) [rec: falling-fountain-6090].

**Suites at the final revision [rec: falling-fountain-6090].** `pixi run test-engine` 2196 passed, 53 skipped; `cli/tests` 938 passed, 1 skipped; 0 failed. The packaged gate was not required: no change under `src/`, `package/`, `shell/` or `pixi.toml` in ot9 [rec: falling-fountain-6090].

**Closing report [rec: falling-fountain-6090].** `docs/probes/ot9/REPORT.md` (commit aecab84e), pinned to the r3-r6 receipts by `cli/tests/test_ot9_report.py`, lists every run with its accounting class (r2 no-policy fall, r3-ppo-1 training, interrupted iteration 6, the 10/10 evaluation, the r4 reopen, B4, the B5 reopen), the checkpoint choice, all ten seed rows, no design/task/reward change, contact compression, and remaining defects: ~0.84 m systematic drift, robustness unmeasured, stale `accepted_geometry` in script.json. It claims done for critic review and ticks no boxes [rec: falling-fountain-6090].

**The reconcile it named as its last step is this pass**, folding candid-wood-6113, long-glacier-5252 and falling-fountain-6090. *Reconcile judgement*: B5's declared evidence is complete once this pass lands; status stays `working` because only the owner ticks the checkbox [rec: falling-fountain-6090].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- falling-fountain-6090 — final reopen, both suites green, REPORT.md written; done claimed, reconcile owed
