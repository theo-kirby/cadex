---
node_id: e24a859f-6663-5e33-a614-0b4170d11030
slug: crimson-trail-6068
title: 'GUI parity slice 3b: the app''s agent sees and measures its design as the CLI''s does (ADR-448)'
created_at: '2026-09-29T11:13:54+00:00'
parents:
- upright-glacier-1185
- warm-spire-8762
summary: ''
---
## What

GUI-parity slice 3b (ADR-448): the app's agent gets what the CLI's has. A `look` tool (the engine's studio render of the accepted revision: images plus the design-language measures). The engine's bounded `fit` and `inventory` blocks at the end of every accepted `write_script`/`edit_script`/`set_params`/`rebuild_model`/`restore_version` reply. `inspect_model` scopes `clearance` and `inventory`. The engine's agent guidance in the system prompt with the shell's tool names. New `mesh_agent/cadex_studio.py` runs `CadexStudio.py` with the payload's `bin/python` and reads `CadexAgentGuidance.md` as text.

## Why

The owner's direction (warm-spire-8762): the app agent designed blind to the design language and to measured fit, the two things ot5–ot10 found an unassisted design needs.

## Method

- Measurement happens in the agent tool layer (`tools._measured`), not in `cadex_backend.Lifecycle`, so slider drags (which share `Lifecycle`) never measure. After the build is adopted on the main thread, `measurement_context` resolves client and engine dir there; a worker thread reads the raw `clearance`/`inventory` values through `_inspect_full` (cached per accepted revision on `_State.measured`) and runs the studio `blocks` kind. `look` uses the accepted `{display, revision}` record hydration already keeps, so it costs no rebuild.
- `_deferred` (now uncalled) deleted. The overlay's `render_views` bullet points at `look` and shrank (3,678 → 3,543 chars, under the 3,800 guardrail).
- `test_prompt_carries_no_api_names` (ADR-123) now holds the add-on's own text and exempts the engine guidance, checking the rest of the prompt is that guidance verbatim: the guidance names calls but ships in the same payload as the API it names.
- The app bundle was rebuilt (`pixi run build-shell`); its first gate run showed the bundle's payload predated the guidance file.

## Result

- Engine-free suite (`bl_mesh_agent.py`): pass, including the new studio-client refusals and "the rest of the prompt is the engine's guidance, verbatim".
- Gate (`pixi run gate`): all 13 new checks pass — build reply carries blocks (fit verdict `fail` on the test pair, inventory appearance `{accent: 1, shell: 1}`), look returns 2 PNGs in the declared palette with the three measures, unknown view refused, `inspect_model scope=clearance` reads the pairs, prompt carries guidance with shell names. GATE `look`: build with blocks 0.653 s, two-view look 4.083 s. Slider median 0.548 s (clean main 0.542 s, bar 0.65 s).
- Gate still `ok: false` on exactly the 8 restore-lockout failures clean `main` has (not touched here).
- Engine suite 2292 passed, 54 skipped. Shell diff only under `mesh_agent/` and `shell/tests/python/`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: gui/shell-agent-parity
- commit: f4a9d5af295952609171e493acadafbe74b927a4

## State Impact

- target: shy-crane-2573 — the app's agent has look (engine studio render via child process), fit and inventory blocks on every accepted build reply, inspect_model clearance/inventory scopes, and the engine's design guidance in its prompt (ADR-448); measured on a worker thread, slider latency unmoved
