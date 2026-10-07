---
node_id: 17736948-d8a0-50ff-b93f-5654ac91e968
slug: falling-walrus-2752
title: M1. Predicates measure the motion, not only where it ended
created_at: '2026-10-07T17:58:12+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **M1. Predicates measure the motion, not only where it ended.** New trace metrics (A3): net signed turns and laps of a body about a point and axis in a frame (rocking on an arc measures about zero), and a body's final and mean distance from a point with no goal declared; a spec bounds them like any metric, and an unmeasurable metric fails (ADR-586). Tests: circling passes a laps predicate, rocking on the same arc fails it, an early end fails rather than crashes. The human owns the checkbox [rec: honest-bay-2056].

**Implemented, evidence complete** (ADR-587, commit `46b57d1d`) [rec: dusty-meadow-8719]. Reconcile judgement: status `working`, as orun4 did — the vocabulary has no `met`, and the human owns the box.

- **Motion family** in `CadexEvaluation`: `turns` (frame-to-frame bearing changes wrapped to ±½ turn), `laps` = floor(|turns|), `final_distance_mm`, `mean_distance_mm`, `max_distance_mm`; all need only `body`, none a goal [rec: dusty-meadow-8719].
- **Spec surface**: `assembly.success(body=, body_offset_mm=, centre=, centre_mm=, centre_axis=)`; the centre is fixed in a component's frame (world if omitted) and carried by it each frame. A spec without `body` is byte-identical, so no task digest moved. Refusals: `success_metric_needs_body`, `evaluation_body_missing`, zero axis, foreign component [rec: dusty-meadow-8719].
- **Early end**: an episode short of its horizon measures no motion metric (`None`, failed by `check`); the played part stays in `detail.motion` with `partial: true` [rec: dusty-meadow-8719].
- **Tests**: `test_evaluation_motion.py` (7) — circling 3 laps passes `laps ≥ 2`; rocking reads |turns| < 0.05 and fails while passing a distance band (the ball-plate circle-6 failure); 50/1/0-frame ends fail without raising; signed turns; a ball circling a tilting, spinning plate reads 2.0 turns in the plate frame. One real-MuJoCo evaluation traces the frame [rec: dusty-meadow-8719].
- **Gates**: `pixi run test-engine` 2632 passed, 59 skipped; CLI (GPU hidden) 1217 passed, 1 skipped. `describe_api`'s assembly page was held under its 21,500-char budget by trimming three restating notes, not by raising it [rec: dusty-meadow-8719].
- **Ledger**: `docs/probes/orun5/LESSONS.md` W1–W12 maps every reference workaround to its replacing criterion; W4, W5 replaced by ADR-587 [rec: dusty-meadow-8719].
- **Not done**: the base-guidance rule on stating a motion as a predicate (left to the long-term guidance rung) [rec: dusty-meadow-8719].

## Negative knowledge

- [scope: evaluation rigs with free payloads | confidence: medium | evidence: dusty-meadow-8719] `evaluation_rig` refuses two free bodies (`evaluation_base_ambiguous`) and reads a lone free ball on a grounded plate as "the base"; harmless unless a spec bounds posture metrics. Stated by the implementer, not tested [rec: dusty-meadow-8719].
- [scope: describe_api assembly page | confidence: high | evidence: dusty-meadow-8719] `describe_api`'s assembly page has ~0–200 chars of headroom; each further surface addition must trim or page it [rec: dusty-meadow-8719].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-m1-predicates-measure-motion-not)
- dusty-meadow-8719 — M1 motion predicates landed (ADR-587) with the orun5 workaround ledger
