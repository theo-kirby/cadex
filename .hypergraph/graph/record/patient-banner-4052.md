---
node_id: 726d27d7-1550-58e9-8841-367661eda759
slug: patient-banner-4052
title: 'ot10: hexapod attempt 5 judged 16/21, misses A5 on an incomplete swept fit (10/12, sweep budget); 0 CPU refusals confirm ADR-423'
created_at: '2026-09-28T07:31:19+00:00'
parents:
- humble-lily-1303
summary: ''
---
## What

Published A5 hexapod attempt 5 (`ot10-hexapod-5`): the frozen cold hexapod prompt, one design-only turn, judged blind **16/21** (all three calls 16; T1 2, T2 3, T3 3, T4 2, T5 2, T6 2, T7 2), with P1 0.013, P2 0.168, P3 3, static fit clean (1,653 pairs, 0 intersections), and electronics carried. It **misses the A5 bar on one item: the swept fit is incomplete, 10 of 12 joints** (`hip_rr` exceeded the runtime budget and `knee_rr` was never reached). The README section, the six candidate PNGs (each under 300 KB), the score file and a contract test are committed.

## Why

The critic asked two things. First, check that the latest hexapod diagnosis accounts for ADR-422, ADR-423 and ADR-424. Second, run hexapod attempt 5 on a new `ot10-hex-*` project and publish it. The diagnosis check: attempt 4's diagnosis named the 300 CPU-second limit as the open cause. ADR-423 lifted it, from 83 to 28 worker CPU-s, and the refused accent-feet candidate went from 417 to 115. ADR-424 changes P2 only, which the judge never sees. ADR-422's face rule held on attempt 4 (T5 1→2). So no open cause remained to fix first. The hero-camera concern (a face at +X seen obliquely) is a separate renderer unit, not a cause of a miss.

**Deviation, stated:** I did not launch a new turn. The previous iteration, which ended in a harness error, had already launched attempt 5 at 05:27:20Z on `ot10-hexapod-5`. The project name uses the run's existing `ot10-hexapod-N` scheme, not `ot10-hex-*`. The turn completed on its own at 06:52:46Z with `ok: true`. The harness error hit the iteration, not the product turn. So this is a conforming attempt, and it has to be published: launching a sixth to replace it would be shopping for seeds. The render and judge pipeline that iteration had queued never ran (its `render.json` was empty), so this iteration ran it.

## Method

1. **Conformance.** The notes directory's `argv`, `started` and `revision` files record `CADEX_EFFORT=medium ./cadex --project …/ot10-hexapod-5 --model claude-opus-5-5 -p <contract.json a5.prompts.hexapod> --json`, started at `3008e1f7`. The project's single commit carries exactly the frozen prompt. `agent.json` records `model = claude-opus-5-5`, one session and no continuation, and no process was left running.
2. **Measurement.** `cp -a` the project to `/tmp/ot10-hexapod-5`, removing a stale `.cadex-cli.lock` from the copy whose PID was not running. Then ran the notes dir's `pipeline.sh`, repointed at the copy:
   - `./cadex render --json`: 9 min 5 s, of which acquisition 269.4 s, drawing 9.2 s and hero 2.6 s, at 183,671 of 894,400 triangles;
   - `look_views.py`;
   - `judge.py`: 3 calls, `claude-opus-5-5`, effort high, the frozen rubric sha `1c81caa2…`.

   Proxies were read from `review/render/summary.json`, and the fit from the turn's `--json` envelope.
3. **Refusals.** `refusals.py` ran on the session jsonl: 20 refused calls, **0 CPU-limit**, and none of the four A4 classes. The one `horn_style` tag is a false match on the MJCF inertia refusal for the body `c_knee_horn_fl`.
4. **Sweep diagnosis.** From the transcript: `sweep_step_degrees` went 10 → 20 → 30 → 80, with 34 `runtime budget exceeded` rows. Read `_SWEEP_TOTAL_SECONDS = 180` and `_SWEEP_JOINT_SECONDS = 90` in `cadex_assembly_worker.py`: one `FreeCADCmd` child per joint, in series.
5. **Contract test.** `test_a5_hexapod_attempt_5_is_published_with_its_score` pins the score file (rubric sha, model, total 16, 3 calls), each candidate's sha256 and 300 KB cap, and the README verdict line. It fails before this commit because the files are missing.

## Result

- **The hexapod's judged half now clears the bar.** 16/21 is the highest hexapod total (earlier attempts: 13, 14, 13, 12). The accents and joint caps are back: 12 orange caps concentric with the hip and knee axes give T3 3 and T2 3. T4 rose to 2: a dome over a rounded base, with curved legs.
- **ADR-423's effect is confirmed on a fresh turn.** There were 0 CPU-limit refusals (attempt 4 had 8), and the agent kept the accents it had to drop last time. The component count is 58, against about 46.
- **The binding limit has moved to the swept fit's wall-time budget**, as ADR-423's record predicted. Coarsening to 80° (two samples per joint) still left 10/12 joints complete. That implies a fixed cost per joint child, from deserialising 58 BREPs and preparing every moving pair, not a cost per pose. **This is an inference from the step changes, not a profile.**
- **Next unit:** profile where the sweep's wall seconds go on `ot10-hexapod-5`, read-only on a `/tmp` copy, as ADR-423 did for the static pass. Fix it with a regression test before the next hexapod attempt. Do not change any prompt or language before that.
- **A5 status:** the biped-1 and quadruped-3 designs pass. The hexapod still has no passing design: 5 attempts, and attempt 5 misses on the sweep only.
- **Second recurrence of a product gap:** the build reply was too large for the agent to read (59.8 KB). It paged `inspect` by hand instead, checking 250 of 1,653 static pairs. Quadruped-3 named the same gap.
- **Suites:** `cli/tests/test_ot10_contract.py` 17 passed, and full CLI suite 1007 passed, 1 skipped (11 min 28 s). No engine code changed, so `test-engine` was not rerun.
- **Tail:** 3 unreconciled records once this one lands, so a reconcile is due.

Dispatch closed: 1 unit — published ot10-hexapod-5 (launched by the errored iteration; conforming): judged 16/21, P1 0.013, P2 0.168, P3 3, static fit clean, but swept fit incomplete 10/12 under the 180 s sweep budget; 0 CPU-limit refusals confirm ADR-423; next is profiling the sweep

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 0fb46c9d70cc985007e7b96488b4f2a2b1309413

## State Impact

- target: loyal-fountain-8709 — ot10-hexapod-5 (frozen prompt/argv/model/effort, started 3008e1f7, rev d2198144) judged 16/21 (no trait 0), P1 0.013, P2 0.168, P3 3, static fit clean (1,653 pairs), electronics carried, but swept fit incomplete 10/12 joints under the 180 s sweep budget even at 80° steps; 0 CPU-limit refusals (ADR-423 confirmed). Hexapod still has no passing design; next is profiling the sweep's wall time
