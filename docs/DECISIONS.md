# DECISIONS.md — Decision Log

Append-only. One entry per decision, newest last. Every removal of code,
files, or public surface gets an entry (policy in `CLAUDE.md`). Format:
date, decision, rationale, consequences.

---

## ADR-001 — Single-engine xscript (inherited, 2026-07)

**Decision.** Cadex has exactly one scripted modeling engine: xscript.
build123d, OpenSCAD, and the native per-workbench tool packs were deleted;
the 18 VibeScript domains were culled to 4 (partdesign, sketcher, part,
assembly).

**Rationale.** One methodology, one sandbox, one publication contract.
Multi-engine surfaces multiplied validation, docs, and provider-tool
complexity without product value.

**Consequences.** Inherited from the VibeCAD `cadex-teardown` branch (6
phases; see that repo's history). Guardrail tests
(`src/Mod/cadex/cadex_tests/test_tool_surface_guardrails.py`) assert the
culled modules stay gone. Recorded here retroactively at repo import.

## ADR-002 — Blender shell endpoint, staged path (2026-07-24, owner)

**Decision.** The product shell is the Blender fork (`/Users/theo/mesh`);
cadex becomes a headless xscript geometry service (**cadexd**) streaming
tessellated BREP + face/edge ID maps into Blender. Path is staged (option D
with endpoint B in `docs/INTEGRATION.md`): near-term work stays engine-side
in this repo and carries over.

**Rationale.** `mesh_agent` already prototypes the exact target UX; Coin3D
is a dead end for Blender-level feel; BMesh solves mesh editing natively;
the engine already runs headless. License direction is clean (LGPL engine →
GPL shell across a process boundary).

**Consequences.** Qt/Coin3D investment is capped (Phase 3 is layout-only);
Phases 5–7 in `docs/ROADMAP.md`; a measured decision gate before Phase 5
re-validates the endpoint.

## ADR-003 — One project script (2026-07-24, owner)

**Decision.** The user-visible artifact is a single top-level project script
(`model.py`-style) that composes the domain APIs; parameters are declared at
its top; the document/scene is a rebuildable cache. The per-domain
multi-program runtime may persist only as an internal staging detail.

**Rationale.** Product principle: nothing happens outside the script; exact
full state is rebuildable from the script at any time. Proven shape in
`mesh_agent` (`docs/BLENDER.md`). One readable artifact beats a set of
per-domain programs no user can hold in their head.

**Consequences.** Phase 2 in `docs/ROADMAP.md` (project-level params,
publisher lint, orphan GC, digest-checked headless rebuild). `docs/XSCRIPT.md`
Part II specifies the target.

## ADR-004 — Removal policy replaces additive-only (2026-07-24, owner)

**Decision.** The repo-wide additive-only rule is retired. In
`src/Mod/cadex/**` and `docs/**`, subtractive change is encouraged; for
inherited FreeCAD core (`src/App`, `src/Gui`, `src/Base`), stay
conservative. Every removal is logged here and verified by build + tests.

**Rationale.** The project philosophy is "remove more than we add"
(`docs/VISION.md`). The inherited `AGENTS.md` mandated the opposite and was
written for a different phase (guarding a large inherited surface during
active multi-engine development).

**Consequences.** Policy text lives in `CLAUDE.md`. Phase 1's tree removals
become normal, logged work instead of exceptional approvals.

## ADR-005 — AGENTS.md retired in favor of CLAUDE.md (2026-07-24)

**Decision.** `AGENTS.md` deleted. `CLAUDE.md` is the single agent entry
point: repo map, commands, doc index, change policy, methodology.

**Rationale.** `AGENTS.md`'s core mandate (additive-only, removals need
case-by-case approval) contradicted ADR-004 and the product philosophy; it
also referenced a nonexistent `AI_POLICY.md`. Two competing agent
instruction files is one too many.

**Consequences.** Agents read `CLAUDE.md` first. PR hygiene expectations
(small coherent diffs, honest test reporting) carried over into `CLAUDE.md`.

## ADR-006 — Phase-0 hygiene removals (2026-07-24)

**Decision.** Deleted the 14 stale `_DOMAIN_WORKER_BUNDLES` entries in
`src/Mod/cadex/CadexScriptedRuntime.py` (draft, surface, spreadsheet,
material, bim, mesh, meshpart, points, reverse_engineering, inspection,
robot, fem, cam, techdraw) and the two dead lazy imports of deleted
`xscript_*` workers in `src/Mod/cadex/CadexScriptedDomains.py`. Moved
`docs/vibescript-system-design-feasibility.md` and
`src/Mod/cadex/RUNTIME_VERIFICATION.md` to `docs/history/` with superseded
banners.

