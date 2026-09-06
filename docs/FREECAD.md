# FREECAD.md — Inherited Substrate Inventory

Verified against source: 2026-09-06

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
| `src/Gui` | Qt6 main window + Coin3D/Quarter viewport. **Present but not built** — release and package configs set `BUILD_GUI=OFF` (ADR-022). Debug builds still compile it, so the tree stays healthy until Phase 8 deletes it. See §3. |
| `src/Main` | `FreeCAD` / `FreeCADCmd` entry points. `FreeCADCmd` is load-bearing: every xscript worker is a `FreeCADCmd --safe-mode` subprocess. |

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
| `src/Mod/Start` | The launch screen. It was shown by the Qt shell's Experimental Mode, which was deleted in Phase 7 (ADR-021) — nothing displays it now. A removal candidate with no dependency story left. |
| `src/Mod/Test` | FreeCAD's own Python test harness. Nothing in `cadex_tests/` uses it. |
| `src/Mod/Help` | In-app help plumbing for a UI that no longer exists here. |

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
(`c2ccddfb3bbcbcff8cecd859968a8750d95832db`, 2026-07-23) — 47 files, 38
under `src/` and 9 in the build substrate (`CMakeLists.txt`, `cMake/`,
`tests/`). This ledger existed only as git history until 2026-08-29
(ADR-171); the machine-readable list is `docs/inherited-modifications.json`,
kept equal to the git diff by `cadex_tests/test_licensing_compliance.py`,
and every file carries a one-line modification notice in its header
(`Modified by the Cadex project, 2026. See docs/FREECAD.md.`), as LGPL-2.1
§2(a) asks — except nine flagged `ledger-only` in the manifest
(`Interpreter.cpp`, `Application.cpp`, `MainWindow.cpp`,
`DlgSettingsGeneral.cpp`, `JointObject.py`,
`BRepOffsetAPI_MakePipeShellPyImp.cpp`, `TopoShapePyImp.cpp`,
`StartView.cpp`, `ThemeSelectorWidget.cpp`), where inserting even a
comment line triggers a whole-file reformat under pre-commit; **this
listing is their notice**, which is what `ledger-only` means. Grouped by
why:

- **Workbench-removal and GUI-off build edits** (Phases 1 and 7 — ADR-007,
  ADR-009, ADR-022): the root `CMakeLists.txt`, five `cMake/` helper
  modules, `src/Mod/CMakeLists.txt`, the kept workbenches'
  `CMakeLists.txt` (`Part`, `PartDesign`, `Assembly` ×3), and the
  `tests/` CMake tree (`tests/CMakeLists.txt`, `tests/src/*/CMakeLists.txt`,
  `tests/src/Gui/DockLayoutState.cpp`) — deletion of removed-workbench
  references and the `BUILD_GUI` guards.
- **The VibeCAD → Cadex rebrand and its revert to stock** (Stage C,
  Phase 7 C6a): `src/App/ApplicationDirectories.cpp`,
  `src/Base/Interpreter.cpp`, `src/Gui/Application.cpp`,
  `src/Gui/MainWindow.{cpp,h}`, `src/Gui/DockWindowManager.cpp`,
  `src/Gui/OverlayWidgets.cpp`, `src/Gui/ToolBarManager.cpp`,
  `src/Gui/StartupProcess.cpp` — product identity strings and versioned
  config discovery, most of it later reverted toward stock, leaving small
  residual diffs.
- **Themes and preference packs**: `src/Gui/Stylesheets/CMakeLists.txt`
  (installs the Cadex themes), `src/Gui/PreferencePacks/CMakeLists.txt` +
  `package.xml`, `src/Gui/PreferencePages/DlgSettingsGeneral.cpp`.
- **The Start view's landing edits** (Phase 1.0):
  `src/Mod/Start/Gui/{AppStartGui,StartView,ThemeSelectorWidget}.cpp`,
  `StartView.h` — removed tiles for removed workbenches. The tree itself
  ships in nothing (§1).
- **Headless-Assembly fixes** (ADR-047, ADR-060):
  `src/Mod/Assembly/{JointObject,CommandCreateView,Preferences,
  UtilsAssembly,InitGui}.py`, `App/AppAssembly.cpp`, and the `Gui/` files
  (`AppAssemblyGui.cpp`, `ViewProviderAssembly.cpp`, `Assembly.qrc`,
  CMake) — import guards so App-level code survives without PySide, and
  GUI-list trims.
- **The ADR-128 kernel features**: `src/Mod/Part/App/` binding files —
  §2a's table is their itemised story; they appear in the manifest like
  every other modified file.
- **Test residue**: `src/Mod/Part/TestPartApp.py` (removed-feature test
  trims).

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

## 3. Disabled, awaiting removal

### `src/Gui` (+ every `src/Mod/*/Gui`, `tests/src/Gui`) — Phase 8

**Disable commit: Phase 7 C6b (ADR-022).** Release and package
configurations set `BUILD_GUI=OFF`; nothing the product ships compiles a
line of it. Measured effect on this tree: `lib/` 43 MB → 8.3 MB, `Mod/`
49 MB → 22 MB, files matching `*Gui*` 93 → 8, and `bin/` reduced to
`FreeCADCmd` + `CadexGeometryWorker`.

Not deleted yet because it is 66 MB across 729 files plus every
`src/Mod/*/Gui`, and `BUILD_GUI=OFF` already captures 100% of the size and
build-time benefit with a zero-line diff in the conservative zone. The
delete commit is Phase 8 (`docs/ROADMAP.md`), and it must also remove the
`BUILD_GUI` guards Phase 7 added to `tests/src/CMakeLists.txt` and
`tests/src/Base/CMakeLists.txt` rather than leave them dangling.

Until then: **do not add to it, do not fix it, do not partially delete it.**

### Phase 1 workbench trees — complete

Phase 1 removals are complete: batch A (`AddonManager`, `BIM`,
`CAM`, `Fem`, `Inspection`, `OpenSCAD`, `Plot`, `ReverseEngineering`,
`Robot`, `Surface`, `TemplatePyMod`, `Tux`, `Web`) deleted per ADR-007;
batch B (`Draft`, `Points`, `Spreadsheet`, `TechDraw`) deleted per
ADR-009 after the grid lost its Draft dependency (Phase 1.3) and the
assembly BOM was dropped (ADR-008). Every tree under `src/Mod/` is now
in §1.

The protocol (per tree, two commits, logged in `docs/DECISIONS.md`):
**disable, verify; delete, verify.** `src/Gui` is mid-protocol — disabled
in Phase 7, delete scheduled for Phase 8.

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
- `src/Mod/Start`, `Test` and `Help` build but ship in nothing. They look
  like a cheap Phase 13b batch; the audit has not been done.
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
