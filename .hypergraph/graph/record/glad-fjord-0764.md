---
node_id: ff7b4097-7cb8-5795-a98c-a76df685cf57
slug: glad-fjord-0764
title: 'ot11 P2: a success spec states its own randomisation; w2-2 and Robin re-measured on the mechanism as built, both 0 of 10 (ADR-458)'
created_at: '2026-09-30T10:32:24+00:00'
parents:
- misty-timber-4175
summary: ''
---
## What

`assembly.success` states its own randomisation (ADR-458), and both known negatives are re-measured on the contract's conditions with it switched off.

- **Engine.** `assembly.success(..., randomisation=...)` is a third condition beside `reset_variation` and `disturbance`, on the same terms: omitted is the task's own, `[]` is none, a list is `assembly.randomise` values. The bundle's `success` block carries it resolved; `evaluation_task` hands it to the episode loop; the evaluation report's `spec` block states the randomisation that was played.
- **Known negatives.** `ot11-w2-negative` and `ot11-robin-negative` now declare `randomisation=[]` in their specs. Both were rebuilt and re-evaluated with `cadex evaluate`, and the two `p2-*` receipts under `docs/probes/ot11/retained/` were replaced.
- **The correcting row.** `ot11-w2-negative`'s `PROGRESS.md` has a new `correction` row marking the 09:09:43Z evaluate row (W1 9 of 10, W6 3 of 10) as superseded by the per-seed fix. The old row is kept.

## Why

Target: frontier nodes `damp-flame-5523` (P2) and `rough-shore-6557` (P1).

The critic's message asked for four things: the correcting row, the randomisation condition with both re-evaluations and an ADR ("do this first"), then the filmstrip, video and dashboard view, and a full CLI suite run. **I did the first two and the suite run, and did not do the filmstrip, video and dashboard view.** The loop allows one unit per iteration, and the critic ordered the randomisation condition first because the filmstrips must show contract conditions. The filmstrip, video and dashboard are the next unit, unchanged.

## Method

