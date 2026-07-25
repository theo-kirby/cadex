# FREECAD.md — Inherited Substrate Inventory

Verified against source: 2026-07-25

Cadex's **engine** is a FreeCAD fork. This is the ledger of what we keep,
what is slated for removal, and what is already gone. Its peer for the shell
half is `docs/BLENDER-TREE.md`, in the same format and under the same rules.
The change policy for inherited code is in `CLAUDE.md`; removals execute
under the two-commit protocol in §3 and are logged in `docs/DECISIONS.md`.

Everything in this file is `[FreeCAD-inherited]` unless noted.

## 1. Kept — the engine stands on these

### Core (conservative-change zone)

| Tree | Why kept |
|---|---|
| `src/App` | `App::Document`, `DocumentObject`, properties, expressions, **transactions** — the persistence/undo substrate the publisher and `CadexTransactions.py` rely on. |
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
| `src/Mod/Start` | Launch screen shown by Experimental Mode when no document is open. |
| `src/Mod/Test` | Test framework harness. |
| `src/Mod/Mesh`, `src/Mod/MeshPart` | Substrate for the minimal `mesh` domain (landed, Phase 4 / ADR-016): import, tessellate, boolean, decimate, export. |
| `src/Mod/Help` | In-app help plumbing; cheap to keep until Phase 1 audits it. |
| `src/Mod/cadex` | `[Cadex-new]` — the engine itself (`docs/ARCHITECTURE.md`). |

## 2. Kept elsewhere

- `src/3rdParty`, `cMake`, `pixi.toml` — build substrate (OCCT, Coin3D, Qt6
  come from pixi/conda deps).
- `src/Tools`, `tests/` — upstream tooling and native test trees (audited,
  not blanket-kept, during Phase 1).

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
`xscript_*` workers, `CadexXScriptCAM`), and only the four domain
packs' publication/validation code remains on those paths. Some
never-dispatched helper code for culled domains that touches only
kept trees (mesh/points/fem/inspection/robot snapshot and rollback
helpers, TechDraw page summaries in `CadexCore.py`) is still present
and is follow-up sweep material.

## 5. Open questions

- Does `src/Mod/Material` reduce to just the property types the four domains
  touch, or stay whole?
- `src/Mod/Help`: any startup references that need unpicking before
  deletion?
- Which `tests/` subtrees cover removed workbenches and go with them?
