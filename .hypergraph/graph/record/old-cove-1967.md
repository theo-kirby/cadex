---
node_id: 6092af94-a5b8-588d-a098-812122087c9e
slug: old-cove-1967
title: 'ot11 P1: the film follows the evaluation''s base and the blind video judge is run; w2-2 and Robin both miss the bar on all three judged seeds (ADR-460)'
created_at: '2026-09-30T12:38:15+00:00'
parents:
- mild-horizon-5182
summary: ''
---
## What

The blind video judge now exists and has been run on both known negatives, and the film it is shown follows the evaluation's base as the frozen contract says (ADR-460, commit `81873196`).

- **The film follows the base.** `cli/cadex_cli/film.py`'s detail sheet is centred on the base the evaluation measured (`rig.base`) in every frame, wide enough to hold the whole design, and side-on is measured on that body's travel. A mechanism with no floating base gets one fixed window. A base that is not a drawn solid is refused. The product changed; the contract did not.
- **The judge runner.** `docs/probes/ot11/runner/judge.py`: a fresh `claude -p --model claude-opus-5-5` process per call, no fallback, effort `high`, in an empty directory outside the repo, with one tool (`Read`) and no MCP, skills, user settings or session. It is given pinned instructions plus the rubric byte for byte, then the intent paragraph and one seed's two sheets. The sheets are read through `evaluation.json` and checked against its digests.
- **Both negatives were filmed again and judged** on seeds 1101, 1105 and 1110, three calls a seed. Six receipts are committed under `docs/probes/ot11/retained/judge-*.json`.
- **Docs and pins.** `docs/probes/ot11/README.md` (the procedure, the re-film, the scores and two diagnosed differences), `contract.json` (`judge_procedure`, `known_negatives.judged`), `docs/CLI.md`, `docs/DECISIONS.md` ADR-460.

## Why

Target: frontier node `rough-shore-6557` (P1). The critic's message named this unit in three steps, and all three were done as asked:

1. settle the film deviation in the product, with a regression test and a re-film, not by amending the contract;
2. build the judge runner under `docs/probes/ot11/runner/`;
3. run it on the three judged seeds of `w2-2` and Robin and commit the receipts.

No deviation from the message. P3 was not started.

## Method

- **Film.** Added `_Stage.centre`, gave `travel_azimuth` and `detail` a `base` argument, and passed `report["rig"]["base"]` from `film_evaluation`. Three new tests in `cli/tests/test_film.py` fail on the old module: a design whose base walks away from a part left behind, a grounded mechanism, and a base that is not drawn.
- **Re-film.** `cadex evaluate --film-only --film 1101,1105,1110` on `ot11-w2-negative` (with `--detail-start 5.0 --detail-step 0.04`) and `ot11-robin-negative`. No new rollout. The `film` block of each retained receipt was replaced and nothing else in it changed.
- **Judge.** Modelled on ot10's runner. `cli/tests/test_ot11_judge.py` (16 tests) calls no model: it runs the runner end to end against a stand-in executable and holds the six committed receipts to what the runner computes from their own calls.
- **Judging.** Eighteen real calls, 162 s of model time, $0.73 at list price. My first launch of the Robin chain failed in the shell before any call was made (an unset interpreter variable, exit 126). No model was called and nothing was written, so it is not an attempt. Each seed was judged exactly once.
- **Suites.** `pixi run python -m pytest cli/tests`: 1211 passed, 1 skipped. `pixi run test-engine`: 2439 passed, 53 skipped. No engine, protocol or payload file changed, so the packaged gate was not run.

## Result

**Neither known negative meets the judge's bar on any judged seed.** Medians of three calls, each trait 0 to 3, bar is a total of 9 with no trait under 2:

| policy | seed | V1 task | V2 manner | V3 control | V4 consistency | total |
|---|---|---|---|---|---|---|
| `w2-2` | 1101 | 1 | 2 | 0 | 1 | 4 |
| `w2-2` | 1105 | 1 | 1 | 0 | 1 | 3 |
| `w2-2` | 1110 | 1 | 2 | 0 | 1 | 4 |
| Robin | 1101 | 0 | 1 | 0 | 1 | 2 |
| Robin | 1105 | 1 | 1 | 2 | 1 | 5 |
| Robin | 1110 | 0 | 1 | 0 | 1 | 2 |

