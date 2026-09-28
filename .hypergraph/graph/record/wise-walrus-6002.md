---
node_id: 1d9bc666-059f-5071-a924-c1bf76c1a9af
slug: wise-walrus-6002
title: 'ot10 biped attempt: every fit gate passes (first complete swept fit) but the design cannot reopen, so it is unscored; cause is face-area drift in the ADR-389 fingerprint'
created_at: '2026-09-28T00:06:08+00:00'
parents:
- fresh-timber-5181
summary: ''
---
## What
Ran the frozen A5 biped cold prompt once on a new project, `ot10-biped-1`, with the sweep left to the agent and ADR-419/420 in place. The design passes every fit gate. It is **not scored**: the product cannot reopen its own accepted design, so `cadex render` refuses it. Diagnosed the cause to one kernel measurement and published the receipt in `docs/probes/ot10/README.md` (commit `4bc30c71`).

## Why
The critic's message asked, as this unit: run the frozen biped prompt on a new `ot10-biped-*` project with the sweep on, record flags, model and effort, then score it blind and publish it, pass or miss. The first half is done. The blind score is not, because the render the judge must see could not be produced. I did not bypass the product with an off-product renderer, since A5 requires the design to be "rendered by A2". I also did not fix the engine in this iteration: that is a separate unit, with its own regression, ADR and packaged gate, and the charter asks that a miss be recorded and diagnosed before the next tool change. The design is unchanged by any such fix, so it can be scored as the fix's replay (the ADR-420 pattern).

## Method
- Launch: `CADEX_EFFORT=medium ./cadex --project ~/cadex-projects/ot10-biped-1 --model claude-opus-5-5 -p "<contract.json a5.prompts.biped, verbatim>" --json`.
  - Detached with `setsid nohup`, from revision `2bdafcee`, at 2026-09-27T23:25:23Z.
  - stdout and stderr went to `~/cadex-projects/ot10-notes/biped-1/`, outside git.
- The turn ended on its own at 23:59:53Z (34 min 30 s), exit 0. It was accepted at revision `44b8497b…`, digest `10e2fd59…`, with project commit `48c994f`.
- Fit and inventory come from turn.json:
  - static fit: 1,275 pairs clear, 0 intersections; the one failing row is the floor's advisory world-geometry row;
  - attachments: 43 pairs touching;
  - sweep: `coverage: complete`, 6/6 joints at 15° steps, `verdict: pass`, 0 failing pairs, 6 floor contacts listed as advisory `world_geometry`;
  - P2: 2,610.9 / 38,132.6 mm = 0.068;
  - P3: 3 (`#2B2F36`, `#E9E4D8`, `#F26A1B`);
  - electronics: ESP32, PCA9685, BNO085, D36V50F6, 2S LiPo, 6 × MG90S, 6 horns, 12 × M2×6.
- `pipeline.sh` (a copy of the quadruped's) failed at `cadex render` after 1 min 45 s with exit 1 and `CADEXD_RESTORE_FAILED`: "The restore pass digest does not match the accepted digest".
- Reproduced on a copy under /tmp through `open_project restore=true`. The `observed` field said `geometry_comparison: the rebuilt model is not the accepted one`, with a different byte digest and a different geometry digest.
- Diffed the per-output definition hash and `brep_geometry_fingerprint` across the three retained attempts of the one revision, under FreeCADCmd.
  - Exactly one of 127 outputs differs: `src_hood` = `part.fillet(edges=all, skip) ∘ part.cut(refine=true) ∘ part.fillet(part.box)`. There is no `part.offset` in it.
  - Its vertex set, sorted edge lengths, counts and bounding box are bit-identical across processes.
  - Face order differs. In the sorted face-area multiset exactly one value differs: a 16-edge plane, 114.68601535158916 against 114.68601535158984, a difference of 6.8e-13 mm².
  - Total area differs by 7.3e-12. Volume differs in the last digits, which ADR-389 already excludes.
- A4 refusal count comes from `refusals.py` on the session transcript, with each refusal read by hand.
- Tests: `cli/tests/test_ot10_contract.py` 13 passed; `cadex_tests -k "ot10 or sharp_edges"` 3 passed.

## Result
- **ot10-biped-1 has a complete, passing swept fit.** It is the first A5 design in the run to have one, and it also passes static fit, attachments, P2 (0.068) and P3 (3) and carries its electronics.
- **It has no judged score, no P1 and no committed renders, because it cannot be reopened.** It is published as unscored, not as a miss and not as a pass. No score was invented.
- **Product defect (engine, open):** ADR-389's `shape_geometry_fingerprint` (`src/Mod/cadex/CadexGeometryDigest.py`) hashes exact face areas and the total area. A face made by `part.cut(refine=true)` drifts in the last bits of its area between processes, so any design with such a face passes its own turn and then refuses every reopen, render, `look` and review.
- **Recommended next unit:** drop face areas and total area from the fingerprint by measurement, as ADR-389 dropped volume.
  - Keep the counts, the exact vertex set, the edge-length multiset, the bounding box and the recipe.
  - Bump the geometry-digest schema, and have `_remembered_geometry` ignore a digest learned under the old schema, so it re-measures rather than refuses.
  - Regression: two fake shapes that differ only by one face area in the last bits. It must fail before the change.
  - Replay: render ot10-biped-1 and score it blind. The packaged lifecycle gate follows.
- **Second, smaller defect:** a failed restore leaves `script.json` `latest_candidate` naming the restore attempt with `status: accepted`. I reverted it by `git checkout` in the project, which is the product's own commit. Nothing about the design changed.
- **A4:** none of the four refusal classes recurred. There were 7 refusals: the `write_script` output guard, a `dir` sandbox refusal, a fillet without `expected_count`, a partial-radius fillet, a reset-lift refusal, and two linked-output retire refusals.
- **Critic's follow-ups still pending:** the P2 `c_floor`/`floor` exclusion as a recorded proxy decision (floor is in this design's measured set too), and re-running the hexapod and quadruped with the sweep on.
- The unreconciled tail is now 2 nodes.

Dispatch closed: 1 unit — ran the frozen biped A5 prompt (ot10-biped-1): all fit gates pass including a complete swept fit, but it is unscored because the restore's geometry fingerprint refuses a last-bit face-area drift

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 4bc30c71d33ee35244b70eda69f30a71eea0936f

## State Impact

- target: loyal-fountain-8709 — biped attempt ot10-biped-1 accepted with complete passing swept fit (6/6), P2 0.068, P3 3, electronics carried; unscored because cadex render refuses to reopen it
- target: forest-wind-0342 — defect: ADR-389 geometry fingerprint hashes exact face areas; a part.cut(refine=true) face drifts 6.8e-13 mm² between processes, so an accepted design can refuse every reopen
