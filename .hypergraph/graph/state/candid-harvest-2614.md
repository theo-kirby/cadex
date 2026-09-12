---
node_id: b88f672e-257e-57ba-83f3-e9061ff94571
slug: candid-harvest-2614
title: D4. Policy videos render, persist and play headlessly
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: open

## Current

**The browser playback/download test passes on fixtures and proves the downloaded bytes; real fresh-biped videos are still absent.** The full CLI suite was briefly red at `test_video.py`'s download assertion (`FileNotFoundError` on the downloaded WebM after a ten-second deadline), reproduced against a clean `git archive` of startup commit 372d68ba, so it was a baseline regression rather than a telemetry change [rec: long-cove-3626]. Measurement located the fault in browser download collection, not artifact delivery: a plain HTTP GET of `/video/run/sample/0?download=1` returned `200 video/webm` with an attachment filename and the record's digest, while this machine's snap Chromium (`/snap/bin/chromium`, Chromium 152) reported all bytes received then `canceled` for a hidden `$HOME` download directory, and `completed` into its private `/tmp` namespace where the host cannot see the file. `cli/tests/cdp_browser.py` now owns downloads: `Page.download(selector)` waits on `Browser.downloadWillBegin`/`downloadProgress` and raises `BrowserError` naming the directory, bytes and snap confinement on cancellation; `HeadlessBrowser.download_dir()` picks a directory the browser can write (a `cadex-review-downloads-*` temp dir under `$HOME` when the executable is under `/snap/` or resolves to the `snap` launcher, the system temp dir otherwise), removed on close. The test asserts the browser's received/total byte counts against the written file and its SHA-256 against the record, and that inline playback survives three freshness polls. Video and review suites: 29 passed, 1 skipped; full CLI suite 351 passed, 1 skipped. No product code, dependency, server or `review.js` change; `docs/CLI.md` documents the harness and ADR-286 carries the follow-up [rec: ready-orchard-4806].

Retain `open`: this is fixture coverage of the download path [rec: ready-orchard-4806]. The criterion needs an intermediate-checkpoint video rendered during the fresh biped's active training and a final-policy video, with decoded frame/timing checks, which depend on D9's creation (`silent-river-6649`).

Charter criterion: **D4. Policy videos render, persist and play headlessly** At least one verified intermediate checkpoint is rendered and appears in the dashboard while training remains active, and the final policy also has a saved video; both play and download in the browser, each identifying model revision, policy digest, rollout seed and simulation time. Evidence: real biped video files, a decoded frame/timing check and a browser playback/download test; a failed render leaves training running and reports its own failure. Declared target `gap-d4-policy-videos-render-persist` [rec: lucky-comet-0031], introduced with no implementation claimed [rec: dusty-peak-9330].

## Negative knowledge

- [scope: headless Chromium download tests on a machine whose Chromium is the snap package | confidence: high | evidence: ready-orchard-4806] Snap confinement gives Chromium a private `/tmp` and refuses hidden paths under `$HOME`; a download directory in either place is invisible to the browser or to the host. A differently confined Chromium would need `CADEX_BROWSER` pointed at an unconfined binary.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d4-policy-videos-render-persist`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- long-cove-3626 — reproduced the baseline browser download failure against the clean startup commit
- ready-orchard-4806 — traced the failure to snap-confined Chromium; harness collects downloads where the browser can write and proves bytes and digest
