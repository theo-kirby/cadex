---
node_id: c5fb9657-19e5-58b4-8f20-f97d36e7bb2d
slug: sage-tower-6445
title: Train Wren on GPU and retain live checkpoint and final review
created_at: '2026-09-13T00:09:43+00:00'
parents:
- late-walrus-6383
summary: ''
artifacts:
- docs/probes/wren-fresh/training-evidence.json
- docs/probes/wren-fresh/README.md
---
## What

Run Wren's first bounded real GPU training experiment, wren1, with live observation on the persistent private-network dashboard, a verified checkpoint video while training remains active, and a retained final-policy video. Publish reusable experiment/browser/summary probes, a compact receipt and the operator's current status. The final policy performs worse on the measured seed; the dashboard shows that latest result and preserves checkpoint 20 as historical.

## Why

Follow late-walrus-6383's accepted-display restore fix and the critic's request for Wren's first training run. This advances D3 (dawn-delta-4361), D4 (candid-harvest-2614), D10 (deep-clover-6012) and the repeated fresh-project lifecycle under D9 (silent-river-6649). No dimensional design change, retraining, project switch or deviation from the requested experiment. Wren's existing accepted product-agent design is the input; no older mechanism, policy or project history is imported.

## Method

Ran the documented PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/train.py command against ot5-wren, run wren1 and the existing Tailscale address on port 8765. The public CLI exports policy_on=0, retains the eight-component training view, imports policies, enables Wren's existing policy declaration and produces verified rollouts. Model XML and task bytes are asserted identical between training and both playback runs. The accepted training revision is c2e89b36b1e27cacc6afab5210a3cc627ec2d91f1f0e95ca37093ed4b7f6cd13; explicit policy_on=0 changes revision from the implicit default but preserves the geometry digest dbd02d7c12a0553b9ffadb3466e73da4055521264dd52e0bea40b2cc16588714.

Used the existing offboard environment, 240 PPO iterations, 1024 environments, seed 0, checkpoint interval 20, XLA memory fraction 0.45. A separate systemd scope enforced MemoryMax=20G (21,474,836,480 host bytes); timeout --signal=TERM --kill-after=20s 1800 bounded the training process. No concurrent experiment training. Captured cgroup limits, sampled host/GPU memory and committed iteration timing. Existing suites ran sequentially after experiment training finished.

The persistent operator service was never replaced by a test server or stopped. Fresh Chromium selected wren1 at startup, then observe.py saw page iterations 3, 4, 6, 7, 8, 10 and 11 without reload, with 0.40–1.43 s measured commit-to-page delays, matching retained revision, orbit and zoom. Checkpoint-20 witness error was 3.9561e-08 versus tolerance 1e-04. Rendering advanced training from iteration 23 to 32; playback/download finished with training active at 34. Another fresh visit at iteration 178 still selected wren1 despite the newer playback entry.

The final witness error was 8.2510e-08. Both saved videos were fully decoded, timing-checked, played and downloaded in the browser with matching digests, revision/policy/seed/time labels, and preserved playback across polling. Fresh final selection, historical checkpoint identity and return to current passed. Inspected saved browser screenshots and the decoded final frame. The common delivered style is cadex-prototype-light-v1, sha256 27893221b3c6cf784d62c16fdaa5c88d1beb031bcb195e5f34e1598ea56e5b0c; this is reuse, not a new D11 visual comparison. All network-browser observations were same-machine private-address checks, not second-device evidence.

## Result

Training exited 0 after 697.035 s, on GPU, with 240 retained points in reward, loss and episode-estimate histories and twelve reported checkpoints. Final batch reward/step 0.319398, loss 0.408266, episode estimate 325.079 steps. Sampled host peak 7,412,912,128 bytes; sampled total GPU peak 15,130 MiB. The trainer's batch episode estimate can exceed the episode horizon and is explicitly distinguished from measured survival.

Same rollout seed 0 and declared eight-second horizon: checkpoint 20 survives 400 steps, moves the torso +49.451 mm forward, and returns 216.297 reward; the final policy crosses the declared fell threshold at 0.46 s/23 steps, moves -105.757 mm forward, and returns -36.266. This is one seed, not a repeatable walking or multi-seed claim. Checkpoint video b534c28452de864328308e96ac8fd111fb305b7cd76b923f1211c31a113197dc has 81 frames/8.1 encoded seconds for 8 simulation seconds; final ba2f38cd38081e8c3fe6aa4dd3a413de6b2a65ce532c7917e478c5bef302cbdd has six frames/0.6 encoded seconds for 0.46 simulation seconds. The renderer includes the final pose. Ordinary iteration medians before/during/after rendering were 1.440/1.342/1.282 s, excluding checkpoint boundaries: an uncontrolled continued-progress observation, not a zero-overhead or speedup claim.

Persistent port 8765 remains active on ot5-wren / wren1-final, accepted revision a8073874ab76e4cc10cd09f4746138feec8b8fcb9f7c45540c1046d40b620849. Published operator status and project PROGRESS.md explain the poorer final result; checkpoint 20 remains historical. Full logs, harness copies, screenshots, policies, telemetry, traces and videos remain project-local under evidence and runs; docs/probes/wren-fresh/training-evidence.json is the compact portable receipt. Wren still needs a declared multi-seed review, review-driven design revision/retraining and the rest of its repeated lifecycle. No goal-completion claim, new dependency, product behavior change, build, state-node edit or reconciliation.

The trainer emitted an initialization overflow-cast RuntimeWarning but completed and both independent engine witnesses passed. A supplemental frame-extraction command initially could not locate ffmpeg outside pixi; the pixi invocation succeeded. These do not hide a failed training or video render.

Validation: full engine suite 2110 passed, 53 skipped in 269.88 s. Full CLI suite 394 passed, 1 skipped and 1 failure in 373.46 s: test_documents_cite_the_receipt required the historical creation revision in operator documentation, which the current-status rewrite had removed. Restored that historical citation, retaining the new current status, and corrected a remaining obsolete run-less-current sentence. The entire affected test_wren_fresh_evidence.py suite then passed all seven tests; the full CLI suite was not repeated after this documentation-only correction. All other CLI tests, including browser/video/current-history gates, passed in the full run. Compact evidence consistency assertions, py_compile and git diff --check passed. No product code changed. Logs are retained in the machine's temporary wren49-engine, wren49-cli and wren49-docs-recheck log files; raw experiment logs are project-local.

Dispatch closed: 1 unit — train Wren once on GPU and retain live checkpoint/final videos, honest outcomes and persistent operator review evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 5ee087efd0f5440e03060bab9d887438afbf53dc

## State Impact

- target: dawn-delta-4361 — Wren's first real GPU run reached 240 iterations; persistent-browser telemetry observation saw seven updates with 0.40–1.43 s commit-to-page delay and retained all three 240-point histories.
- target: candid-harvest-2614 — Wren checkpoint 20 was engine-verified, rendered and browser-played/downloaded while training remained active; final policy video also persists with verified identities and decoded timing.
- target: deep-clover-6012 — Persistent port 8765 stays on Wren and now defaults to wren1-final; active-first selection during training, historical checkpoint browsing, playback preservation and return to current pass.
- target: silent-river-6649 — Wren's first bounded GPU experiment is complete: checkpoint 20 survives 8 s on seed 0, final falls at 0.46 s; both videos and honest comparison are retained. Multi-seed review, design revision/retraining and remaining repeated lifecycle are still outstanding.
