---
node_id: b7dfb486-a069-5276-9046-aebd32fb808a
slug: calm-grove-2647
title: Keep review documents open across live dashboard polls
created_at: '2026-09-13T02:37:40+00:00'
parents:
- tender-vine-9199
summary: ''
artifacts:
- docs/probes/wren-fresh/AGENT-REVISION.md
- docs/probes/wren-fresh/document61-evidence.json
---
## What

Fixed the inspection dashboard closing its open document on every live poll (ADR-306). Added browser regressions for accepted/historical reading, arrival of a newer current run, and a superseded document response. Updated the user-facing CLI contract and Wren operator report with compact real-browser evidence.

## Why

Follows tender-vine-9199 and advances D2/D10 through reliable inspection of retained specs and decisions. The critic first requested one bounded product-agent revision using Wren's comparison; the public CLI again returned the provider session-limit error before authoring. Per the critic's explicit fallback, this unit instead fixes a demonstrated review defect with a failing regression. It does not count another refusal as lifecycle progress, substitute caller-authored geometry, or repeat a preservation audit as the unit. Wren's D9 product-agent revision gap remains open.

## Method

Inventoried the active copy's runs/assets and retained one fresh bounded prompt under evidence/agentrev61. Invoked timeout --signal=TERM --kill-after=10s 900 ./cadex --project <cadex-projects>/ot5-wren-copy54 --out <project>/evidence/agentrev61/output --json -p <retained prompt>. The prompt supplies the retained comparison, requests one agent-chosen geometry change, disables the model-bound policy before changing geometry, preserves task/history, and forbids training. Stored claude-sonnet-5 returned exit 1 with no outputs or accepted revision. No second provider attempt followed.

The new parametrized Chromium regression failed on the old source for accepted and historical documents: the first refresh hid doc-view. The fix preserves its loaded text across polls, labels explicit link-click refresh, suspends automatic current following while reading, and clears text when view/revision changes. A request sequence rejects superseded responses. The final browser regression publishes a new fixture attempt during document reading, verifies preserved selection and visible current navigation, then resolves a delayed old document after switching and loading a newer one.

The project-local browser.py opened the persistent private-network URL on port 8765, verified project/run/model identities, and read decisions in current wren57-retry, accepted now, and historical wren2-final through 6.5 seconds of automatic polling each. Return-to-current clears the historical document and selects wren57-retry. Inspected the screenshot of visible historical decisions with its snapshot and loaded-on-open labels. A project-local copy of check_video.py redirects only evidence output paths to the fresh directory: the existing retry video fully decoded, played through three polls and downloaded with its recorded SHA-256. No temporary server, restart or experiment training. Raw prompt, refusal, inventories, probes, screenshots and logs stay project-local; compact identities are docs/probes/wren-fresh/document61-evidence.json.

## Result

Persistent service remains active on ot5-wren-copy54, default wren57-retry, accepted/playback revision 79f86c69bfc38dbf650f266446f256a72dd5547f3eaa386c7328ce85c81224fa. Historical wren2-final remains 26332a5955e3a044b968e3ec14eec809d2090dfe10922c4f242c1a5a12bdc477. All 465 prior run/asset files remain byte-identical. Current video hash 4d418967d41c1fe39b3ec2fa6945a0e8b5cf18343c4e3f5b1d0cf3dffbc3945e matches its browser download; 81 frames decode at 10 fps, 8.1 encoded seconds for eight simulation seconds. These are same-machine private-network checks, not second-device or new D11 visual-reference evidence.

Verification: bounded-thread full CLI suite 400 passed, 1 skipped in 381.31 s. Final document regressions 3 passed, 34 deselected in 4.12 s; the delayed-response case was added after full-suite collection and is covered by this final targeted pass. Sequential engine suite 2110 passed, 53 skipped in 253.28 s. Both full gates exit 0. git diff --check passes; hypergraph export/check is required before commit. No new dependency, build, engine/protocol/payload/shell change or state/view edit. Deliberately loaded document text refreshes by clicking its link, rather than changing under a reader; the page labels this. Provider capacity still prevents the requested Wren product-agent revision, and no new gait/design result is claimed.

Dispatch closed: 1 unit — preserve document reading across live dashboard polls with persistent Wren and browser-regression evidence.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: c784562aea3cc9bdd0a1aa5c1c997938ca9b6cdd

## State Impact

- target: shy-meadow-0959 — Accepted and historical specs/decisions remain readable across polls; browser regressions cover view changes, newer attempts and superseded document responses (ADR-306).
- target: deep-clover-6012 — Persistent Wren dashboard keeps document reading selected while current navigation updates; real private-address document, model identity and retry playback/download checks pass, service remains active.
- target: silent-river-6649 — Wren product-agent revision still refused by provider capacity; fallback unit fixes a demonstrated review defect, with no caller design or refusal counted as lifecycle progress.
