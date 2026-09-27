---
node_id: 4464ce3a-20a7-5250-b38c-558b6efbe814
slug: scarlet-summit-7670
title: 'ADR-410: draw every model, pay for survival, stop a collapsed run'
created_at: '2026-09-27T14:28:15+00:00'
parents:
- late-sky-2627
summary: ''
---
## What
ADR-410, commit 54b1219f. It makes four changes:
- The renderer clusters vertices instead of refusing: it reads up to 2M triangles and draws at most 400k, with the cell doubling from a quarter pixel.
- The pixel-work budget scales with image area.
- A render refusal in the walk's review is recorded rather than fatal.
- The overlay gets an alive-bonus rule. The trainer gets `episode_collapse` and `--stop-on-collapse`, which `cadex walk` always passes.

## Why
hex3 (late-sky-2627) lost every `look` and its review to the triangle cap. It then trained for 7.2 h on a policy that had learned to end its own episodes by iteration ~80, because ADR-409's overlay (fond-light-6196) taught a net-negative per-step reward.

## Method
- Measured hex3 with the caps lifted: 589,268 triangles, mostly six 56,712-triangle filleted brackets.
- Clustering on the first pass (0.24 mm cell) kept 106,326; the four review views take 3.6 s. `look` at 768 px needed 20.27M pixel visits against the unscaled 20M.
- Collapse rule: all of the last 50 iterations under min(5% of horizon, 0.5 × the mean of iterations 1–10).
- Evidence added: `docs/probes/hex/hex3-GAPS.md` and `shots/hex3-look_iso.png`.

## Result
- On hex3's curve (28 early, 3 by iteration 77) the detector fires at about iteration 90. It does not fire on hex2's flat 215/500, or on a run that was always short.
- Tests: engine 2209 passed; CLI 962 passed, 1 skipped (the two remote-walk tests' pinned argv updated for `--stop-on-collapse`).
- Open: the design still looks crude because the agent has never been able to see it; the API is still learned by refusal; there is still no rollout video.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: hex/after-hex3
- commit: 54b1219f8b33defe2b6d72cf3a722b4f70413267

## State Impact

- target: shady-rose-6292 — close: look/review refused by render cap (decimation), review lost to a render failure, early-termination hacking unguarded (alive-bonus rule, collapse detector, walk stops on collapse); open: design quality never yet seen by the agent, API learned by refusal, no rollout video
