# FREECAD.md — Inherited Substrate Inventory

Verified against source: 2026-09-07

Cadex's **engine** is a FreeCAD fork. This is the ledger of what we keep,
what is slated for removal, and what is already gone. Its peer for the shell
half is `docs/BLENDER-TREE.md`, in the same format and under the same rules.
The change policy for inherited code is in `AGENTS.md`; removals execute
under the two-commit protocol in §3 and are logged in `docs/DECISIONS.md`.

Everything in this file is `[FreeCAD-inherited]` unless noted.

## 1. Kept — the engine stands on these

### Core (conservative-change zone)

| Tree | Why kept |
|---|---|
| `src/App` | `App::Document`, `DocumentObject`, properties, expressions, **transactions** — the substrate `publish_project_candidate` applies one candidate under, as a single transaction. (The Qt shell's `CadexTransactions.py` wrapper is gone with it, ADR-021; the publisher uses `App` directly.) |
| `src/Base` | Units, vectors, matrices, persistence primitives, Python bindings glue. |
| `src/Gui` | **Deleted** with all eleven workbench Gui directories and tests/src/Gui (Phase 8, ADR-214). Retained headless metatypes live in App/MetaTypes.h. |
| `src/Main` | Headless Python module / `FreeCADCmd` entry points. `FreeCADCmd` is load-bearing: every xscript worker is a `FreeCADCmd --safe-mode` subprocess. |

### Capability workbenches (the product's four areas)

| Tree | Backs |
|---|---|
| `src/Mod/Part` | `part` domain — direct OCCT shapes, booleans, filleting. |
| `src/Mod/PartDesign` | `partdesign` domain — bodies, sketch-based features. |
| `src/Mod/Sketcher` | `sketcher` domain — constraint solver (planegcs). |
| `src/Mod/Assembly` | `assembly` domain — links, joints, ondsel solver. |

### Support trees

| Tree | Why kept |
|---|---|
| `src/Mod/Import` | STEP/IGES exchange. |
| `src/Mod/Material` | Part material properties referenced by kept workbenches. |
| `src/Mod/Measure` | Measurement backend. |
| `src/Mod/Show` | Visibility automation used by TreeView/ViewProviders. |
| `src/Mod/Mesh`, `src/Mod/MeshPart` | Substrate for the minimal `mesh` domain (landed, Phase 4 / ADR-016): import, tessellate, boolean, decimate, export. |
| `src/Mod/cadex` | `[Cadex-new]` — the engine itself (`docs/ARCHITECTURE.md`). |

**Built but not shipped.** Three trees still build and are not in the engine
payload's keep-list (`package/engine/build_engine_payload.sh`), so nothing
the product installs contains them:

| Tree | Status |
|---|---|
| `src/Mod/Start` | The launch screen. It was shown by the Qt shell's Experimental Mode, which was deleted in Phase 7 (ADR-021) — nothing displays it now. **Disabled (ADR-220), then deleted 2026-09-07 (ADR-221, [START-AUDIT.md](START-AUDIT.md)).** All 27 module/test sources, three gates, option, report and maintenance references are gone. Neither `Mod/Start` nor `lib/Start.so` installs or stages. |
| `src/Mod/Test` | FreeCAD's own Python test harness. Nothing in `cadex_tests/` uses it. |
| `src/Mod/Help` | In-app help plumbing for a UI that no longer exists here. **Disabled (ADR-217), then deleted 2026-09-07 (ADR-218)**: the 85 tracked files, the `BUILD_HELP` option, its parent gate and report line, and its crowdin row are gone. The first engine-side whole-tree removal under the two-commit protocol; [HELP-AUDIT.md](HELP-AUDIT.md) holds both halves' gates. |

## 2. Kept elsewhere

- `src/3rdParty`, `cMake`, `pixi.toml` — build substrate (OCCT, Coin3D, Qt6
  come from pixi/conda deps).
- **One shipping pypi wheel**: `mujoco == 3.10.0`, the
  dynamics kernel. It is not inherited FreeCAD substrate and it is not a
  build-only dependency — it is redistributed **inside the engine payload**,
  carried there by name through `CARRIED_PYPI_PACKAGES` because the manifest
  has not been re-solvable as conda since conda-forge moved past our `occt`
  pin (ADR-075, ADR-076). Ledger entry: `docs/PROVENANCE.md` §4; the payload
  build hard-fails if it cannot import it.
- `src/Tools`, `tests/` — upstream tooling and native test trees (audited,
  not blanket-kept, during Phase 1).

## 2a. Our delta against upstream — additions inside the inherited tree

The peer of `docs/BLENDER-TREE.md` §2, and it stayed empty far longer:
until 2026-08-05 every Cadex engine feature lived under `src/Mod/cadex/`
and reached OCCT through bindings FreeCAD already had. Two do not, and both
exist because a Python-side workaround would have been an *approximation of
the kernel* rather than a call into it. Every line here is a future merge
conflict against upstream FreeCAD, so the list stays short and stays
itemised.

| File | What we added | Why it could not be Python | ADR |
|---|---|---|---|
| `src/Mod/Part/App/BRepOffsetAPI_MakePipeShell.pyi` + `…PyImp.cpp` | `setLaw(Profile, Law, WithContact=, WithCorrection=)`, taking `[[position, factor], …]` and building a `Law_Interpol` | `BRepOffsetAPI_MakePipeShell` was bound whole *except* `SetLaw`. Without it a scaling law has to be faked as a loft through computed stations, which is an approximation: the kernel law lands on the closed-form volume to six figures, the loft does not. | ADR-128 |
| `src/Mod/Part/App/TopoShapePyImp.cpp` | a third `makeFillet` form, `makeFillet([r, …], edges)` — one radius, or one `(start, end)` pair, per edge | `BRepFilletAPI_MakeFillet` resolves its edges in the shape it was constructed with, so a second call cannot address the first call's result. One radius per call means one radius per body. | ADR-128 |

Note what is *not* here: guide curves on a sweep. ADR-125 priced them as a
fork delta and was wrong — `Part.BRepOffsetAPI.MakePipeShell` already had
`setAuxiliarySpine`. Grep the class bindings before pricing C++.

## 2b. Our delta against upstream — modifications to inherited files

§2a is the *additions*; this is the ledger of every inherited FreeCAD file
this repository has **modified** since its import
(`c2ccddfb3bbcbcff8cecd859968a8750d95832db`, 2026-07-23) — 56 files,
40 under `src/` and 16 in the build substrate. The machine-readable list
is `docs/inherited-modifications.json`, pinned to git by the licensing suite.
Every modified file carries a Cadex modification notice except the four
`ledger-only` entries: `Interpreter.cpp`, `JointObject.py`,
`BRepOffsetAPI_MakePipeShellPyImp.cpp` and `TopoShapePyImp.cpp`. Inserting a
comment there triggers whole-file formatting; this listing is their notice.

- **Headless metatypes** (ADR-213): twelve Material App files and six retained
  tests include `App/MetaTypes.h`. That relocated, attributed FreeCAD header
  is a derived addition. Its temporary Gui forwarding header is now deleted.
- **Build and directory removal** (ADR-007, ADR-009, ADR-022, ADR-214): root
  CMake, five helper modules, `src/CMakeLists.txt`, `src/Doc/CMakeLists.txt`,
  `src/Main/CMakeLists.txt`, `src/Mod/CMakeLists.txt`, the eleven retained
  workbench parent CMake files and the retained tests CMake tree. Phase 8
  removes retired Gui registrations, GUI-only script/resource registrations,
  Main GUI targets and their resource configuration, the Qt test helper and
  dead Doxygen paths. App registrations and unconditional install lists stay.
- **Product configuration**: `src/App/ApplicationDirectories.cpp` and
  `src/Base/Interpreter.cpp` preserve the engine's config discovery. The
  modified GUI identity, theme, preference-pack and Start-view files were
  deleted with their directories; they are no longer manifest entries.
- **Headless Assembly** (ADR-047, ADR-060): retained
  `src/Mod/Assembly/{JointObject,CommandCreateView,Preferences,UtilsAssembly,
  InitGui}.py`, `App/AppAssembly.cpp` and its CMake registration preserve
  headless imports and native publication. Modified Gui files are deleted.
- **Kernel features** (ADR-128): `src/Mod/Part/App` bindings listed in §2a.
- **Test residue**: `src/Mod/Part/TestPartApp.py` trims retired-feature tests.

**The pre-import bound, stated rather than hidden**: the import commit is
a squashed snapshot of VibeCAD's `cadex-teardown` branch, itself a FreeCAD
fork with edits. Modifications made *before* the import cannot be
enumerated from this repository; the notices are dated 2026 and cover this
repository's own edits. The same bound holds on the Blender side
(`docs/BLENDER-TREE.md` §2).

## 2c. Licence

Everything inherited here is **LGPL-2.1-or-later** (the root `LICENSE`,
FreeCAD's, unchanged); everything of ours under `src/Mod/cadex/` carries
`SPDX-License-Identifier: LGPL-2.1-or-later` and
`SPDX-FileCopyrightText: 2026 Cadex Authors`. Upstream license headers in
inherited files are never edited; a modified inherited file gains the
one-line notice *after* its header, applied and checked by
`tools/apply_modification_notices.py`. Attribution and the component map
live at the root: `NOTICE` and `THIRD_PARTY_LICENSES.md`.

## 3. Removal protocol and remaining boundaries

**Surviving modification audit (2026-09-07, ADR-227).**
[SURVIVING-DIFF-AUDIT.md](SURVIVING-DIFF-AUDIT.md) inventories all 56 FreeCAD
M entries; the qualified JointObject Preferences guard removal has landed.
FreeCAD M totals fall from 56/1637/1819 to 56/1634/1819; inherited remaining
stays 3434. Manifest membership and ledger-only notice remain accurate.
The broader reduction remains open; the audit records verification.


**Microsoft GSL tail removed (2026-09-07, ADR-222).** Start was its only
compiled consumer. After Start disable/delete, the GSL gitlink, submodule
entry and three checkout references are removed. No retained CMake consumer
exists; the Import DXF `gsl::owner` mention is only a TODO comment.
OndselSolver and the shell library submodules remain.

### `src/Gui` (+ every `src/Mod/*/Gui`, `tests/src/Gui`) — Phase 8

**Disable commit: `d2c8bcc5` — Phase 7 C6b (ADR-022).** Release and package
configurations set `BUILD_GUI=OFF`; nothing the product ships compiles a
line of it. Measured effect on this tree: `lib/` 43 MB → 8.3 MB, `Mod/`
49 MB → 22 MB, files matching `*Gui*` 93 → 8, and `bin/` reduced to
`FreeCADCmd` + `CadexGeometryWorker`.

**Directory delete: 2026-09-07 (ADR-214).** Following the retained metatype
move and complete GUI disable (ADR-213), delete all thirteen audited directory
trees, MainGui.cpp, FreeCADGuiPy.cpp and the orphan InventorBuilder test.
The exact removed volume and gate evidence are in [PHASE8-AUDIT.md](PHASE8-AUDIT.md).
`App/MetaTypes.h`, all eighteen migrated Material includes, QtCore,
QtConcurrent and LinguistTools remain. All presets stay headless and explicit
GUI-on requests are rejected.

**Residual GUI lineage remains open.** Mixed Assembly publication modules,
unconditional GUI Python install lists and other sources outside the audited
directories remain. ADR-215 and PHASE8-AUDIT.md trace the named consumers:
Assembly App proxies are required. Measure/MassPropertiesGui.py was disabled
in the shared copy/install list, then deleted separately (ADR-215). The other four Measure scripts and App identity are retained.
ADR-225 disabled the shared copy/install entries for Material/InitGui.py,
MaterialEditor.py and TestMaterialsGui.py in `d7e2b59c`, then deleted exactly
those three sources separately (2026-09-07). App/tests/resources and TestMaterialDocument.py remain. MeshPart/InitGui.py
was deleted after the separately verified install disable; App, Init.py,
meshFromShape and export macros remain (ADR-224, PHASE8-AUDIT.md);
Help is deleted (ADR-217, ADR-218). Start is deleted after its separate disable (ADR-220, ADR-221); neither `Mod/Start` nor `lib/Start.so` installs or stages. Test still builds and installs; its `Mod/` directory is pruned from the payload.
The residual audit is complete at this bounded scope, not the broader ROADMAP
exit claim that no GUI source exists. Mixed Part/PartDesign helpers and the
shared Windows launcher need separate disposition. ADR-226 deleted only the
previously disabled freecad.rc.cmake template
(2026-09-07). The shared launcher is unchanged; its four inactive GUI arms
remain deferred pending a separate bet and Windows validation path.
Command-line behavior/resources remain; Windows execution has not been
verified (PHASE8-AUDIT.md).

### Phase 1 workbench trees — complete

Phase 1 removals are complete: batch A (`AddonManager`, `BIM`,
`CAM`, `Fem`, `Inspection`, `OpenSCAD`, `Plot`, `ReverseEngineering`,
`Robot`, `Surface`, `TemplatePyMod`, `Tux`, `Web`) deleted per ADR-007;
batch B (`Draft`, `Points`, `Spreadsheet`, `TechDraw`) deleted per
ADR-009 after the grid lost its Draft dependency (Phase 1.3) and the
assembly BOM was dropped (ADR-008). Every tree under `src/Mod/` is now
in §1.

The protocol (per tree, two commits, logged in `docs/DECISIONS.md`):
**disable, verify; delete, verify.** The Phase 8 directory boundary has now
passed through both commits; residual GUI-lineage disposition follows ADR-215.

## 4. Already deleted (VibeCAD teardown) — do not resurrect

The `cadex-teardown` branch of the parent **vibecad** repo holds the full
6-phase history: engines deleted (build123d, OpenSCAD, native tool packs) →
domains culled 18 → 4 → Intent Memory / Design Review deleted →
experimental-mode-only UI → single xscript engine → rebrand. Consult that
branch's log for why anything is missing; nothing from it comes back without
a `docs/DECISIONS.md` entry.

The `[VibeCAD-era]` culled-domain residue inside `src/Mod/cadex/` was
swept 2026-07-24 (ADR-010): `CadexScriptedRuntime.py`,
`CadexScriptedDomainPublication.py`, and `CadexScriptedDomains.py` no
longer reference any deleted tree (`draftutils`, `ArchSite`,
`xscript_*` workers, `CadexXScriptCAM`), and only the five domain
packs' publication/validation code remains on those paths.

The "follow-up sweep material" this section used to list is **done**. The
never-dispatched helper code for culled domains (robot / FEM / inspection /
points snapshot and rollback helpers) was deleted in Phase 9 —
`CadexScriptedDomainPublication.py` went 7,012 → 3,613 lines, 48% removed
(ADR-026). The TechDraw page summaries went earlier still, with `CadexCore.py`
itself, in the Phase 7 Qt-shell deletion (ADR-021).

## 5. Open questions

- Does `src/Mod/Material` reduce to just the property types the five domains
  touch, or stay whole?
- `src/Mod/Help` is gone (ADR-217 disable, ADR-218 delete,
  [HELP-AUDIT.md](HELP-AUDIT.md)): one whole-tree removal, counted once.
  `Start` is also deleted after its separate disable (ADR-219..221,
  [START-AUDIT.md](START-AUDIT.md)); it has no App or MainCmd dependant.
  `Test` is retained: `MainCmd` depends on `TestSources` and Test installs
  the App tests. Its standalone Tk runner is disabled in the copy/install
  list; its source remains for a separate verified deletion (ADR-230,
  [TEST-TK-AUDIT.md](TEST-TK-AUDIT.md)).
  The rest of Test remains unaudited; payload exclusion alone is insufficient.
- Which `tests/` subtrees cover removed workbenches and go with them?
- `cadex_assembly_worker.py` imported `CommandCreateView` — GUI-lineage
  code used headlessly for exploded views, and the one import that made
  deleting `src/Gui` look more than mechanical. **Answered in two steps.**
  ADR-047 made the module importable headless (the `PySide` guard;
  ADR-149 added the `pivy` one). ADR-197 removed the worker's import: it
  computes the exploded view itself, FreeCAD's rule ported, and the audit
  found `src/Mod/Assembly/CMakeLists.txt` installs `CommandCreateView.py`
  outside its `if(BUILD_GUI)` blocks, so Phase 8 never would have removed
  it. The publisher (`CadexScriptedDomainPublication.py`) still imports it
  to build the native `ExplodedView` document object — that is what a
  published view *is* — and that import is not a Phase 8 obstacle.
- The engines we test with are not the engine that ships. `.pixi/envs/default`
  carries a `FreeCADGui.so`; `build/release` (`BUILD_GUI=OFF`) does not.
  `test_cadexd_lifecycle.py` prefers the former, so a GUI-coupling break can
  pass every source-tree run and only appear in the payload — ADR-047 was
  exactly that. Should the default flip to `build/release`?
