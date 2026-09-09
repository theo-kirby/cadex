---
node_id: 4675e33f-e6cb-58d9-8072-33764196409c
slug: humble-sky-8445
title: Resumed agent turns receive current project decisions and domain notes
created_at: '2026-09-08T20:44:21+00:00'
parents:
- easy-delta-3016
summary: ''
---
## What

Pinned history-aware resumed prompt turns with one behavioral regression in cli/tests/test_turn_loop.py. Updated CLI documentation and the corresponding ROADMAP checkbox. No runtime or scaffold change was necessary.

## Why

Advances the charter's "The walk exists and is tested headlessly" criterion and its project-as-codebase/iterate requirement, targeting crisp-reef-5607 and calm-peak-5247. The overseer explicitly replaced the seed study with a history-aware resume regression when provider capacity is unavailable. The supplied Claude five-hour usage remains 100%; no new capacity signal exists. Chose that reversible fallback without quota probing, provider dispatch, seed study, or training experiment.

## Method

Two scripted model turns run command_prompt through the real engine and bridge. The first accepts a plate and writes a decision plus sensor/gear-ratio notes. Between visits the test adds architecture, sensor-offset and prior-clearance context. At the resumed factory boundary it asserts the original session id, project cwd, prior decision, both domain notes and all new context. The second accepts changed geometry and appends a decision and sensor note while preserving existing text.

Targeted regression: 1 passed, 16 deselected. Negative control: an external temporary pytest plugin replaces read_project_docs with an empty result; the regression fails on missing architecture context (1 failed), without changing tracked runtime source. An initial test assumption that command_prompt alone appends progress was incorrect: main owns that step; corrected the fixture to provide explicit between-visit progress evidence. No product omission found.

## Result

Full required CLI gate: `pixi run python -m pytest cli/tests` — 245 passed, no skips, in 227.57 s. Output remains local at `/tmp/cadex-iteration32-cli.log`; negative-control output at `/tmp/cadex-iteration32-negative.log`. `git diff --check` passed. No build required for test/doc-only changes.

The test verifies delivery and persistence, not actual model understanding, Claude resume transport, training, or a full walk. No current charter box can newly be ticked from this unit alone. The next history-guided geometry/train/review iterate still requires a supplied capacity signal and must preserve the existing bounds and artifact exclusions; no quota probe or clock-based waiting unit is authorized. The lifecycle implementation remains unchanged and its prior end-to-end evidence stands. No removal or direction change, so no new ADR is required. No generated output is committed.

Dispatch closed: 1 unit — pin current project history on resumed agent turns.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 82f029c639db7e18cd5de4c9355cce03fdccd378

## State Impact

- target: crisp-reef-5607 — Real-engine resumed-turn regression pins fresh project context delivery and note persistence; 245 CLI tests pass, live provider-guided iterate remains unmeasured.
- target: calm-peak-5247 — Existing decisions, domain notes and between-visit architecture/sensor/progress edits reach resumed agent context; no runtime omission found.
