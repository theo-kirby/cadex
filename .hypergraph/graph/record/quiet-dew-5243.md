---
node_id: d042d4c7-d838-5e8b-aca8-e51c8c535ef1
slug: quiet-dew-5243
title: 'F5: frozen arm create attempt refused by provider session limit'
created_at: '2026-09-14T23:00:18+00:00'
parents:
- western-fox-7010
summary: ''
artifacts:
- docs/probes/ot7/attempts/README.md
- docs/probes/ot7/attempts/heron-refusal.json
---
## What

Dispatched the frozen F5 Heron arm create prompt once in a fresh external ot7-heron project using the existing collector and claude-fable-5. Published docs/probes/ot7/attempts/README.md and a portable refusal receipt, and corrected the runner overview to link the actual attempt.

## Why

Advances F5 accounting (stormy-aspen-5433). The critic requested F4's frozen repair after the documented provider reset, or the frozen F5 arm attempt if the provider remained unavailable. At 18:58 America/New_York the 20:20 reset was still ahead. This is the requested F5 fallback, not further collector hardening. F4's seed and single repair slot were untouched.

## Method

Ran `pixi run python docs/probes/ot7/runner/run.py heron <external-projects>/ot7-heron --model claude-fable-5`. The collector verified the frozen prompts, persisted the create slot, retained the provider transcript, read fit and inventory, and attempted its bounded one-second holding smoke. No actor script, parameter or accepted-state edit occurred. Full evidence stays in cadex-projects/ot7-heron/evidence; the committed receipt cites project-relative artifacts and their SHA-256 digests, including the original manifest.

## Result

The provider refused with its session limit and 20:20 New York reset after 1.917318514 seconds (CLI exit 1). One provider dispatch, zero completed design turns, zero continuations, zero accepted revisions. Static and swept fit and inventory are unavailable; zero measured pairs and zero failure count do not establish a pass. Smoke exited 1 in 0.113656627 seconds because script.json does not exist; no simulation ran. The collector exited 0 only because evidence collection completed. F5 remains open with an actual refusal, not a design result. Relative to ot6's accepted Heron this attempt has no geometry to compare. No retry or additional attempt was started, and this attempt must remain in final accounting.

Validation: all eleven retained artifact hashes and sizes verified against the manifest; the compact receipt is below 16 KB. `pixi run python -m pytest cli/tests/test_ot7_runner.py -q`: 33 passed in 0.61 s. No product code, protocol, payload, engine or dashboard change; no full suite, build or packaged gate required for this evidence/documentation unit. The initial receipt-generation command used unavailable bare python and wrote nothing; rerunning it through pixi succeeded. No new dependency or new broken product behavior. Assumption: honor the documented reset for F4 and preserve its sole repair dispatch for availability. No fourth prompt, alternate provider, or substitute design edit is authorized by this refusal.

Dispatch closed: 1 unit — record the frozen F5 arm attempt's actual provider refusal.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 19ade7ee6dc1fb9211fe75d46c6f0abb5e68bfd6

## State Impact

- target: stormy-aspen-5433 — Frozen Heron create dispatched once; provider refused in 1.917 seconds before reset. Zero completed design turns or continuations, no accepted revision, fit and inventory unavailable, smoke could not run. Portable receipt and transcript digest retained; F5 remains open.
