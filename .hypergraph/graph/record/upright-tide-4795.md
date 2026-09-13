---
node_id: c200e506-73ce-5107-b1e7-95e35347d6be
slug: upright-tide-4795
title: Run Lark's first bounded real GPU training on the persistent dashboard with checkpoint and final videos
created_at: '2026-09-13T07:07:25+00:00'
parents:
- soft-forest-5662
summary: ''
---
## What

Lark's first bounded real GPU training experiment, `lark1`, on the persistent private-network operator dashboard: 240 PPO updates on the accepted product-agent design, the live page observed updating without reload, checkpoint 20 published as a witness-verified rollout with a browser-verified video while the trainer was still active, and the final policy recorded with a verified, downloadable video. Committed as `acaabde2`.

## Why

The critic asked that, after recording iteration 81, the next unit start Lark's bounded real training probe, verify live updates on the persistent dashboard, and carry it through checkpoint recording and final review — the ladder's rungs 4 and 5 and medium-term rung 1 for the clean-project repeat, advancing D3, D4, D9 and D10 with real artifacts rather than another audit. Iteration 81's record (`soft-forest-5662`) was written first, with the actual gate results from both suites run on its committed tree.

## Method

`docs/probes/lark-fresh/train.py` is the Wren driver with nothing named after Wren: the model, task and policy outputs are discovered from the CLI's own envelopes by kind (`assembly_mjcf_xml`, `assembly_training_task_json`, `assembly_policy_receipt_json`), the one policy declaration substitution is asserted, and the project-agnostic `observe.py` and `check_video.py` beside the Wren driver are reused by path. `docs/probes/wren-fresh/summarize_training.py` takes the receipt schema as an optional third argument and finds the torso as the one traced component named for it (`c_torso` on Wren, `torso_link` on Lark); Wren's committed receipt regenerates byte-identically. Bounds unchanged from `wren1`: 240 updates, 1024 environments, seed 0, checkpoints every 20, `timeout 1800`, a `MemoryMax=20G` user scope, the existing `~/cadex-train-venv`; no new dependency. Both gate suites were run to completion on the committed tree *before* the GPU run so the two never overlapped. The compact receipt `docs/probes/lark-fresh/training-evidence.json` is guarded by a new test in `cli/tests/test_lark_fresh_evidence.py`; the probe README, `docs/HEADLESS-BIPED-REVIEW.md` and the operator status README were updated.

## Result

`lark1` exited 0 on the GPU after 240 updates in 1,052 s of wall clock (ordinary updates 1.34 s median; eleven checkpoint exports at 54–58 s each account for 694 s), sampled host peak 9.33 GB under the 20 GB cap, GPU peak 15,152 MiB. Training identity: revision `ebe0f62df802…` (explicit `policy_on=0`) at the creation digest `3b704a3fc1c4…`, model `7e24cabd622d…`, task `402cca3b869d…`. D3: a fresh visit to the persistent URL selected `RUN lark1` without a click and moved through seven page iterations on its own poll with one navigation, each 0.39–1.52 s after the trainer's commit, curves updating. D4/D10: `lark1-checkpoint20` (policy `e6dcbbcc68b4…`, witness error 8.0e-8, video `c5f165541dd1…`, 11 frames, 0.98 s) was published while the trainer was at updates 18–26, played and downloaded hash-equal on the persistent page, which kept selecting the active run; trainer intervals 1.39/1.42/1.34 s median before/during/after the render. `lark1-final` (policy `396c013c3c35…`, video `25b363291b40…`, 6 frames, 0.50 s) is now the fresh-visit default; checkpoint 20 selects as HISTORICAL with its own revision and return-to-current works. Measured on seed 0 with the 8 s limit: checkpoint 20 fell at 0.98 s (−110.8 mm torso X), the final policy fell at 0.50 s after lunging +194.3 mm forward. A measured poor result, not a gait: the reward rising while the episode estimate falls says the forward term is paid for by falling. The accepted script now declares the final policy (digest `bfd2bdeb36a2…`); the pre-training run record was unchanged by the playbacks. The persistent service was never restarted and keeps serving; no trainer remains active.

Gates: `pixi run python -m pytest cli/tests` 433 passed, 1 skipped, exit 0 and `pixi run test-engine` 2110 passed, 53 skipped, exit 0 on the committed tree before the experiment; the two evidence-guard files (24 tests) pass after it. The only `cli/` change is the new guard test. No protocol, payload, engine, shell or dependency change.

Concerns for the next iteration: the unreconciled tail is now four records (`sweet-anchor-6246`, `honest-rain-3132`, `soft-forest-5662`, this one) and is due a reconcile pass. Lark still lacks its review-driven design change, retraining and comparison (D9), copy isolation (D7) and an interrupted attempt (D8); the checkpoint export cost (~55 s per checkpoint, two thirds of the wall clock) is worth measuring against the trainer rather than assuming. Same-machine private-address checks only; no second-device test.

Dispatch closed: 1 unit — Lark's first bounded real GPU training with live persistent-dashboard observation, an active-training checkpoint video and a verified final video; both policies fall within a second on seed 0.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: acaabde20c6c9780c6cdcc63b00de4283bd843e7

## State Impact

- target: dawn-delta-4361 — D3 repeated on the third fresh project: during lark1's real GPU run a fresh visit to the persistent URL selected the active run and showed seven trainer iterations without reload, each 0.39–1.52 s after commit, with reward, loss, episode-estimate and curve updates (evidence in docs/probes/lark-fresh/training-evidence.json).
- target: candid-harvest-2614 — D4 repeated on Lark: lark1-checkpoint20 published with a witness-verified rollout and browser-verified video (0.98 s, 11 frames) while the trainer was active at updates 18–26, and lark1-final has a verified downloadable video (0.50 s, 6 frames); both identify revision, policy digest, seed and simulation time; render overhead 1.39/1.42/1.34 s median before/during/after.
- target: deep-clover-6012 — D10: the persistent port 8765 page tracked Lark's real experiment throughout — active run selected by default during training, lark1-final selected by default afterwards, checkpoint 20 browsable as HISTORICAL with return-to-current — with no service restart; operator status README updated.
- target: silent-river-6649 — D9 clean-project repeat: Lark now has a trained, recorded and reviewed first run (lark1) with measured seed-0 results (both policies fall within a second, final +194.3 mm lunge); the review-driven design change, retraining and comparison remain open for Lark.
- target: crisp-sun-1239 — The exhaustion-policy repeat on ot5-lark reached training, checkpoint publication and final review with the Wren experiment driver generalised to discover outputs by kind; the unreconciled tail is four records and due a reconcile.
