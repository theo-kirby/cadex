---
node_id: 3c2c86d9-baa6-5104-a744-27a491b19d2b
slug: ancient-current-9419
title: 'Linked parts: one project''s accepted solid, used in another'
created_at: '2026-08-09T16:41:52+00:00'
parents:
- quiet-wing-7912
summary: ''
---
## What

A part built in one project can now be used in another. It travels as **one
content-addressed file in the consuming project's `assets/`** — a `.cxpart`
container carrying an exact OCCT solid plus the script that made it — along the
path an imported STL already travels.

Four pieces, shipped together (ADR-138):

- `CadexLinkedPart.py`, a FreeCAD-free container module:
  `CXPART1\n | <u64 LE header length> | <canonical JSON header> | <raw BREP>`,
  deliberately isomorphic to `CadexDynamics`' `.cxpolicy`.
- `link_part`, a new cadexd `MODELING_OP`
  (`{source_project, output?, name?}` → `{name, bytes, sha256, source_revision,
  source_digest, previous_revision, changed, assets}`).
- `part.import_part("sensor.cxpart")`, a part-domain leaf yielding a `solid`.
- `_LINKED_PART_ASSET_SUFFIXES`, a fourth constant joining
  `_STORED_ASSET_SUFFIXES`; `_ASSET_SUFFIXES` stays exactly three.

Plus **File → Link Part…** / **File → Refresh Linked Parts**, a `link_part` MCP
tool, and `cadex link --from DIR --output NAME`.

This **answers a question the docs had parked twice** — `docs/VISION.md`'s "how
assemblies-of-parts compose in a single project script (sub-scripts? imports?
one flat script?)" and `docs/XSCRIPT.md` Part II's *Sub-modules*. The answer is
none of the three: a project stays one flat script and composes another through
that project's *store*. Both paragraphs were rewritten rather than left standing.

## Why

The only route between projects was STL: export, `mesh.import_file`,
`part.shape_from_mesh` — which `cadex_part_api.py` describes in its own
docstring as "not feature-editable … for cutting clearance against, not for
editing." The part arrived **baked**: a shell of thousands of planar triangle
faces, no params, no rebuild, no way back to the thing that made it.

Nothing else existed. There is no include, no sub-script and no cross-project
reference anywhere in the engine; the AST policy refuses every `import`
statement outright, and `assembly.component` refuses a foreign source by name.
"Use the sensor module I built last week" was impossible.

## Method

Two findings from exploration carried the design, and both were checked before
any code was written.

**The accepted solid is already a file on disk.** `accepted_attempt_dir`,
`load_worker_report` and `accepted_output_item` (public since ADR-043) locate a
pinned staging directory holding `request.json` — the exact source that ran —
and `outputs/output-NNN.brep`. `prune_artifacts` resolves `accepted_attempt` and
skips it explicitly (`CadexScriptStore.py:324`), which is the one assumption the
whole pull path rests on. So `build_linked_part` is **pure Python file reading:
no FreeCAD, no worker, no OCCT call**, and the source project may be closed, or
open in another session, while it runs.

**The asset union has now been widened three times at zero cost.**
`_STORED_ASSET_SUFFIXES` is the union of separate constants — ADR-084 added
`.cxpolicy`, ADR-135 added `.json`/`.xml`, this adds `.cxpart` — because
widening the union costs no `shell/` diff while widening `_ASSET_SUFFIXES`
(mirrored by name at `cadex_backend.py:53`) would.

**One op, not two.** The obvious shape is export from A, import into B: two
operations, two sessions, a file the user shuttles by hand. Collapsing it to
"B pulls from A's directory" removes all three, and A never opens. Refresh is
then *the same call with the same arguments* — overwriting an asset is
re-import, which `store_project_asset` already did — so there is no second op
and no second code path.

`link_part` is a `MODELING_OP` for ADR-043's reason verbatim: it ends in the
same `store_project_asset` call, and membership is what makes it mutually
exclusive with an in-flight rebuild.

The build order was container → op → script primitive → **end-to-end** → shell →
CLI → docs, with the end-to-end step non-optional. ADR-135 is why: ADR-134
shipped unusable with all 52 of its unit tests green because not one went
through `store_project_asset`.

## Result

**All gates green.**

- `pixi run python -m pytest src/Mod/cadex/cadex_tests` — **1,723 passed, 22
  skipped** (was 1,698).
