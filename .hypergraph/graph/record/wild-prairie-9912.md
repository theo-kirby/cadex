---
node_id: fb7c26ef-f83d-5445-bea2-6214e8dc320b
slug: wild-prairie-9912
title: 'ADR-179: the Blueprint Editor window — CADEX_BLUEPRINT space type by the §2b checklist, one selection per editor, viewport keeps only the restyle'
created_at: '2026-08-30T17:36:26+00:00'
parents:
- winter-bloom-8543
summary: ''
---
## What

ADR-179: the Blueprint Editor becomes a window of its own —
`SPACE_CADEX_BLUEPRINT = 31`, the seventh Cadex space type, added by the
BLENDER-TREE §2b checklist's first single-editor run. Each editor area
carries its own selection (the live ADR-178 draft, or any sheet in the
project's blueprint store), so two windows show two drawings side by
side; the controls (sheet menu — draft first, store newest-first —
pager, Save, Export) live in the editor's header; the window's ground is
the theme of the sheet it shows. The viewport keeps only the ADR-150
restyle: its settings box in the Parameters panel is removed, and the
ADR-178 in-viewport draft display is removed with it (`cadex_drawings`
no longer touches `SpaceView3D`).

## Why

Owner direction on ADR-178's heels: a dedicated blueprint editor window
("we are gonna end up making a lot of new windows so might as well get
good at it"), multiple windows viewing different blueprints, controls in
the window, blueprint settings out of the Parameters panel, the window
background matching the sheet's style. This is the §2b spend ADR-178
explicitly deferred, now owner-authorized.

## Method

C++: cloned `space_cadex_live/` → `space_cadex_blueprint/` (two files of
ours) and added one row per inherited touch point per the §2b checklist
— DNA enum + `SPACE_TYPE_NUM` bump, bare `SpaceLink` DNA struct (no
fields, gate-pinned), `ED_space_api.hh`, `spacetypes.cc` (the editor
menu), two CMake lists, `rna_space.cc` (menu row `Blueprint Editor` /
`ICON_IMAGE_DATA`, refine case, struct definer + call),
`BKE_context.hh`/`context.cc`, `screen.cc` header/footer lists,
`resources.cc` two theme sites, `bpy_rna_callback.cc` (draw handlers),
and the three `-Wswitch` files. All sixteen inherited files were already
manifested and noticed → `docs/inherited-modifications.json` untouched,
licensing test green. Python: `cadex_drawings.py` rewritten — per-space
selection registry keyed by `space.as_pointer()` (session state; DNA
must stay bare), header + menu + select/step/save/export operators,
POST_PIXEL draw on `SpaceCadexBlueprint`, clicks via two `poll`-gated
items on the Window keymap (params-clone spaces install no keymap;
unhandled clicks bubble to window handlers), stored-sheet index read
restored from ADR-177 (disk, never the inspect pager), all guarded by
`EDITOR_AVAILABLE` for bundles predating the C++ half (the `wiring_ui`
arrangement). `make_blueprint` reply now says whether an editor is open
and suggests opening one (no auto-open — ADR-165 holds).

## Result

`pixi run build-shell` exit 0 (full 2230-target rebuild; the DNA enum
touch rebuilds wide, `-Wswitch` confirmed every exhaustive switch).
Headless suite exit 0, "All tests passed" — seven-editor pins
(`KEPT_EDITORS`, `test_cadex_editors_are_registered` including the
no-own-DNA-properties check on `SpaceCadexBlueprint`), the
selector/caption/hit-test pure tests, the over-1-KiB disk-index
regression kept. `pixi run gate` exit 0, `ok: true` — the new ADR-179
block passes headless: the space type exists, `area.type =
'CADEX_BLUEPRINT'` takes in `--background`, a fresh editor opens on the
draft, selections are per-space. `test_licensing_compliance`: 9 passed,
1 pre-existing failure (biped-demo script headers, predates this work);
the manifest tests green with zero manifest edits. Windowed probe
(scratchpad copy of mgactu): 24/24 checks — draft renders into the
editor (`make_blueprint` reply names it), click in the editor region
hits cell 0 and drains as `@cell-1`, save grows the store exactly once,
re-draft never grows it, **two editors hold two selections and the
final screenshot shows the stored technical sheet (paper-white ground)
above the live blueprint-theme draft (blue ground), each with its own
header controls** — probe_bp_4_two_editors.png in the session
scratchpad; the byte-identical-screenshot pitfall (an area flip needs
an event-loop tick before DRAW_WIN_SWAP repaints) is recorded in the
probe. `pixi run install-app` exit 0; installed add-on files
byte-identical to source.

Known limits, stated: per-editor selections are session-only (a
reopened file starts on the draft or newest sheet); tagging works on
the draft, stored sheets are view-only.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: cc1e711b0a2877c8dd5ae455ee908ef1bd3b27f5

## State Impact

- target: shy-crane-2573 — the drawing is a window of its own: SPACE_CADEX_BLUEPRINT (seventh Cadex editor, first solo run of the §2b checklist), per-editor selection of draft or stored sheet so multiple windows show multiple drawings, controls in the editor header, ground matching the shown sheet's theme; the viewport keeps only the ADR-150 restyle and the Parameters panel loses its blueprint box
