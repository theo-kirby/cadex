---
node_id: 42743093-6b6e-5246-b94e-f95889bb5dba
slug: curious-sail-8332
title: 'ADR-183: the assistant becomes application code — scripts/startup, JSON settings, and an AI section in Preferences'
created_at: '2026-08-31T10:54:57+00:00'
parents:
- honest-harvest-7271
summary: ''
---
## What

ADR-183: the assistant becomes application code and its settings get a
real Preferences section. `mesh_agent` moved from
`shell/scripts/addons_core/` to `shell/scripts/startup/` (registered by
the script loader at every launch, `bl_info` deleted, nothing in the
Add-ons list, the Mesh app template's deferred `addon_utils.enable`
deleted); its settings left `AddonPreferences` for
`mesh_agent/prefs.py` (a JSON file, `<config>/cadex_agent.json`,
mirrored into a WindowManager `PropertyGroup`, saved by property
`update` callbacks); and the Preferences window grew an **AI** rail
entry — `USER_SECTION_AI = 20` in `DNA_userdef_types.h` plus one row in
`rna_enum_preference_section_items` (`rna_userdef.cc`) — holding two
panels (AI Assistant, Engine) registered from `prefs.py`
(`bl_context = "ai"`). The chat header's gear opens
`screen.userpref_show(section='AI')`. The headless CLI's default model
also moved to `claude-fable-5`.

## Why

Owner direction 2026-08-31: Cadex is its own application, not "Blender
plus an add-on" — the Add-ons page did not even show the assistant, the
settings were buried under add-on machinery, and the product must not be
built around an optional component. Follows the same session's ADR-182
(transcript copy, tool-run collapse, default model Fable 5), which is
what surfaced the discoverability hole.

## Method

Two recon passes first (Preferences-section machinery; everything
coupled to add-on identity — enablement chain, path references, startup
loader semantics, get_prefs call sites). Ten traps identified and
handled, the load-bearing ones: `keyconfigs.addon` does not exist when
startup modules register (`WM_keyconfig_init` runs later), so the
landing screen's and drawings editor's keymaps install from a deferred
timer retried until ready; `register()`/`unregister()` made idempotent;
each of the four Blender harnesses unregisters the bundled copy, purges
`sys.modules`, and imports the source copy so the suites keep testing
the tree; the manifest's `ours` needed BOTH path prefixes (the import
commit was the mesh-repo snapshot, which already carried mesh_agent at
the old path); `build_app.sh` now prunes the pre-move copy from
existing build trees (CMake install never deletes). Engine-side
guardrails re-pointed (`test_engine_purity_guardrails.py`,
`test_licensing_compliance.py`). Inherited-file cost: one enum value in
an already-§2a-manifested DNA header plus one RNA row — manifested,
noticed via `tools/apply_modification_notices.py`, ledgered in
BLENDER-TREE §2b. No exhaustive switch exists over `eUserPref_Section`,
so no other C moved. Docs renamed the path and dropped the add-on
language (AGENTS, BLENDER, BLENDER-TREE, ARCHITECTURE, VISION,
INTEGRATION, PROVENANCE, SECURITY, PRIVACY_POLICY, ROADMAP, CLI);
DECISIONS.md history left as written. Internal package name kept —
renaming `mesh_agent` touches the pinned `mcp__mesh__*` tool surface and
is its own decision.

## Result

All green against the rebuilt bundle: headless smoke run (13/13 —
auto-registration from `scripts/startup`, no `bl_info`, absent from
`preferences.addons`, AI on the rail, both panels registered, defaults
claude/claude-fable-5, JSON round trip both ways);
`bl_mesh_agent.py` "All tests passed"; wiring suite exit 0; `pixi run
gate` `"ok": true` with `engine_from_bundle: true`; `cli/tests` 83
passed; licensing + purity guardrails pass except the two known
non-regressions (manifest test diffs committed state, so it goes green
at commit; the biped-demo SPDX gap predates this change, ADR-181).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — mesh_agent is application code registered from scripts/startup (not an add-on, no bl_info, nothing to enable); its settings live in prefs.py (cadex_agent.json + WindowManager PropertyGroup) drawn in a new AI section of the Preferences window (USER_SECTION_AI, one DNA value + one RNA row); the chat gear opens that section; the Mesh template no longer enables anything; harnesses swap the bundled copy for source; the CLI default model is claude-fable-5 (ADR-183)
