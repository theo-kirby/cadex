---
node_id: 890c3201-64d6-5d93-981a-36aebb17a395
slug: tender-vine-9199
title: Wren retry verified video arrives without disrupting historical playback
created_at: '2026-09-13T02:22:54+00:00'
parents:
- dawn-bell-5364
summary: ''
artifacts:
- docs/probes/wren-fresh/RETRY-VIDEO.md
- docs/probes/wren-fresh/retry-video-evidence.json
---
## What

Engine-verified and published the saved wren57-retry policy's truthful 110 mm-foot rollout video on the persistent operator dashboard. Added a real-renderer browser regression for the current attempt gaining its own video while historical playback stays selected and intact, plus a reproducible publication probe, compact evidence and operator-facing report.

## Why

Follows dawn-bell-5364 and the critic's requested next unit. Advances D4 (verified retained video) and D10 (current attempt gains output without disrupting deliberate historical browsing), targeting candid-harvest-2614 and deep-clover-6012. Wren's product-agent geometry-revision gap remains open; no provider retry or new training was attempted.

## Method

Ran PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 pixi run python docs/probes/wren-fresh/publish_retry.py "$HOME/cadex-projects/ot5-wren-copy54" wren57-retry "http://$(tailscale ip -4):8765/" wren2-final. The probe uses public asset/script/params/render CLI operations and the shipped video renderer, never engine internals. It keeps the original training record as training-run.json, preserves training script/view/docs/files, and enriches the existing attempt with the actual playback revision and trace. The original recorded_at and training configuration remain unchanged. Model XML and task bytes are compared against retained training inputs before publication. Historical wren2-final plays throughout verification/rendering; the probe checks DOM identity, active playback, historical revision, current navigation and fresh current selection.

check_video.py fully decoded the real WebM with FFmpeg, checked timing with ffprobe, played through three polls and downloaded via Chromium with matching byte count and SHA-256. The persistent URL is the same machine's private-network address on port 8765, not a second-device test. Screenshot and decoded-midpoint inspection confirmed the existing shared prototype-grid environment and truthful authored blue ground plate; no new D11 reference-matching claim. Raw logs, screenshots and receipts remain project-local under evidence/wren57-retry-publication60/ and evidence/wren57-retry-check.json. Compact identities are committed in docs/probes/wren-fresh/retry-video-evidence.json; instructions/results are in RETRY-VIDEO.md.

## Result

Policy a232fec18df3ed7621e13f966302adeeab23259039cb0ab4a6ea2d09f09d9814 passed 32 engine witness samples with error 8.677468489214458e-09 < 0.0001. Training revision 5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6 is retained explicitly; enabling that policy produces accepted playback revision 79f86c69bfc38dbf650f266446f256a72dd5547f3eaa386c7328ce85c81224fa, digest dc1e707ae72120b92d6cfb6fb79d81f515db7b5fa20f96bf0c877f73b47bcb35. Feet remain 110 mm; model/task files are byte-identical to training. The video hash is 4d418967d41c1fe39b3ec2fa6945a0e8b5cf18343c4e3f5b1d0cf3dffbc3945e: 81 decoded 512x512 frames at 10 fps, 8.0 simulation seconds and 8.1 encoded seconds including the final-pose sample, seed 0, rendered in 12.629 seconds. All 395 files in other runs are unchanged; all 35 original retry files are retained, with its original record under the explicit training filename. Persistent service remains active, default wren57-retry, showing eight components, 110 mm feet, curves and its own playable/downloadable video. Historical selection/player survived publication.

No new dependency, renderer style change, build or product runtime change. No walking-quality inference from this short retry. Wren's 110 mm change remains caller-authored; the failed product-agent revision is not closed. The first CLI-suite tool session ended with SIGTERM without a summary. A systemd launch initially lacked pixi on PATH; the corrected job uses the resolved executable. The initial regression opened a fresh tab before checking playback and timed out on the backgrounded page; moving the fresh-tab check after playback passed. Its final fixture makes the new video distinct so download checks detect historical substitution.

Verification: full CLI suite 398 passed, 1 skipped in 378.43 s; sequential engine suite 2110 passed, 53 skipped in 253.11 s; final distinct-video browser regression 1 passed, 33 deselected in 6.43 s. Both full gate exits are 0. The final regression was rerun after strengthening its two-video distinction; no experiment training overlapped the suites. Log hashes are in the compact receipt. git diff --check and hypergraph export/check pass before commit.

Dispatch closed: 1 unit — publish the engine-verified Wren retry video and prove historical playback survives its arrival.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 9013150907ebfc540d3b25226e5e977024982b4e

## State Impact

- target: candid-harvest-2614 — The 110 mm Wren retry now has an engine-witness-verified 8-second seed-0 video, full decoded timing and hash-matching browser playback/download evidence, with original training identity retained.
- target: deep-clover-6012 — Persistent port 8765 remains on ot5-wren-copy54 default wren57-retry, now playback revision 79f86c69bfc3; its video arrival preserves historical playback in the real browser and a distinct-video regression.