**Rationale.** The entries referenced `xscript_*` files that no longer
exist; the docs described the pre-teardown state as current.

**Consequences.** Substantial dead culled-domain code remains — ~24 more
lazy `xscript_*` imports inside unreachable helpers in
`CadexScriptedRuntime.py`, plus unreachable branches in
`CadexScriptedDomains.py` and `CadexScriptedDomainPublication.py` — all
catalogued in `docs/FREECAD.md` §4 and scheduled for Phase 1. Deliberately
not swept in Phase 0: removing them means deleting whole functions across a
16k-line file, which needs its own audited, test-verified pass.

## ADR-007 — Phase 1 batch A: 13 unused trees deleted (2026-07-24)

**Decision.** Deleted `src/Mod/{AddonManager, BIM, CAM, Fem, Inspection,
OpenSCAD, Plot, ReverseEngineering, Robot, Surface, Tux, Web}` and the
never-built `src/Mod/TemplatePyMod`, following the two-commit protocol
(disable commit `8f98463`, then delete). Their `BUILD_*` options,
`REQUIRES_MODS` lines, `src/Mod/CMakeLists.txt` blocks, and satellite
references (NETGEN find logic, `SetupLark.cmake`, PySide6 QtSvgWidgets
BIM consumer, final-report lines, FEM/CAM/BIM visual-test scenes, the
Start view's Draft/BIM tiles) went with them. The AddonManager submodule
entry was removed from `.gitmodules`.

**Rationale.** No runtime domain, tool, or UI path reaches these trees
(`docs/FREECAD.md` §3); the product ships four domains. Remove more than
we add.

**Consequences.** Batch B (Draft, Points, TechDraw, Spreadsheet) follows
after the cadex grid is reimplemented without Draft and the assembly BOM
feature is dropped (see ADR-008/ADR-009). `pixi run configure` on an
existing build dir needs the removed `BUILD_*` cache entries purged
(`cmake -U`) or a fresh build directory.

## ADR-008 — Assembly bill of materials dropped (2026-07-24)

**Decision.** The assembly BOM feature is removed end to end:
`api.bill_of_materials` and the `bom` output type from the cadex assembly
domain (API, worker, runtime validation, publication, prompt text, tests,
`CadexAssemblyBOM.py`), and the native substrate from the Assembly module
(`Assembly::BomObject`/`BomGroup` + Python bindings, `ViewProviderBom*`,
`CommandCreateBom.py`, task panel, icons, `Assembly_CreateBom`
registration). Assembly no longer links or imports Spreadsheet;
`REQUIRES_MODS(BUILD_ASSEMBLY …)` drops `BUILD_SPREADSHEET`.

**Rationale.** `Assembly::BomObject` inherits `Spreadsheet::Sheet` — the
BOM was the only thing keeping the Spreadsheet tree alive. Owner chose
dropping the feature over keeping Spreadsheet as substrate (v0.0.1
planning, 2026-07-24). v0.0.1 assemblies are geometry + joints; a parts
table can return later on a cadex-owned substrate if wanted.

**Consequences.** Spreadsheet becomes removable (batch B). The assembly
source-hierarchy snapshot keeps its `bom_properties` field name — it feeds
the reference-contract hash; renaming it is a schema bump left for later.

## ADR-009 — Phase 1 batch B: Draft, Points, TechDraw, Spreadsheet deleted (2026-07-24)

**Decision.** Deleted `src/Mod/{Draft, Points, TechDraw, Spreadsheet}`
and `tests/src/Mod/{Points, Spreadsheet, TechDraw}` following the
two-commit protocol (disable commit `237d5d8`, then delete). Options,
`REQUIRES_MODS` lines, `src/Mod/CMakeLists.txt` and test gates,
final-report lines, and the Draft/TechDraw/Spreadsheet visual-test
scenes went with them. Kept-tree residue removed in the disable commit:
Part's `TestPartMirror.py` and PartDesign's `Scripts/Gear.py` (both
imported Draft); Part's two `BUILD_SPREADSHEET`-gated tests
(`testIssue2671`, `testIssue2876`) deleted with the tree.

**Rationale.** Unreachable from the four-domain product surface. The two
former dependents were unwound first: the viewport grid is cadex-owned
as of Phase 1.3 (no Draft), and the assembly BOM was dropped in ADR-008
(no Spreadsheet).

**Consequences.** Every tree under `src/Mod/` is now kept:
Part, PartDesign, Sketcher, Assembly (domains); Import, Material,
Measure, Mesh, MeshPart, Show, Start, Test, Help (support); cadex (the
engine). Residual culled-domain code inside cadex referencing
draftutils/Points dies in the Phase 1 dead-code sweep.
