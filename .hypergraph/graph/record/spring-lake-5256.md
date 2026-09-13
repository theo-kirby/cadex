---
node_id: d2fb7b57-5c30-5b0d-9344-36cb57b77370
slug: spring-lake-5256
title: 'Resolve video lineage from retained identities, not run names: name-free check_video with policy_lineage and default_run readers (ADR-316)'
created_at: '2026-09-13T08:47:51+00:00'
parents:
- scarlet-ocean-2381
summary: ''
---
## What

Removed the run-name dependency the critic named in the fresh-project video checker (`docs/probes/wren-fresh/check_video.py`, which the Lark drivers reuse by path; the critic's message located it under `lark-fresh`). The checker had hard-coded a `-final`/`-checkpoint20` pairing, "a `-final` run is the fresh visit's selection" and eight components, which is why iteration 86's playback had to be named `lark86-retry-video`. It now resolves training/video relationships from retained identities: `cadex_cli.review_record.policy_lineage(root, run)` matches a run's recorded policy digest against the bytes every run retains under its own `train/` (the holder is the origin — `final`, `checkpoint` with the telemetry's iteration, or `retained`; the record's `source_run` is checked against it as `source_agrees`; `playbacks` are the other runs whose policy the same origin retains; symlinks out of the project are refused), and `cadex_cli.review_server.default_run(review)` is the page's fresh-visit rule in Python. The checker checks every declared parameter, takes the component count from the run's own trace, asserts the page's checkpoint-provenance line names the identity-resolved origin, picks the historical run to select afterwards as the latest historical sibling by identity else the latest other historical video run, and takes `--not-default` (with `--historical` kept as its old spelling) plus `--label` so a re-check never overwrites an earlier receipt. Both probe trees' drivers pass `--not-default` for checkpoint checks during active training and for older videos. ADR-316; docs: `docs/CLI.md` (reader and dashboard sections), both fresh-project READMEs and the operator status README.

## Why

The critic asked for exactly this unit: remove the demonstrated run-name dependency, resolve training/video relationships from retained identities, add a regression using unrelated run names, and verify playback/download on the persistent working-copy dashboard — advancing recording reliability under the exhaustion policy rather than another fresh biped or evidence audit. It advances D4 (videos identified by revision, policy digest, seed and time, now with the training run behind each resolved by bytes) and D10 (the persistent URL's default selection verified against the reader's own rule). The critic's first fix — `candid-harvest-2614` counts four Lark videos where four earlier plus the retry make five — is declared as an impact on that state node here, because a work iteration may not edit state nodes. Nothing deviates from the message.

## Method

Read the retained records on the working copy: a playback run's `run.json` carries `policy.sha256` and `training.requested.source_run`; the training run's own `train/` holds the `.cxpolicy` bytes and its `progress.json` lists checkpoints with digests. Wrote `policy_lineage` over that (one hash pass of `runs/*/train`, files ≤ 4 MiB, containment-checked) and `default_run` mirroring `review.js`'s `currentView`. Tried both on `ot5-lark-copy85` before touching the checker: every Lark run resolved by identity (`lark1-checkpoint20` → `lark1` checkpoint iteration 19; `lark86-retry-video` → `lark86-retry` final; `lark86-interrupt` → no policy recorded), default `lark86-retry-video`. Rewrote the checker on the two readers; updated the six driver call sites. Regressions with unrelated names: `policy_lineage` over `kestrel`/`pear`/`quince`/`fig`/`plum`/`apple`/`zebra`/`mango` in `cli/tests/test_review_record.py`; `default_run` over `zebra`/`aardvark`/`mango` in `cli/tests/test_review_server.py`. Ran the rewritten checker on the persistent private-network URL (port 8765, `ot5-lark-copy85`, not restarted, no trainer) for `lark86-retry-video` (default) and `lark1-final --not-default`, both with `--label lineage88`; committed the compact receipt `docs/probes/lark-fresh/lineage88-evidence.json` with a guard test in `cli/tests/test_lark_fresh_evidence.py`. Full CLI suite: `441 passed, 1 skipped` in 417 s (one browser timing test failed once under `-x` and passed on the unmodified tree and in the full run — a flake, not this change). No engine, shell, protocol, payload, page or dependency change, so no engine suite or packaged gate.

## Result

The video checker consults no run name. On the persistent URL a fresh visit selects `RUN lark86-retry-video`, which `default_run` expects; that video resolved to origin `lark86-retry` (final policy, `source_agrees` true, no sibling, so `lark2-final` was the historical selection) and `lark1-final` to origin `lark1` with sibling `lark1-checkpoint20` at checkpoint iteration 19 by identity; both decoded whole (81 and 6 frames), played through three polls and downloaded hash-equal (`1f53d43d1c18…`, `25b363291b40…`). Port 8765 still serves `ot5-lark-copy85` with `lark86-retry-video` default; no trainer active; nothing in the copy overwritten (new `evidence/*-lineage88-*` files only). Lark's video count is five: `lark1-checkpoint20`, `lark1-final`, `lark2-checkpoint20`, `lark2-final`, `lark86-retry-video`. Concerns: the dashboard page itself still shows checkpoint provenance from the record's `source_run` name (which the checker now cross-checks against the bytes), not from `policy_lineage` — a later unit could surface `source_agrees` on the page; the `-recheck`/`-label` evidence naming remains the checker's, not a product contract; same-machine private-address checks, not a second-device test. No new dependency. The unreconciled tail is now one record.

Dispatch closed: 1 unit — the fresh-project video checker resolves a video's training run, its historical sibling and the expected fresh-visit selection from retained identities instead of run names, with unrelated-name regressions and both Lark videos re-verified on the persistent working-copy dashboard (ADR-316).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 67715737a84155e8baecc76b0350e5126e57286f

## State Impact

- target: candid-harvest-2614 — correction: Lark has five videos, not four (lark1-checkpoint20, lark1-final, lark2-checkpoint20, lark2-final, lark86-retry-video); the video checker now resolves each video's training run and historical sibling from retained policy bytes via policy_lineage rather than run names, and lark86-retry-video and lark1-final were re-verified on the persistent URL (decoded whole, played through polls, downloaded hash-equal) with receipt docs/probes/lark-fresh/lineage88-evidence.json (ADR-316)
- target: chilly-union-8972 — two read-only reader functions (ADR-316): cadex_cli.review_record.policy_lineage resolves a run's policy origin (final/checkpoint/retained), source_run agreement and playback siblings from the bytes runs retain under train/, refusing paths outside the project; cadex_cli.review_server.default_run is the page's fresh-visit selection rule in Python; both regression-tested with unrelated run names
- target: deep-clover-6012 — iteration 88 re-verified the persistent port 8765 URL on ot5-lark-copy85 without restart and with no trainer: a fresh visit selects RUN lark86-retry-video, which the reader's default_run rule expects, and historical browsing with return-to-current still holds; the operator status README records it
