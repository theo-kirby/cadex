---
node_id: e415ccd8-63d7-5821-9501-90f153646bdd
slug: still-wave-6655
title: 'Printable parts: mark an output, then one click to STL (ADR-156)'
created_at: '2026-08-20T18:31:39+00:00'
parents:
- humble-peak-6095
summary: ''
---
## What

**A model can now leave for a slicer.** Tick which outputs are parts you mean to
print, then **File → Export Printable Parts…**, and the engine writes one STL per
marked part into `<project>.cadex/print/`, each at its own origin. A second export
refuses and asks Overwrite or Keep Both. ADR-156.

Two new protocol ops (`set_printable`, `export_printable`), one new pure engine
module (`CadexPrintables.py`), a sixth spec/value pair in `script.json`
(`print_specs` / `print_values`), a `printable` block on `inspect scope="script"`,
and shell-side a `cadex_print.py` cache, a per-row checkbox operator in the
Parameters editor, and one File-menu row with its conflict dialog.

## Why

Cadex could build an assembly and could not hand it to a slicer. The only STL path
was `_tool_export_stl` (`tools.py:1140`) — an **AI tool** rather than a menu item,
which exported the Blender **display mirror** rather than the accepted solid and
wrote beside the `.blend` rather than into the project store. Wrong geometry, wrong
place, reachable only by asking the model for it in words.

Three decisions carried the design, and two of them are the interesting ones:

1. **The engine writes the files**, because `docs/ARCHITECTURE.md` says cadexd is
   the store's sole writer. The rule settles it; the result is better anyway on
   three counts the rule was not arguing for — the mesh comes off the accepted BREP
   rather than a viewport tessellation, the call works headless with no Blender in
   the process, and each part lands **in its own frame for free** (the staged
   `.brep` is written in that frame; assembly placement lives in the display block
   the shell applies). A slicer wants a plate to lay out, not a model posed as it
   was assembled.

2. **The marks are not a `set_params` table**, though they would have been the
   sixth and the pattern was right there. `set_params` feeds
   `CadexScriptedDomains.project_script_revision`, so a mark routed through it would
   enter the content hash and buy **a full rebuild for every tick of a checkbox**.
   `set_printable` therefore validates, writes the store and returns: no worker, no
   rebuild, no revision bump.

3. **The specs are the accepted output roster, not a script global.** There is no
   `printable(...)` and the AI never declares printability. Every other table's
   specs are a declaration the script makes; this one's are the `brep`/`mesh`
   outputs the last accepted run published, harvested in `validate_project_result`.
   That is the better fit rather than the cheaper one — the `result` dict already
   declares the outputs, and printability is metadata *about* an output rather than
   a new declared entity — and it removed roughly half the planned work (no
   collector module, no worker change, no `describe_api` block, no threading through
   `prepare_project_candidate`).

## Method

**Engine.** `CadexPrintables.py` is pure Python with no FreeCAD, beside `CadexCage`
and the four other table modules: `roster_from_outputs`, `canonical_printable_rows`,
`declared_printables`, `prune_printable_rows`, `effective_printables`, plus
`stl_file_name` / `allocate_file_name` for names on disk. `CadexScriptStore`
gained `print_specs`/`print_values` through the same defaults merge every other pair
uses, so a pre-ADR-156 `script.json` needs no migration.
`validate_project_result` harvests the roster and prunes the marks against it —
two lines, and the whole rebuild-side integration. `_op_set_printable` refuses a
requested unknown name (`UNKNOWN_PRINTABLE_OUTPUT`, roster in `observed`);
`_op_export_printable` resolves the whole job before writing any of it, refuses on
collision with the file list attached (`PRINT_FILES_EXIST`), and writes atomically
per file. BREP outputs go through `cadex_tessellation.tessellate_shape` rather than
`MeshPart.meshFromShape` — already in cadexd's declared closure, and `BRepMesh`'s
skip-already-tessellated behaviour is the digest hazard `cadex_part_worker` documents.
`CadexPinResolution.staged_artifact_path` was made public so both callers share the
containment check.

**Shell.** `cadex_print.py` caches the roster and pushes a flipped list; the cache
costs no round trip because the roster rides in the `inspect scope="script"` block
`_adopt_script_state` already takes on open and after every accepted rebuild.
`ui.py` draws one operator row per entry (an operator, not a `BoolProperty`, so no
runtime `PropertyGroup` registration); `topbar.py` adds the File row and the
Overwrite / Keep Both dialog, built from the engine's refusal rather than from a
directory listing the shell is not allowed to take. Neither operator sets
`bl_options` — a store write is not a scene edit.

