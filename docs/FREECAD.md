# FREECAD.md — Inherited Substrate Inventory

Verified against source: 2026-07-24

Cadex is a FreeCAD fork. This is the ledger of what we keep, what is slated
for removal, and what is already gone. The change policy for inherited code
is in `CLAUDE.md`; removals execute in Phase 1 (`docs/ROADMAP.md`) and are
logged in `docs/DECISIONS.md`.

Everything in this file is `[FreeCAD-inherited]` unless noted.

## 1. Kept — the engine stands on these

### Core (conservative-change zone)

| Tree | Why kept |
|---|---|
| `src/App` | `App::Document`, `DocumentObject`, properties, expressions, **transactions** — the persistence/undo substrate the publisher and `CadexTransactions.py` rely on. |
| `src/Base` | Units, vectors, matrices, persistence primitives, Python bindings glue. |
| `src/Gui` | Qt6 main window + Coin3D/Quarter viewport. Kept for the **interim** Qt shell only (`docs/INTEGRATION.md`); no new rendering investment (Phase 3 cap). |
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
| `src/Mod/Mesh`, `src/Mod/MeshPart` | Substrate for the planned minimal `mesh` domain (Phase 4): import, tessellate, boolean, decimate, export. |
| `src/Mod/Help` | In-app help plumbing; cheap to keep until Phase 1 audits it. |
| `src/Mod/cadex` | `[Cadex-new]` — the engine itself (`docs/ARCHITECTURE.md`). |

## 2. Kept elsewhere

- `src/3rdParty`, `cMake`, `pixi.toml` — build substrate (OCCT, Coin3D, Qt6
  come from pixi/conda deps).
- `src/Tools`, `tests/` — upstream tooling and native test trees (audited,
  not blanket-kept, during Phase 1).

## 3. Slated for removal (Phase 1) — present but unused

Empty. Phase 1 removals are complete: batch A (`AddonManager`, `BIM`,
`CAM`, `Fem`, `Inspection`, `OpenSCAD`, `Plot`, `ReverseEngineering`,
`Robot`, `Surface`, `TemplatePyMod`, `Tux`, `Web`) deleted per ADR-007;
batch B (`Draft`, `Points`, `Spreadsheet`, `TechDraw`) deleted per
ADR-009 after the grid lost its Draft dependency (Phase 1.3) and the
assembly BOM was dropped (ADR-008). Every tree under `src/Mod/` is now
in §1.

Future removals follow the same protocol (per tree, two commits, logged
in `docs/DECISIONS.md`): disable, verify; delete, verify.

## 4. Already deleted (VibeCAD teardown) — do not resurrect

The `cadex-teardown` branch of the parent **vibecad** repo holds the full
6-phase history: engines deleted (build123d, OpenSCAD, native tool packs) →
domains culled 18 → 4 → Intent Memory / Design Review deleted →
experimental-mode-only UI → single xscript engine → rebrand. Consult that
branch's log for why anything is missing; nothing from it comes back without
a `docs/DECISIONS.md` entry.

Known residue inside `src/Mod/cadex/` `[VibeCAD-era]`: dead culled-domain
code remains in three places, all unreachable because only four domain packs
exist (`XSCRIPT_WORKBENCH_PACKS`, `CadexScriptedDomains.py:194`):

- `CadexScriptedRuntime.py` — ~24 lazy `from xscript_*_worker import …`
  statements inside validation/publication helpers for culled domains
  (spreadsheet, material, bim, mesh, points, reverse_engineering,
  inspection, robot, fem, cam, techdraw, surface), plus domain-name checks
  that can never match.
- `CadexScriptedDomains.py` — domain-name branches for culled domains in the
  inspection snapshot builder.
- `CadexScriptedDomainPublication.py` — unreachable publication paths still
  importing deleted `xscript_*` workers (lines ~2798–8727).

The stale `_DOMAIN_WORKER_BUNDLES` entries and two self-contained lazy
imports were pruned on 2026-07-24 (ADR-006). The rest is Phase 1 cleanup:
delete the whole dead functions/branches in one audited sweep rather than
nibbling at imports.

## 5. Open questions

- Does `src/Mod/Material` reduce to just the property types the four domains
  touch, or stay whole?
- `src/Mod/Help`: any startup references that need unpicking before
  deletion?
- Which `tests/` subtrees cover removed workbenches and go with them?
