---
node_id: bc6c4278-42c0-5106-958b-9f79775ff222
slug: honest-harvest-7271
title: 'ADR-182: transcript copy button, tool-call runs collapse, settings gear, default model Fable 5'
created_at: '2026-08-31T10:10:42+00:00'
parents:
- damp-fountain-8719
summary: ''
---
## What

Chat usability, four owner asks in one unit (ADR-182): the transcript
grows a per-message copy button; a run of consecutive tool calls
collapses into one clickable row; the chat header gains a settings gear
that opens the preferences window; and the default Claude model becomes
Fable 5 (`claude-fable-5`).

## Why

Owner direction 2026-08-31. Text in the transcript could not be
selected or copied at all; ADR-180's long turns made a run of twenty
tool calls read as twenty transcript rows and scroll the conversation
out of the 40-row display window; the assistant/model settings existed
(chat header dropdowns, add-on preferences) but nothing in the editor
said where; and the owner wants Fable 5 as the default model.

## Method

All changes in ours-only files — `mesh_agent/ui.py`, `spaces.py`,
`agent.py`, `__init__.py`, the `bl_mesh_agent.py` suite,
`docs/BLENDER.md`, `docs/DECISIONS.md`. Inherited Blender untouched.

- Copy: Blender's label widget cannot be text-selected (the widget, not
  a setting), so `mesh_agent.chat_copy` writes the whole message to the
  system clipboard from a `COPYDOWN` button on each user/assistant box.
- Collapse: `_transcript_groups` groups consecutive `· tool` status
  rows *before* the last-40 trim; a run > 1 draws as
  `N tool calls — <last>` and expands via one WindowManager flag
  (`mesh_agent.chat_toggle_tools`, session state, never saved). The
  empty streaming placeholder is dropped from display so it cannot
  split a run.
- Settings door: `screen.userpref_show` as a gear in the chat header.
  ADR-074's status-in-the-header rule stands — the pinned header test
  now asserts exactly that one operator and no chat actions.
- Default: `DEFAULT_MODEL = "claude-fable-5"`; enum labels follow. A
  saved preference keeps its stored choice.

## Result

`bash package/app/build_app.sh gate tests/python/bl_mesh_agent.py`
green ("All tests passed."), including the new
`test_tool_call_runs_collapse_in_the_transcript` (grouping, placeholder
handling, history-index carry for the copy button) and the amended
header pin. `pixi run gate` (bl_mesh_agent_cadex.py) green against the
built bundle, `"ok": true`. `pixi run build-shell` re-installed the
add-on into the bundle. ADR-182 appended; `docs/BLENDER.md` chat-editor
section updated same change.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the chat transcript is copyable (per-message clipboard button), tool-call runs collapse to one expandable row before the display trim, the chat header carries a settings gear, and the default Claude model is claude-fable-5 (ADR-182)