**Verification.** `pixi run python -m pytest src/Mod/cadex/cadex_tests`,
`pixi run build-engine && pixi run stage-engine` plus the packaged lifecycle gate,
`pixi run build-shell && pixi run gate`, `bl_mesh_agent.py`, `cli/tests`, a
scratch end-to-end run against a real cadexd, and two windowed probes of the built
bundle (panel draw + screenshot; conflict dialog).

## Result

**All green.**

- Engine suite: **1899 passed, 33 skipped** (was 1871 before this work; 26 of the
  new tests are `test_printable.py`).
- Packaged gate, `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64`:
  **14 passed**, and the payload carries `CadexPrintables.py`.
- `pixi run gate`: `"ok": true`, with
  `"printable": {"bytes": 684, "files": ["bracket-002.stl", "bracket.stl"],
  "outputs": ["arm", "bracket"]}` — a two-part model whose roster is both outputs,
  one ticked, one 684-byte STL out, the second export refused **by name**,
  `keep_both` leaving two files. The gate also asserts the revision guard does
  **not** move across a tick, which is claim (2) above stated as a test.
- `tests/python/bl_mesh_agent.py`: all passed, `mesh_agent.export_printable`
  resolving in the built bundle.
- `cli/tests`: 83 passed. The CLI's model-facing surface is an explicit allowlist
  (`CLI_TOOL_OPS`), so the two new ops are not exposed there — `put_blueprint`'s
  standing exactly.
- Against a real cadexd: a `part.box(40, 25, 15)` came back as **12 triangles
  spanning exactly `[0,0,0] … [40,25,15]`**, measured out of the binary STL rather
  than asserted — the part at its own origin. A mesh output round-tripped through
  its staged PLY the same way. Marking, dropping and re-marking behaved: a rewritten
  script that stopped publishing `hull` silently lost its mark, and asking for
  `hull` afterwards was refused with the roster attached.

**One thing the plan did not predict.** A windowed probe of the built bundle showed
the Print box drawing **nowhere**: `CADEX_PARAMS_PT_parameters.draw` returns early
when a model declares no parameters, and a plain `result = {"bracket": part.box(…)}`
is exactly the model somebody wants to print. The box is now drawn on the way out of
that branch too, through one shared `_draw_printable`. A second probe caught the row
layout — a full-width `emboss=False` operator puts its label at the far side of the
panel, reading as two unrelated widgets; `row.alignment = 'LEFT'` fixed it. Both
were invisible to every test in the repo, because no suite draws a panel.

**Deliberately not done.** The old AI-facing `export_stl` tool is now redundant and
exports the wrong thing; removing it is a separate removal under the normal
protocol. `deflection` is on the op from day one and the shell does not pass it, so
STL quality is the display default until somebody asks for a knob. And the cage,
section and exploded-view boxes still sit behind that early return — whether that is
right for them is a separate question, deliberately not answered here.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 0a4c7503200dec652d5e82066a48bdba261c9e0e

## State Impact

- target: forest-wind-0342 — Two new protocol ops, 17 -> 19: set_printable records which accepted outputs are parts to print, export_printable writes one STL each into <project>.cadex/print/ off the accepted BREP/PLY, at each part's own origin. New pure module CadexPrintables.py in the declared engine closure and the payload. script.json gains a SIXTH spec/value pair (print_specs/print_values) and it is the first whose specs no script declares -- the roster is the accepted run's own brep/mesh output list, harvested in validate_project_result -- and the first deliberately OUTSIDE project_script_revision, because a print mark changes no geometry and a checkbox that costs a rebuild is not a checkbox. Loud on a requested unknown name, silent on drift (ADR-039). print/ is the one store directory nothing prunes: it is a deliverable, so a repeat export refuses and names the files rather than overwriting. inspect scope=script gains a printable block.
- target: shy-crane-2573 — The model can leave for a slicer: a checkbox per accepted output in the Parameters editor (an operator per row, not a BoolProperty, so no runtime PropertyGroup) and File > Export Printable Parts..., with an Overwrite / Keep Both dialog built from the engine's own refusal the way Link Part's is. New mesh_agent/cadex_print.py; the roster costs no round trip because it rides in the inspect scope=script block _adopt_script_state already adopts. Two panel bugs found only by a windowed probe of the built bundle: the parameters panel returns early for a model with no declared parameters (so the box drew nowhere for exactly the model somebody wants to print), and a full-width emboss=False operator puts its label at the far side of the panel. Both fixed; no suite in the repo draws a panel.
