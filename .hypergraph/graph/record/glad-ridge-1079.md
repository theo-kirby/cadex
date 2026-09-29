---
node_id: fe9d2b58-71d2-5740-9ffb-155f70936f4c
slug: glad-ridge-1079
title: 'ot10 close: dark w2-2 video plays in the dashboard; REPORT reconcile note corrected'
created_at: '2026-09-29T07:43:59+00:00'
parents:
- glad-oak-4897
summary: ''
---
## What
Ran the review dashboard's existing Chromium playback check on the dark-floor (ADR-444) re-render of `w2-2`'s rollout video, and replaced REPORT.md's two "dashboard playback of the dark video was not re-checked" lines with the result. Marked REPORT.md's old "Reconcile before done" paragraph as history (its records `morning-tooth-4242` and `rich-path-1948` are folded into `loyal-fountain-8709` and `southern-prairie-3683`). Also updated the closing paragraph so it names every record the last reconcile must fold.

## Why
The critic asked for two things. The first was a housekeeping reconcile: fold `keen-comet-6140` and `glad-oak-4897`, then regenerate STATE.md. **I did not do that.** This iteration's dispatch forbids the hypergraph-reconcile skill, `hypergraph update` and edits to state nodes or STATE.md in a work iteration, "no exceptions". The dispatch is the binding instruction, so the reconcile is left to the reconcile pass. The critic's second item was "optional and cheap": the dark-video playback check and the REPORT.md trim. That is what this unit did. No product work was started. Target: C1 (`first-snow-5587`-style closing work for ot10), and A8/W1 evidence.

## Method
- Copied the scratch project `/tmp/a8-w2` (which holds the ADR-444 dark re-render) to a throwaway copy, so the check could not mutate it.
- Served the copy with `cadex_cli.review_server.serve` and drove it with the suite's `HeadlessBrowser`/`_open` helpers. The steps mirror `test_browser_plays_downloads_and_keeps_playback_across_polls`: select run `w2-2`, wait for `readyState >= 2`, play muted, run three `cadexReview.refresh()` polls, then download via the page's link and hash the file.
- Decoded one frame at t=5 s with pixi's ffmpeg and sampled its corner pixels.
- Ran `test_ot10_report.py` and `test_ot10_contract.py` on the edited page.

## Result
- The dark video plays in the dashboard. Its source is `/video/run/w2-2/0`, and the page shows SHA prefix `3fb52b44…`. It is 512×512 with a duration of 10.1 s. Playback passed 1.108 s, and the same element was still playing after three polls.
- The download is the retained file byte for byte: `rollout-3fb52b44ba6dc31b882f541c7d0314a8a40ebf915d3ad6e2dc819a88aef44336.webm`, 438,625 bytes, SHA-256 matched.
- The decoded frame's corners are `#161616`/`#181818` (and `#2e2e2e` on the mat grid region), which is the `#141414` scene after VP9 compression.
- REPORT.md's tests: 48/48 pass.
- No engine, `cli/` code or payload changed, so the suites and the packaged gate are not re-run. The final-revision results in REPORT.md still stand.

**Concern for the next pass:** the unreconciled tail is now three records: `keen-comet-6140`, `glad-oak-4897` and this one. C1's "reconcile, then claim done" still needs the reconcile pass. After it runs, done should be re-claimed in one line citing it.

Dispatch closed: 1 unit — dark w2-2 video verified playing and downloading byte-exact in the dashboard's Chromium; REPORT.md's "not re-checked" lines and stale reconcile paragraph corrected; reconcile deferred to the reconcile pass as the dispatch requires.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: bc8b9b3fbe3fb299a5113a49941cb3109a9a778b

## State Impact

- target: plain-harbor-3410 — the dashboard's Chromium playback check passes on the dark-floor w2-2 webm (3fb52b44…, 10.1 s, 512², downloaded byte-exact); REPORT.md no longer says it was not re-checked
