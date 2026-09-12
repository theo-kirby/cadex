---
node_id: b0164fb3-4873-56d7-8370-2065b2b82ac3
slug: neat-vine-2517
title: Prevent overlapping browser polls during initial video verification
created_at: '2026-09-12T20:38:39+00:00'
parents:
- young-cedar-2719
summary: ''
artifacts:
- docs/probes/video-history/README.md
---
## What

Bound dashboard polling to one pending request per browser page during slow initial retained-video verification (ADR-297). Added a headless-browser fault-injection regression and documented the remaining cold-read and multiple-client limits.

## Why

Advances D3 bounded review operation and D8 integrity under the critic's explicit initial-verification fallback. First retried the requested product-agent-authored, review-informed physical revision on the independent Reed copy. The product CLI returned exit 1 on session quota before authoring. No actor-authored substitute revision, training, video or D9 completion claim. This work follows young-cedar-2719's measured 7.04-second initial verification and resolves the demonstrated overlapping polls, not the underlying initial byte-read latency.

## Method

The product request used timeout --signal=TERM --kill-after=10s 240 ./cadex --project "$COPY" --out "$COPY/evidence/revision33" --json -p <read retained review, decisions and ten-seed comparison; author, document and accept one reasoned physical revision; do not train or render>. Project-local evidence/revision33-agent.json and .stderr retain the receipt. claude-sonnet-5 reported "You've hit your session limit · resets 5:30pm (America/New_York)"; accepted_revision was empty, with no authoring success.

The browser now shares one pending poll promise across timer ticks and explicit refreshes and clears it on settlement. No project state or verification result is added to this browser coordination. The new test blocks a video hash for 7.2 seconds across three actual two-second timer ticks. It asserts loading and no playback while verification is pending, exactly one read, digest-mismatch refusal on release and a subsequent run-status update without reload. The fixture is synthetic corruption and controlled delay, not real video or GPU telemetry evidence.

pixi run python -m pytest cli/tests/test_review_server.py -k coalesces -q: 1 passed, 28 deselected in 9.09 seconds. A control served a temporary copy of review.js with only the pending-request guard removed through STATIC_FILES, without rolling back product source. The same test failed in 8.33 seconds: four simultaneous byte reads rather than one. The test releases its hash barrier even on failure.

## Result

A slow initial verification no longer multiplies hashing requests from one browser page. Integrity refusal and later polling remain visible. First verification still reads every uncached video; separate browser pages can still verify concurrently. This does not tick D9 or establish a new universal five-second telemetry bound. No new dependency, engine, shell, protocol, payload, generated state/plan or charter change; no full build needed or performed.

Validation: full CLI suite 367 passed, 1 skipped in 338.96 seconds; full engine suite 2103 passed, 54 skipped in 278.85 seconds. git diff --check passed. No packaged or shell gate required for this CLI-only change.

Dispatch closed: 1 unit — prevent overlapping browser polls during slow initial video verification after quota-blocked revision authoring

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 44ccf925cb6dabbd861ee70bde5cdbf04b6f3918

## State Impact

- target: dawn-delta-4361 — One pending poll per browser page prevents four concurrent reads during 7.2-second initial verification; cold-read latency and multiple clients remain unbounded.
- target: cool-gate-3332 — Browser regression proves loading without playback during verification, corrupt-video refusal and subsequent status polling after release.
- target: silent-river-6649 — Product-agent review-informed physical revision again refused on session quota before authoring; D9 remains open, explicit critic fallback taken.
