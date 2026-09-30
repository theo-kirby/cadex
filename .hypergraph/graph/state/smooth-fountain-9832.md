---
node_id: a42d8504-4b29-5497-8c42-2d9874704b88
slug: smooth-fountain-9832
title: R1. A quadruped walks with real steps
created_at: '2026-09-30T07:04:57+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion for run ot11: **R1. A quadruped walks with real steps.** - The final pre-registered confirmation evaluation passes the frozen walk spec on every evaluation seed, and meets the video judge's bar. - The policy is installed, verified and reopened through the supported path, on an accepted design. That design may be one of ot10's, copied into a new `ot11-*` project. - Every earlier training run and evaluation is published, including the failures. [rec: kind-spire-3578]

Declared target: `gap-r1-quadruped-walks-real-steps`. This node tracks the criterion as a gap; it becomes working only with causally parented, measured evidence that the criterion is met. The human owns the charter checkbox; roles report results and do not tick it. The directive's impact line is truncated; its wording is resolved from the full charter carried verbatim in the same record [rec: kind-spire-3578].

**R1 has two evaluated walk rounds, both 0/10, and neither is evidence about its reward design: both trained on MJX physics that disagreed with the engine through saturated servos (ADR-465), fixed in the trainer since** [rec: empty-bay-8350] [rec: copper-sun-7929] [rec: long-badger-5117]. No passing evaluation exists; these are loop rounds, not confirmations.

- **Project.** `ot11-quad-1`, a `cp -a` copy of `ot10-quadruped-3-w2` at accepted revision `84ff4c98…`. The mechanism is fixed for the session because HIP_MM (96.7006), WEIGHT_N and SPEC_LIFT are this model's; reopening it later is its own recorded decision [rec: lively-ledge-7354].
- **Spec.** The frozen walk spec as a thirteen-predicate xscript block with a commanded-speed goal in [0.6, 1.0] hip heights/s (`retained/walk-spec-block.txt`, sha256 `487416af…`); W3 as `speed_ratio` in [0.75, 1.25], W4 as `lateral_ratio` ≤ 0.25 plus `max_heading_deg` ≤ 45; 10 s, tilt 0–3°, one 0.05–0.20 × weight shove for 0.15 s between 3 s and 7 s. It appears verbatim in the accepted script (revision `db1cfc96…`); an evaluation whose spec block differs from the retained one is void [rec: lively-ledge-7354].
- **Session.** Walk loop pre-registered and committed before GPU time (`626141c8`: `retained/p4-quad-1-preregistration.json`, `prompts/walk.loop.prompt.txt` `13386046…`); unchanged `runner/rounds.py`, at most 4 runs of ≤ 2400 s each, stop-on-collapse, claude-opus-5-5 with no fallback; output in `~/cadex-projects/ot11-notes/quad-1/`. The prompt says nothing about how to reward a gait [rec: lively-ledge-7354].
- **Round 1** `r1-clearance` (seed 7, 1000 it × 2048 envs, 2350 s budget). The agent's design charges foot-height error × foot speed, feet sinking and diagonal desync, restructured to 15 terms on its own after the 16-term limit and an "expression is too complex" refusal; its MJCF differs from `w2-2`'s only by added foot `subtreecom`/`subtreelinvel` sensors [rec: lively-ledge-7354]. **It collapsed** at iteration 568 after 1,542 s of GPU time (reward per step negative throughout, so ending an episode paid). Its best checkpoint `8db0cb61…` (iteration 273) **fails the frozen 13-predicate spec on 10/10 seeds, for the right reasons**: W3 −1.46..−0.05 (backwards against 61–93 mm/s commands), W5-share, W6, W7 (slip 0.48–0.90) and W10 fail on every seed, W4-heading and W9 on 8, and seeds 1102/1106/1107/1110 tip. The seed-1101 filmstrip shows the trunk turning and backing away. Receipt `retained/p4-quad-1-r1-evaluation.json`, commit `74debd53` [rec: empty-bay-8350].
- **Round 2** `r2-bounded` (seed 11, 800 × 2048, 2,380 s) cites round 1's W3/W7/W10/W6 ranges and the collapse; the change is reward-only (every cost tanh-bounded, alive 2→3, wider speed Gaussian, quadratic sink, re-weighted heading/yaw) [rec: empty-bay-8350]. It **finished all 800 iterations without collapsing** (2,251 s) and **fails 0/10**: W1/W2 now pass everywhere, but W3 is −2.06..−1.22, backing away at 114–144 mm/s already in the first 3 s before any shove; the rear feet take 0 steps on nine seeds and drag (slip 0.51–0.63, ~10 mm into the floor); W3, W5, W6, W7, W8-low, W9 and W10 fail 10/10, W4-heading 5/10. The bounded costs sit near their caps and `speed_track` earns 0.00–0.02 of 2.0. Receipt `retained/p4-quad-1-r2-evaluation.json`, commit `150988d9` [rec: copper-sun-7929].
- **Round 3** `r3-nochatter` (seed 23, 800 × 2048, 2,380 s) was registered citing round 2's W3, W7, W5-steps and W10 ranges and a knee-chatter reading (checked correct: ~364°/s RMS), and was training on the pre-fix trainer [rec: copper-sun-7929] [rec: long-badger-5117].
- **The spec block is unchanged** at every evaluated and registered revision so far (`8498db6e…`, `80ba9fb9…`, `27da0754…`) [rec: empty-bay-8350] [rec: copper-sun-7929].
- **The train/evaluation gap is explained** (r2 trained +2.48/step, evaluated −1.69..−1.21; r1 −1.39 vs −7.51..−4.34): rounds 1, 2 and `r3-nochatter` trained on MJX physics that kept a clamped servo's −kv in the implicit step, where the r2 policy really does walk forwards. Their engine evaluations stand — `cadex evaluate` was never on the drifted path — but they say nothing about their reward designs. The next round the agent registers trains on the fixed trainer automatically; a policy's `trainer_sha256` tells the runs apart. Receipt `retained/p3-quad-1-mjx-parity.json` [rec: long-badger-5117]. The mechanism is on `late-pond-2851`.
- **While the session is alive** (`pgrep -f "rounds.py --project ot11-quad-1"`, up to ~3 h), no other GPU job is started [rec: lively-ledge-7354].

## Negative knowledge

- [scope: checking an xscript edit on a project copy | confidence: high | evidence: lively-ledge-7354] `cadex params` rewrites `script.py` from the accepted revision, so a hand edit followed by `params` is silently lost; the spec check was redone with `cadex script --set`.

## Provenance

- kind-spire-3578 — ot11 operator-declared charter gap
- lively-ledge-7354 — R1 started: ot11-quad-1 copied, full walk spec with speed goal pre-registered (626141c8), round 1 r1-clearance training
- empty-bay-8350 — walk round 1 r1-clearance collapsed at it 568; best checkpoint fails 10/10 (backwards, slip, sinking, idle rear legs); round 2 cites it (74debd53)
- copper-sun-7929 — walk round 2 r2-bounded finished without collapse, 0/10, still backwards with dragging rear feet; round 3 cites it; train/eval gap flagged (150988d9)
- long-badger-5117 — ADR-465: rounds 1–3 trained on MJX physics that diverged from the engine through saturated servos; evaluations stand, reward designs unevidenced