- `pixi run python -m pytest cli/tests` — **80 passed** (was 76).
- `CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pytest
  test_cadexd_lifecycle.py test_linked_part_live.py` — **14 passed against the
  packaged payload**, which is what proves `CadexLinkedPart.py` actually ships.
- `pixi run gate` — `"ok": true`, no failures.

**The measured claim.** `test_linked_part_live.py` drives two real cadexd
children: project A builds a sensor and accepts it, B pulls it, imports it, cuts
a plate with it and hangs an assembly component on it; then A's bore moves, B
refreshes, B rebuilds, and B's geometry follows. The imported solid's volume
equals A's to `rel=1e-12` and its **face count equals A's exactly** and is under
100 — which is the whole difference from the STL route, stated as a number.

**The `simple-willow-8989` risk was checked, not reasoned about.** A refresh
moves B's digest by design, and a digest-moving change that a project cannot
restore from would lock it out at open with no button back in. The live test
closes B after the refresh, reopens it, and asserts the restore pass performed
**and matched**. It does — refresh goes through the ordinary rebuild path rather
than swapping bytes under an accepted model.

**One defect found and fixed on the way.** `cadex_backend._assets_in` filtered
Save-As's carry-forward on the shell's three-suffix `ASSET_SUFFIXES`, so a
Save-As would have **dropped** every `.cxpart` and left the new file with a
script that could not run — ADR-046's exact bug arriving on a new file type. A
separate `CARRIED_ASSET_SUFFIXES` fixes it and the gate pins it.

**What it gives up**, stated rather than discovered later: a linked part is a
snapshot, not a live link; an ADR-029 selector naming a face of it can break on
refresh (correctly and loudly — the refusal names the selector); one solid per
container; and `project_root` in the header is a hint, never a load-bearing path.

**Carried and not yet read.** The header records the source project's `script`,
`params` and `param_specs`. Nothing in this slice consumes them — they are what a
parameter override (`part.import_part("s.cxpart", bore=6)`) needs and what makes
a linked part rebuildable rather than baked. Recording them now costs bytes;
adding them later would cost a container version bump. A test asserts them so
their presence reads as a decision rather than an oversight.

**Shell diff:** +541/-5 across six files, every one under
`shell/scripts/addons_core/mesh_agent/` or `shell/tests/python/`. Nothing in
`docs/BLENDER-TREE.md` §2 moved; §2a is still eight files.

## Negative knowledge

- Sub-scripts and Python imports are the wrong answer for composing projects,
  and not because the sandbox forbids them. They would make a rebuild here
  depend on another project's current state, its assets and its engine version.
  A content-addressed container makes it deterministic from this project's own
  `assets/` alone.
- The viewport polygon count cannot distinguish a linked BREP part from a
  converted STL: the mesh in the viewport is a tessellation either way. The
  first version of the gate test asserted on it and failed at 520 polygons for a
  40-face solid. The BREP claim has to be made against engine facts, not against
  `obj.data.polygons`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 5ade410f356d0d5f194ebf00b7f49a69163bdc52

## State Impact

- target: forest-wind-0342 — The engine gains linked parts (ADR-138): a new `link_part` MODELING_OP pulls one accepted solid out of another project's pinned accepted attempt as a `.cxpart` container (pure file reading — no FreeCAD, no worker, no OCCT call, and the source project never opens), and `part.import_part` reads it back as the exact OCCT solid. New engine module `CadexLinkedPart.py`, in both DECLARED_ENGINE_MODULES and the project worker bundle. Part domain is 50 -> 51 operations. Refresh is the same call again; `changed` says whether the source moved. No new output type, no new artifact_kind, no change to compute_project_digest. Suite count 1,698 -> 1,723 passed / 22 skipped. Answers the parked open question of how projects compose: one flat script each, joined by content-addressed files, not sub-scripts or imports.
- target: shy-crane-2573 — The shell gains File > Link Part... and File > Refresh Linked Parts, a `link_part` MCP tool (17 tools), and the backend trio link_part/linked_parts/refresh_linked_parts (ADR-138). Also fixes a real defect: `_assets_in` filtered Save-As's carry-forward on the three-suffix ASSET_SUFFIXES, so a Save-As would have dropped every .cxpart and left the new file with a script that could not run — ADR-046's bug on a new file type, now pinned by the gate. Shell diff +541/-5 across six files, all under mesh_agent/ or tests/python/; BLENDER-TREE.md section 2a still eight files.
