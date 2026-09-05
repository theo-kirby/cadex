---
node_id: f893aacc-1c39-529b-acd1-f70b1d841a15
slug: calm-flame-0305
title: The drawings browser reads the store off disk — the inspect pager stubbed every real sheet list
created_at: '2026-08-30T13:53:09+00:00'
parents:
- cool-jasper-0086
summary: ''
---
## What

The stored-drawings browser (ADR-177) showed a full store as empty. Its
list read went over `inspect scope=blueprint`, and the inspect pager
stubs any value over 1 KiB — every real store's entry list is bigger
(the owner's projects measure 2.7 KB to 108 KB), so `blueprints` came
back as a stub dict and the browser listed nothing. Fixed by reading
the store directly: `cadex_drawings.read_index(root)` opens
`<project>.cadex/blueprints/blueprints.json` beside the .blend
(schema-checked `cadex-blueprint-v1`), the tessellation-artifact
precedent — and the browser now also works before the engine session
is open. The assistant's own scope read is unaffected: it resolves
stubs through `_inspect_full`.

## Why

Owner report, minutes after install: "the blueprint mode in sheets
doesn't show any that exist but they are there — look for the folder in
the same directory as the blend with the same name, then the
blueprints folder in there." That folder is exactly what
`cadex_backend.project_root` already derives.

## Method

Diagnosed from the pager contract (`_inspect_full`'s docstring states
the 1 KiB stub rule; `read_blueprint` already routes around it), then
verified against all 13 real stores under `~/arch` — every index over
the stub limit, every sheet file resolving via `_sheet_path`.

## Result

`read_index` replaces the protocol read; new suite assertions pin the
regression (an over-1-KiB fixture index lists in full; a missing folder
is an empty store; a malformed index is an error). `bl_mesh_agent.py`:
exit 0, All tests passed. App rebuilt and reinstalled. ADR-177's text
and `docs/BLENDER.md` corrected in place (both uncommitted from the
same session).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — cadex_drawings lists sheets via read_index on <project>.cadex/blueprints/blueprints.json rather than inspect scope=blueprint, whose pager stubs every real-size entry list