- Followed the pattern the other two conditions already have, end to end: the API value, the worker's conversion to model names, `_success_records` resolving through the same `_randomisation_records` a task uses, and `evaluation_task` substituting it.
- Moved `api.task`'s inline randomisation-against-assembly check into `_check_randomisation` and called it for both lists. `api.task`'s behaviour is unchanged.
- Kept `cadex-success-spec-v1`. A bundle without the key is played on its task's randomisation, as it was when written; a test pins that.
- Confirmed the new tests fail on the old source: with the three engine files stashed, 6 tests failed (5 new, 1 extended).
- Rebuilt and staged the engine (again after each later engine edit), edited each copy's script through `cadex script --set`, and ran `cadex evaluate` on each.
- **Agreement gate.** Robin's task never randomised, so `randomisation=[]` must change nothing: its ten seed rows are identical to ADR-457's receipt, field for field (trace digests aside, because the task bundle's digest is in each trace).
- The first re-evaluation showed the report's `spec` block did not list the randomisation. I added it (as played), rebuilt, and ran each evaluation once more. The seed rows of the second run are identical to the first. These are evaluations of known negatives, not confirmation evaluations.

## Result

True now:

- A success spec can switch off, keep or replace a task's randomisation. The task's semantic digest does not move, so no policy is orphaned.
- **`w2-2`, mechanism as built (`ot11-w2-negative`): 0 of 10 seeds pass.** W5 (fewest steps 0 to 3 against ≥ 4; step share 0.00 to 0.08 against ≥ 0.70) and W7 (slip 0.49 to 0.81 against ≤ 0.15) fail on **all ten**, as do W9 and W10. W2 fails on eight. `tipped` fires on two (1107 at 6.26 s, 1110 at 6.32 s).
- **These are different episodes from ADR-457's.** The mass draw came first in each seed's stream, so removing it changed each seed's start and shove. Three things moved with it:
  - W6 now passes on six seeds (it failed all ten before).
  - No seed "sits back and travels under 5 mm/s"; the slowest moves at 47 mm/s.
  - The seed the reward paid most is 1109 (836.0), not 1104. Its least-stepping foot took one step.
- **Robin (`ot11-robin-negative`): 0 of 10, numbers unchanged.** B3, B4 and B5 fail on all ten; `fallen` on six.
- No seed was void on either. Both receipts state `spec.randomisation == []` and every seed drew none; `cli/tests/test_ot11_contract.py` pins that.
- The frozen contract text is unchanged. Only the measured section of `docs/probes/ot11/README.md` was rewritten.

Evidence, at commit `21e368e6`:

```
pixi run test-engine
  2439 passed, 53 skipped in 330.44s (0:05:30)
CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest \
    cadex_tests/test_cadexd_lifecycle.py cadex_tests/test_success_spec_live.py
  27 passed in 21.88s                      (after build-engine and stage-engine)
CADEX_ENGINE_ROOT=<the same payload> pytest cli/tests/test_evaluate.py cli/tests/test_smoke.py \
    cli/tests/test_client.py
  60 passed in 21.47s
pixi run python -m pytest cli/tests -q
  1147 passed, 1 skipped in 840.73s (0:14:00)
```

- **The first full CLI run at this unit failed one test**, and the failure was mine: `test_client.py::test_every_page_of_the_live_contract_fits_one_tool_result`. The new keyword put the `assembly` page of the model's `describe_api` view at 21,532 characters against a 21,500 budget (ADR-360). I did not raise the budget. I deleted the assembly notes' closing sentence in `CadexScriptedRuntime.py`, which states no rule of the surface; the page is now 21,411. All four commands above were run again after that edit, on the committed tree, and those are the figures shown.

- The payload's `CadexDynamics.py` is byte-identical to the source.
- The 53 engine skips are the standing ones (MJX-gated, platform); I did not inspect them individually.

Concerns and assumptions for the next iteration:

- **P2 is still open.** Missing: the filmstrip and rollout video on the dark floor from the per-seed traces, and the review dashboard's view of `evaluation.json`, with tests. Filmstrip PNGs at most 300 KB each under `docs/probes/ot11/`; no videos or traces committed. Then the blind judge on the two negatives, then P3.
- The per-seed traces the filmstrip should read are in `evaluations/064d8d7cd34c-7a4e8c233214/` (w2) and `evaluations/3a42fdec8b94-ef71f370a2f1/` (Robin). The older `evaluations/60f655537c0b-*` directory in the w2 copy is the superseded drawn-mass reading; do not film it.
- Each copy's `PROGRESS.md` has two identical evaluate rows from this iteration (before and after the report's `spec` block gained `randomisation`).
- **The `assembly` API page has 89 characters of budget left**, and its notes do not mention `assembly.success` at all. P3 (goals) and P4 (agent guidance) both add to this surface and will not fit. Cutting the notes properly, or splitting the section, is a unit of its own and should come before P3's API lands.
- A spec for R1–R3 should state its randomisation explicitly. One that inherits it changes its evaluation conditions whenever the training randomisation is revised. Nothing enforces this; the agent guidance for P4 should say it.
- `cli/tests/test_evaluate.py` does not assert on `spec.randomisation`; the engine tests and the contract test do.
- Carried from ADR-457, unchanged: W3, W4's lateral half and Q1–Q4 wait on a goal (P3); `apply_randomisation` still writes into the compiled model for any caller that reuses one; nothing prunes the ~6 MB per-seed traces; the trainer does not refuse an evaluation seed as `--seed`.
- The unreconciled tail is two records after this one.

No new dependency. No protocol change. One removal: the notes sentence above, logged in ADR-458.

Dispatch closed: 1 unit — a success spec states its own randomisation (ADR-458); w2-2 and Robin re-measured on the mechanism as built, both 0 of 10, w2-2 failing W5 and W7 on every seed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 21e368e6dd66395845b104f6a3cbd37e7e9c4b8e

## State Impact

- target: damp-flame-5523 — still open. assembly.success now takes randomisation= on the terms of its other two conditions (omitted is the task's own, [] is none, a list replaces it); the bundle's success block carries it resolved, evaluation_task plays it, and evaluation.json's spec block states the randomisation played (ADR-458, commit 21e368e6). The task's semantic digest does not move; a bundle without the key plays its task's randomisation. The earlier limit 'the spec cannot switch off a task's randomisation' is gone. Still missing under P2: the rollout video and filmstrip on the dark floor, and the review dashboard's view of the report. The assembly page of the model's describe_api view is 21,411 of 21,500 characters after one notes sentence was deleted to fit, and the notes do not mention assembly.success.
- target: rough-shore-6557 — no status change. Both known negatives are re-measured through the product with randomisation=[] in the spec, as the frozen contract lists none (receipts docs/probes/ot11/retained/p2-*.json replaced, commit 21e368e6). w2-2 on ot11-w2-negative passes 0 of 10 and fails W5 (steps and step share) and W7 on all ten, with W9 and W10; W2 fails on eight, tipped fires on 1107 and 1110, and W6 now passes on six. These are different episodes from ADR-457's drawn-mass reading, which is superseded: no seed sits still, and the best-paid seed is 1109 (836.0) with one step on its least-stepping foot. Robin on ot11-robin-negative passes 0 of 10 with numbers identical to ADR-457's: B3, B4 and B5 fail on all ten, fallen on six. The contract text is unchanged. The judge has still not run.
