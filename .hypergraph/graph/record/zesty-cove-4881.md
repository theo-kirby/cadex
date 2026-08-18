---
node_id: 5dfa0632-f457-55b8-ad8b-561f50b779a7
slug: zesty-cove-4881
title: 'ADR-149: the exploded view rides the display entry, and the shell interpolates it'
created_at: '2026-08-18T12:49:57+00:00'
parents:
- grand-peak-3688
summary: ''
---
## What

The exploded view a user can see (ADR-149), end to end. The engine half of
the feature existed since `assembly.exploded_view` did — staged moves, final
placements and leader lines, all computed and validated in the worker — and
every byte of it died there: the output's display entry was all-nulls and no
shell code read it. Now the worker attaches a compact record
(`_exploded_display_record`) to the exploded-view output's item,
`cadexd._display_block` copies it as the fourth optional display key (after
`measurement`/`mesh_check`/`stress`), `CadexdProtocol.NESTED_RESPONSE_SPECS`
pins its shape, and a new shell module
(`mesh_agent/cadex_explode.py`, cloned structurally from `cadex_section.py`)
interpolates it: a toggle plus a factor slider 0→1, staged windows (stage i
of N owns factor [i/N, (i+1)/N]), lerp positions, hemisphere-corrected slerp
orientations, leader lines growing with each component's own staged
progress. The moves are engine-declared — the AI authors them in the script;
the shell invents no geometry.

## Why

Cadex had no exploded view a user could see, and an assembled mechanism
hides its own construction. Two owner decisions framed the build: source is
engine-declared, gesture is toggle + factor slider with live interpolation.
The wire route is the ADR-139/144/145 display-key pattern rather than a
retained artifact, because an artifact's hash would enter the restore digest
and demand byte-reproducible native readback. The shell applies poses via
`matrix_world` re-applied by the hydrate hooks (engine poses first, spread
after, always) rather than delta channels, whose composition with
`matrix_world` assignment is undocumented. A baked simulation REFUSES the
toggle: F-Curves and matrix_world writes cannot share an object honestly.

## Method

Plan executed in six stages on top of the uncommitted S0–S4 + ADR-148 tree.
Engine: `_compact_pose` (quaternion xyzw, the simulation-trace convention) +
`_exploded_display_record` (pure dict→dict) in `cadex_assembly_worker.py`;
item-key write beside `assembly_data`; fifth optional-key block in
`cadexd._display_block`; protocol pins; unit test on a synthetic dict plus
`test_cadexd_serves_an_exploded_view_display_record` (jointed two-component
assembly, two staged moves on one component, cumulative stage poses
asserted). Shell: pure half unit-tested in `bl_mesh_agent.py` (staged
windows at t=0/0.5/0.75/1, slerp midpoint, hemisphere flip, matrix
decomposition, one-output rule, line growth);
`test_the_exploded_view_spreads_the_assembly` in the gate — the factor-0.5
viewport-vs-pure-half check written first, then factor 1 vs `final_poses`,
restore on 0/off, sibling "Exploded Lines" collection, `set_params` rebuild
keeping the spread from the NEW record, preview drag surviving settle,
baked-simulation refusal, suspend round trip, revision unchanged.

## Result

All green: `pixi run test-engine` 1853 passed; packaged lifecycle gate
against the staged payload 13 passed; `pixi run gate` OK
(`GATE["exploded_view"] = {stages: 2, factor_step_seconds: 0.0}` — a factor
step costs under 0.1 ms, against the 6.3 ms section cut and the 0.65 s
slider bar); `bl_mesh_agent.py` all passed; `cli/tests` 80 passed with zero
changes — the protocol pin is what keeps its reply validation green.

Two findings worth keeping. **The packaged gate caught ADR-023's class of
miss again**: `CommandCreateView.py` imported `pivy` bare at module scope;
the pixi environment carries pivy so the source tree passed, the payload
prunes it so the staged engine failed on the first exploded-view script.
Fixed with the guard shape `JointObject.py` already carries (`coin = None`;
only never-instantiated view providers use it). **One gate flake observed**:
a slider-latency run at 0.762 s median against the 0.65 s bar under machine
load right after the shell build; the re-run passed at 0.496 s with the
exploded-view checks green both times.

This deepens the engine's `CommandCreateView` import — ROADMAP Phase 8's one
non-mechanical obstacle. The out is known: `_calculateExplodedPlacements` is
~40 lines and portable into the worker; the display key is the seam that
makes that port invisible to clients. Deliberately not taken now.

(Working-tree note: this work is stacked on the uncommitted S0–S4 and
ADR-148 arcs on `main`, base commit be7ff63d; the engine and shell halves
are separable for the two-commit landing the plan asks for.)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: be7ff63d8766f3cede9545152af00a5e01c06fe8

## State Impact

- target: forest-wind-0342 — the exploded-view output's display entry now carries an optional exploded_view record (assembly_output, bounds, staged cumulative poses, final_poses, leader lines), copied by cadexd._display_block and pinned in NESTED_RESPONSE_SPECS as the fourth artifact-less display key; the preview path drops it by design (skip_derived); CommandCreateView's bare pivy import is guarded so the packaged engine serves it
- target: shy-crane-2573 — mesh_agent gains cadex_explode.py (a view, not a feature, the ADR-148 shape): toggle + factor slider 0→1 interpolating engine-declared staged moves via matrix_world re-applied by the hydrate hooks, leader lines as a wire object in a sibling Exploded collection, exploded_view agent tool, render_views suspend; refuses while a simulation is baked; one exploded view per model
