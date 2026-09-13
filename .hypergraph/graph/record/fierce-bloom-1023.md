---
node_id: 714894ac-1c7e-5173-ae2f-83a6a7029831
slug: fierce-bloom-1023
title: Repair Unicode video downloads and verify persistent Lark review
created_at: '2026-09-13T12:06:24+00:00'
parents:
- red-shade-9740
summary: ''
artifacts:
- docs/probes/lark-fresh/download103-evidence.json
---
## What

Fix D4 retained-video downloads whose Unicode filenames crashed the HTTP response. The server sends an ASCII fallback plus an encoded UTF-8 filename when needed; a browser saves the original Unicode name and byte-identical content. Document ADR-323 and recheck real Lark playback/download on the persistent dashboard.

## Why

Criterion D4, recording/review reliability under the maintenance horizon. Bet: fix the demonstrated filename-dependent download failure before repeating training that already has evidence. A Chromium regression on `歩行 résumé.webm` failed on the original implementation: Python's header writer raised UnicodeEncodeError and the browser timed out waiting for downloadWillBegin. This is a different criterion from the banned disk-accounting bet and does not resume clearance work.

The critic requested direct corrections to chilly-union-8972/crisp-sun-1239 and a reconcile. This dispatch explicitly forbids state edits and reconciliation, and requires a work record instead; I declare the correction below for the authorized reconciler. Iteration 100's civic-nest-8285 alone is NOT evidence of bounded disk accounting. Iteration 102's red-shade-9740 supersedes that unsupported claim with aggregate lazy traversal and honest partial-size evidence. No state or charter edits were made.

## Method

Encode non-ASCII and header syntax characters in the extended download filename; sanitize the ASCII fallback, retaining existing headers for ordinary ASCII names. Add one headless Chromium regression verifying original Unicode filename and downloaded bytes, and three HTTP cases for accented names, quotes and CR/LF. Focused tests: `pixi run python -m pytest cli/tests/test_review_server.py -k 'download_filename or downloads_unicode' -q` (4 passed in 2.99s). Ordinary recorded artifacts plus Unicode browser test: 2 passed in 2.24s. The synthetic payload tests download transport only, not video decoding.

Restart only the persistent review server with its existing command, project and private address on port 8765. Run `PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/check_video.py "$HOME/cadex-projects/ot5-lark-copy85" lark98-final "http://$(tailscale ip -4):8765/" --label download103`. This existing assertion-bearing probe verifies the real retained video, model/spec identity, curves, policy origin, playback/download, historical browsing and return to current. Retain raw output project-locally and the compact address-free receipt at docs/probes/lark-fresh/download103-evidence.json. Publish status in the Lark README.

## Result

Persistent dashboard remains running on ot5-lark-copy85; a fresh visit selects lark98-final. Its real video decodes into 81 differing frames, 8.1 encoded seconds, downloads as sha256 6c0bf873dc95fbb8b7994eca6bd54ffcf8f458688e45d8722272e5d7b6d9a3b9. Historical lark98-checkpoint20 selection and return to lark98-final pass. This is a same-machine browser over the private address, not a second-device check. No project mutation, new training, new recording, dependency, engine/payload/shell change or build. This maintains D4 evidence; no whole-goal completion or checkbox change is claimed.

Handoff: tried a permitted Unicode filename and reproduced a concrete download failure, then fixed its response encoding. Next try the D4 maintenance bet of interrupting a large video download and verifying that a fresh download and concurrent dashboard polling recover; do not infer a defect before measuring it. Separately an authorized reconcile must fold red-shade-9740 and explicitly supersede iteration 100's unsupported accounting evidence; this contributor dispatch cannot do it. The unreconciled tail remains pending.

Full required CLI suite: `pixi run python -m pytest cli/tests -q` — 465 passed, 1 skipped in 464.11s, exit 0. `git diff --check` passes. No known new broken tree. Engine suites, packaged gate and shell gate were not run because those zones are unchanged.

Dispatch closed: 1 unit — repair Unicode video downloads and verify real Lark playback/download on the persistent dashboard.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 23a6760b51816fd4217763db7df91357530ba1e8

## State Impact

- target: candid-harvest-2614 — D4 maintenance: Unicode retained filenames no longer crash download headers; Chromium verifies original name and bytes. Real lark98-final decode/playback/hash-equal download passes after persistent server restart; 465 CLI tests pass, 1 skipped.
- target: chilly-union-8972 — ADR-323 encodes download filenames with an ASCII fallback. For accounting, explicitly supersede iteration 100 civic-nest-8285 as standalone bounded-accounting evidence: the aggregate traversal and partial-size bound is established by red-shade-9740, not civic-nest-8285 alone.
- target: crisp-sun-1239 — D4 filename-dependent download defect fixed and tested; no new lifecycle completion claim. Correct the bounded-accounting summary using red-shade-9740 and explicitly supersede iteration 100 civic-nest-8285 unsupported standalone evidence; reconcile remains pending under this dispatch prohibition.
- target: deep-clover-6012 — Persistent server remains on ot5-lark-copy85 with lark98-final selected after restart; real final video plays/downloads, historical lark98-checkpoint20 selection and return to current pass. No training or working-project switch.
