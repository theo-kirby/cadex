---
node_id: 94b5abb0-d87f-5b7b-85e4-6df4e380fce6
slug: cool-gate-3332
title: D8. Interrupted and failed runs remain understandable
created_at: '2026-09-12T14:51:25+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**Empty-project review and final-publication failure are verified on fixtures; a real interrupted biped run remains untested.** A browser regression and same-machine private-address test of the actual refused-creation project show zero runs, no revision/digest, missing geometry/specs, readable documents and the next `cadex -p` action, with project files byte-for-byte unchanged after server shutdown [rec: zesty-star-7710]. The trainer's failure handler now extends through final policy header construction, policy validation, witness comparison, atomic final save and done reporting: a failure there publishes a `failed` progress snapshot retaining the last committed metrics, histories, task/model identities and checkpoint references, and is still re-raised. Before ADR-288 such a failure left `state=training`, error empty, at the last iteration. Four headless-browser fault-injection cases (header, validation, witness, save) drive the real trainer orchestration with fixture math and real atomic writes, each observing training in Chromium then failed without reload; they assert exception identity, missing final policy, retained curves/iteration/hashes, checkpoint bytes/digest, historical revision identity, the next CLI action and another run record's byte-for-byte preservation. No algorithm, dependency, engine, payload or shell change [rec: long-cove-3626]. Stale labelling for starting/training snapshots older than 30 seconds comes from D3's telemetry work [rec: kind-fountain-5086].

Remaining limits: hard kills and failure to write the progress file still leave stale rather than failed telemetry [rec: long-cove-3626]. Retain `open`: the criterion needs one real interrupted biped training run followed by a successful new attempt, which depends on D9's creation (`silent-river-6649`).

Charter criterion: **D8. Interrupted and failed runs remain understandable** A controlled training interruption, a failed run, and missing/partial review output are tested; the dashboard distinguishes interrupted/failed/stale states from success, preserves prior completed results and explains the next CLI action. Evidence: fault-injection tests and one real interrupted biped training run followed by a successful new attempt; checkpoint resume is not required. Declared target `gap-d8-interrupted-failed-runs-remain` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: the ot5-biped quota-refused creation attempt | confidence: high | evidence: zesty-star-7710] The provider refusal is absent from dashboard run history and has no automatic PROGRESS row; only accepted runs receive those rows. Readable empty-state guidance does not expose the provider error [rec: zesty-star-7710].
- [scope: the offboard trainer's progress snapshot | confidence: high | evidence: long-cove-3626] A hard kill, or a failure to write the progress file itself, produces no `failed` snapshot; observers see a stale training state instead.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d8-interrupted-failed-runs-remain`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- zesty-star-7710 — empty-project browser regression and real refused-creation evidence; training fault coverage still absent
- kind-fountain-5086 — ADR-287 stale/failed/terminal telemetry labelling that these states render through
- long-cove-3626 — ADR-288: final policy publication failures publish failed telemetry; four browser fault-injection cases
