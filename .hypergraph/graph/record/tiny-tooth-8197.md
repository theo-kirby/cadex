---
node_id: e364fa0e-e54c-5b70-a6df-ac24f8526d9b
slug: tiny-tooth-8197
title: 'The D6 evidence handoff: iterations 12–13 (ADR-336) recorded against D6 — Finch''s stand task declared, one bounded GPU run measured over ten seeds, checkpoint and final videos in the new look, the recorder taking a real tessellation; the CLI suite run and the false preserved-records claim corrected'
created_at: '2026-09-14T01:20:44+00:00'
parents:
- loyal-canyon-4623
summary: ''
---
## What

The two iterations after the free-base unit, recorded late: iteration 12 (commit `e626d9ea`) and iteration 13 (commit `0a5bce13`), together the D6 evidence unit (ADR-336), plus this iteration's repair of one false sentence in that evidence. Finch's stand task is declared in its script as data (400 steps at 50 Hz, fall below 84.0 mm pelvis height, seeds 0–9, reset variation on `pelvis_link`), accepted as revision `a3dc4e9a0f84…` with `cadex script --set`. The recorder (`cli/cadex_cli/video.py`, `review_scene.js`) takes a real tessellation: Finch's 29 solids are 95 212 triangles against a 20 000 cap sized for Lark's boxes, so the page now fetches each retained solid over the loopback server and computes the per-frame bounds and the follow track in the scene module; the cap is 500 000, pinned by `test_video.py` on a 27 652-triangle run. One bounded real GPU run, `finch1` (`docs/probes/ot6/finch/train.py`, 240 PPO updates on 1024 environments, checkpoints every 20, `MemoryMax=20G`, `timeout 3600`): exit 0 in 2048.7 s, host peak 9.72 GB, GPU peak 15 695 MiB. `evaluate.py` rolled each retained policy over seeds 0–9 in scratch projects; `report_training.py` wrote `training.json` (14.3 KB) and one decoded frame per video. Measured: **checkpoint 20 fell on 10/10** at 0.20–0.34 s (x displacement −60.2 mm mean); **the final policy stood the full 8 s on 10/10** and shuffled +361.1 mm mean (319–433). Both videos are `cadex-prototype-dark-v1` with the identity strip `tessellated solids of the accepted revision; collision proxies not drawn`, browser-checked on the persistent dashboard — the checkpoint's at trainer update 54 with the trainer active (update-interval medians 4.934 / 4.909 / 4.949 s before, during and after the 3.47 s render), the final's after `done`, where a fresh visit selects `finch1-final`. The receipt is pinned by `test_finch_training_receipt_measures_the_real_biped_in_the_new_look`.

The repair: the README said "the D5 run records that preceded training are unchanged (their digests are in the driver's result)". No run record existed before `finch1` — D5 and ADR-335 accepted revisions and wrote `evidence/`, never `runs/` — so the driver's preservation check ran over an empty set (`preserved_records: {}`). The README now says so, `report_training.py` and `training.json` carry the same note in place of `unchanged_verified_by_driver: true`, and the focused test still passes.

## Why

The critic's first item for iteration 14: "Record iterations 12–13 causally against dusty-otter-7562, including required CLI-suite results and graph verification. Correct Finch README's claim of preserved D5 run-record digests: the driver reports preserved_records={}." Iteration 12 was rejected (a test read a receipt that did not exist; ADR-336 carried a `<<RESULTS>>` placeholder) and iteration 13 repaired both but neither iteration minted a record, so the D6 evidence was invisible to the graph. This record is that handoff, parented on the free-base unit the training followed from, and it carries the CLI-suite run this iteration made (iteration 12 changed CLI code and iteration 13 ran only the focused test).

## Method

1. Read both critic verdicts, both commits' diffs, ADR-336, the README, `train.py`, `report_training.py` and `finch1-experiment-result.json` (`preserved_records: {}`, `runs/` holding only `finch1*`).
2. Corrected the README paragraph, the generator's `earlier_run_records` row and the committed receipt's same row by hand (the generator would otherwise re-read the live dashboard and change `served_at`); the receipt stays at 14 275 bytes under the 16 KB cap.
3. Ran `cli/tests/test_review_design.py -k "finch or caps"`: 56 passed. Ran the full CLI suite in the background while the D7 unit started: `pixi run python -m pytest cli/tests` **557 passed, 1 skipped** in 526 s (exit 0), with the product agent's balancer turn and the engine running concurrently.
4. `hypergraph export` + `hypergraph check` after minting: `hypergraph check` exit 0 before minting, the mint's own checker on this node, and export + check re-run before the commit.

## Result

What is true now: D6's evidence list is complete pending the owner's tick — task declared, one bounded real GPU run measured over ten seeds, checkpoint and final videos in the D3 look on the operator dashboard, the stand bar met by the final policy and failed by the checkpoint, both measured — and the receipt no longer claims a preservation it did not check. The persistent operator unit serves `ot6-finch` at accepted revision `b68622345563…` with `finch1-final` selected on a fresh visit.

Concerns the next iteration must know: the trainer's own running episode-length estimate at the last update (211 of 400 steps) and the ten CLI rollouts' 400/400 are different measurements and the receipt records both without reconciling them; the driver's own checkpoint publication failed at the old triangle cap and the hand render on the fixed recorder stands in for it, as the receipt says; the final policy's forward shuffle is a stand-task behaviour, not a walking result. No new dependency.

Dispatch closed: 1 unit — the D6 evidence handoff: iterations 12–13 (ADR-336) recorded against D6, the CLI suite run, and the false preserved-records claim corrected in the Finch receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 0a5bce134fcdbcef06013a9d4905e171a1f18570

## State Impact

- target: dusty-otter-7562 — blocked→working: evidence list complete pending the owner's tick (ADR-336, commits e626d9ea and 0a5bce13, receipt docs/probes/ot6/finch/training.json): task declared as revision a3dc4e9a0f84…, finch1 exit 0 in 2048.7 s under MemoryMax=20G, checkpoint 20 fell 10/10 at 0.20–0.34 s, final policy stood 8 s on 10/10 with +361 mm mean shuffle, both videos cadex-prototype-dark-v1 on the persistent dashboard which selects finch1-final; the receipt's preserved-records row corrected to say no run record preceded finch1
- target: chilly-union-8972 — the recorder fetches each retained solid over the loopback server and computes bounds and the follow track in the scene module; the triangle cap is 500 000 (was 20 000), pinned by test_video.py
