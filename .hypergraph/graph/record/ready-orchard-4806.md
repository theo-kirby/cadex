---
node_id: c807d17f-c47f-56a6-91db-84ffa8350858
slug: ready-orchard-4806
title: D4 browser download failure traced to snap-confined Chromium; harness collects downloads where the browser can write
created_at: '2026-09-12T16:40:49+00:00'
parents:
- long-cove-3626
summary: ''
---
## What

Fixed the reproduced D4 browser download failure in `cli/tests/test_video.py` (the assertion at the old line 153 raised `FileNotFoundError` on the downloaded file) by moving download collection into the headless-browser harness. `cli/tests/cdp_browser.py` gains `Page.download(selector)`, `HeadlessBrowser.download_dir()`, `HeadlessBrowser.wait_event(...)` and a `snap_confined()` probe; the test now asserts the browser's own received/total byte counts against the file it wrote and that file's SHA-256 against the record. `docs/CLI.md` documents the harness behaviour and adds the missing `test_video.py` row to the suite table; ADR-286 carries a download-evidence follow-up.

## Why

The critic named this unit: determine whether artifact delivery or browser download collection caused the failure, fix that cause, and prove playback and downloaded bytes in the headless browser suite while keeping fixture coverage distinct from real biped evidence. It advances D4 (`candid-harvest-2614`), whose browser download evidence was red. I did what was asked; the fix is in the test harness rather than the server because the measurement put the fault there.

## Method

1. Reproduced: `pixi run python -m pytest cli/tests/test_video.py -k browser_plays` failed at the download assertion after a ten-second poll for a file that never appeared.
2. Probed three ways in one throwaway test (deleted afterwards): a plain `urllib` GET of `/video/run/sample/0?download=1` returned `200 video/webm`, `Content-Disposition: attachment; filename="rollout-<sha>.webm"`, 5402 bytes with the record's digest — artifact delivery is correct. The browser download into a hidden `$HOME/.cache/...` directory: `Browser.downloadProgress` reported all 5402 bytes received, then `state: canceled`, no file. The browser download into pytest's `tmp_path` under `/tmp`: `state: completed`, no file on the host; `/tmp/snap-private-tmp/snap.chromium/` is root-owned and unreadable.
3. Cause: the machine's Chromium is `/snap/bin/chromium` (Chromium 152, snap). Snap confinement gives it a private `/tmp` namespace and refuses hidden paths under `$HOME`. The test's download directory was invisible to it in both forms it could have taken.
4. Fix: the harness chooses a download directory the browser at hand can write — `tempfile.mkdtemp(prefix="cadex-review-downloads-", dir=$HOME)` when the executable is under `/snap/` or resolves to the `snap` launcher, the system temporary directory otherwise — removed in `close()`. `Page.download` enables `Browser.setDownloadBehavior` with events, clicks, waits on `Browser.downloadWillBegin` for the guid and suggested filename, then on the matching `Browser.downloadProgress` reaching `completed` or `canceled`; `canceled` raises `BrowserError` naming the directory, the bytes received and whether the browser is snap-confined. The pipe reader was factored into `_pump` so events and replies share it.
5. Verified: `pixi run python -m pytest cli/tests/test_video.py cli/tests/test_review_server.py` → 29 passed, 1 skipped (the private-address smoke, which needs `CADEX_REVIEW_HOST`). No `cadex-review-downloads-*` directory remains under `$HOME` after the run. Full CLI suite result is in `## Result`.

## Result

The D4 browser test now passes on this machine and proves what it claims: inline playback survives three freshness polls, the download the browser wrote matches the retained file byte for byte, and the browser's reported byte counts match the file size. Artifact delivery over HTTP was never at fault. A confined browser that cannot write its download now fails with a message naming the state it saw rather than a `FileNotFoundError` after a timeout.

This is fixture coverage of the download path. D4's real-biped evidence — an intermediate checkpoint video during active training and a final policy video from the fresh biped — remains open, as does D9's fresh project creation, which was refused by provider quota in `zesty-star-7710`.

Assumption recorded: a snap is detected by the executable path (`/snap/...`) or by its realpath resolving to the `snap` launcher; a Chromium installed some other way with its own confinement would need `CADEX_BROWSER` pointed at an unconfined binary, and the error message says the download was cancelled and where.

No new dependency. No product code changed; `cli/cadex_cli/review_server.py` and `review.js` are untouched.

The unreconciled tail is now three records (`kind-fountain-5086`, `long-cove-3626`, this one): the next unit is the reconcile pass, as the critic said.

Full CLI suite: `pixi run python -m pytest cli/tests -q -x` (the fixed test run separately beforehand) → 351 passed, 1 skipped, 1 deselected in 4 min 38 s. Engine-needing tests ran; nothing in the engine tree changed.

Dispatch closed: 1 unit — D4 browser download failure traced to snap-confined Chromium's private /tmp, harness now collects downloads where the browser can write and proves the bytes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 698e2efddd908862703c14a039403c8a5204e229

## State Impact

- target: candid-harvest-2614 — The D4 browser download step now passes and proves the downloaded bytes: the failure was browser collection (snap Chromium's private /tmp and refused hidden $HOME paths), not artifact delivery, which a plain HTTP probe showed correct. cli/tests/cdp_browser.py owns downloads via Page.download, waiting on Browser.downloadProgress and failing loudly on cancellation; test_video.py asserts byte counts and digest. Fixture coverage only; intermediate-checkpoint and final-policy videos from the fresh biped remain open.
