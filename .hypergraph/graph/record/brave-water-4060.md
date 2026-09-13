---
node_id: e6429b7a-18b8-563b-b759-93b8b36571ed
slug: brave-water-4060
title: 'Backfill: iteration 84 revised Lark through the product agent, retrained lark2 and compared four policies on seeds 0–9 (ADR-313)'
created_at: '2026-09-13T07:38:50+00:00'
parents:
- upright-tide-4795
summary: ''
---
## What

Backfill record for iteration 84 (commit `b7a8d58b`, "ouroboros #84: no record"), which landed without a record node. That iteration completed Lark's review-driven design change the way D9 asks: one bounded product-agent turn read `lark1`'s measured results and accepted `torso_h` 70 → 45 mm with `policy_on=0` (revision `62f4e2a0e2df…`, project ADR-004); `lark2` retrained it under the unchanged bounds on the persistent port 8765 dashboard with a checkpoint video published during training and a verified final video; and all four retained policies were compared on Lark's declared seed set 0–9 from their own retained models, tasks and hash-verified policies. ADR-313; `docs/probes/lark-fresh/REVISION84.md` with receipts `training84-evidence.json` and `revision84-evidence.json`, guarded by `cli/tests/test_lark_fresh_evidence.py`.

## Why

The critic's first instruction for iteration 85 was to add the missing iteration-84 causal record and handoff before taking the next unit, targeting the ot5 charter node with the evidence and the remaining D7/D8 gaps, and to record suite results or their limits. Unrecorded work is invisible to the project; this node makes iteration 84's lineage explicit so the D7 unit that follows can parent on it.

## Method

Iteration 84 (as read from its commit and retained project artifacts): the agent turn ran as `./cadex --project ot5-lark --out evidence/agentrev84/output --json -p "$(cat prompt.txt)"` under a 900 s timeout (session `6319e8a1-8837…`, exit 0, five `inspect` and two `set_params` calls), with a SHA-256 inventory of the 125 files under `runs/` and `assets/` taken before the turn. `lark2` used `docs/probes/lark-fresh/train.py` with the same bounds as `lark1` (240 PPO updates, 1024 environments, seed 0, checkpoints every 20, `timeout 1800`, `MemoryMax=20G`, the existing `~/cadex-train-venv`). The comparison ran `docs/probes/wren-fresh/compare.py` once per retained policy into a fresh scratch project (`ot5-lark-eval84-{c1,f1,c2,f2}`) and `report_revision.py` over the four evaluations; the one tooling change was that both scripts now take the seed count from the project (Lark declares ten seeds, Wren five) and find the torso as the one traced component named for it, and Wren's committed `revision66-evidence.json` regenerates byte-identically. Docs updated: ADR-313, `docs/ROADMAP.md`, `docs/HEADLESS-BIPED-REVIEW.md`, the probe README and the operator status README.

Verification observed by iteration 85: iteration 84 started both gate suites but its logs (`/tmp/cli-tests-84.log`, `/tmp/engine-tests-84.log`) end mid-run with no summary line, so neither is a recorded pass for that tree. Iteration 85 ran the two evidence-guard files on the committed tree: 16 passed. The only `cli/` change in iteration 84 is the guard test; the probe scripts live under `docs/`.

## Result

Lark's revision is the product agent's own, with its hypothesis (0.433 kg of 0.596 kg at z = 203 mm drives the hip toppling moment; lowering the torso cuts it about 35 percent) and its tradeoff recorded as project ADR-004 and a design-spec bullet. `lark2` exited 0 after 240 updates in 718.8 s, host peak 7.42 GB under the 20 GB cap, GPU peak 15,122 MiB; model `1e318f184459…`, task `4615c6ddcaaa…`. A fresh visit to the persistent URL during training selected `RUN lark2` and moved through seven page iterations on its own poll, each 0.24–1.62 s after the trainer's commit. `lark2-checkpoint20` (policy `8eb15d8a7570…`, video `dfb45737df66…`, 81 frames, 8.0 s) was published while the trainer was at updates 18–33 and played and downloaded hash-equal; `lark2-final` (policy `b79a63908e94…`, playback revision `ca88f223b54c…`, video `af610491bedf…`, 8.0 s) is the fresh-visit default, with checkpoint 20 browsable as HISTORICAL and return-to-current working. Measured on seeds 0–9 at 8 s: both 45 mm policies survive all ten episodes (final mean +34.8 mm torso X, checkpoint +24.4 mm); `lark1-final` falls on every seed after a 181–197 mm lunge, `lark1-checkpoint20` on two. Consistent with the agent's balance hypothesis but one training seed per design, and 35 mm in eight seconds is a shuffle, not a gait. The 125 pre-revision run/asset files are byte-identical. Same-machine private-address browser checks; no second-device test; no new D11 similarity claim.

What remains for Lark after this: copy isolation (D7) and a controlled interruption (D8) have no Lark-specific evidence. The persistent service was not restarted and keeps serving `ot5-lark`. No protocol, payload, engine, shell or dependency change.

Dispatch closed: 1 unit — backfill of iteration 84: the product agent's 70→45 mm Lark revision, `lark2` retraining on the persistent dashboard and the four-policy comparison on declared seeds 0–9 (ADR-313); its own full-suite runs were cut off, the 16 guard tests pass.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: b7a8d58b6420d125375536c30422385705f94899

## State Impact

- target: silent-river-6649 — D9 on Lark: the product agent made the review-driven design change (torso_h 70→45 mm, project ADR-004) from lark1's measurements, lark2 retrained it under the same bounds, and both runs have saved playable videos and displacement/survival/falls measured over the declared seeds 0–9 (both 45 mm policies survive all ten; lark1-final falls on all ten); one training seed per design, not a gait.
- target: candid-harvest-2614 — D4 repeated on lark2: checkpoint 20 published with a witness-verified rollout and browser-verified 8.0 s video while the trainer was active (updates 18–33), final policy video verified, played and downloaded; render overhead medians 1.528/1.391/1.368 s before/during/after.
- target: dawn-delta-4361 — D3 repeated on lark2: a fresh visit to the persistent URL during training selected the active run and moved through seven page iterations without reload, each 0.24–1.62 s after the trainer's commit.
- target: sharp-union-6036 — D5 on Lark: after the agent's 70→45 mm revision and retraining, lark1 and lark2 runs remain selectable with their own revisions, curves and videos and the 125 pre-revision run/asset files are byte-identical.
- target: deep-clover-6012 — D10: the persistent port 8765 page tracked lark2 from start (lark1-final default) through active training (RUN lark2 selected) to completion (lark2-final default) without a restart; operator status README updated.
- target: crisp-sun-1239 — Iteration 84 recorded: Lark's D9 lifecycle through revision, retraining and declared-seed comparison is complete; Lark-specific D7 (copy isolation) and D8 (controlled interruption) evidence remains open; iteration 84's own full-suite runs were cut off before a summary, the 16 evidence-guard tests pass on its tree.
