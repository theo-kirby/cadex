---
node_id: 4595d93b-b960-5ccb-9da9-4321c34770ce
slug: mild-hill-0753
title: 'Heron trains: one bounded run completed, the final policy reaches on 10/10 seeds, videos in the new look on the operator dashboard (ADR-340, D8 training half)'
created_at: '2026-09-14T04:55:05+00:00'
parents:
- narrow-quill-3259
summary: ''
---
## What

D8's training half: Heron, the product-agent two-DoF MG90S arm (ADR-339), trained once under the charter's bounds in `ot6-heron` (`heron1`: 240 PPO updates on 1024 environments, seed 0, default learning rate 3e-4, `MemoryMax=20G`, 3600 s timeout; trainer exit 0 after 619.6 s, host peak 7.08 GB, GPU 15 137 MiB), its checkpoint-20 and final videos published in the D3 look on the persistent operator dashboard, and each retained policy measured over seeds 0–9 in a fresh scratch project: checkpoint 20 reached on 0 / 10, the final policy on 10 / 10. Receipts under `docs/probes/ot6/heron/`: `training.json` (15.1 KB), `TRAINING.md` (the assessment), `video-heron1-checkpoint20.png`, `video-heron1-final.png`, `servo-view-1400.png` with `servo-view.json`; ADR-340; the receipt test iteration 25 added now passes. Commit `630ab736`.

## Why

The critic rejected iteration 25 because its test failed on a missing `heron/training.json` and asked for Heron's D8 evidence to be completed from retained project artifacts before any second training run, with the receipt, decoded frames, assessment and ADR-340 published and the CLI suite green. That is what this unit did. The trainer and its driver launched by iteration 25 were still alive at update 139 of 240 when this iteration began; they were left to finish under their own timeout rather than killed or re-launched, so there is one run, and nothing retained was rewritten. The critic's first line also asked for the missing causal record and verification handoff for iteration 25: this record is that handoff — it states what iteration 25 actually completed (the four scripts, the test, the launch, the checkpoint publication) and what this iteration finished.

## Method

- At the start the driver (`train.py`, started 00:21 by iteration 25) was mid-run; the checkpoint-20 video had already been published with the trainer active (updates 18–37, browser check exit 0) and the observer had already sampled the live page (six updates each within 1.1 s, one reload). Waited on the driver's PID; it exited at 00:32 having stored the final policy, rolled and rendered `heron1-final`, browser-checked it as the fresh-visit default, and written `evidence/heron1-experiment-result.json`.
- `evaluate.py` twice, into `ot6-heron-eval-heron1-c` and `-f`: each policy asset content-verified, the recorded effective parameters baked into the scratch script, seeds 0–9 through `rollout_seed`, seed 0 asserted byte-identical to the retained trace, the source run asserted unchanged; per seed the tip's reach error at episode end, over the final second (max and mean), the smallest error, the first time within 10 mm, survival, termination.
- `report_training.py` wrote `training.json` (15 097 bytes, under the 16 KB cap) from the driver's result, the timeline, the resource bound, the observer, the two browser checks, both comparisons (copied into the project under `evidence/comparison-heron1/`) and `/api/project` at the end; `ffmpeg` decoded one frame at 2.0 s from each retained video (110 and 116 KB).
- `servo_view.py` orbited the persistent dashboard's viewport for `heron1-final` from yaw 0.8 to −1.2 by one 200 px drag and kept the frame (104 KB, quantised): shoulder servo case and tab plate on the base's outboard cheek, elbow servo on the upper arm's, both horns, the forearm's reach in front.
- Wrote `TRAINING.md` (task as declared; the run; the two policies over the seeds with a table; the look and the live dashboard; what is not claimed; commands), ADR-340, a training note in the project's own `DECISIONS.md`, and linked the README to the training half.
- Tests: `test_review_design.py -k "heron or caps"` 106 passed (the new receipt test plus the size/privacy gate over the six new files); full CLI suite 609 passed, 1 skipped (522 s). Engine suite not re-run: no engine code changed. Operator service `cadex-operator-review` active throughout, serving `ot6-heron` with `heron1-final` as the fresh-visit default at the end.

