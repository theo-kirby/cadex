---
node_id: 02cd06f3-b977-5ec4-ace6-d08c1864c120
slug: dusty-meadow-8719
title: 'ADR-587: motion predicates (turns, laps, distance about a centre); orun5 workaround ledger'
created_at: '2026-10-07T18:25:08+00:00'
parents:
- honest-bay-2056
summary: ''
---
## What

M1's predicates landed (ADR-587, commit `46b57d1d`), with the orun5 workaround ledger's skeleton (`docs/probes/orun5/LESSONS.md`).

- `CadexEvaluation` gains a fourth metric family, **motion**: `turns` (net signed turns of a body about an axis through a centre, frame-to-frame bearing changes wrapped to ±½ turn), `laps` (`floor(|turns|)`), `final_distance_mm`, `mean_distance_mm`, `max_distance_mm`. All need only `body`; none needs a goal.
- `assembly.success(body=, body_offset_mm=, centre=, centre_mm=, centre_axis=)`: the centre is fixed in a component's frame (world when omitted) and is carried by that frame at every trace frame. The worker resolves it, `_success_records` checks the `body` need (`success_metric_needs_body`), `evaluation_rig` checks the body and frame exist (`evaluation_body_missing`), and `evaluate_success` traces both. A spec without `body` is byte for byte the block it was, so no task digest moves.
- An episode that did not run to its horizon measures no motion metric (`None`, which `check` fails, as ADR-586 does); what was played stays in `detail.motion` with `partial: true`.
- The ledger has 12 rows, W1–W12, covering every workaround in both reference projects, each with the project ADR or file it comes from and the criterion that replaces it. W4 and W5 are now marked replaced by ADR-587. W6 and W11 were replaced by ADR-586 and ADR-585 in orun4.

## Why

The critic named short rung 1 (read both references and write the ledger) and asked for M1 in the same iteration if possible, because M1 unblocks P1's spec. Both were done. The ledger is a page of evidence with no code in it, so this record treats the two as one unit: M1, plus the ledger it is justified by.

## Method

I read both reference projects end to end: `DECISIONS.md`, `docs/*.md` and `PROGRESS.md`. I did not re-read the run directories, because the ADRs carry their numbers. The `tip` slot was not reused, because `evaluation_rig` refuses a tip that no actuated joint moves (`evaluation_tip_is_not_driven`), and a free ball is exactly such a body. So a separate `body` was added. Tests:
- `test_evaluation_motion.py` has 7 fast unit tests: circling 3 laps passes `laps ≥ 2`; rocking on the same arc reads |turns| < 0.05 and fails it, while still passing `final_distance_mm` in [30, 50] (the failure the ball-plate's circle-6 run hit); an early end with 50, 1 or 0 frames fails every motion predicate without raising; turns are signed and the axis flip reverses them; distance is read with no goal; a ball circling on a plate that tilts 10° and spins reads 2.0 turns in the plate frame, and a ball held still on that plate reads 0 turns in the plate frame and >2 in the world frame.
- API and model tests cover what the spec carries and what it refuses: a centre with no body, a zero axis, a component outside the assembly or the model, a motion metric with no body.
- One real-MuJoCo evaluation (`test_evaluate_success_model.py`) measures a resting block about a centre beside it and confirms the frame is traced.
- `test_the_vocabulary_is_exactly_what_the_families_measure` was extended to cover the motion family.

The five new keyword arguments pushed `describe_api`'s assembly page to 21,701 characters, over the 21,500 budget (ADR-360). I cut three sentences from the assembly notes in `CadexScriptedRuntime.py`, each a restatement of a docstring or a refusal: that a script may declare several `assembly.mjcf`s (the `mjcf` docstring says so), that a script may declare several policies, and that two channels producing one name are refused (the refusal says so). The budget was not raised.

## Result

- `pixi run test-engine`: **2632 passed, 59 skipped** (5:48).
- `pixi run build-engine` ran, then the CLI suite (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`): **1217 passed, 1 skipped** (7:54).
- No op, protocol, tool or payload change, so the packaged gate was not needed.

M1 now has evidence for each of its test claims: circling passes, rocking fails, and an early end fails without crashing. It also has spec bounds, ADR-587 and docs (`docs/XSCRIPT.md` metric table and argument paragraph). Not done:
- the base-guidance rule on stating a motion as a predicate is left to the long-term guidance rung;
- `docs/MUJOCO.md` holds no metric table, so it was not touched.

Concerns for the next iteration:
- **Two free bodies are refused by `evaluation_rig`** (`evaluation_base_ambiguous`). A free ball on a *grounded* plate is one free body and will be read as "the base". Its posture metrics are then about the ball, which is harmless unless a spec bounds them. A free ball on a free-standing machine would be refused. P1 will meet this, so check it before writing P1's spec.
- The assembly page of `describe_api` has about 0 to 200 characters of headroom. S1, S2, L1 and R1 will all add API surface, so expect to trim notes again or page the section.
- Next by charter priority: S1, the grounded position sensor.

The tail holds 1 unreconciled record.

Dispatch closed: 1 unit — M1 motion predicates (turns, laps, distance about a centre; ADR-587) plus the orun5 workaround ledger skeleton

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 46b57d1da3562d411c95f5366e6c69dbc89a6914

## State Impact

- target: falling-walrus-2752 — Motion family landed (ADR-587, 46b57d1d): turns, laps, final/mean/max distance of a success-spec body about a centre carried by a component frame; early-ended episodes unmeasured; circling passes, rocking fails, early end fails without crash; both gates green. Guidance rule pending (long-term rung).
- target: peaceful-orchard-2220 — P1's spec can now bound laps and distance from the plate centre without a point goal (ADR-587); caveat: evaluation_rig reads a lone free ball as the base.
