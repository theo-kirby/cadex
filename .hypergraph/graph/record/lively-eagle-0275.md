---
node_id: 80b9f793-f10b-53e3-8d97-f423b545bb58
slug: lively-eagle-0275
title: 'ot9 B5 retaken at ADR-405: reopen heals script.json, suites and packaged gate green, defect 3 fixed'
created_at: '2026-09-22T20:50:20+00:00'
parents:
- falling-fountain-6090
summary: ''
---
## What

Retook B5 at the ADR-405 revision. ADR-405 (commit `c2f1c802`, iteration 11, which left no record) makes `CadexProjectScriptStore.write` drop an `accepted_geometry` whose key is a different accepted digest. That moved the final revision, so this unit reran both full suites, rebuilt and staged the engine, ran the packaged lifecycle gate, did a fresh-process reopen of `ot9-robin`, and confirmed that its `script.json` healed on the first write. The unit then added receipt `docs/probes/ot9/retained/r7-robin-adr405.json`, updated `docs/probes/ot9/REPORT.md` (remaining defect 3 marked fixed by ADR-405, new suite counts, packaged gate, ADR-405 reopen row) and extended `cli/tests/test_ot9_report.py` to pin the page to r7. Commit `ae588e82`.

This record also covers iteration 11's ADR-405 fix, which the critic says holds: the store clears a stale `accepted_geometry`, and the restore path writes the digest and the measurement together. The regression `test_the_store_drops_a_measurement_once_its_accepted_digest_moves_on` fails on the old store.

## Why

The critic's message. Iteration 11 committed ADR-405 with no record, and that change made B5's regression and reopen evidence stale. I followed steps 1–3 as written. **Deviation on step 4:** the critic asked for "record, reconcile, export and check". This dispatch forbids `hypergraph-reconcile` in a work iteration, so I recorded, exported and checked, and left the reconcile to the loop's reconcile iteration. I also ran the packaged gate, which the critic did not ask for. The charter's quality bar requires it for payload changes, and `CadexScriptStore.py` ships in the payload.

## Method

- `pixi run test-engine` at `c2f1c802`: 2197 passed, 53 skipped, 0 failed (+1 over B5: the ADR-405 regression).
- `pixi run build-engine && pixi run stage-engine`. Confirmed the ADR-405 hunk is present in `build/release` and in the staged payload. Then ran `CADEX_ENGINE_ROOT=<payload> pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py`: 23 passed.
- Before the reopen, `script.json` (sha `67020218…`) had `accepted_digest` `078ebe87…` and `accepted_geometry` keyed on `0a6fe0f5…` / `4c75ff53…`.
- Ran `./cadex export --project $PROJECTS/ot9-robin --out $PROJECTS/ot9-robin/reopen/b5-adr405 --json` as a new process with no cadexd or worker running beforehand. Exit 0, 199.3 s, project commit `9a0b669`.
- After the reopen, `script.json` (sha `9ed31862…`) has `accepted_geometry: null`. The accepted revision `ae889a9b…` and digest `078ebe87…` did not change.
- Reopen identity matches the B5 reopen and the seed-9 evaluation exactly: MJCF `933b1ac6…`, task `1f8c1040…`, policy receipt `8df0c267…` (witness 6.9e-8 against 1e-4), stored policy `ef71f370…`, trace `5d64a9ee…`. `balance_eval.py` on the trace: pass, 400 steps, 8.0 s, peak tilt 2.783°, no termination.
- Report test edits added one test. The full `cli/tests` run with them was 938 passed plus 1 failure, the new count test: the receipt still said 938 while the page said 939. I corrected the receipt to the measured 939 and reran the report tests: 5 passed. At `ae588e82` that makes cli/tests 939 passed, 1 skipped, 0 failed.

## Result

At the final revision `ae588e82`:
- Both suites are green: engine 2197/53 skipped, cli 939/1 skipped.
- The packaged gate passed: 23/23.
- The final ot9 project reopens in a fresh process with the evaluated revision, digest, policy, model, task and trace.
- `script.json` no longer names a model the project does not have.
- REPORT remaining defect 3 is closed. Defects 1 (drift) and 2 (unmeasured robustness) stand.

ot9 claims done again for critic review. Owner boxes are unticked. Concern: the unreconciled tail now holds this record, and it still needs a reconcile pass. That was not run here because this dispatch forbids it. No new dependency, no training and no design change.

Dispatch closed: 1 unit — B5 retaken at ADR-405: suites, packaged gate, fresh reopen healing script.json, REPORT defect 3 fixed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot9
- commit: ae588e8267e06be53f81ad76f2931dfef95d8a18

## State Impact

- target: true-anchor-9584 — B5 evidence moved to the ADR-405 final revision (ae588e82): test-engine 2197 passed 53 skipped, cli/tests 939 passed 1 skipped, packaged lifecycle gate 23 passed after rebuild+stage; fresh reopen of ot9-robin identical to the evaluated identity and its script.json stale accepted_geometry cleared on first write; REPORT remaining defect 3 fixed (ADR-405), receipt r7-robin-adr405.json
- target: open-cabin-5892 — ADR-405 fixed REPORT remaining defect 3; closing report updated to the final revision and done re-claimed for critic review, owner boxes unticked
