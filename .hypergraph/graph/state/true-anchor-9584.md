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

**Final revision is ADR-405, commit `ae588e82` [rec: lively-eagle-0275].** ADR-405 (iteration 11, `c2f1c802`) made `CadexProjectScriptStore.write` drop an `accepted_geometry` keyed on a different accepted digest, with a regression that fails on the old store; that moved the final revision, so B5 was retaken there [rec: lively-eagle-0275].

**Suites and packaged gate at the final revision [rec: lively-eagle-0275].** `pixi run test-engine` 2197 passed, 53 skipped; `cli/tests` 939 passed, 1 skipped; 0 failed. Because `CadexScriptStore.py` ships in the payload, the engine was rebuilt and staged and the packaged lifecycle gate passed 23/23 [rec: lively-eagle-0275].

**Final fresh reopen [rec: lively-eagle-0275].** A new process (`./cadex export`, exit 0, project commit `9a0b669`) rebuilt accepted ae889a9b to digest 078ebe87 with stored policy ef71f370 (witness 6.9e-8), MJCF 933b1ac6, task 1f8c1040 and trace 5d64a9ee — identical to the earlier B5 reopen [rec: falling-fountain-6090] and to evaluation seed 9, which the reader passes (8.0 s, 400 steps, peak tilt 2.783 deg, no termination). Its `script.json` stale `accepted_geometry` was cleared on that first write [rec: lively-eagle-0275].

**Closing report [rec: falling-fountain-6090] [rec: lively-eagle-0275].** `docs/probes/ot9/REPORT.md`, pinned by `cli/tests/test_ot9_report.py` to receipts r3-r7 (r7 = `r7-robin-adr405.json`), lists every run with its accounting class, the checkpoint choice, all ten seed rows, no design/task/reward change, contact compression, the ADR-405 reopen, and remaining defects: ~0.84 m systematic drift and unmeasured robustness; defect 3 (stale `accepted_geometry`) is marked fixed by ADR-405. It claims done for critic review and ticks no boxes [rec: lively-eagle-0275].

**The reconcile it names as its last step is this pass**, folding lively-eagle-0275 and scarlet-bramble-6134 (the latter declared no state change: it deferred this fold to housekeeping and re-verified nothing moved since `ae588e82`) [rec: scarlet-bramble-6134]. *Reconcile judgement*: B5's declared evidence is complete at the final revision once this pass lands; status stays `working` because only the owner ticks the checkbox [rec: lively-eagle-0275].

## Negative knowledge

None yet.

## Provenance

- curious-branch-9704 — the criterion as the ot9 charter declares it
- falling-fountain-6090 — final reopen, both suites green, REPORT.md written; done claimed, reconcile owed
- lively-eagle-0275 — B5 retaken at ADR-405: suites, packaged gate 23/23, fresh reopen heals script.json, REPORT defect 3 fixed
- scarlet-bramble-6134 — reconcile deferred to housekeeping; no state change, done re-claimed