Every call returned a score. None was refused, retried or answered by another model. The three calls agreed on every trait of every seed except Robin 1105's V2 (1, 2, 1).

**The re-film.** Every overview sheet is byte for byte what it was. The detail half-width went from 140–148 mm to 161–174 mm on the quadruped and changed by under 1 mm on Robin.

**P1's listed parts all now exist**: the frozen specs, seeds, pass rule, judge and bar; both negatives measured against the predicates and judged. I believe P1 is met and do not tick it.

**Concern 1: the judge does not see the shuffle.** It fails `w2-2` because it falls, not because it shuffles. On seeds 1101 and 1110 every call scored manner 2 and described "real steps". Those seeds measure 8.5 % and 3.6 % of a foot's path made in steps (W5, limit 70 %) and 60 % and 81 % made sliding (W7, limit 15 %). Twelve frames 0.04 s apart, in a window that follows the base, do not show a planted foot moving across the floor. A shuffle that stayed upright could plausibly meet the bar. The frozen pass rule already requires the predicates and the bar together, so nothing frozen was changed. If the judge is wanted as an independent check on stepping, that needs a recorded contract decision (for example a detail window fixed to the floor), and it re-judges everything.

**Concern 2: a fall no termination reported.** On `w2-2` seeds 1101 and 1105 the judge reports the robot down and still from about 8 s and 6.4 s. The traces agree: the base goes to 42° and stops moving. The w2 task's own `tipped` termination did not fire, so W1 passes on both; W2 fails on both (43.6° and 43.7°). The contract reads the fall; a product agent's task termination may not.

**Assumptions taken.**
- Side-on is measured on the base's travel over the whole episode, as ADR-459 measured it on the design. The contract's own "forward" (the base's +X) was not used: Robin's +X is its wheel axle, so that view would have been front-on.
- The judge's effort (`high`) and its five-sentence instructions are not in the frozen `judge` block. They are pinned beside it as `judge_procedure`, before any ot11 policy was judged. The contract's `decisions` list still has one entry.
- The judge is shown the two sheets as two images, not twenty-four separate frames.

**Still open from earlier.** A reach frame's target marker is not drawn until a trace carries a goal (P3). P2 stays open until a product spec can state a goal.

No new dependency. Nothing removed. The unreconciled tail is this one record.

Dispatch closed: 1 unit — the film follows the evaluation's base, the blind video judge runner exists, and both known negatives were judged on seeds 1101/1105/1110 with neither meeting the bar (ADR-460).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot11
- commit: 81873196ce71a28afb227614bb5445c73d56caf7

## State Impact

- target: rough-shore-6557 — P1's listed parts all exist; the actor believes the criterion is met and does not tick it. The blind video judge runner is docs/probes/ot11/runner/judge.py (ADR-460, commit 81873196): a fresh claude-opus-5-5 call with no fallback, effort high, in an empty directory with one tool, given pinned instructions plus the rubric byte for byte, the intent paragraph and one seed's two sheets read through evaluation.json and digest-checked; a refusal, harness error or other model's answer writes no score. Run on seeds 1101/1105/1110, three calls each, all eighteen scored: w2-2 totals 4, 3, 4 of 12 and Robin 2, 5, 2, so neither negative meets the bar (9, no trait under 2) on any seed; receipts docs/probes/ot11/retained/judge-*.json, held by cli/tests/test_ot11_judge.py. Two diagnosed differences, no frozen item changed: the judge fails w2-2 for falling and scores its manner 2 on seeds 1101 and 1110 where W5 and W7 measure a shuffle (the detail frames cannot show slip), and it saw falls on w2-2 seeds 1101 and 1105 where the task's tipped termination did not fire while W2 failed at 43.6 and 43.7 degrees. The procedure is pinned as contract.json judge_procedure beside the untouched judge block.
- target: damp-flame-5523 — no status change. The evaluation film's detail sheet now follows the base the evaluation measured (rig.base): the window is centred on it in every frame and holds the whole design, side-on is measured on its travel, a mechanism with no floating base gets a fixed window, and the block's follows names it (cli/cadex_cli/film.py, ADR-460, commit 81873196; three regression tests in cli/tests/test_film.py fail on the old module). Both negatives were filmed again with no new rollout; every overview sheet is byte-identical and the receipts' film blocks alone changed. The reach target marker is still not drawn until P3.