## Result

- **D8 has both halves evidenced pending the owner's tick**: a product-agent arm on catalog MG90S with inventory and fit check (ADR-339), one bounded real GPU run, checkpoint and final videos in the dark reference look naming what they show, browser-checked on the persistent dashboard, and the reach measured over seeds 0–9 (ADR-340).
- **Measured**: checkpoint 20 folds the arm back to (−6, 0, 148) at the joint limits on every seed and is never nearer the target than its 67.08 mm start (0 / 10, total reward −0.33 to −0.68). The final policy is within 10 mm by 0.1 s on every seed, nearest 0.36–1.85 mm, ends 2.96–5.19 mm away, never further than 9.60 mm over the final second after the two pushes, no termination (10 / 10 by the script's own bar). Reward per step −0.154 → 0.595, best at the last update and still rising.
- **Two facts the bar does not measure, observed not diagnosed**: the hold sits about 3 mm below the target on most seeds (the 30 mm reach scale makes that nearly free; servo sag is the plausible cause but the trace does not separate it from the policy's setpoint), and the tip oscillates within the tolerance (final-second max 8.3–9.6 mm against a mean of 4.9–6.2 mm). A tighter tolerance, smaller reach scale or heavier tip-speed weight is a design decision noted in the project's `DECISIONS.md` for the next turn on Heron, not taken.
- **Trainer metric caveat**: the trainer's `episode_steps` is unroll × envs over endings in the unroll, so on a task whose only endings are the synchronized time limit it alternates 20 480 / 20.0 and says nothing about episode length; the receipt reports it as such. No floor termination was recorded during training.
- **Render overhead**: unlike Robin, Heron's 13.2 s checkpoint render fell across plain updates (23–35), so the during-window is populated: median 1.072 s against 1.071 s before and 1.070 s after; no measurable cost.
- The rollout leg's STL exports give 53 620 triangles for the run views against 29 234 for the accepted view (a different tessellation source, both the real solids); noted, not a defect.
- Assumption: the critic's "using retained project artifacts before considering another training run" was read as permission to let the already-running trainer finish, since killing it would have discarded a bounded run in progress and produced no final video; the result is one run, as the charter asks.
- Frontier now: D9's final assessment and D10's closing report. D7 and D8 both carry a full recorded lifecycle. The unreconciled tail is two records (narrow-quill-3259 and this one).
- No new dependency. No product code or protocol change. No engine build. Evaluation scratch projects and the trainer log stay outside the repo under `~/cadex-projects/`, cited by path and digest.

Dispatch closed: 1 unit — Heron trains once, bounded; the final policy reaches on 10/10 seeds and checkpoint 20 on 0/10; both videos in the new look on the operator dashboard; receipt, frames, assessment and ADR-340 published and test-pinned (D8 training half).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 630ab73693fb7290dd419e4ab702ac4692e3064d

## State Impact

- target: civic-creek-8215 — D8's training half is evidenced (ADR-340): heron1 completed 240 updates in 619.6 s at the default rate under the charter's bounds; over seeds 0–9 checkpoint 20 reached on 0/10 and the final policy on 10/10 (within 10 mm by 0.1 s, ending 2.96–5.19 mm away, never beyond 9.60 mm over the final second, no termination); both videos cadex-prototype-dark-v1 naming what they show, browser-checked on the persistent dashboard, which selects heron1-final on a fresh visit; receipt training.json, decoded frames, servo-side viewport frame and TRAINING.md pinned by the receipt test; the hold is 3 mm low and oscillates within tolerance, an open design decision for the project; both D8 halves now evidenced pending the owner's tick
- target: round-sun-8398 — D7 and D8 each carry a full recorded lifecycle (design, inventory and fit, bounded training, seed-set measurement, videos in the D3 look on the operator URL); the frontier is D9's final assessment and D10's closing report
- target: late-pond-2851 — a third fresh mechanism (Heron, a grounded two-DoF arm) trained end to end at the default rate with no divergence and the reach task met on every seed; the trainer's episode_steps metric is uninformative on tasks whose only endings are the synchronized time limit (20480/20 alternation)
