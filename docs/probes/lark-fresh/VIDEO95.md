# Lark missing/partial-video recovery

Verified against source: 2026-09-13. [Cadex-new]

D8's missing/partial review-output probe passed on a disposable full copy of
`ot5-lark-copy85`. The [receipt](video95-evidence.json) records the actual
browser labels and playback/download identities. No training was started.

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/video_recovery.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-lark-copy85" \
  "$HOME/cadex-projects/lark-video95-evidence" lark86-retry-video lark2-final
```

Use a new output directory for repeats. The probe copies every project file to
a temporary sibling directory, serves that copy on an ephemeral private-network
port, and removes only that disposable copy afterward. Screenshots and the raw
receipt remain in the external output directory; their hashes are in the
committed receipt. The persistent port 8765 server is inspected before and after
the faults and is never restarted or switched.

For current `lark86-retry-video`, the probe removed its saved WebM, replaced it
with its first 64 bytes, then wrote a failed-render receipt while the truncated
bytes remained. Automatic polling on the already-open page showed respectively
**missing**, **refused: video digest mismatch**, and **Recorded video render:
failed — injected encoder failure**. All three showed **Video files: unavailable
(0/1 retained)** and instructions to retry the CLI video command after restoring
inputs or fixing the encoder. The broken video had no player/download link and
its direct URL returned 404. The recorded ready status in the first two cases
was visibly separate from current file availability.

During every fault, historical `lark2-final` remained selectable, labelled
historical, playable through two refreshes and downloadable with SHA-256
`af610491bedf8ed8d13b8bbc7c05c94954747d95f86514b387256148c84cf826`.
Return-to-current preserved the fault rather than substituting the old success.
Restoring the original video and receipt recovered current playback in the same
page, with SHA-256
`1f53d43d1c187de363eadae51931e90d91e8a7928e25ce5ebdb70df46322ca01`.
All **2,517 files** matched the original inventory after restoration; the
operator project also remained byte-identical.

The persistent operator page still selected `lark86-retry-video`, revision
`7f6c23913d55…`, policy `074e22f1070c…`, and played/downloaded the same
video afterward. This is a same-machine headless browser over the private
address, not a second-device check. The failed receipt is controlled injection,
not evidence of a real encoder failure concurrent with training.

The CLI browser regression
`test_browser_current_run_gains_video_preserving_historical_playback` now also
removes and truncates real encoded output, checks full/range URL refusal and
guidance, plays/downloads history during the fault, restores output while history
plays, and returns to the recovered video without navigation. A background
Chromium page can defer media loading: the test observes its recovered player
element, then verifies media readiness and download in the foreground page.

Validation: the real Lark probe passed. `pixi run test-engine` passed **2,110**
tests with **53 skipped**. The full `pixi run python -m pytest cli/tests -q`
process loaded the test before its background-readiness correction: **445 passed,
one skipped, one failed**, with that assertion the sole failure (460.02 s).
The corrected final source was verified with
`pixi run python -m pytest cli/tests/test_review_server.py -k 'current_run_gains_video or refuses_damaged_video' -q`:
**two passed**, 45 deselected (26.33 s). No full-suite clean rerun is claimed.
No engine/product code, protocol or payload changed; no build was needed.
