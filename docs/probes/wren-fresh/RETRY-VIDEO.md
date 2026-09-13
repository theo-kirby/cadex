# Wren retry policy publication

Verified against source: 2026-09-13. [Cadex-new]

The persistent dashboard on private-network port 8765 serves `ot5-wren-copy54`
and defaults to `wren57-retry`, now with its own engine-verified video. This
advances D4 and D10 after the controlled interruption/retry. It launches no
training and makes no walking-quality or product-agent revision claim.

The [compact receipt](retry-video-evidence.json) records the identities and
checks. The policy SHA-256 is
`a232fec18df3ed7621e13f966302adeeab23259039cb0ab4a6ea2d09f09d9814`.
The engine independently checked 32 witness samples: maximum error
`8.677468489214458e-09`, below tolerance `0.0001`. The rollout's MJCF and task
files are byte-identical to this retry's retained training inputs.

Enabling the saved policy changed the accepted script revision from
`5b61ef31ff134f0f31b079347d9e5d3fd6aec236f12ad9c7b45910640388d7e6` to
`79f86c69bfc38dbf650f266446f256a72dd5547f3eaa386c7328ce85c81224fa`.
The foot length remains **110 mm**. The existing attempt's record now names
the verified playback revision; its original `run.json` remains byte-for-byte
in `training-run.json`. Original `script.py`, assembled training view, specs,
project document snapshots and all training files remain intact. The playback
script is separately retained as `playback-script.py`; the record explicitly
identifies the training record as the earlier identity source. Its chronology
and original training configuration are preserved. This is a policy declaration,
not a newly authored design or a new training attempt.

The seed-0 trace covers **8.0 simulation seconds**. FFmpeg fully decoded **81
512×512 frames at 10 fps**, with differing first/last frames; encoded duration
is **8.1 seconds**, including the renderer's final-pose sample. Video SHA-256:
`4d418967d41c1fe39b3ec2fa6945a0e8b5cf18343c4e3f5b1d0cf3dffbc3945e`.
Rendering took **12.629 seconds**, using the existing shared
`cadex-prototype-light-v1` style (`27893221b3c6…`). The decoded midpoint and
persistent viewport screenshots were visually inspected: the colored biped and
its authored blue ground plate sit within the fogged prototype-grid scene.
No new reference-matching assessment or style change is claimed.

A headless browser on the persistent private address selected `wren2-final`
and played its video throughout engine verification and new-video publication.
After publication and polling, it retained the same video DOM element, active
playback and historical revision. Return-to-current selected `wren57-retry`
and its new video. A fresh visit selected the same current attempt, displayed
110 mm feet, eight components and curves, played through three refreshes, and
downloaded the video with a matching SHA-256 and byte count. This is a
same-machine private-address test, not a second-device test. All **395 files
in other runs** remained unchanged; all **35 original retry files** were retained
(the original record under its explicit training filename).

## Reproduce and retain

The publication probe refuses a previously used evidence directory and a run
with an already recorded trace. It uses public CLI asset/script/params/render
commands, verifies the exported identities, enriches the existing attempt and
uses the shipped renderer. For a new completed retry with the same 110 mm
Wren script contract and saved policy:

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/publish_retry.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren57-retry \
  "http://$(tailscale ip -4):8765/" wren2-final
```

The command above identifies the executed publication; do not repeat it on the
already-published run. Recheck its retained video without changing project state:

```bash
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/check_video.py \
  "$HOME/cadex-projects/ot5-wren-copy54" wren57-retry \
  "http://$(tailscale ip -4):8765/"
```

Keep the whole project. `runs/wren57-retry/` holds the original inputs,
verification outputs, playback source and content-addressed WebM;
`evidence/wren57-retry-publication60/` holds command envelopes, screenshots,
decoded midpoint, full receipt and suite logs. No external evidence path is a
runtime dependency. The server was left running throughout.

The browser regression
`test_browser_current_run_gains_video_preserving_historical_playback` publishes
through the actual renderer while an older video plays, then checks historical
selection/player preservation, fresh default selection, return-to-current,
new playback and hash-matching download. Synthetic fixture coverage complements
the real persistent-browser observation above.

The [product-agent revision gap](AGENT-REVISION.md) remains explicit: the
110 mm design was a parameter edit in the working copy. Iteration 58's product
agent could not complete a revision because of its provider quota. This unit
made no quota retry and does not close that gap.

## Verification

The full CLI suite passed **398 tests, 1 skipped** in **378.43 seconds**.
The first tool-session invocation ended with SIGTERM before a summary; its
partial log is retained. A systemd launch initially lacked `pixi` on PATH;
the successful invocation used the resolved executable. The initial browser
regression tried playback after opening a new tab and timed out on the
backgrounded page; moving the fresh-visit check after playback fixed the test.

The sequential engine suite passed **2110 tests, 53 skipped** in **253.11
seconds**. The final distinct-video regression passed independently in **6.43
seconds** after both suites (1 passed, 33 deselected). No build was needed.
The persistent service remained active; graph export/check and diff checks
were run before committing the unit.
