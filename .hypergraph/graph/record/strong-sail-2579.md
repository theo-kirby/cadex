---
node_id: 64d24094-ef49-5fc8-aa83-0984b3851898
slug: strong-sail-2579
title: 'GUI parity slice 2: the agent guidance is engine data both front ends paste in (ADR-446)'
created_at: '2026-09-29T10:30:12+00:00'
parents:
- fond-dawn-4115
- light-hill-1224
summary: ''
---
## What

GUI-parity slice 2 (ADR-446): the part of the CLI's system prompt that is about designing well — proof by measured facts (look, fit, catalog identity, motion fit), the four-step design language, a complete robot, grounded policy inputs, a walking reward, refusals — moved verbatim into engine data, `src/Mod/cadex/CadexAgentGuidance.md`, installed in the payload. The CLI builds `CLI_OVERLAY` from it with its own tool names; the shell will read the same file (slice 3).

## Why

The app's agent is told none of it (its overlay is 60 lines about the API, collisions and blueprints). Two copies of the text would drift. A file, not a `describe_api` field: the text belongs in the system prompt, not behind a tool call, and prose does not justify a response-spec change. A data file crosses no import boundary, so the shell's no-cadex-imports rule holds.

## Method

Extracted by script from the evaluated `CLI_OVERLAY` (from "YOU SEE YOUR WORK WITH `look`" to just before "A FILE THE CALLER HANDS YOU"), then replaced tool names with `{{look}}`, `{{inspect}}`, `{{write_script}}`, `{{edit_script}}`, `{{set_params}}`, `{{rebuild}}`. One CLI-only phrase generalised: "`cadex train` refuses a task" → "Training refuses a task". The new overlay was compared with the previous commit's evaluated string: identical but for that sentence. Tests: `cadex_tests/test_agent_guidance.py` (marker, closed placeholder set, headings, no front-end-only names, CMake install) and `cli/tests/test_agent_guidance.py` (overlay carries the file verbatim; unfilled placeholder and missing marker refused).

## Result

Payload carries `Mod/cadex/CadexAgentGuidance.md` (18,920 bytes). Engine suite 2289 passed, 54 skipped. CLI suite 52 failed / 1026 passed / 2 skipped / 7 errors; failure list identical to slice 1's (browser tests only, Chromium missing on this machine).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/agent-guidance
- commit: 442978a82de5fd8a7a0913fac505175edd117603

## State Impact

- target: forest-wind-0342 — the engine ships the agent guidance (CadexAgentGuidance.md, ADR-446): design language, proof by measured facts, complete robot, grounded policy inputs, walking reward; tool names are placeholders each client fills
- target: chilly-union-8972 — the CLI's overlay is built from the engine's guidance file; only the headless situation, parametric rule, assets/policies, project docs and revision guards stay CLI text
