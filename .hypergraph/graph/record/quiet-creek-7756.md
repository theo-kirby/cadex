---
node_id: daabaedc-fcdb-5d70-9877-21b628033ccc
slug: quiet-creek-7756
title: Fix bundled demo SPDX headers and keep saved script revisions consistent
created_at: '2026-09-05T09:17:11+00:00'
parents:
- smooth-lantern-7016
- dawn-oak-0677
summary: ''
---
## What

Correct the bundled biped demo's missing GPL-2.0-or-later SPDX headers in its working script and single saved history snapshot.

## Why

The owner requested fixing the licensing failure reported by the complete snapshot verification (smooth-lantern-7016). The scripts ship inside the GPL shell and are covered by the existing source-header check.

## Method

Prepended the shell's standard copyright and license declarations. Used the production project_script_revision function to verify the old saved revision and compute the corrected revision from the new source and unchanged parameter/table state. Updated script.json revision references and history.json revision, filename and character count; replaced the old hash-named history file. Geometry digest and policy bytes remain unchanged. AST comparison confirms executable content is identical.

Copied the corrected store into a temporary directory and opened it with restore enabled through the real cadexd CLI client. Rebuilt the bundle, removed its obsolete installed history file (CMake install copies without pruning), and checked every bundled demo-store file against source. Documented the correction under ADR-173 and in docs/BLENDER.md.

## Result

The licensing suite passes: 10 passed, 1 skipped (payload-only check without CADEX_ENGINE_ROOT). Real-engine demo restore performed and matched the accepted digest 6752e7daa12458cec2e7c945a6c97f3b60471bcde851d0891edb8a59574e5a72. The bundle build passes; its demo matches source byte for byte. Source diff whitespace check passes.

`pixi run gate` passes against the rebuilt bundle: ok true, picking fidelity 1.0 and slider latency within its 0.65-second bar.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 253db45f709d24b5193bfa5320a27d3efd72dc84

## State Impact

- target: easy-wind-9848 — bundled biped working and history scripts now declare GPL-2.0-or-later; licensing suite passes, with matching saved revisions and a real-engine restore reproducing the accepted geometry digest
