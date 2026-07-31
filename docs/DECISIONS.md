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

## ADR-010 — Phase 1 dead-code sweep of src/Mod/cadex (2026-07-24)

**Decision.** Deleted the remaining unreachable culled-domain code paths
from the engine, completing the residue sweep promised in ADR-009.
`CadexScriptedRuntime.py` was swept from ~21.4k to ~7.8k lines in the
first pass. This pass swept the other two files:

- `CadexScriptedDomainPublication.py` (11,202 → 6,732 lines): the whole
  draft, BIM, spreadsheet, material-card, TechDraw, and CAM publication
  chains — `_create_draft_object`/`_configure_draft`/
  `_draft_object_compatible`/`_draft_configure_order` (~365 lines), the
  `_create_bim_object`/`_configure_bim`/`_bim_*` family incl. rollback
  (~760 lines), `_configure_sheet` + spreadsheet rollback (~145 lines),
  `_material_card_state` + the full material carrier/appearance chain
  incl. `_publish_material_candidate` and `_delete_material_program`
  (~1,050 lines), the `_techdraw_*` family incl.
  `_publish_techdraw_candidate` and `_delete_techdraw_program`
  (~1,030 lines), the `_cam_*` family incl. `_publish_cam_candidate`
  and `_delete_cam_program` (~1,010 lines), plus the culled branches in
  `_native_type`/`_create_object`/`_configure_object`/
  `publish_candidate`/`delete_live_program`, the culled entries in
  `_NATIVE_TYPE_BY_OUTPUT`, orphaned `PROP_MATERIAL_*`/
  `PROP_APPEARANCE_*`/`PROP_CAM_VALIDATION`/`PROP_TECHDRAW_VALIDATION`/
  `MATERIAL_OWNERSHIP_SCHEMA` constants, `_BIM_ASSIGNED_PROPERTIES`/
  `_BIM_LINK_PROPERTY_TYPES`, and the orphaned
  `_set_native_property`/`_require_native_property` helpers.
- `CadexScriptedDomains.py` (4,904 → 4,626 lines):
  `_draft_document_snapshot` (138 lines), `_bim_document_snapshot`
  (120 lines), their `domain_context_snapshot` entries, and the
  now-unreferenced `MAX_DRAFT_CONTEXT_*`/`MAX_BIM_CONTEXT_*` constants.

**Method.** Grep for imports of deleted trees (`draftutils`, `ArchSite`,
`xscript_spreadsheet_worker`, `xscript_material_worker`,
`xscript_techdraw_worker`, `xscript_cam_worker`, `CadexXScriptCAM`);
delete each containing function whole; chase callers recursively with an
AST reference graph until only the four-domain dispatchers remained;
delete newly unreferenced module constants. Verified with the full
engine pytest suite green (387 passed, 1 skipped) after each file, and a
final zero-hit grep gate over `src/Mod/cadex` (guardrail tests that
assert the culled modules stay gone excepted).

**Consequences.** No engine file references a deleted tree. Culled-domain
helper code that touches only kept trees (mesh/points/fem/inspection/
robot snapshot+rollback helpers, TechDraw page summaries in
`CadexCore.py`) is never dispatched but still present — follow-up sweep
material, tracked in `docs/FREECAD.md` §4.

## ADR-011 — One project script: store + lifecycle, no v2 migration (2026-07-24)

**Decision.** The project domain becomes the fifth internal domain: ONE
script per project executed by one multi-domain worker
(`cadex_project_worker.py`), with `sketcher`/`part`/`partdesign`/
`assembly` APIs plus `params`/`num` staged as script globals. The store
(`cadex-project-script-v1`) lives at `<project>/script.py` (the sole
source of truth) + `<project>/script.json` (param spec cache, values,
working/accepted revision, accepted contract, accepted digest, latest
candidate) + `script_artifacts/<revision>/`. Revision =
`project_script_revision` over `{schema, domain:"project", source,
param_specs, param_values}`. Tools: `xscript.project.{write_script,
edit_script, set_params}`; `edit_script` reuses the unique-match
replacement machinery; `set_params` patches values only. Expected
outputs are recorded from the executed result (accepted contract), not
pre-declared. Assembly components take part/partdesign values created
in the same script, resolved worker-side to in-run serialized BREPs;
cross-document component references retire (rigid same-script solids in
v0.0.1; flexible subassemblies out of scope).

**Rationale.** docs/VISION.md: one project script as the sole source of
truth. The per-domain v2 program surface forced the model to shard one
design across programs and pre-declare outputs.

**Consequences.** Existing v2 per-domain program stores are NOT
migrated (pre-release; owner decision 2026-07-24): conversations are
preserved by their own store, scripts start empty. The per-domain
lifecycle tools dissolve in the Phase 2 tool-surface swap.

## ADR-012 — Project-script publication: one transaction, ownership lint, orphan GC (2026-07-24)

**Decision.** `publish_project_candidate`
(`CadexScriptedDomainPublication.py`) applies ONE validated multi-domain
project result to the live document under ONE transaction ("Publish Cadex
project script"), reusing the per-domain publishers with new keyword-only
`manage_transaction`/`check_surface` flags (defaults preserve the
per-domain behavior). Same-script assembly component sources are
tightened: every source must be a DECLARED part/partdesign output (the
worker's build-on-demand path for undeclared part payloads is removed);
the worker reports `component_sources: {token: output_name}` and
publication rewrites each token to the live object published in the same
pass. After the sub-publishes, still inside the transaction: orphan GC
removes owned objects whose (domain, base output name) left the accepted
contract (`CadexScriptedOwnership.orphaned_outputs`), and an ownership
lint aborts the transaction with `PUBLICATION_UNTAGGED_OBJECT` if any
document object falls outside the program's owned closure
(`owned_closure`/`untagged_objects`). `accept_project_candidate`
(`CadexScriptedRuntime.py`) persists accepted revision/contract/digest to
the script store. `CadexDigest.document_digest` adds a diagnostic
document-side digest (`cadex-document-digest-v1`) that is deterministic
across publishes of one revision (it intentionally does not equal the
worker digest).

**Rationale.** docs/VISION.md: the script is the sole source of truth, so
publication must be atomic, own every document object, and collect what
the script no longer produces.

**Consequences.** Undeclared component sources now fail worker-side with
a correction message; project publication carries no per-domain surface
check (there is no workbench surface for the project domain).

## ADR-013 — Phase 2.4 tool-surface swap: one project script is the only mutation surface (2026-07-24)

**Decision.** The per-domain multi-program tool surface dissolves. The ONLY
mutation surface is `xscript.project.{write_script, edit_script, set_params}`
plus the read-only `xscript.project.describe_api`; every other model-facing
read lives in `core.inspect` (new scope `script` for source, params,
revisions, accepted contract/digest, and the latest candidate; scopes
`domain` and `program` are removed; scope `api` now returns the project
describe payload). The surface is GLOBAL: `resolve_modeling_surface` returns
the project surface for any workbench (surface generation
`project-v1-single-script`); the workbench no longer selects a domain and
`UNSUPPORTED_WORKBENCHES` is dropped. Removed in the same swap:

- The dissolved per-domain lifecycle tools
  (`xscript.<domain>.{create_program, edit_source, set_inputs,
  set_parameter_controls, reconfigure_program, delete_program,
  inspect_program, describe_api}`) and their spec builder
  (`domain_tool_specs`); `register_project_tools` registers the four
  project tools instead.
- The editable Model Code Editor `CadexScriptedEditor.py` (3223 lines) with
  all of its `CadexGui.py` registration/menu/command wiring (Python-only; no
  C++ referenced it).
- The per-domain host lifecycle in `CadexScriptedRuntime.py` (8254 → ~950
  lines): capture/prepare/finalize/validate/accept/retain per-domain
  candidates, reference capture, per-domain host validators
  (part/sketcher/assembly execution validation), inspection/delete/controls
  plumbing, and the domain adapter registry + the four adapter classes. The
  project path keeps `_stage_worker_bundle` (project bundle only),
  `execute_candidate`, `_worker_environment`, `_staged_artifact_path`,
  `_apply_replacements`, `_merge_patch`, and the project lifecycle;
  `describe_project_api` composes the project describe payload from the
  live capability APIs.
- The per-domain provider context/document snapshots and program-contract
  validation in `CadexScriptedDomains.py` (4695 → ~660 lines): domain
  context snapshots for every workbench, `complete_domain_context`,
  manifest migration (`migrate_program_manifest`), `program_revision*`,
  input/schema/output validation, and the adapter registry. The capability
  packs remain as worker execution/publication contracts with an empty tool
  surface.
- The session domain dispatch and editor-candidate bridges in
  `CadexSession.py`, replaced by `_run_project_xscript_tool`
  (capture → prepare → execute → validate → publish → accept with the
  existing thread-dispatch/cancellation/progress plumbing; failures persist
  via `record_project_candidate_failure` and return `model_state` with
  `next_write_expected_revision` = the store's working revision).
- Test suites superseded by `project_xscript_api_integration.py`: the four
  per-domain integration suites, `domain_xscript_worker_integration.py`,
  `test_partdesign_xscript_v2.py`, `test_xscript_parameter_controls.py`,
  `test_scripted_editor_architecture.py`, and the partdesign schema golden
  fixture. `qt_domain_worker_heartbeat_integration.py` was adapted to the
  project lifecycle. `test_tool_surface_guardrails.py` pins the new exact
  surface and asserts the dissolved operations stay gone.

Net: ~24.8k lines deleted, ~1.3k added.

**Rationale.** docs/VISION.md and ADR-011: one project script is the sole
source of truth; a per-domain multi-program surface contradicts it and
carries an order of magnitude more host machinery than the project path
uses.

**Consequences.** `CadexParametersPanel.py` is intentionally untouched: it
still imports `CadexSession.run_domain_xscript_operation` (now a structured
`DOMAIN_TOOLS_RETIRED` failure stub) and
`domain_program_index_snapshot`/`complete_domain_program_index` (now an
always-empty index), both unreachable in practice because the project
surface lists no per-domain programs. Phase 2.5 rewires the panel to the
project script's `param_specs` and deletes these compatibility symbols.
Resurrecting any per-domain lifecycle machinery is a direction change and
needs a new ADR.

## ADR-014 — Phase 2.5 Parameters panel bound to the project script (2026-07-24)

**Decision.** `CadexParametersPanel.py` reads its rows from the project
script's declared parameters and commits changes through
`xscript.project.set_params`. The heuristic control-guessing layer dies.

- Row source: `script.json` `param_specs` (declaration order) +
  `param_values`, read via `CadexProjectScriptStore` (`_project_parameters`).
  The pure `spec_control(spec, value)` helper resolves each declared spec to
  slider metadata — declared `label`/`unit`/`min`/`max`/`step`/`description`
  win per-field; missing bounds fall back to a value-bracketing band widened
  so the stored value is always reachable, rounded outward onto the step
  grid.
- Commit: `CadexSession.run_project_xscript_operation` (the
  `run_domain_xscript_operation` retirement stub replaced by this public
  wrapper over `_run_project_xscript_tool`) with
  `{"values": {name: value}, "expected_revision": working_revision}`.
  `STALE_PROGRAM_REVISION` re-guards from `observed.current_revision` and
  retries once; failures track `model_state.next_write_expected_revision`
  (a failed rebuild advances the working revision on disk) and revert the
  row — accepted live geometry is never touched by a failed commit.
- Deleted: `heuristic_control`, `resolve_control`, the name-token
  unit/angle/count heuristics, the program-selector combo box and its
  `_active_xscript_surface`/`_list_xscript_programs` plumbing, and the
  ADR-013 compatibility symbols
  (`domain_program_index_snapshot`/`complete_domain_program_index` in
  `CadexScriptedDomains.py`). One project script — there is nothing to
  select.

**Rationale.** D6 (plan): parameter controls are declared in the script
(`params(width=num(...))`), so guessing ranges from parameter names is dead
vocabulary; the panel must ride the same guarded rebuild path as the
provider tools so a slider drag and an assistant edit are
indistinguishable to the store.

**Consequences.** Undeclared parameters no longer get invented sliders —
the panel shows exactly what the script declares. Resurrecting the
heuristics needs a new ADR.

## ADR-015 — Phase 3 shell: 50/50 layout + native-route lockdown (2026-07-24)

**Decision.** The interim Qt shell converges on the product layout within
the capped-investment rule (no Coin3D work, no new workbench-style UI):

- **Read-only script view** (`CadexScriptView.py`): a QPlainTextEdit dock
  rendering `script.py` from the store. Not an editor — mutations go
  through `xscript.project.*` or the sliders. The editable Model Code
  Editor died in ADR-013.
- **50/50 split**: a main-window event filter re-issues `resizeDocks` on
  every Show/Resize, sizing the visible right-column docks to half the
  window width. The signal-severing constraint is load-bearing:
  `QMainWindow.addDockWidget`/`splitDockWidget` on FreeCAD-managed docks
  at runtime severs other panels' Python signal connections, so docks are
  never repositioned after registration. Consequence: the stable
  top-to-bottom order is tree / parameters / script / chat (creation
  order — the C++ tree dock exists first, the assistant pin appends
  last), not the nominal chat-first order; reordering would require the
  forbidden runtime repositioning.
- **Native-route lockdown** (re-applied on every chrome pass, since
  workbench activation rebuilds menus and shortcuts): the menu bar is
  rebuilt to one Cadex menu (About / Preferences / Quit — Preferences
  stays reachable because the API keys live there); every non-allowlisted
  QAction shortcut is stripped; a tree event filter swallows ContextMenu
  and MouseButtonDblClick; a Gui document observer resets any native edit
  session that no tool sanctioned (`sanction_native_edit`, called by
  `partdesign.edit_sketch`; the sanction is consumed when the session
  closes).

**Rationale.** docs/VISION.md: a user session touches only chat, sliders,
tree, script view, viewport. Blocking routes beats hiding chrome the next
workbench activation would re-show.

**Consequences.** Manual FreeCAD modeling is unreachable in the shell;
resurrecting any native route is a direction change and needs an ADR. The
whole layer is disposable with the Qt shell (docs/INTEGRATION.md).

Verified by adversarial GUI probe: minimal menu and empty shortcut table
before and after workbench-switch attempts; hidden toolbars; blocked tree
context menu; unsanctioned sketch edit reset while the sanctioned one
survives; 50/50 held at three window sizes.

## ADR-016 — Phase 4 minimal mesh domain (2026-07-24)

**Decision.** Mesh joins the project script as the fifth capability domain
(`cadex_mesh_api.py` / `cadex_mesh_worker.py` on `Mod/Mesh` + `Mod/MeshPart`),
scoped to the roadmap's minimal surface:

- **API** (`MeshDomainAPI`, staged as the `mesh` global): `from_shape`
  (tessellate a same-script part value via `MeshPart.meshFromShape`),
  `import_file` (one flat STL/OBJ/PLY from `<project>/assets/`), `union` /
  `difference` / `intersection` (native mesh set operations), `decimate`.
  One output type: `mesh`. Export needs no new tool — `file.export_model`
  already meshes and writes `Mesh::Feature` objects.
- **Pipeline**: evaluation order becomes sketcher → part → partdesign →
  mesh → assembly; mesh outputs export one binary PLY artifact and a
  vertex-set geometry fingerprint that joins the content digest
  (`mesh_sha256`; brep entries unchanged, so existing digests stay
  stable); validation imports the detached native mesh off-thread;
  publication reuses the pre-existing `mesh`-domain apply routine
  (`_configure_mesh` → `Mesh::Feature`) inside the ONE project
  transaction. The tool surface is unchanged: capability packs carry no
  tools (ADR-013).
- **Asset staging**: `prepare_project_candidate` copies the project's flat
  `assets/` mesh files (64 files / 128 MB cap, known suffixes, no symlinks)
  into the worker staging dir; `mesh.import_file` resolves only against
  that staged copy, so the sandbox never reads the durable tree.
- **Mesh determinism, measured and handled in two layers.** The native set
  operations are non-deterministic at the representation level — measured
  run to run (even within one process): (a) identical point sets returned
  in permuted vertex/facet order, and (b) occasionally a *different
  triangulation* of the same coplanar cut region (same surface and vertex
  set, facet count 371 vs 372). Layer 1: the worker rebuilds every mesh in
  canonical order (vertices sorted, facet cycles rotated to the smallest
  index, facets sorted) — immediately after each boolean, so downstream
  consumers like decimate see one deterministic input, and again before
  export. Layer 2: the content digest identifies a mesh output by a
  SHA-256 over its sorted exact vertex set (`geometry_sha256` →
  `mesh_sha256`), not artifact bytes — triangulation-invariant, exact (no
  rounding, so no quantization boundary flips). Layer 3: `decimate` is an
  *approximating* kernel (GTS-derived edge collapse with
  address-dependent tie order — measured ≥3 distinct results across runs
  of identical input), so decimate outputs and every value built on one
  carry no geometry fingerprint and are digest-identified by their
  canonical definition instead (`payload_sha256`;
  `payload_tree_is_deterministic`). Verified: an 8-output mixed
  part/assembly/mesh script (tessellation, boolean union, decimation, STL
  import) rebuilds digest-stable across repeated headless runs on both
  the release and pixi FreeCAD builds (20+ seed+rebuild+rebuild cycles);
  union vertex sets were exact across ~100 measured worker runs.
- **Removal**: the stale generic-builder entry
  `_DOMAIN_OPERATION_OUTPUT_TYPES["mesh"] = {"from_object": "mesh"}`
  (culled-domain residue) is deleted; the mesh domain now has an explicit
  production API class like the other four.

**Rationale.** docs/ROADMAP.md Phase 4: the fourth-plus capability area
through the same pipeline, with rebuild determinism intact. No interactive
mesh editing — that waits for BMesh in the Blender shell (Phase 6).

**Consequences.** Mesh booleans inherit the native kernel's geometric
behavior (set operations, not exact CSG); partdesign/sketcher values are
not tessellatable in v1 (only part values — partdesign Bodies build through
their own document machinery). Both are candidates for the cadexd protocol
era if needed.

## ADR-017 — Phase 5.1–5.3: cadexd, the headless engine service (2026-07-25)

**Decision.** The xscript engine runs behind **cadexd**, a persistent
headless FreeCADCmd process speaking schema `cadex-cadexd-v1` — newline-
delimited JSON over stdio, one cadexd child per open project, spawned and
owned by the shell. Owner decisions locked 2026-07-25:

- **Document of record stays in the shell** (the .FCStd saved by the Qt
  app). cadexd hosts an *ephemeral* headless `App::Document` per project
  (the `cadex_rebuild` pattern) so publication semantics — ownership lint,
  contract-driven GC, output identity, document/object inspect — run
  engine-side. Both documents are rebuildable and digest-verified.
- **Latency: parity only.** The worker is still spawned per run; a
  warm-standby worker is documented future work, not built.
- **Transport: stdio NDJSON**, 8 MB frame cap; binary artifacts are
  referenced by filesystem path, never inlined.

Mechanics (`CadexdProtocol.py` — pure, FreeCAD-free; `cadexd.py` — entry,
`pixi run cadexd`):

- Ops: `open_project, describe_api, write_script, edit_script, set_params,
  rebuild, resolve_pin, inspect, cancel, shutdown`. The INTEGRATION.md
  sketch's `run` dissolved into the real lifecycle ops so the
  `STALE_PROGRAM_REVISION` guard and failure envelopes carry over verbatim.
  Lifecycle responses are **exactly** the accept payload / `tool_failure`
  envelope the in-process session tool produced (shared engine entry
  `CadexScriptedRuntime.run_project_lifecycle`, also used by
  `cadex_rebuild` — net-zero), plus a per-output `display` block
  `{artifact_kind, artifact_path (absolute), placement, tessellation|null}`.
- **Restore pass**: every `open_project` with an accepted digest re-runs
  THE script into the fresh ephemeral document and asserts digest equality
  — each open re-proves restart determinism (`CADEXD_RESTORE_FAILED`
  otherwise).
- **Budgets** resolve once at `open_project` (request args, preferences
  fallback) and reach the pipeline via `service.scripted_budgets()`.
- **stdout-pollution defense**: fd 1 is dup()ed to a private protocol fd
  before FreeCAD can print, then redirected to stderr. stdin EOF is the
  lifetime signal (shell death ⇒ self-exit).
- **Serial dispatch**: one modeling request in flight; a concurrent
  modeling request is refused `CADEXD_BUSY` by the reader thread;
  read-only requests queue; `cancel` reaches the running worker through
  the existing `run_process` kill path (`RUN_CANCELLED`). cadexd itself
  runs *without* `--safe-mode` (trusted engine code); user scripts stay in
  the per-run `--safe-mode` worker sandbox.
- `inspect` serves `script/api/image` (store) and `document/object`
  (ephemeral document); `selection` is rejected as shell-only.

Supporting engine capabilities landed with it:

- **5.1 Display tessellation + ID maps** (`cadex_tessellation.py`, staged
  into the project worker bundle): per BREP output one
  `cadex-tessellation-v1` artifact — binary buffer (f32 vertices, u32
  triangles, f32 edge polylines) + JSON sidecar whose
  `face_ranges`/`edge_polylines` map spans back to the exact 1-based
  Face/Edge enumeration of `face_details`. Adaptive deflection
  `clamp(rel × bbox_diagonal, 0.05, 5.0)` with coarse/standard/fine
  presets (explicit override wins); mesh outputs emit a trivial one-range
  map. Opt-in per request (`display`), computed after the digest —
  **digest-neutral by construction and by test**.
- **5.2 Headless pin resolution** (`CadexPinResolution.py`): resolves
  `{output, selection}` against the accepted revision's staged BREP.
  `script.json` gained `accepted_attempt` (attempt id + staging path;
  the accepted attempt directory is pinned — no GC exists). Selections are
  the exact `_query_subelements` fingerprint vocabulary (reused by import
  from `cadex_partdesign_worker`) or a direct `{element_type, index}`
  (client picking path: triangle → `face_ranges` → index happens
  client-side). `CadexReferenceContracts.resolve_interface` stays the
  document-bound twin.

**Verification.** Stub suites for codec/dispatch/cancel/pin/tessellation;
FreeCADCmd integrations `tessellation_id_map_integration.py`,
`pin_resolution_integration.py`; ctest `CadexdLifecycle` drives a real
cadexd child end-to-end including kill -9 → respawn → restore digest
equality and a mid-run cancel. `CadexProjectRebuildDigest` unchanged and
green over the shared-lifecycle refactor.

**Consequences.** The branding contract admits exactly one non-prefixed
module name (`cadexd.py` — the service's product name). The worker staging
bundle grew by `cadex_tessellation.py`. Progressive tessellation and the
warm-standby worker remain future work under the Phase 6 gate.

## ADR-018 — Phase 5.4–5.5: shell switchover; the in-process path is removed (2026-07-25)

**Decision.** The Qt shell drives **all** modeling through cadexd; the
in-process capture→execute→publish path inside `CadexSession` is gone.

- **Seam**: `run_project_xscript_operation` kept its signature — the
  Parameters panel and provider dispatch are byte-for-byte unchanged
  callers. `_run_project_xscript_tool` now resolves the project's client
  (`CadexdClient.client_for_project`, budgets read from preferences on the
  document thread), sends the lifecycle op, forwards progress events to
  the chat UI, and polls cancellation every 50 ms (a `cancel` frame
  reaches the running worker). `describe_api` stays local — it is pure
  authoring metadata, identical on both sides of the protocol.
- **Hydration** (`CadexShellHydration.py`): on the Qt document thread, ONE
  transaction (one undo step) mirrors the accepted contract into the
  .FCStd of record — find-or-create `Part::Feature`/`Mesh::Feature`
  display objects keyed by the existing xscript ownership tags, solved
  assembly placements applied, revision tag updated, **contract-driven
  GC** (tagged objects whose output left the accepted contract are deleted
  with their closure — robust across cadexd restarts, and it sweeps
  publication-era native objects on first hydration after the
  switchover). Hydration failure returns `SHELL_HYDRATION_FAILED` while
  the engine state is already accepted — a documented asymmetry; the next
  success self-heals. The per-output `display` block is consumed
  shell-side and stripped from the provider-visible payload, which
  therefore stays exactly the pre-split contract.
- **Crash policy**: child death or timeout mid-request →
  `CADEXD_CRASHED` envelope, client marked dead, next request respawns
  and replays `open_project` (the panel already self-heals via
  `STALE_PROGRAM_REVISION` / `next_write_expected_revision`). Clients are
  killed on document close (`slotDeletedDocument`) and at exit.
- **Inspect routing**: `core.inspect` scopes `document/object/script/api/
  image` route to cadexd (engine truth: the ephemeral document and the
  store); `selection` stays shell-local. Without an open project the
  local read-only path answers as before.
- **Removals**: the in-process lifecycle body in `CadexSession` (replaced
  by the client call); `CadexGui`'s publication-internal hooks —
  `slotChangedObject` → `mark_programs_stale_from_source` (shell objects
  are display mirrors; human edits no longer feed engine dependency
  state) and the document-open input-snapshot compaction / assembly
  dependency-anchor migration (publication metadata no longer lives in
  the shell document). Verified by build + tests in this change.
- **What stays shell-side and why**: viewport + selection (the only
  viewport), the .FCStd document of record (persistence + undo), the
  provider loop and chat UI, the Parameters panel (reads `script.json`
  specs; commits through the same guarded seam), reference-image store
  access. The pipeline modules stay in-tree — the split is
  **process-level**, cadexd and `cadex_rebuild` run them — and the new
  guardrail `test_engine_shell_split_guardrails.py` pins that
  `CadexSession`/`CadexGui`/`CadexParametersPanel`/`CadexShellHydration`/
  `CadexdClient` never import `CadexScriptedDomainPublication`,
  `CadexScriptedProcess`, or the pipeline entry points.

**Measured.** `cadexd_shell_switchover_integration.py` (client → cadexd →
worker → hydrate on the 24-hole/fillet/mesh-skin baseline part): median
set_params drag **0.479 s** over 10 drags (bar ≤ 0.65 s; in-process
baseline 0.57 s) — protocol framing + hydration cost less than the
in-process publication it replaced, with the per-drag worker spawn still
dominating (warm-standby worker remains future work). GUI smoke (probe
script in the real `freecad-release` shell, tools on a worker thread with
document-thread dispatch): write_script hydrates one `Part::Feature` +
one `Mesh::Feature`, a set_params drag updates the geometry, each
accepted revision is exactly ONE undo step, and undo restores the prior
accepted geometry.

**Consequences.** Undo in the shell now spans exactly one hydration
transaction per accepted revision (display mirrors), not per-domain native
feature edits; engine-truth inspection reflects cadexd's ephemeral
document. Resurrecting an in-process modeling path is a direction change
requiring an ADR and owner sign-off.

## ADR-019 — Phase 6: the Blender shell speaks cadexd (2026-07-25)

**Context.** Phase 5 left cadexd as the sole modeling path with the Qt
shell as its first protocol client. The confirmed endpoint (ADR-006,
`docs/INTEGRATION.md`) is the Blender shell: the `mesh_agent` prototype in
`/Users/theo/mesh`. Two decision-gate criteria still needed shell-side
evidence: ID-map/picking fidelity in a real viewport, and slider-drag
latency through the full shell path.

**Decision.** `mesh_agent` gains a cadex backend as a third assistant mode
("Cadex CAD", `modes.py backend: "cadexd"`) **alongside** the local-exec
path — same chat, same tool names (`get_script`/`write_script`/
`set_params`), routed per mode. All integration code is new files in the
mesh repo (additive-only policy holds; ledger updated):

- `cadexd_client.py` — GPL, dependency-free NDJSON stdio client; spawns
  `FreeCADCmd -c "import cadexd…"` per project root (found via add-on
  preference / `MESH_FREECADCMD` / PATH; module dir `<prefix>/Mod/cadex`).
  No cadex imports: the process boundary is the integration contract and
  the LGPL↔GPL seam. Crash → `CADEXD_CRASHED` envelope, respawn + reopen
  on next request.
- `cadex_backend.py` — per-scene session (project root beside the .blend,
  `<stem>.cadex/`), revision-guarded lifecycle ops with one
  `STALE_PROGRAM_REVISION` self-heal retry, engine `param_specs` bridged
  into the same `scene.mesh_params` PropertyGroup the local path uses
  (slider drag → debounced `set_params` via `model.rebuild()` backend
  dispatch — the only edit to the local loop).
- `cadex_hydrate.py` — `cadex-tessellation-v1` buffers → mesh objects in
  the Model collection: per-triangle **`cadex_face` INT face attribute**
  (1-based BREP face ids from `face_ranges`), `cadex_edge` wire child,
  placement matrices, contract-driven GC keyed by a `cadex_output`
  custom property (mirrors ADR-018's Qt hydration).
- `cadex_pick.py` — viewport pick: ray-cast → polygon → `cadex_face` →
  `resolve_pin {element_type, index}`; resolved pins are queued and
  attached to the next chat message like image attachments.
- One `undo_push` per chat turn is unchanged (verified through the real
  bridge in cadex mode).

**Progressive display (engine-side addition).** Streaming standard-quality
tessellation on every drag cost ~0.86 s extra on the baseline part. New
`"draft"` quality preset (relative deflection 0.05) in
`cadex_tessellation.py`; the Blender shell requests
`{quality: "draft", edges: false}` while a drag is in flight and issues a
background `rebuild` at `standard` once the drag settles (cancelled by the
next drag; revisions are content-derived so the refine keeps the accepted
revision). Verified by `cadex_tests` (424 passed).

**Measured** (`tests/python/bl_mesh_agent_cadex.py`, headless Blender
5.3.0-alpha against the release cadexd; gate report
`CADEX-BLENDER-GATE`):

- **Picking fidelity 100%** (372/372 ray-cast picks; bar ≥ 99%) on the
  tessellation corpus (box, cone, torus, drilled+filleted plate), with
  every one of the 40 BREP faces' tessellation aggregates (area,
  centroid, planar residual) matching the engine's `resolve_pin` truth;
  ID-map attributes byte-identical to the sidecar ranges; mesh-domain
  outputs refuse pins.
- **Slider-drag median 0.548 s** (bar ≤ 0.65 s) on the 24-hole/fillet/
  mesh-skin baseline — through Blender → cadexd → worker → tessellation
  → numpy hydration, i.e. *including* the display streaming the Qt
  measurement (0.479 s) did not carry. Post-drag refine: 1.38 s.
- Engine restart: reopen rehydrates geometry, params, and script text
  from the store.

**Consequences.** The decision gate's shell-side criteria are met in the
real shell; Phase 7 (convergence) is unblocked. The per-drag worker spawn
still dominates drag latency; the warm-standby worker remains the named
lever for sub-100 ms drags. Blender remains display-only: engine truth
lives in the cadexd project store, and the mirrored `model.py` text block
is read-only context, not a rebuild input.

## ADR-020 — Phase 7 shape: the Blender shell is the product (2026-07-25, owner)

**Decision.** Phase 7 converges the two shells into one product. Six
sub-decisions, all owner-approved:

1. **The Qt shell is retired outright** — not kept as a headless harness.
   This closes the open question at `docs/VISION.md` (Qt shell's fate). The
   deletion covers the UI *and* the provider stack it exists to serve:
   `CadexGui`, `CadexSession`, `CadexProvider`, `CadexCore`, `tool_impl/`,
   the conversation store, prompt starters. **No API-key provider path
   survives**: the product's model loop is the Claude Code CLI running
   inside Blender (`mesh_agent`'s `backend.py`), and a second model loop in
   a second shell is exactly the duplication this phase removes.
2. **Scope** is three tracks in order: close the seven blocking Blender
   gaps (M) → delete the Qt shell (C) → packaging, onboarding, docs (P/O).
3. **One bundle.** The Blender application carries the cadex engine as a
   payload; the add-on defaults to it. A user installs one thing. This is
   affordable because `BUILD_GUI=OFF` takes ~250 MB (Qt6, PySide6, Coin,
   `lib*Gui*`) off the engine payload — see ADR-022/ADR-023.
4. **Conversation history lives in the `.blend`**, alongside the Claude Code
   `session_id`. This ratifies Phase 6's `history.py` and **explicitly
   reverses** `docs/INTEGRATION.md`'s open-question lean toward the cadexd
   project store / `$CADEX_HOME`. Rationale: the conversation is shell
   state, not engine state; the engine has no notion of a turn. One file
   the user can move, copy, and mail is worth more than a second store.
5. **Local (mesh-native) modes stay**; `CADEX` becomes the default mode.
   General and Part Design modes remain for mesh-native work. This is a
   knowing exception to ADR-003 and `docs/VISION.md`'s "one project script
   is THE user-visible artifact": in Cadex mode the project script is the
   artifact, and the local modes are a *different product surface* (direct
   BMesh authoring) that happens to share a chat panel. Recorded rather
   than silently kept; revisit if the two script formats start leaking into
   each other.
6. **The mesh repo's additive-only upstream policy ends here.** Phase 7
   modifies upstream Blender files for the first time — the default app
   template and the engine install rules. `docs/mesh/UPSTREAM_DIFFS.md`
   gains its first "Modified upstream files" rows. (See ADR-024.)

**Rationale.** Phase 6's gate closed in the real shell (ADR-019: 372/372
picks, 0.548 s drag median). Carrying two shells for one engine past that
point costs a second model loop, a second hydration path, a second
packaging story, and a doc set that has to describe both. The exit
criterion — *a new user only ever sees the Blender shell* — is not
reachable while the cadex repo still ships a user-facing application.

**Ordering.** Blender gaps first, Qt deletion second. Deleting Qt first
would turn five working reference implementations into archaeology while
the mesh work is in flight: cancellation polling through the protocol,
budget resolution, contract-driven GC with document-close lifetime, and
the revision-guard commit path. The latency-evidence objection is handled
by landing C0 (a client-agnostic engine benchmark) before the Qt client is
deleted.

### The engine discovery contract `cadex-engine-v1` `[Cadex-new]`

Fixed here so both repos can code against it before either implements it.
A packaged engine payload is a directory containing a manifest file named
**`cadex-engine.json`** at its root:

```json
{
  "schema": "cadex-engine-v1",
  "version": "0.0.2",
  "protocol": "cadex-cadexd-v1",
  "freecadcmd": "bin/freecadcmd",
  "module_dir": "Mod/cadex"
}
```

- `schema` — literal `"cadex-engine-v1"`. A shell that does not recognise
  the value must refuse the payload, not guess.
- `version` — the cadex engine version the payload was built from.
- `protocol` — the cadexd wire protocol the payload speaks
  (`docs/INTEGRATION.md`). A shell checks this, not `version`.
- `freecadcmd` — path to the command-line FreeCAD binary, **relative to the
  manifest's directory**, using forward slashes on every platform.
- `module_dir` — path to the directory that must be on `sys.path` for
  `import cadexd` to work, same relative-path rule.

**The manifest is the point.** Shell-side discovery becomes "find
`cadex-engine.json`, read two paths out of it" instead of guessing at
`<prefix>/Mod/cadex` vs `<prefix>/../Mod/cadex` vs a macOS `.app` interior.
That retires the layout-guessing bug class permanently, on all three
platforms, and it lets a developer point at a dev build by dropping one
file. Discovery order (shell side): explicit preference → `MESH_FREECADCMD`
→ bundled manifest → `PATH`.

**Consequences.** Phase 7 in `docs/ROADMAP.md`; a new Phase 8 for the
`src/Gui` tree removal that ADR-022 defers. ADR-021 (Qt deletion), ADR-022
(GUI build off), ADR-023 (one bundle), ADR-024 (onboarding) implement this
one. `docs/VISION.md`'s Qt open question is answered and its Qt non-goal
becomes historical. `docs/INTEGRATION.md` becomes the two-repo contract
document.

## ADR-021 — The Qt shell and the provider stack are deleted (2026-07-25)

**Decision.** Phase 7 track C removes the Qt shell and everything that
existed to serve it. This repository stops being an application.

**Inventory.** UI layer (C3): `CadexGui`, `CadexExperimentalMode`,
`CadexParametersPanel`, `CadexScriptView`, `CadexGrid`,
`CadexExperimentalChat`, `CadexPromptStarters`, `InitGui`, nine SVGs, the
`Cadex_Resources` install set, and the three Qt preference pages.
Provider/session stack (C4): `CadexSession`, `CadexProvider`, `CadexCore`,
`CadexAuth`, `CadexCodex`, `CadexDebug`, `CadexTransactions`,
`CadexPointArtifacts`, `CadexGeometry`, `CadexAssemblyHierarchy`,
`CadexEditState`, `CadexPreferences`, the whole `tool_impl` package,
`requirements.txt`. Protocol seam (C5): `CadexdClient`,
`CadexShellHydration`. `src/Mod/cadex` went from 57 Python modules to 34.

**No API-key provider path survives.** The product's model loop is the
Claude Code CLI inside Blender; a second one here was duplication.

**The four splits that made it possible (C1, C2).**

1. `CadexEngineSettings.py` — the engine needed exactly two numbers out of
   `CadexPreferences`, which imported `CadexAuth`/`CadexDebug`/
   `CadexPromptStarters` at module scope.
2. `CadexScriptStore.py` — `CadexProject` was two stores in one module;
   only the script store is engine state. Measured effect: cadexd's
   transitive closure lost `CadexProject`.
3. `test_engine_purity_guardrails.py` — an AST closure walk with a
   `KNOWN_RESIDUE` ledger that named each remaining forbidden edge and the
   commit that would remove it, and failed when an entry stopped being
   true. It guarded C3/C4 as they happened and is now empty.
4. C2 cut `CadexReferenceContracts`'s dead `tool_impl` edge, established by
   instrumenting a real publication (`managed: []`, `_rebind_one` never
   entered), not by reading.

**`requirements.txt` is deleted, not emptied.** `jsonschema` had one
importer (`ToolRegistry`) and one other user (`ToolSpec.validate_arguments`),
both provider machinery. The engine now needs FreeCAD's own runtime and
nothing else — which is what lets ADR-023's payload be a directory of files
rather than an environment.

**Test reshaping.** 36 files / 425 tests → 20 files / 154 tests, inside the
declared acceptance band of **150–200**: above 200 would mean something
Qt-shaped survived, below 150 that an engine contract was dropped. Two
files the plan expected to survive in half did not:
`test_geometry_references` died whole (all 12 tests drive `CadexCore`'s
viewport-selection capture; the fingerprint contract is produced by the
workers, matched by `CadexPinResolution`, and covered by
`test_pin_resolution` plus `pin_resolution_integration`), and
`test_model_context_contract` kept 4 of 20 rather than ~10. Three files
were renamed in C7 (`test_project_tool_surface`,
`test_engine_identity_contract`, `test_engine_defaults_and_envelopes`) and
`CLAUDE.md`'s "not subject to relaxation" clause was updated in the same
commit, so the guardrail it names still exists.

Contracts asserted through the UI were preserved, not dropped:
`TestStageAwareFailureRendering` (which tested `CadexGui`'s transcript
renderer) became `TestFailureEnvelopeContract`, asserting every
`FAILURE_STAGES` value round-trips and the `tool_failure` envelope's keys
are stable — the Blender shell parses exactly those keys, across a
repository boundary.

**The successor evidence (C0).** `cadexd_latency_integration.py` re-established
the switchover measurement client-agnostically **before** C5 deleted the
client that produced it: the same 24-hole/fillet/mesh-skin baseline and ten
`set_params` drags over raw NDJSON. Measured 0.457 s engine-only (Qt-era
0.479 s) and 0.557 s with the draft display block (Blender-era 0.548 s).
The bar survives the client.

**Consequences.** `docs/INTEGRATION.md` becomes the two-repo contract
document, and `test_engine_purity_guardrails` now asserts
`CadexdProtocol.OP_ARG_SPECS` equals its op table — with the shell in
another repository, the document is the contract and a doc↔code
cross-check is the only thing that catches cross-repo drift.

## ADR-022 — GUI build off; `isVibeExperimentalModeSession` reverted (2026-07-25)

**Decision.** Release and package builds set `BUILD_GUI=OFF`. The
`isVibeExperimentalModeSession` hook is reverted to stock FreeCAD. The
`src/Gui` tree is **not** deleted in Phase 7.

**The hook (C6a).** It let a Cadex "experimental mode" session suppress
stock chrome — toolbars, docks, the status bar, overlay state, the Start
page's first-start view and workbench autoload. Its UI died in C3, and the
preference defaults **true**, so keeping it would have meant a FreeCAD that
hides its own interface for a shell that no longer exists.

Fifteen sites: `src/Gui/MainWindow.cpp` (7 uses + the definition),
`MainWindow.h` (the declaration), `ToolBarManager.cpp` (2),
`DockWindowManager.cpp` (1), `OverlayWidgets.cpp` (1),
`src/Mod/Start/Gui/StartView.cpp` (3), `AppStartGui.cpp` (1).

**Conservative-zone justification.** `CLAUDE.md` asks for the smallest
possible diff in inherited core. This change *reduces* the fork's delta
against upstream FreeCAD to zero in every file it touches — it is the most
conservative-zone-friendly change available, because it removes fork code
rather than adding any. The "Vibe" identity leaves the tree entirely and
`_ALLOWLISTED_VIBE_RESIDUE` empties. The lowercase-preference-group test
inverts accordingly: it now asserts the inherited GUI core reads *nothing*
of ours, across five files.

**`BUILD_GUI=OFF` (C6b).** Two blockers, found by a throwaway configure
spike, each fixed in three lines without changing GUI-on behavior:
`LinguistTools` was gated behind `BUILD_GUI` although `src/App` compiles
translations with the GUI off (it is a build tool, not a runtime library);
and the `Gui` test suite plus `setup_qt_test(InventorBuilder)` link
`FreeCADGui`, so both are now guarded the way every kept workbench already
guards its own `Gui` subdirectory.

Scope is narrow on purpose: only the `conda-release` preset and
`package/rattler-build/build.sh`. `pixi run configure` (debug) still builds
the GUI, so a breakage here cannot block daily work.

**Measured**, GUI build vs GUI-less build of this tree: `lib/` 43 MB →
8.3 MB, `Mod/` 49 MB → 22 MB, files matching `*Gui*` 93 → 8, and `bin/`
reduced to `FreeCADCmd` + `CadexGeometryWorker`. 61 MB off this
repository's own output; the larger saving (Qt6 ~85 MB, PySide6 ~52 MB,
Coin ~7 MB) is dependency weight the payload no longer carries, realised
in ADR-023.

**`src/Gui` is deferred, not kept.** It is 66 MB / 729 files plus every
`src/Mod/*/Gui`, and `BUILD_GUI=OFF` captures 100% of the size and
build-time benefit with a zero-line conservative-zone diff. Per
`docs/FREECAD.md` §3's removal protocol, **this is the disable commit**;
the delete commit is Phase 8.

**Gate.** Both cadex ctests pass against the GUI-less build
(`CadexProjectRebuildDigest` 1.64 s, `CadexdLifecycle` 3.75 s), with zero
new failures against the environmental baseline.

## ADR-023 — One bundle: the engine ships inside the shell (2026-07-25)

**Decision.** This repository stops producing a user-facing application and
starts producing an **engine payload**. The Blender shell carries it and
finds it by manifest. A user installs one thing.

**The payload** (`package/engine/build_engine_payload.sh`):

```
cadex-engine-<version>-<os>-<arch>/
  cadex-engine.json     the discovery manifest (schema in ADR-020)
  bin/{freecadcmd,CadexGeometryWorker,python}
  lib/                  no Qt GUI, no PySide, no Coin
  Mod/{cadex,Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,
       Material,Measure,Show}
```

Descended from `osx/create_bundle.sh` minus the `.app` wrapper, icon
pipeline, DMG and the two provider-install scripts — none of which survive
ADR-021.

**The manifest is the point.** Shell-side discovery becomes "find
`cadex-engine.json`, read two paths out of it" rather than guessing at
`<prefix>/Mod/cadex` vs `<dir>/../Mod/cadex` vs a macOS `.app` interior.
That retires the layout-guessing bug class on all three platforms at once,
and lets a developer point at a dev build by setting one variable.

**Correction to the plan's Qt claim.** "The audit reports zero
Qt/PySide/Coin" is not achievable: FreeCAD's App layer links **Qt6Core and
Qt6Xml**, and `FreeCADCmd` inherits that (verified with `otool -L`). The
gate implemented is the one that matters — no widget toolkit, no Qt Python
bindings, no scene-graph renderer — and the build script *prints* the Qt
libraries it does carry, so the exception is visible rather than silent.
Verified on the first payload: Qt6Core, Qt6Xml, Qt6Concurrent, Qt6Network,
Qt6DBus, and none of Gui/Widgets/Quick/Qml/OpenGL/Svg/PrintSupport/UiTools,
no PySide, no shiboken, no Coin/Quarter/SoQt, no `libFreeCADGui`.

**The gate: ctest `CadexEnginePayloadSmoke`.** It runs
`test_cadexd_lifecycle.py` against the *packaged* tree, discovered through
its manifest exactly as the shell discovers it. Strictly stronger than the
`--cadex-launcher-smoke` it replaces (which ran `freecadcmd --version`),
and it reuses a test that already existed.

**It immediately earned its keep.** The first packaged engine could not
model at all: `DOMAIN_CANDIDATE_FAILED`, `No module named 'PySide'`.
`src/Mod/Assembly/JointObject.py` imported PySide, `pivy.coin` and its
preferences page at module scope, and the cadex assembly worker imports
that module for `Joint`, `GroundedJoint` and `JointTypes` — pure
App-level document classes. Every test to date had passed because the
development environment happens to have Qt installed. Those imports are now
guarded: the feature classes import headlessly; the task-panel and
view-provider classes, which nothing headless instantiates, raise clearly if
touched. **No packaging gate weaker than "run the real lifecycle against
the real payload" would have caught this.**

**Shell side (mesh repo).** `build_files/cadex_engine.txt` pins the version
and a SHA256 per platform; `fetch_cadex_engine.py` verifies and stages, and
**refuses an unpinned platform** rather than downloading it. The install
rules live behind `WITH_CADEX_ENGINE` in `source/creator/CMakeLists.txt`:
`Blender.app/Contents/Resources/cadex` on macOS, `<install>/cadex`
elsewhere.

**Workflows.** `cadex-macos.yml` and `cadex-windows-installer.yml` deleted;
`cadex-release.yml` rewritten as `cadex-engine.yml` (same triggers; no
AppImage, deb, 7z or NSIS). `src/Main/CadexPortableLauncher.cpp` is **kept**
against the plan: it is also the source for `CadexCmdPortableLauncher`, a
Windows launcher for `FreeCADCmd` that belongs to the engine.

**Verified** with `MESH_FREECADCMD` unset, against a payload placed where a
bundle carries it: preflight green with zero configuration, and
`CADEX-BLENDER-GATE` ok with `engine_from_bundle: true` — picking 372/372,
slider median 0.572 s, restore performed, cancel honoured.

**Open.** macOS notarization of the embedded engine (hardened runtime,
per-binary entitlements for a `freecadcmd` that spawns subprocesses and
dlopens OCCT) is not yet exercised. Linux and Windows payloads build but
have no shell CI.

## ADR-024 — Onboarding: Cadex is what a new user meets (2026-07-25)

**Decision.** The Mesh app template is the default, Cadex is the default
mode, the engine needs no configuration, and engine failures are visible to
the user.

**Default app template.** `UserDef::app_template`'s DNA default changes
from `""` to `"Mesh"`. Chosen over editing `creator_args.cc`: a data default
in a header conflicts as a data blob on upstream merges, argument-parsing
code conflicts as logic, and `--app-template default` escapes to stock
Blender either way. Only a fresh profile takes the default.

**Default mode.** `modes.DEFAULT_MODE` becomes `CADEX` and it leads the
mode list. The local modes (General, Part Design) remain for mesh-native
work — the tension with `docs/VISION.md`'s "one project script is THE
user-visible artifact" is recorded in ADR-020 decision 5, not silently kept.

**Zero configuration.** The engine-path preference now reads "leave empty
to use the cadex engine bundled with Mesh". `preflight()` — written in
Phase 6 and never once called — reports from three surfaces: the
preferences panel (with the resolved path when green), the chat panel in
Cadex mode, and the first cadex tool call, where the model previously
received a raw subprocess traceback and now gets a sentence plus "do not
retry".

**Error surfaces.** `cadex_backend`'s failure reports are written for the
model: structured, detailed, and invisible to the person watching the
panel. A rejected script, a rejected parameter change and an unavailable
engine each add one line to the transcript, because otherwise a rejected
revision looks exactly like a hang.

**The additive-only upstream policy ends here** (ADR-020, decision 6).
`docs/mesh/UPSTREAM_DIFFS.md` gains its first "Modified upstream files"
rows — three, each with what changed, why, and what a conflict in it would
mean — and its policy text changes from "never edit" to "every edit is
listed here, kept minimal, and justified".

**Consequence worth recording.** Flipping the default broke three tests
that had been relying on `GENERAL` being it. They now state which path they
exercise instead of inheriting a default. Tests that depend on an unstated
default are exactly what a default change should find.

## ADR-025 — One project: OCCT kept, FreeCAD and Blender dropped (2026-07-25, owner)

**Decision.** Cadex becomes **one application** — a derivative of, but not
dependent on, either FreeCAD or Blender. Parametric BREP parts and
assemblies, mixing parametrics and meshes over time, in a body that acts and
feels like Blender, entirely agentic and script-driven, with no human edit
controls. Four owner decisions settle the shape:

1. **Keep OCCT, drop FreeCAD.** OCCT is the geometry kernel; FreeCAD is the
   application layer around it, and that layer is what we have spent seven
   phases removing. What remains of it — `App::Document`, the recompute
   graph, the property system, `Part::TopoShape` — is the part we still pay
   for and no longer want.
2. **The shell is Rust + wgpu + egui.**
3. **The local bpy modes (GENERAL, PART_DESIGN) are deleted**, resolving
   ADR-020 decision 5's knowing exception in favour of one script format.
4. **The engine stays Python**, calling OCCT through our own pybind11
   binding rather than through FreeCAD's.

**What this reverses.** ADR-002 (Blender as the product shell) and ADR-020
(the Blender shell *is* the product) — the shell becomes ours. ADR-023 (the
engine ships inside the shell bundle) — there is one bundle because there is
one application, not because one hosts the other. ADR-001 survives in
substance and not in mechanism: xscript remains the single scripted modeling
engine, but the substrate under it stops being FreeCAD. `docs/VISION.md`'s
non-goals lose "a second shell of any kind" — the Rust shell is not a second
shell, it is the first one we own.

**What we actually own** (measured against source, not estimated).
**5,840 lines of domain API** (`cadex_{part,sketcher,partdesign,mesh,assembly,project}_api.py`)
define the xscript vocabulary — 94 user-facing ops — and import FreeCAD zero
times; 17 of 34 engine modules are already FreeCAD-free. The protocol
(`CadexdProtocol.py`, 187 lines, zero FreeCAD imports) is a real process
boundary. **Pins resolve by geometric fingerprint, not `TopoDS` name** — the
most kernel-portable decision in the codebase. In the shell, `backend.py`,
`bridge.py`, `mcp_shim.py` and `cadexd_client.py` carry zero `bpy`.
`CadexGeometryWorker.cpp` (1,031 lines) is pure-OCCT, FreeCAD-free, and
currently has no caller; its `TriangleBvh` + `meshDistance` + `BRepGProp` +
`BRepCheck` is roughly 80% of the differential oracle Phase 11 needs. It is
the **oracle seed, not the binding seed**: 20 OCCT headers, zero
construction API.

**What must be rebuilt or vendored.** planegcs (13,311 lines, LGPL-2.1+)
vendored, with the 5,772-line `Sketch.cpp` translation rewritten for the 32
exposed constraint variants. OndselSolver (41,385 lines, LGPL-2.1) vendored,
with its 2,218-line bridge and ~4,900 lines of FreeCAD Python rewritten.
`modelRefine.cpp` (1,491 lines, two strippable FreeCAD headers) vendored
as-is. PartDesign feature semantics for the 19 exposed ops (~6k lines) is
genuinely new code. The mesh kernel and decimator — FreeCAD-native and
non-deterministic, per ADR-016 — are replaced by **manifold** (MIT).

**Licensing.** Dropping Blender *removes* a GPL obligation; that is a
simplification, not a cost. Vendored LGPL code (OCCT, planegcs,
OndselSolver, `modelRefine`) carries an attribution obligation that cannot
be erased by rewriting around it. "References to neither" is achievable for
dependencies, API names and runtime; it is **not** achievable for the NOTICE
file, and we do not pretend otherwise.

**Rationale for the order: engine first, not shell first.** The plan was
shell-first. Auditing, rather than reasoning, reversed it on three counts.

*Subshape enumeration is a model input, not a display contract.* Five ops —
`subshape`, `defeature`, `fillet`, `chamfer`, `thicken` — take 1-based
`TopExp::MapShapes` ordinals as **script arguments**, saved in
agent-authored programs. An enumeration shift does not break a pin the way a
missing pin breaks: it silently builds *different geometry* that passes
`isValid()`, then shifts every downstream index, and compounds with no
alarm. This is a latent bug **today**, independent of any migration — those
indices break on any parameter change that alters topology, which is the
entire point of parametric CAD.

*The real risk is unverifiability, not difficulty.* 41 of 49 `part` ops, 32
constraint variants, 13 joint types and 19 PartDesign features have no
recorded expected behaviour anywhere; a spot check of 15 ops (`loft`,
`sweep`, `thicken`, `slice`, `project`, `repair`, `sew`, `general_fuse`,
`helix`, …) found zero test hits across both repositories. The content
digest is defined not to match across kernels for BREP — **and not for mesh
either**: `mesh_sha256` is triangulation-invariant but not
kernel-invariant, and manifold's boolean vertices are neither bit-identical
to FreeCAD's nor equal in count. So Phase 11's failure mode is not a wall,
it is a grind with no "done" signal. The counter is **characterization
testing recorded from the current engine before it is touched**.

*Shell-first has no measurable payoff and the worst stall state.* The
0.548 s slider median is dominated by the per-drag `FreeCADCmd --safe-mode`
spawn; a new shell inherits that cost and cannot beat it. Picking is already
372/372. A stall after a shell-first phase leaves us maintaining a new Rust
application *and* a 500k-line FreeCAD fork taking no upstream merges, having
deleted the shell we got for free. A stall after the engine phase leaves a
shippable product on a working Blender shell.

**Consequences.** `docs/ROADMAP.md` gains Phases 9–13 and Phase 8 gains one
item (`cadex_assembly_worker.py` imports `CommandCreateView` — GUI-lineage
code used headlessly; that dependency is verified during the `src/Gui`
deletion, not in Phase 11). Phase 10 is a **go/no-go gate**, not a
formality: a two-day enumeration probe, then a time-boxed characterization
of ten of the deepest ops. If ten ops take a week, ninety-four take two to
three months of archaeology before a line of the new engine exists — and
that number, not the size of the binding, decides whether Phase 11 starts.
Two new gates land in Phase 9 (`test_response_schemas.py`, and an OCCT
enumeration fingerprint) because everything downstream assumes contracts
that are currently assumed rather than asserted.

**STEP import/export is promoted to a first-class engine deliverable.**
`file.export_model` / `file.import_model` are named in
`CadexModelingSurface.py` with no implementation and no cadexd op; the only
export today is `bpy.ops.wm.stl_export` of *display tessellation*. A
parametric CAD application that cannot emit STEP is not a product. It is
scheduled in Phase 11, not left to the shell.

**Open.** The honest time shape is not knowable before Phase 10's probe and
time-box; the binding is weeks, the characterization is the unknown that
sets the scale. Whether parameter sliders count as "human edit controls" is
resolved in favour of *no* — `docs/VISION.md` principle 5 has humans steer
via chat **and** sliders. macOS notarization of a Rust application bundling
an OCCT engine that spawns subprocesses remains unexercised (inherited open
item from ADR-023).

## ADR-026 — Phase 9: the unreachable publication paths are deleted (2026-07-25)

**Decision.** Delete the publication paths no live domain can reach — the
subtractive half of Phase 9 (ADR-025).

**The deletion.** `CadexScriptedDomainPublication.py` goes from 7,012 to
3,613 lines — **3,399 removed, 48%**. The five live domains are exactly
`assembly`, `mesh`, `part`, `partdesign`, `sketcher`
(`XSCRIPT_WORKBENCH_PACKS`); publication dispatches on `pack.domain`, so
every `robot` / `fem` / `inspection` / `points` / `reverse_engineering` /
`meshpart` / `surface` branch was unreachable. Not merely unreachable —
**unrunnable**: those workbench trees were deleted in Phase 1 (ADR-007/009),
so `import ObjectsFem`, `import Inspection` and `import Robot` in the
create-object factories could not have resolved since.

Removed: 7 dispatch branches, 50 dead functions (the `_configure_*` bodies
and their whole rollback/restore/freeze machinery), 19 module constants, and
the `*_data` response keys for those domains — which no engine module
produces and, checked against `/Users/theo/mesh`, no shell consumes.
`_configure_mesh`'s `data_key` / `validation_property` parameters went with
`meshpart`, its only other caller.

**Method, because "delete the dead code" is where the bodies get buried.**
Branches first, then an AST reachability walk from the module's real entry
points — the names other modules and tests import, plus everything public,
plus module-level statements — iterated to fixpoint, twice (round 2 found
`_FEM_RESULT_VECTOR_LISTS`, reachable only from a constant round 1 had just
removed). Then the same sweep for constants, refusing to remove any name
another file references. Then an undefined-name check. The tests were the
weakest evidence here and are stated as such: unreachable code cannot be
exercised by a suite, so reachability was proved structurally and the suite
only confirms nothing *else* broke.

**Consequences.** The suite stays green at 154 tests. The contract gates
that Phase 9 also calls for land separately in ADR-027; the mesh-repo half
of Phase 9 (the local bpy modes, the app template) is its own repository's
commits.

## ADR-027 — Phase 9: the request half of the contract was tested, the reply half was prose (2026-07-25)

**Decision.** Pin the two contracts everything downstream of ADR-025
assumes: the shape of every cadexd response, and the kernel's subshape
ordering.

**Response schemas** (`OP_RESPONSE_SPECS`, `NESTED_RESPONSE_SPECS`,
`validate_response`, `cadex_tests/response_schemas/*.json`).
`OP_ARG_SPECS` pinned requests; replies were prose. Fixtures were recorded
from a live cadexd and reduced to shape — every leaf is its JSON type name,
so no digest, temporary path or machine state is committed and a diff means
the contract moved. `docs/INTEGRATION.md` gains a response table, enforced
against the code the same way the op table already was.

Wiring the validator into `test_cadexd_lifecycle`'s client — so real frames
are checked, not only fixtures — immediately found three shapes the
recording had missed, which is the argument for doing it that way:

1. **Server-level failures are a different envelope.** `CADEXD_*` codes
   produce `{ok, failure_code, error}`; a tool-level failure produces
   twelve keys the agent reads and acts on. One spec would have let a bare
   protocol error pass as an actionable pipeline failure. Now
   `SERVER_FAILURE_SPEC` is separate, dispatched on the code, and a test
   asserts it stays *strictly smaller*.
2. `restore` carries `digest` and `matches_accepted` only when a restore
   was actually performed.
3. `domain_failure_stage` appears when a failure came from a domain worker
   rather than the lifecycle.

**OCCT pinned exactly** — `occt = "==7.8.1"`, not `>=7.8,<7.9`. Five ops
(`subshape`, `defeature`, `fillet`, `chamfer`, `thicken`) take 1-based
`TopExp::MapShapes` ordinals as **saved script arguments**, and BOPAlgo's
ordering is not a documented contract. `test_subshape_enumeration.py` /
ctest `CadexSubshapeEnumeration` fingerprints a canonical box → cut×4 →
fillet through the engine's own part domain — 10 faces / 24 edges before
the fillet, 38 / 84 after — recording geometry type, area or length, centre
and normal or direction per ordinal. Verified by construction: swapping two
recorded ordinals turns it red with the exact diff. A red test after a
dependency bump means every saved script changed meaning; it does not mean
the file needs updating.

**Consequences.** 154 → 189 engine tests, all green. Two ctests added
(`CadexSubshapeEnumeration`, `CadexResponseSchemas`). `conftest.py` puts the
suite's own directory on `sys.path` so a test can reuse another's helpers.

**Not done in this change, and not silently:** the mesh-repo half of Phase 9
(deleting the local bpy modes, the app template, and asserting these same
fixtures from the shell side) is its own repository's commits; the
warm-standby worker is untouched; and Phase 10a's probe has not run, so
whether the enumeration is *reproducible outside FreeCAD* — as opposed to
merely stable within it, which is what this gate proves — remains open.

## ADR-028 — Phase 10a: the enumeration is reproducible outside FreeCAD, and `modelRefine` is why (2026-07-25)

**Decision.** Phase 10a's probe has run. The subshape enumeration that five
xscript ops save as script arguments **is reproducible from raw OCCT**, on the
condition ADR-025 anticipated: FreeCAD's `modelRefine` must be vendored, not
substituted. Phase 11 has a known shape; the pin/index contract does not need
to change first, and saved scripts are not invalidated.

**What was built.** A throwaway C++ binary against the pinned OCCT 7.8.1,
outside the cadex tree, constructing shapes through raw `BRepPrimAPI` /
`BRepAlgoAPI` / `BRepFilletAPI` and dumping `TopExp::MapShapes` order with the
same per-subshape fields `_subshape_geometry` emits. Three refine variants: no
refine, `ShapeUpgrade_UnifySameDomain`, and vendored
`BRepBuilderAPI_RefineModel` (`modelRefine.{h,cpp}` compiled straight out of
`src/Mod/Part/App/`). Compared against a FreeCAD oracle that replays the same
construction through `Part.makeBox` / `.cut` / `.removeSplitter` /
`.makeFillet` — first verified faithful by reproducing
`cadex_tests/subshape_enumeration.json` ordinal-for-ordinal on all four probes.

**Result.**

| shape | none | UnifySameDomain | vendored RefineModel |
|---|---|---|---|
| canonical box → cut×4 → fillet | matches | matches | matches |
| coplanar fuse → refine → fillet | 10f/20e vs 6f/12e | right counts, **wrong order** | matches |

Three findings, in order of consequence:

1. **The canonical shape in `test_subshape_enumeration.py` cannot discriminate
   between the variants** — `removeSplitter` is a *no-op* on it. Raw and
   refined fingerprints are byte-identical at all four cut stages: cylinders
   through a box leave no coplanar split to remove. The gate is still a valid
   OCCT-drift tripwire, which is what ADR-027 built it for, but it says
   nothing about the refine implementation. A second shape was needed to run
   the probe at all.
2. **`ShapeUpgrade_UnifySameDomain` is not a drop-in for `modelRefine`.** On
   the coplanar fuse it produces the *same face and edge counts* (6/12) and a
   *different ordering* — 89 differing ordinals against the engine, starting
   at `Face1`. This is precisely the failure mode the index contract cannot
   survive: the shape is valid, the counts reconcile, and every saved index
   means something else. Had Phase 11 reached for the OCCT-native cleanup as
   the obvious equivalent, nothing would have failed loudly.
3. **The vendored `BRepBuilderAPI_RefineModel` matches ordinal-for-ordinal on
   both shapes.** It also vendors cheaply: `modelRefine.{h,cpp}` compiled
   against raw OCCT needing only two stub headers (`PartExport` as an empty
   macro, and a `Base::Console()` with a no-op `message`). No other FreeCAD
   dependency.

Output is deterministic — five consecutive runs hash identically — despite
`SetRunParallel(Standard_True)` on the booleans, which the engine also sets.

**Consequences.** The 10a branch ADR-025 called "the contract is reproducible,
`modelRefine` is the only special case" is the one taken. Phase 11a's
"vendor `modelRefine.{h,cpp}` as an explicit deliverable" is now load-bearing
rather than housekeeping, and the differential oracle must cover a
refine-firing shape or it will not detect a wrong refine. 10b (kill index
arguments) and 10c (characterization corpus) are unblocked and unchanged.

**Not done in this change, and not silently:** the probe is throwaway and is
not committed — it lives outside the tree, and landing it as a permanent gate
would mean a C++ target in a repo whose release build is engine-only. The
canonical fixture's blind spot is recorded here but *not* fixed: adding a
coplanar shape to `test_subshape_enumeration.py` would widen the ADR-027 gate
to cover refine, and is worth doing, but it is a test change with its own
golden data. 10c's timing gate — the number that actually decides whether
Phase 11 starts — has not been run.

## ADR-029 — Phase 10b: subshapes are named by geometry, not by ordinal (2026-07-25)

**Decision.** The five index-taking part ops — `subshape`, `defeature`,
`fillet`, `chamfer`, `thicken` — take a **geometric selector**. The
`Sequence[int]` form is deleted, not deprecated.

```python
part.fillet(drilled, 0.5,
    edges={"geometry_type": "Circle", "radius": 3.0, "expected_count": 8})
```

**Rationale.** An index named a position in `TopExp::MapShapes`. ADR-028
proved that ordering is *reproducible*; it never made it *stable across
edits*. Any parameter change that alters topology renumbers every subshape
after it, so a saved `edges=[3, 7]` keeps passing `isValid()` and silently
fillets different edges. The roadmap called this "worth doing on its own
merits even if the migration stops here", and it is: this is a correctness
fix for today's product, not migration scaffolding.

The vocabulary was not invented here — `resolve_pin` has spoken it since
Phase 5.2. A pin captured from a click and an argument written into the
script now name geometry identically.

**The extraction came first, and was forced.** `CadexSubshapeQuery.py` holds
`subshape_geometry` / `query_subelements` / `resolve_selected_subshapes` /
`SELECTOR_KEYS` / `fingerprint_key`, kernel-neutral and staged into the
worker bundle. This is Phase 11a's "extract pin resolution out of
`cadex_partdesign_worker`" item, pulled forward with no choice about it:
`cadex_partdesign_worker` imports `cadex_part_worker`, so the part domain
could not reach the vocabulary without an import cycle. That is *why* the
five ops still took integers. Two consequences beyond 10b:

- `resolve_pin` no longer drags the entire partdesign feature-building stack
  (and through it sketcher and part) into cadexd to fingerprint one face.
  `cadex_partdesign_worker` accordingly leaves `DECLARED_ENGINE_MODULES` and
  joins the other sandbox-staged workers.
- `PartDesignCandidateError` is now an alias of `SubshapeSelectionError`.
  Aliased rather than subclassed so every existing `except` still catches;
  the two classes had identical shape.

**Three things the work turned up.**

1. **Cylindrical faces had no `radius_mm`.** Only *edges* were ever
   fingerprinted with a radius, so `{"geometry_type": "Cylinder",
   "radius": 3.0}` — the most natural way to name four drilled holes —
   matched nothing while looking entirely reasonable. Faces now carry it.
   This changes the ADR-027 enumeration golden, so the regeneration was
   gated on a proof that the change was *field-additive only*: every
   recorded ordinal kept its identity and `radius_mm` was the sole new key.
   A future reader must not mistake that diff for the enumeration moving.
2. **An unrecognised selector key is rejected.** `SELECTOR_KEYS` is closed.
   A typo like `radius_tolerence` would otherwise be ignored, widening the
   match to every radius and building wrong geometry that validates.
   `expected_count` is required for the same reason: declared cardinality is
   what turns a wrong selector into a failure instead of less work.
3. **The payload gate did not notice a missing module.** `CMakeLists.txt`
   lists engine modules by hand, `CadexSubshapeQuery.py` was not in it, and
   every source-tree gate stayed green while the shipped payload lacked a
   module the part ops import — `test_cadexd_lifecycle` never exercises
   those ops. This is exactly ADR-023's "a source tree that passes proves
   nothing about a payload", caught by inspection rather than by a test.
   `test_every_engine_module_is_installed_by_cmake` now pins the closure and
   the worker bundles against the install list, verified by construction.

**Tessellation sidecar.** `face_keys`: one fingerprint key per `face_ranges`
span, same length and order, so a click can become a durable selector rather
than an ordinal. Purely additive; `face_ranges` and the index picking path
are untouched. Mesh outputs emit `"mesh|whole"` for their single span.

**Evidence.** 203 engine tests green (14 new in
`test_subshape_selectors.py`, including a real-kernel run asserting that
selectors pick the geometry they name: the plate is 6 planes + 4 cylinders,
filleting the eight radius-3 rims adds exactly 8 toroids, defeaturing the
four holes by radius heals back to a bare box, thickening with the top face
removed leaves a 6+5 hollow box). All four cadex ctests pass. The packaged
gate passes, and the selector suite was re-run against the payload — then
verified by construction, by removing the module from the payload and
confirming it fails. Slider-drag median 0.554 s display / 0.471 s raw
against the 0.65 s bar, unchanged by the per-face fingerprinting (Phase 6
measured 0.548 s, Phase 7 0.572 s).

**Not done in this change, and not silently:** the shell (mesh repo) still
sends `resolve_pin {element_type, index}` for picking, which is unchanged
and still correct — but nothing there yet *writes* a selector into a script,
so the round trip from click to durable argument is only half built; that is
the shell's commit. `partdesign`'s own selections were already fingerprint
queries and are untouched. `sketcher` geometry indices are a different
contract and out of scope. No migration path exists for saved scripts using
the index form: they now fail loudly at the API boundary with the reason,
which is the intended behaviour for a form that could silently build the
wrong solid.

## ADR-030 — Phase 13a: one repository, pulled to the front (2026-07-25)

**Decision.** The Blender shell moves into this repository under `shell/`,
as a squashed snapshot. Clone cadex, `pixi run setup && pixi run app`, and
you have a running application. ROADMAP Phase 13's merge item is pulled to
the front of Phases 11 and 12, which become **unscheduled internal swaps**
rather than prerequisites for anything.

**Rationale.** Cloning cadex gave you an NDJSON service and no way to use
it. The product lived in `/Users/theo/mesh`, which fetched a digest-pinned
engine tarball from this repository's releases and installed it into its own
bundle. Everything about that arrangement was overhead: two checkouts, two
CI systems, a release cadence between them, and a per-platform SHA256 pin
whose entire job was to notice if a file got corrupted crossing between two
directories on the same disk.

Merging never needed Phase 11 or Phase 12. The seam was already a real
process boundary — NDJSON over stdio, pinned on requests (`OP_ARG_SPECS`)
and on responses (the ADR-027 goldens) — so nothing about the runtime
architecture had to change. The delta on top of stock Blender was 34 files
and ~6,500 lines. This was a repo-layout and build-orchestration job, and
doing it first is what makes every later resting place shippable.

**What this reverses, and what it keeps.** ADR-023's *mechanism* is gone:
the engine is built in place, not fetched by digest. The digest pin existed
to guard a cross-repository transfer that no longer happens, so
`fetch_cadex_engine.py`, `build_files/cadex_engine.txt` and the
release-publication job that fed them are deleted. ADR-023's *substance* is
untouched and is the part that mattered: one bundle, discovery by manifest,
and a payload gate that runs the lifecycle test against the packaged tree
because a source tree that passes proves nothing about a payload.

ADR-025's direction is unchanged. Phases 11 and 12 are not cancelled; they
are unscheduled and unblocked, which is a better place for them to be. The
test-pinned protocol is exactly what keeps them available, and it gets *more*
valuable in one repository, not less — distance used to enforce the boundary
and now only discipline does.

### The import

Squashed deliberately: Blender's 163,789 commits and 3.1 GB of history stayed
behind. We delete from this tree; we do not track upstream. Provenance is
recorded instead of history — the `mesh` repository @ `ac5af55948d` (branch
`mesh-main`), plus one working-tree change to
`source/creator/CMakeLists.txt`, since committed there as `f7e85e80039`.
That history lives at `github.com/theo-kirby/mesh`; the local working copy
was deleted 2026-07-25 once the remote tip was verified to match.

The tree lands under `shell/` with the FreeCAD tree left at the root, so no
existing CMake path, pixi task, test or doc reference had to change. Four
pieces of bookkeeping were the only non-mechanical part:

- `lib/*` are submodules, not content — 1.3 GB of prebuilt binaries per
  platform. Re-pointed at `shell/lib/<platform>` in the root `.gitmodules`,
  keeping `update = none`.
- **`.github/workflows/mesh-build.yml` had never been committed.** Blender's
  `.gitignore` opens with `.*`, which swallowed it silently. Force-added
  rather than lost — and the same rule is why the import commit is
  `git add -Af`.
- The nested `.gitmodules` dropped in favour of the merged root one.
- `.gitignore` gained the shell's build trees.

### The one real technical risk: two toolchains

The engine builds inside the pixi/conda-forge environment (OCCT 7.8.1, Qt6,
conda compilers, a conda sysroot). The shell builds against
`shell/lib/<platform>` with Xcode and a homebrew `cmake`/`ninja`. They
overlap on names — zlib, libpng, OpenSSL and Python exist in both at
different versions — so conda on `PATH` during a shell configure resolves the
wrong ones and either fails at link time or produces a binary that
misbehaves at runtime.

`package/app/build_app.sh` owns the fix, and that is why `pixi run
build-shell` is a script rather than a `cmd = ["cmake", ...]` task: pixi
would otherwise hand cmake the exact environment being removed. It filters
pixi and conda entries out of `PATH` and unsets the ~50 variables conda
activation exports.

**Verified by construction, not asserted.** The resulting
`shell/build_darwin/CMakeCache.txt` is identical to a configure run from the
standalone shell repository apart from the source path: five differing lines,
all accounted for — two blanks and two flags the old invocation passed
explicitly. Python resolves to `shell/lib/macos_arm64/python`, the compilers
are `/usr/bin/cc` and `/usr/bin/c++`, and the cache holds zero references to
`.pixi`.

### One application, one backend

`Cadex.app`, executable `Cadex`, bundle id `dev.cadex.Cadex`, icon built from
the cadex mark. One CMake variable (`CADEX_APP_NAME`) replaces the
`Blender.app` string literals. The `.app` skeleton keeps its inherited
directory name — renaming it would churn every file underneath for no product
benefit. `CFBundleIconName` is *removed* rather than repointed: it resolves
into `Assets.car` and wins over `CFBundleIconFile` on macOS 11+, so leaving
it would have meant shipping our icns and never showing it.

Behind it, ROADMAP Phase 9's shell items land. `modes.py` offered three modes
from a dropdown and two of them ran the model script with `exec()` against
`bpy`. The local pair goes, and with it `cad_api.py` (431), `validation.py`
(183), `scene_graph.py` (47), `bl_mesh_agent_cad.py` (472), most of
`model_api.py`, the local half of `model.py`, and the branches in `tools.py`
/ `ui.py` / `agent.py` / `cadex_pick.py`. Net −1,953 lines, and the largest
single block of deep Blender coupling in the tree: BOOLEAN and BEVEL
modifiers, the depsgraph, BVHTree, `orphans_purge`, and a
`sys.modules["mesh_cad"]` alias installed at add-on registration.

The app template is **not** deleted. It is still what suppresses Blender's
UI, and since ADR-024 a fresh profile already starts in it, so it is already
the startup configuration rather than something a user selects. It retires
when a startup config replaces it, as its own commit.

### Three things this turned up

1. **The relocating payload path cannot run on a development machine, and
   `conda_pack` was a red herring.** `build_engine_payload.sh`'s default path
   failed with `ModuleNotFoundError: conda_pack`; adding the dependency moved
   the failure one step to *"the package-managed environment is
   incomplete"*. Relocation rewrites Mach-O load commands from conda's
   package manifests, so it only works when the engine's own files are
   package-managed — i.e. inside a rattler build, exactly as the script's own
   header says. The dependency was removed again rather than left in as
   cargo. `pixi run stage-engine` therefore stages (correct on the machine
   that built it, and nowhere else) and `stage-engine-release` relocates.
   **Every payload verified during this work was a staged one; the
   relocation path remains untested by it.**
2. **The agent suites do not run out of the installed bundle**, though the
   CI workflow said they did. They import the add-on from the source tree —
   which is how they resolve it, and what makes an edit testable without a
   reinstall. What comes from the bundle is the *engine*, discovered through
   `bpy.app.binary_path`, which is what `engine_from_bundle: true` asserts
   and the only part that has to come from the install. The workflow now says
   what actually happens.
3. **The staged payload carries GUI libraries the leak gate does not
   catch.** `lib/FreeCADGui.so`, `FemGui.so`, `InspectionGui.so` and
   friends, plus modules from workbenches deleted in Phase 1, are present in
   `.pixi/envs/default/lib` from older installs and get copied. The payload
   gate greps for `libFreeCADGui*` and `*Gui.so` **under `Mod/`**, so these
   pass. Pre-existing, unrelated to the merge, and left alone deliberately —
   but it means the "no GUI in the payload" assertion is narrower than it
   reads, and it belongs on the Phase 13b list.

**Evidence.** `CADEX-BLENDER-GATE` against `Cadex.app` built entirely from
this repository, with `MESH_FREECADCMD`, `MESH_CADEXD_MODULE` and
`MESH_CADEX_ENGINE` all unset: `ok: true`, `engine_from_bundle: true`,
picking 372/372 (fidelity 1.0, bar 0.99), slider-drag median **0.576 s**
(bar 0.65; the pre-merge baseline measured 0.629 s on this machine in the
same session, and the ROADMAP records 0.572 s), restore performed and
digest-matched, cancellation answered, 127 main-thread ticks during a 1.59 s
rebuild. Engine suite 204 passed; the packaged `CadexdLifecycle` gate passes
against a staged payload; ctest matches `build/ctest_baseline_failures.txt`
exactly (160 environmental failures, no drift in either direction);
`bl_mesh_agent.py` all green.

### The clone-and-build story, measured

Not estimated. A fresh `git clone` into a scratch directory, then the two
commands the README gives, on an M-series Mac:

| Step | Time | Note |
|---|---|---|
| `git clone` | 9 s | 2.2 GB working tree |
| `pixi run setup` | 43 s | installs the 3.9 GB pixi env and checks out the 1.3 GB `shell/lib/macos_arm64` |
| `pixi run build-engine` | 5 min 27 s | 2,124 targets |
| `pixi run stage-engine` | 42 s | 2.3 GB payload |
| `pixi run build-shell` | 13 min 59 s | 8,122 targets, plus a re-stage of the payload (`build-shell` depends on `stage-engine`) |
| **total** | **~21 min** | |

Then, against that bundle, with every `MESH_*` unset: `CADEX-BLENDER-GATE`
`ok: true`, `engine_from_bundle: true`, picking 372/372, slider-drag median
**0.579 s**. A fresh clone produces a working, gated application.

**Two honest caveats on that number.** ccache is machine-wide and was warm —
the engine build reported 58% hits — so a genuinely cold machine is
materially slower; this measures *a second build on this machine*, not a
first build anywhere. And it could not be run past that point in one place:
disk headroom was 19 GB against a ~22 GB requirement for the full chain in a
scratch clone, so the fresh-clone run reused this machine's ccache and each
stage was measured as it completed rather than from a clean cache. The
"hours" the README warns about is the cold-cache case, and it is the honest
expectation for a new machine.

Shell build from a cold build tree in the main checkout, for comparison:
12 min 53 s.

## ADR-031 — The inherited policy files were FreeCAD's, and said the wrong thing (2026-07-25)

**Decision.** `PRIVACY_POLICY.md` and `SECURITY.md` are rewritten for Cadex,
and a new `docs/PROVENANCE.md` states which code came from FreeCAD, from
Blender, and from VibeCAD, under which licence.

**Rationale.** A repository audit found no secrets anywhere in the tree or
in the history — but it did find that both root policy files were still
upstream FreeCAD's, published verbatim from a public repository, and that
both were now false in ways that matter:

- The privacy policy stated that the application "does not collect,
  transmit, share or use any Personal Data." Cadex spawns the Claude Code
  CLI per chat turn, which transmits the user's message, the project script,
  scene structure, geometry measurements, attached images and **viewport
  screenshots** to Anthropic. Publishing a policy that denies this is a
  liability, and cheaper to fix before release than after.
- The security policy routed vulnerability reports to FreeCAD's advisory
  page and the FPA. A researcher finding a bug in `src/Mod/cadex` or
  `mesh_agent` had no correct address, and FreeCAD would have received mail
  about software that is not theirs.

The provenance doc is the third leg of the same problem. `README.md` credited
both upstreams in five lines; that is enough for attribution and not enough
for a reader asking which half is whose, why two licences coexist here, or
what the process boundary has to do with the GPL. It also settles the
VibeCAD question honestly: cadex is not *inspired by* VibeCAD, it is
**descended from** it — `src/Mod/cadex/` was imported from the
`cadex-teardown` branch, and `[VibeCAD-era]` tags in `ARCHITECTURE.md` mark
the code that came with it.

**Consequences.** Both policies now name the file that backs each claim, so
they can be re-verified rather than trusted: the no-telemetry claim rests on
there being no outbound network call under `src/Mod/cadex/` or
`mesh_agent/`, the sandbox claims on `CadexScriptedRuntime.py` and
`CadexScriptedProcess.py`, the loopback-and-token claim on `bridge.py`. Two
disclosures are new and deliberate — that a `.blend` carries its own chat
transcript and Claude Code session id (`history.py`), and that a Cadex
project *is* a program, so opening an untrusted one runs untrusted code.

`SECURITY.md` splits scope explicitly: ours is `src/Mod/cadex/**`,
`mesh_agent/**`, the protocol, and packaging; inherited FreeCAD and Blender
bugs go upstream where they can be fixed for everyone. **This depends on
GitHub private security advisories being enabled on the repository** — the
reporting URL is dead until they are.

Two stale counts were corrected in passing: `CLAUDE.md` said the delta
against upstream Blender was "three files" and `BLENDER-TREE.md` §2 said
"six", while its own table lists seven paths across six changes. Both now
say seven.

The `docs/images/` screenshots remain stale (they show VibeCAD branding and
a provider settings page deleted in ADR-021) but contain no credentials —
the audit opened both. Replacing them is not this entry's job.

## ADR-032 — The parameters get an area of their own (2026-07-25)

**Decision.** The parameter sliders move out of the chat column and into
their own screen area: a second Properties editor split off the bottom 30% of
the viewport, headerless, hosting `VIEW3D_PT_mesh_params` alone. Both columns
stay pinned to the Tool tab and the two panels sort themselves out by area.
The user opens and closes the parameters area from a toggle at the end of the
chat input bar. The panel's `poll` stops being about whether there is
anything to show.

**Rationale.** The panel appeared and disappeared on its own, and the reason
was invisible from the UI. `VIEW3D_PT_mesh_params` was a `"Tool"`-category
sidebar panel sharing one region with the chat — the Properties editor's
Tool tab mirrors those panels (`space_buttons.cc` calls
`ED_view3d_buttons_region_layout_ex(C, region, "Tool")`), which is how one
Properties editor hosted both. Its `poll` returned false whenever
`model.load_specs()` was empty, so any script that declared no parameters,
or any state where the specs had not been bridged back yet, silently removed
the sliders. A control the user cannot summon is not a control.

Making it an area rather than fixing the `poll` is the point of the change:
a panel is a resident of someone else's region and comes and goes with it,
an area is a thing the user owns. Blender does not let a Python add-on
register a new editor type, so the area is an existing editor pinned to a
tab — the same trick the chat column already uses. This keeps the whole
change in `mesh_agent/ui.py` and the Mesh app template; **`shell/`'s
seven-file delta against upstream Blender is untouched**
(`docs/BLENDER-TREE.md` §2).

**Consequences.** The Simple-mode layout is three areas, not two.

**Both columns are pinned to the Tool tab, and that is load-bearing.** The
first attempt hosted the parameters on the Scene tab and emptied it the way
the template already empties the Tool tab. It rendered a stray "Scene" row
above the sliders that no amount of Python panel-hiding removed, because it
is not a Python panel: `PROPERTIES_PT_context` is registered in C
(`buttons_context.cc`, `buttons_context_register`) with the comment *"C panels
unavailable through RNA bpy.types!"*, and its poll is
`sbuts->mainb != BCONTEXT_TOOL`. Every Properties tab except Tool draws that
breadcrumb, and nothing in Python can poll it out. So Tool is the only tab a
column of ours can sit on, and `_column_role()` decides which panel belongs
to which area instead. A corollary for anyone adding a third column later:
the tab is not free real estate.

The split direction is load-bearing too, and documented at `PARAMS_SPLIT`:
with `factor <= 0.5`, `area_split` (`screen_edit.cc`) gives the *new* area the
bottom half, which is what lets `open_params_area()` identify it by pointer
diff instead of waiting for `area.x`/`area.y` to settle. Pinning the tab and
stripping the chrome still needs a timer, because `area.spaces.active` can
lag its `area.type` by a tick.

`draw_chat_input_header` now serves two Properties areas, so it identifies
the chat column by geometry (right-most) rather than by pinned tab — which it
must, since both are on the same tab now. Keying off `space.context` would
also have deleted the chat input bar the moment a user switched tabs, exactly
when they need it to switch back.

With the `poll` reduced to a layout question, an empty model reads as "No
parameters in this model" instead of an empty strip.

## ADR-033 — A duplicated file must not lose what it remembers (2026-07-25)

**Decision.** Opening an engine project that holds no script no longer
overwrites the scene's parameter specs or the `model.py` mirror. The
"this file has no engine project" notice is keyed on the current file rather
than on whether some previous root happened to be open, and it now comes with
a way out: **Rebuild From Saved Script** (`mesh_agent.adopt_script`) re-runs
the script the .blend carries into the new project. The `.cadex` directory is
still **not** copied on Save-As — ADR unchanged on that point.

**Rationale.** A .blend and its engine project are two halves of one model:
the file carries the baked tessellation, the `model.py` mirror, the specs
JSON and the parameter values; `<stem>.cadex/` carries the xscript source,
the BREP artifacts and the accepted digest. `project_root()` derives the root
from the file name every time, so duplicating a .blend — in the file manager
or through Save-As — names a project that does not exist. That much is by
design.

What was not by design is what happened next. `open_project` does
`root.mkdir(parents=True, exist_ok=True)` (`cadexd.py`), so a missing project
is created **empty and returns ok** — no error, no signal. `ensure_open` then
called `_adopt_script_state` unconditionally, and an empty project's script
block is `script_present: False` with `source: ""`. Adopting it wrote
`scene["mesh_model_specs"] = "[]"`, unregistered the slider PropertyGroup,
and — because `""` is a `str` and the mirror is written on any `str` — cleared
`bpy.data.texts["model.py"]` too. The file kept its baked mesh, so it still
*looked* right, while the last copies of both the parameter declarations and
the script were destroyed by the act of opening it.

This is also the likeliest cause of the vanishing parameters panel that
prompted ADR-032: the old poll was `bool(model.load_specs(scene))`, so wiping
the specs deleted the panel.

**Consequences.** `_adopt_script_state` grows a `preserve_local` flag, set
only on the open path. An engine that *has* a script stays authoritative,
including when that script declares no parameters — the guard is specifically
about adopting emptiness, not about preferring local state.

The guard has to run **before** the mirror write, not after. The first cut
placed it after and would have cleared `model.py` anyway, taking with it the
one thing `adopt_saved_script()` reads.

`orphaned_project()` asks the engine (`script_present`, over the protocol)
rather than looking inside `<root>` for `script.py`. Once `ensure_open` has
run, `os.path.isdir` cannot answer the question — the engine created the
directory — and reaching into the store's layout would cross the process
boundary the protocol exists to keep (CLAUDE.md methodology 6).

Recovery writes the mirrored script through the normal `write_script` path,
so the new project earns its own accepted revision and digest. It is a
genuine sibling of the original, not a copy of its artifacts, which is the
same principle that keeps Save-As from copying `.cadex`.

Regression-tested by `test_duplicated_file_keeps_its_parameters` in
`shell/tests/python/bl_mesh_agent_cadex.py`; verified to fail with the guard
removed.

## ADR-034 — The input gets a strip of its own, and Return sends (2026-07-26)

**Decision.** The chat input leaves the Properties header. It becomes a
multi-line text-box widget (`layout.textbox()`) in a fourth screen area — a
short strip split off the foot of the chat column — with the button row
staying in that strip's header, one row underneath. **Return sends the
message; Shift+Return puts in a newline.** The trash-can *Clear Chat* becomes
**New Chat**, which resets the Claude Code session as well as the transcript.

**Rationale.** Three separate things, one change to the input.

*Multi-line is not optional and could not stay in the header.* A message long
enough to be worth typing ran off the end of a one-line field with no way to
see it. Header regions are one row tall by construction: `ED_region_header_layout`
(`editors/screen/area.cc`) recomputes `region->sizex` for a layout-based
header and never `sizey`, and `ED_area_headersize()` is a global constant. So
either the input moves out of the header or it stays one line. It moves, into
an area, for the reason ADR-032 gave for the parameters: the box has to stay
put while the transcript beside it scrolls, and only an area does that. The
end of the transcript panel was the cheap alternative and was rejected — an
input you have to scroll down to reach is worse than a short one.

*The widget already existed.* `ButtonType::TextBox` wraps, scrolls, and
carries a resize grip, and its C key handling is already chat-shaped:
`EVT_RETKEY` under `ButtonType::TextBox` inserts a newline with Shift held
and ends the edit without (`interface_handlers.cc`). Sending on Return is
then just the `update=` callback on `WindowManager.mesh_chat_input`, which is
where Blender reports a committed text button. Everything but `confirm_only`
below is `mesh_agent/ui.py`, `agent.py` and the Mesh app template.

*Clearing a chat that the model still remembers is a lie.* `chat_clear`
emptied `history` only. The backend outlives the turn and keeps the
`session_id` it learned from the stream, so the next turn still passed
`--resume` and the model answered with the whole cleared conversation in
context. `Agent.new_conversation()` drops the session and the image
attachments (their indices are what `get_attached_image` takes) along with
the transcript. Naming it *New Chat* follows: what the user wants back is an
assistant with an empty head, not a tidy scrollback.

**Consequences.** The Simple-mode layout is **four** areas, not three, and
`_column_role` grew into `_area_roles`: the right-most column is the chat,
its top half the transcript and its bottom half the input strip; any
Properties area outside that column is the parameters.

**Two `screen.area_split` calls cannot share a tick.** The second reads a
screen whose geometry has not caught up with the first and quietly does
nothing — which silently cost the parameters area its split the moment the
input strip started splitting ahead of it. The app template now opens the
parameters one tick behind (`_open_params`). Anything that adds a fifth area
inherits this constraint.

**Clicking outside the box must not send, and that took C.** A Blender text
button has exactly one "the edit finished" signal, reached by Return and by
clicking elsewhere alike, and no way to tell them apart from Python —
committing is the only thing Python hears about, so a click elsewhere sent the
draft. `layout.textbox(..., confirm_only=True)` adds the distinction: the value
is committed only when the edit ends by explicit confirmation. That is five
inherited files (`UI_interface_layout.hh`, `interface_intern.hh`,
`interface_layout.cc`, `interface_handlers.cc`, `rna_ui_api.cc`) and the first
behavioural — rather than string-literal — entry in the delta table; see
`docs/BLENDER-TREE.md` §2b. Escape still cancels the edit without sending.

**The box does not grow as you type.** It wraps to its height, scrolls past
it, and has a grip. The wrapped line count and the box height are both C-side
(`ButtonTextBox::last_total_lines`, `TextboxState::visible_lines`), reachable
from the layout API only as `initial_visible_lines` at the moment the region
first creates the state. Auto-growing means editing inherited Blender, and
that trade is not worth a merge conflict in `interface_handlers.cc`.

If the strip is missing — a viewport sidebar, or a column too short to split
— the chat panel draws the box and buttons inline rather than leave a
transcript that cannot be answered.

Covered by `test_confirming_the_input_sends`,
`test_message_box_widget_is_available` and
`test_new_conversation_starts_a_fresh_session` in
`shell/tests/python/bl_mesh_agent.py`; layout and fallback verified against
the built bundle, `CADEX-BLENDER-GATE` green.

**Superseded in part by ADR-035.** The input strip's *area* is gone: the
message box is a `RGN_TYPE_EXECUTE` region of the Cadex Chat editor, which is
not a header region and so was never subject to the one-row limit that forced
the fourth area. The two-splits-per-tick constraint and
`test_column_roles_are_read_off_the_geometry` go with it. What stands is the
widget, Return-sends, `confirm_only`, and New Chat.

## ADR-035 — Chat and Parameters become editors (2026-07-26)

**Decision.** `SPACE_CADEX_CHAT` and `SPACE_CADEX_PARAMS` are real Blender
space types — named entries in the editor-type dropdown that split, dock and
resize exactly like the 3D Viewport. The transcript, the message box and the
parameter sliders become panels of those two editors. The geometry classifier
that told three Properties areas apart by comparing `area.x` and `area.y`
(`_area_roles` and everything hanging off it) is deleted. The script gets a
view through the **stock Text Editor**, not a third space type.

**Rationale.** The layout was held together by a guess. Chat, the input strip
and the sliders were not editors: they were three Properties editors pinned to
the Tool tab, drawing `bl_space_type='VIEW_3D'` sidebar panels that appeared
there only because the Properties Tool tab mirrors the viewport's Tool-category
sidebar. Which of the three an area *was* got decided at draw time from its
coordinates, and every `poll()` hung off that. The cost was everywhere: a
340-line retrying timer that split areas and monkeypatched two header draw
functions; the ADR-034 bug where two `screen.area_split` calls could not share
a tick and the parameters area silently went missing; and an editor-type
dropdown that still offered a dozen editors, each of which destroyed the
layout if picked.

*Why the input stops needing an area of its own.* ADR-034 gave the message box
a fourth **screen area** because header regions are one row tall by
construction. `RGN_TYPE_EXECUTE` is the answer it was missing:
`RGN_TYPE_IS_HEADER_ANY` (`DNA_screen_types.h`) covers `HEADER`,
`TOOL_HEADER`, `FOOTER`, `ASSET_SHELF_HEADER` and `SCRUBBING` and
deliberately **not** `EXECUTE`, so an execute region is an ordinary sizable
panel region — `space_project.cc` already uses one that way. The input is now
a region of the chat editor, `RGN_ALIGN_BOTTOM` with
`prefsizey = 6 * HEADERY` and user-resizable. The fourth area and the
two-splits-per-tick constraint both go with it.

*Two editors, not three.* `model.py` already exists as a text datablock with a
fake user (`model.set_script`), and the Text Editor brings syntax
highlighting, line numbers and find for free. A third space type would be a
reimplementation of `space_text` for a buffer we do not even own.

*What they cost.* Both are bare `SpaceLink` headers with no fields of their
own — transcript scroll is region state, parameter values live in
`scene.mesh_params`, the model selector is an add-on preference. DNA is
append-only forever, so that emptiness is the point. Both reuse
`btheme->space_properties` rather than adding two `ThemeSpace` blocks, and
both reuse existing icons (`ICON_OUTLINER_OB_LIGHT`, `ICON_OPTIONS`): the
editor-type dropdown draws the icon from the `rna_enum_space_type_items` row,
not from `SpaceType::iconid`, so no new artwork and no generated icon sheet.

**Consequences.** Every `poll()` in `ui.py` that answered "which area am I?"
is gone; `VIEW3D_PT_mesh_params`'s ADR-032 caveat ("the poll is about *where*
this draws") simply becomes true. `ui.py` goes from 705 lines to 449.
`MESH_AGENT_OT_toggle_params` keeps its purpose and loses its mechanism: find
`area.type == 'CADEX_PARAMS'` and close it, or split the viewport and set the
type. No pointer bookkeeping, no retry timer, because there is no space-data
swap to wait on.

Headers live in the new `mesh_agent/spaces.py`, not in
`shell/scripts/startup/bl_ui/` — `bl_ui` is inherited and conservative,
`mesh_agent` is ours. The price is that a Cadex editor draws an empty header
with the add-on disabled, which is honest: the editors *are* the add-on's UI.

**The script view is a mirror, and the panel says so.** `get_script` reads the
text datablock; `write_script` goes to the engine. So a hand edit is visible to
the assistant immediately but does not reach the engine until **Apply to
Model** (`MESH_AGENT_OT_adopt_script`) runs. Blender text datablocks have no
read-only flag to enforce this with, so `CADEX_PT_script` states it rather
than pretending.

**This is a deliberate, large increase in the inherited-Blender delta**, and it
reverses the pressure `CLAUDE.md` and `docs/BLENDER-TREE.md` §2 put on that
number. The case: the delta is *additive* — two new `space_cadex_*`
directories plus one-line entries in enums, exhaustive switches and CMake
lists — so it conflicts as insertions rather than as rewritten logic, and
`-Wswitch` finds the ones that matter; it buys the removal of ~550 lines of
Python layout hacks and the whole class of bug ADR-034 documents; and Phase 12
retires the Blender shell wholesale, so the cost has a horizon. Keeping the
geometry classifier would have cost the same complexity forever.
`docs/BLENDER-TREE.md` §2 is restructured to say this out loud rather than
imply it.

Covered by `test_cadex_editors_are_registered` and
`test_panels_are_homed_on_the_cadex_editors` in
`shell/tests/python/bl_mesh_agent.py`; driven by hand against the built
bundle (send, parameters toggle, script view); `CADEX-BLENDER-GATE` green.

## ADR-036 — An editor Cadex does not build is not offered (2026-07-26)

**Decision.** The editor-type menu lists only what Cadex ships: 3D Viewport,
Cadex Chat, Cadex Parameters, Properties, Outliner, Text Editor, Python
Console, Info, Preferences and the File Browser. The dope sheet/timeline,
graph/drivers, NLA, image/UV, shader/compositor/geometry nodes, sequencer,
spreadsheet, movie clip and the asset browser are gone from it. The mechanism
is **not registering the space type**: `rna_Area_ui_type_itemf`
(`rna_screen.cc`) now skips any row whose `BKE_spacetype_from_id` comes back
null, instead of hardcoding a blacklist.

**Rationale.** Not registering a space type did *not* previously hide it — the
loop added the item regardless, so picking it left a dead area. One guard
turns "stop registering it" into "it leaves the menu", which is also the
*disable* half of the removal protocol in `docs/FREECAD.md` §3: the two steps
line up instead of fighting.

The enum rows themselves must stay. `ED_area_name()` and `ED_area_icon()`
(`screen_edit.cc`) index `rna_enum_space_type_items` by `area->spacetype` via
`RNA_enum_from_value`; deleting rows returns `-1` and reads out of bounds.
Headings carry `value = 0`, which would collide with `SPACE_EMPTY` under the
same lookups, so they stay too — the loop instead holds a group label back
until something survives underneath it, which is what keeps "Animation" from
being emitted with nothing under it. `SPACE_EMPTY` is exempt from the guard:
it has no space type by construction and exists for the Python API.

**Consequences, and one correction to the plan this came from.** Dropping the
editors' `add_subdirectory()` and `LIB` entries — "the tree stays; the build
stops compiling it" — **does not work and was not done.** The dependency audit
fails: kept subsystems link against all nine. `ED_operatormacros_action`,
`ED_operatormacros_graph` and `ED_operatormacros_nla` are called from
`ED_spacemacros_init`; `ANIM_graph_context_fcurve` and `ANIM_nla_context_strip`
from the animation editors' shared code; `ED_space_image_*`, `uiTemplateImage`
and the UV paint tiles from `editors/uvedit` and `sculpt_paint`;
`ED_node_set_active`, `ed::space_node::*` and `uiTemplateNodeLink` from
properties and render; `ed::vse::*` and `ed::spreadsheet::*` likewise —
252 undefined symbols in all. Compiling them out is the *delete* half, and it
belongs to Phase 13b with the trees. So the C++ change is exactly one thing:
the nine `ED_spacetype_*()` calls leave `ED_spacetypes_init()`.

Five consequences had to be handled, each verified by launching:

- **Unchecked `SpaceType::create` call sites.** `screen_area_spacelink_add`
  (`screen_edit.cc`) and `do_version_area_change_space_to_space_action`
  (`versioning_280.cc`) dereference the result of `BKE_spacetype_from_id`
  without a null check, and `ED_area_newspace` (`area.cc`) carries a null
  `area->type` through. Inherited call sites still ask for these: the render
  result wants `SPACE_IMAGE` (`render_view.cc`), the drivers editor
  `SPACE_GRAPH` (`screen_ops.cc`). All three now fall back to the viewport the
  way loading a file that names an unknown space type already does
  (`area_init_type_fallback`).
- **`bl_ui` modules.** `space_clip`, `space_dopesheet`, `space_graph`,
  `space_image`, `space_nla`, `space_node`, `space_sequencer`,
  `space_spreadsheet` and `space_time` leave `_modules`. They cross-import each
  other and nothing outside the set imports them, so they go as a group or not
  at all. `space_toolsystem_toolbar` also stops registering
  `IMAGE_PT_tools_active`, `NODE_PT_tools_active` and
  `SEQUENCER_PT_tools_active`: registering a panel against a space type that
  does not exist raises `"Region not found in space type"`, and that **aborted
  bl_ui's whole registration loop**, taking the top-bar menus with it.
- **The asset browser is a `SpaceFile` subtype**, not a space type, so it
  cannot be hidden by not registering it. It is filtered in
  `file_space_subtype_item_extend` instead. The file browser itself stays —
  file dialogs need it.
- **Operator macros over missing operators.** A space type's operators are
  registered from its `operatortypes` callback, which no longer runs, so
  `ED_operatormacros_{node,graph,action,clip,nla,sequencer}` built macros
  around operators that do not exist. `WM_operatortype_macro_define` survives
  that, but only by warning on every missing property at startup, so those six
  calls are now conditional on the space type being registered. The knock-on:
  four keymap items in `blender_default.py`'s node keymap named a macro
  sub-operator, which raises in `_init_properties_from_data`; they pass `None`.
- **Three bundled add-ons.** `cycles` (shader-node panels), `pose_library`
  (dope sheet and asset browser) and `io_mesh_uv_layout` (appends to the UV
  editor's menu) each raised on every launch. They are no longer enabled by
  default — `cycles` and `pose_library` leave
  `BKE_blendfile_userdef_from_defaults`, `io_mesh_uv_layout` leaves
  `_addons_hidden_core` in `addon_utils.py`, which is the list that actually
  decides because it enables unconditionally. All three are still installed.

**Known residue, deliberately left.** A headed launch still prints ~92
`Warning: property '<name>' not found in item 'OperatorProperties'` lines:
`blender_default.py` carries keymaps for all nine editors, and a keymap item
for an operator that does not exist cannot have its properties set. Removing
them means deleting ~3,000 lines of keymap data from an inherited file, which
is a large merge liability for cosmetics — that data should go when the trees
go. They are warnings, not errors, and a keymap item for a missing operator is
simply never matched. Recorded in `docs/BLENDER-TREE.md` §4.

Covered by `test_editor_menu_is_short` in
`shell/tests/python/bl_mesh_agent.py`, which asserts on the identifiers the
menu actually uses — the animation, image, node and file editors surface
*subtype* identifiers, so asserting on `DOPESHEET_EDITOR` or `GRAPH_EDITOR`
would have passed vacuously.

## ADR-037 — The layout is a file, not a program (2026-07-26)

**Decision.** `shell/scripts/startup/bl_app_templates_system/Mesh/startup.blend`
carries the Cadex layout. The app template's timer state machine is deleted;
what remains is a 98-line stub. This closes `docs/ROADMAP.md` Phase 9's
"delete the app template".

**Rationale.** The layout became expressible as a saved screen the moment the
columns became real editors (ADR-035) — a saved screen can only record area
*types*, and until then the area types were lying. Every other template ships
a `startup.blend` (81–111 KB) with an `__init__.py` of 874–1,624 bytes,
against Mesh's 13,746.

`blo_is_builtin_template` (`versioning_defaults.cc`) hardcodes
`2D_Animation`, `Storyboarding`, `Sculpting`, `VFX`, `Video_Editing`. **"Mesh"
is not in that list**, so `BLO_update_defaults_startup_blend`'s destructive
pass — free every stored panel, reset region sizes, rename screens — never
runs on ours. Only the universal reset of `V2D_IS_INIT` on
`RGN_TYPE_UI`/`TOOLS`/`TOOL_PROPS` regions applies, and none of our regions is
one of those. The file loads verbatim.

**What stays in Python, and why it must.** Enabling the add-on:
`preferences.addons` is `UserDef`, not `Main`, so a startup file cannot carry
it, and shipping a `Mesh/userpref.blend` would pin the user's theme, paths,
keymap and autosave as well. Blanking the top bar: `bScreen.flag` has
`SCREEN_COLLAPSE_STATUSBAR` and no topbar counterpart, so there is nothing to
save. Everything else — `_apply_simple_ui` and its 40-attempt retry loop,
`_remove_other_workspaces`, `_collapse_to_viewport`, `_empty_scene`,
`_hide_foreign_tool_panels`, `_style_props`, `_style_viewport`, `_open_params`,
`MESH_PANELS`, `_hidden_panel_polls` — is gone. Viewport shading, matcap,
overlays, region visibility, the single "Simple" workspace and the empty scene
all save into the file.

**The costs, stated plainly.** A `.blend` is opaque to review and to
`git diff`; nobody can read the layout, it can only be run. It pins DNA, so a
later DNA change can silently degrade it — re-author rather than rely on
zero-fill. It is a git-LFS object (`shell/.gitattributes`, `*.blend`) on a repo
already near GitHub's free ceiling, and **every re-save is a new object that is
never reclaimed**, so iterate locally and commit once. Ours is 267 KB, larger
than the other templates' 81–111 KB and still noise against ~790 MB.

The mitigation for all of it is `test_startup_layout_is_the_shipped_file` in
`shell/tests/python/bl_mesh_agent_cadex.py`, which loads the template with
`wm.read_homefile(app_template="Mesh")` and asserts the area types are exactly
`{VIEW_3D, CADEX_CHAT, CADEX_PARAMS}`, one workspace named "Simple", an empty
scene, and the viewport's solid/matcap styling and hidden chrome. It also
emits `startup_areas` into the `CADEX-BLENDER-GATE` line, so the layout is
evidence rather than a pass/fail. Without it, a `startup.blend` that stopped
loading would degrade quietly to Blender's factory screen — the stub no longer
rebuilds anything.

Verified on a wiped profile: `rm -rf` the config directory, launch with
`--app-template Mesh`, land in the right layout with no timer.

## ADR-038 — `inspect` is the assistant's reader; the shell must read the whole value (2026-07-26)

**Decision.** The shell no longer takes the first page of an `inspect` reply
at face value. `_refresh_script_state` reads THE script's state through a new
`_inspect_full()` in `cadex_backend.py`, which follows `page.next_offset`
until the container is exhausted and re-reads any value the engine replaced
with a preview marker, through the `inspect_path` that marker carries. The
engine's inspection contract is unchanged.

**Rationale.** `core.inspect` is a *bounded* reader, and deliberately so: it
caps a reply at 32 KiB, pages mappings, arrays and strings, and substitutes
anything over 1 KiB with `{"type": ..., "inspect_path": ...}`
(`CadexInspection.py`, `_preview` / `_bounded_page`). That is exactly right
for the audience it was written for — a model that pays for every byte it
reads and should drill in on purpose.

The shell is not that audience. It needs `params.specs` to build sliders and
`source` to fill the script mirror, whole or not at all. It was calling the
same op, reading `value["params"]["specs"]`, and getting `None` — because
`value["params"]` was the marker, not the params. `list(None or [])` is `[]`,
so `_bridge_params` wrote `scene["mesh_model_specs"] = "[]"` and unregistered
the slider PropertyGroup; `source` was a marker too, so it failed the
`isinstance(source, str)` test and the mirror was never written.

The visible result was a parameters editor that drew "No parameters in this
model" for every model that had any, and a Script view showing an empty
`model.py`. `ensure_open` bridges the *complete* block that `open_project`
returns, and then calls `_refresh_script_state`, which overwrote it — so the
sliders were correct for the duration of one function call. Every
`write_script` did the same on accept.

**Why it survived.** The 1 KiB threshold is above every fixture in the suite
and below every real model. `BASELINE_SCRIPT` declares one parameter, so the
ADR-027 golden for `inspect` has one `specs` entry in it and the whole block
fits in a preview; the gate was green while the product bridged nothing. This
is the second time a params-bridging bug has hidden behind a one-parameter
fixture (ADR-033 was the first).

**Consequences.** The fix is shell-side. Exempting the script scope from
paging would have put the shell's appetite into the assistant's reader and
made a 60-parameter model a 32 KiB budget question; following the pointer is
what the pointer is for.

`_refresh_script_state` now also refuses to adopt a block with no
`script_present` key — an error body or a truncated page reaches
`_adopt_script_state` otherwise, and bridging one costs the specs.

Regression-tested by `test_params_survive_the_inspect_pager` in
`shell/tests/python/bl_mesh_agent_cadex.py`, on an eight-parameter script
that is over the threshold; it asserts *that* it is over the threshold as
well, so a shrunk fixture fails loudly instead of silently testing nothing.
Verified to fail with the fix reverted (0 of 8 params bridged, mirror empty).

## ADR-039 — Stale parameter values do not wedge the sliders, and the script has a live view (2026-07-26)

**Decision.** Two changes with one root, in
`src/Mod/cadex/CadexScriptedRuntime.py` and the `mesh_agent` add-on.

1. **The store's parameter values are pruned to what the script declares.**
   `_project_param_values()` narrows the stored values to the declared names
   *before* merging one `set_params` patch over them, and
   `validate_project_result()` writes the pruned dict back into the store
   beside the newly collected `param_specs`. A key in the **patch** that is
   not declared still raises `UNKNOWN_PROJECT_PARAMETER` — that is a caller
   error. A key in the **store** that is not declared is dropped.
2. **The xscript gets a persistent, editable view.** The script-view button is
   a toggle beside the Parameters toggle; the mirror is refreshed without
   moving the cursor; and the Text Editor sidebar always says whether the
   buffer matches the model, with **Apply to Model**, **Revert to Model** and
   **Rebuild Model** as the three ways out.

**The bug.** On `whoop-chassis-v01` every slider drag failed, permanently:

```
cadexd set_params failed [UNKNOWN_PROJECT_PARAMETER]
The project script declares no parameter named 'duct_gap'.
requested: {"values": {"cam_hole_d": ..., "wheelbase": ...}}   <- no duct_gap
```

`duct_gap` was in neither the request nor the declared specs. It was in the
*store*: the script had been rewritten, `param_specs` was updated with it and
`param_values` was not. `_project_param_values()` merged the stored values
into every patch and then validated *every merged key*, so a value whose
parameter no longer existed refused every later `set_params` — for a name the
caller never sent.

**The asymmetry is what made it a bug.** `ParamsCollector`
(`cadex_project_api.py`) looks values up *by declared name*, so the worker
already ignored `duct_gap` and the model built fine. Only the precondition
check was strict. The engine tolerated the stale key everywhere it mattered
and rejected it where it did not.

**Nothing healed it.** `write_script` never touched `param_values`, and
"Rebuild From Saved Script" is the same call. There was no route back except
editing `script.json` by hand.

**Why pruning is safe.** It is digest-neutral by construction: the worker
resolves each declared parameter by name and never reads the rest, so removing
undeclared keys cannot change what it computes. Verified on the reported
store — pruning `duct_gap` left `accepted_digest` at
`5b484f2d046f97d7…` unchanged. The *revision* does move, but
`final_revision` → `working_revision` → `accepted_revision` all derive from
the same pruned dict, so they stay consistent, and `open_project`'s
restore-pass digest comparison still matches.

**It self-heals.** `open_project`'s restore pass runs
`xscript.project.write_script` with the stored source, and `rebuild` is the
same call, so the prune fires on the next open. `whoop-chassis-v01` repaired
itself with no migration and no user action — confirmed against a copy of the
real store: `open_project` alone dropped `duct_gap`, and the drag that had
been failing succeeded.

**A way out, for both hands.** `rebuild_model` re-runs the script the engine
already stores and re-derives specs, values and geometry from it. It is a
shell function (`cadex_backend.rebuild_model`), an operator
(`mesh_agent.rebuild_model`, drawn next to the failure in the parameters
panel and in the script sidebar) and an assistant tool. It is built on the
existing `rebuild` op with `guarded=False` — that op's `OP_ARG_SPECS` entry is
`({}, {"display": dict})` and rejects `expected_revision`, which is right,
because re-running what is stored has nothing to be stale against. **No
protocol change and no new op**; the engine tool surface pinned by
`test_project_tool_surface.py` is untouched.

A failed slider drag is also no longer console-only: `model._last_error`
(session state, not saved — a failed drag is a fact about now) is drawn as an
alert row in the parameters panel, with the Rebuild Model button beside it.
The debounce timer runs outside any operator, so there was no operator report
for it to land in, and a permanently wedged slider looked exactly like a
slider that did nothing.

**Deliberately not done:** an automatic retry on `UNKNOWN_PROJECT_PARAMETER`
in `Lifecycle.poll()`, beside the existing `STALE_PROGRAM_REVISION` retry.
With the prune the condition cannot arise, and a recovery path for an
unreachable failure is code that can never be exercised.

**The script view.** Same root: the script was *invisible*, so a store and a
buffer could disagree with nothing on screen saying so.
`MESH_AGENT_OT_show_script` is now a toggle in the shape of
`MESH_AGENT_OT_toggle_params` — it closes the Text Editor showing the mirror
if one is open, else splits and points one at it — and it no longer polls
itself off on a file with no mirror, because that is exactly when someone
wants to look (`model.ensure_script_text` makes an empty one). It moved out of
the chat header and into the button row under the message box, so the two
views are one pair of buttons. **The stock Text Editor is kept**; no new space
type, so nothing is added to `docs/BLENDER-TREE.md` §2b.

`agent._tag_redraw()` tags `TEXT_EDITOR`, and `mirror_script_text()` tags too
(the mirror is written outside agent turns). `model.set_script()` returns early
when the source is already in the buffer and otherwise saves and restores the
cursor — `clear()` + `write()` sends it to the end of the file, and the mirror
is rewritten on every accepted request, so a slider drag used to fight anyone
reading the script.

Divergence is marked, not inferred: `set_script` stamps the digest of what it
wrote onto the text datablock as an ID property (so it saves with the .blend),
and `CADEX_PT_script` compares it against the buffer. Clean says "Matches the
model." with **Rebuild Model**; dirty says "Modified — not applied" with
**Apply to Model** and **Revert to Model**, plus the first line of the last
failure when there was one. A source the engine *refused* is mirrored with
`accepted=False`: it stays in the buffer to be fixed and does not get the
clean stamp, because labelling a script the model does not have as matching
the model is the one thing this display must never do. An unstamped buffer
counts as clean, so files saved before this ADR do not all open with a false
alert.

**Chosen over the alternatives** (asked and answered): the script view is a
toggle button rather than a fourth area in `startup.blend`, which would mean
re-saving a ~270 KB git-LFS object on a layout change (ADR-037);
"Reinitialize" means re-running the stored script, not deleting the store; and
a failed hand edit keeps the text and marks the editor dirty rather than being
reverted under the user.

**Evidence.**
- `src/Mod/cadex/cadex_tests/test_project_param_pruning.py` — the merge rule
  in-process (stale store key dropped, patch key still raises, RFC 7396
  deletes unaffected) and the persistence through a real worker: dropping `b`
  prunes `b`'s value, the digest is identical with and without the stale key
  in the worker's inputs, and the next `set_params` succeeds. 3 of its 4 cases
  fail with the fix reverted; the one that passes is the "still raises loud"
  case, which is the point.
- `shell/tests/python/bl_mesh_agent_cadex.py` — three cases:
  `test_dropping_a_param_leaves_the_sliders_working` (reverted: the exact
  reported `UNKNOWN_PROJECT_PARAMETER` on both drags),
  `test_rebuild_model_rederives_from_the_engine`, and
  `test_script_view_marks_hand_edits` (reverted: 4 checks fail, including the
  cursor jump and the missing dirty mark).
- Engine suite 208 passed; `pixi run gate` `"ok": true` with the slider median
  at 0.575 s, inside the 0.65 s bar.

## ADR-040 — Apply as Defaults: the sliders can write themselves into the script (2026-07-26)

**Decision.** A button in the parameters panel takes the value every slider is
currently sitting at and writes it into the script as that parameter's `num()`
default. Shell-side: `model.rewrite_defaults()` splices the source,
`cadex_backend.apply_slider_defaults()` sends the result through the ordinary
`write_script`. No protocol change, no new op, no engine change.

**Why.** The sliders are an *override layer* over the declarations: drag one and
the value lives in `param_values` in the store, while the script still says
`num(36.0, ...)`. That is right for exploring, and wrong as a resting state —
the script is the artifact that gets read, committed and diffed (`docs/VISION.md`),
so a value the user has settled on belongs in it. There was no way to get it
there except editing the script by hand and retyping numbers off the panel.

**Splice, don't unparse.** `ast.unparse` would return a canonical rewrite of the
whole script — comments gone, layout reflowed — for a change to a handful of
numbers. So the rewrite parses with `ast`, takes the *source span* of each
default expression (`lineno`/`col_offset`/`end_*`, resolved against utf-8 byte
offsets because a label or description may hold a non-ASCII character), and
splices back to front. On the real 116-line whoop chassis script the entire diff
is five changed numbers: same line count, same eight comments, every label, unit
and min/max byte-identical.

**It refuses rather than guesses.** `params(**declared)` hides the names from
static reading, a declaration that is not a literal `num(...)` call has no
default to replace, and a script that does not parse cannot be rewritten at all.
Each of those is a sentence in the panel, not a traceback and not a guess —
guessing which literal belongs to which slider is exactly how this kind of tool
silently corrupts someone's file. A parameter with no slider value is left as
declared.

**Float32.** Blender's `FloatProperty` is single-precision, so a slider reading
3.6 holds 3.5999999046325684, and writing that into a script is indefensible.
Values are cut to six significant digits (`model._DEFAULT_DIGITS`), which is
under the float32 noise floor and still readable. That is deliberately *coarser*
than float32's ~7.2 digits, so a literal can sit ~1e-7 of its magnitude from the
slider — negligible against OCCT's own tolerance, and it does not affect the
current build at all, because of the next point.

**The geometry does not move.** The stored `param_values` are left alone, and a
stored value shadows the default it was just written from, so the rebuild this
triggers computes the same shapes and reports the same content digest. Clearing
the store instead would have been the tidier model — the script would be the
only place a value lives — but it costs a second engine round-trip for no
visible difference, and the redundant overrides are inert. Noted as a known
interaction rather than fixed: a *later* hand-edit of a default is still
shadowed by a stored value, which is pre-existing behaviour (ADR-039's prune is
what bounds it), and **Apply as Defaults** makes it likelier to be met.

**A dirty buffer is refused.** `write_script` refreshes the mirror, so rewriting
while the buffer holds unapplied hand edits would destroy them. The button says
to apply or revert first — which is what the ADR-039 dirty marking is for.

**Greyed out when it would do nothing.** `model.defaults_differ_from_sliders()`
compares the bridged specs against the stored values (no parse, cheap enough for
a draw handler) with both sides rounded — unrounded, float32 noise would leave
the button lit for ever after it was pressed.

**Evidence.** `test_rewrite_defaults_splices_only_the_default` in
`shell/tests/python/bl_mesh_agent_cadex.py` drives the pure function with no
engine: comments and non-ASCII text preserved, a trailing comment on the
rewritten line preserved, `num(default=...)` keyword form handled, float32 noise
rounded to what the panel showed, an unchanged default not reported, a parameter
without a value untouched, and all four refusals returning sentences.
`test_apply_slider_defaults` covers it end to end: the engine's script declares
the new defaults, the bridged specs come back with them, the button goes back to
greyed out, **the content digest is unchanged**, a second press reports there is
nothing to do, and a dirty buffer is refused with the buffer left alone.
`pixi run gate` ok, slider median 0.574 s. Confirmed through `bpy.ops` in a real
window on the nine-parameter whoop chassis file.

**Not done:** exposing this as an assistant tool. The assistant can already
rewrite a default with `edit_script`, and it has no sliders to read.

## ADR-041 — The File menu comes back, as ours (2026-07-26)

**Decision.** The Mesh app template no longer blanks the top bar. It installs
a Cadex bar with two menus, **File** and **Edit**, defined in the new
`shell/scripts/addons_core/mesh_agent/topbar.py`.

File: New, Open…, Open Recent, Revert, Save, Save As…, Save Copy…, Import ▸,
Export ▸, Quit. Edit: Undo, Redo, Preferences…

**Rationale.** ADR-037 blanked `TOPBAR_HT_upper_bar` because nothing else
suppressed Blender's bar, and that took the whole of `File` with it — there
was no way to open a file, save one under a new name, or import and export
geometry without going through the assistant or a keyboard shortcut nobody is
told about. `Edit > Preferences` went with it, and it is the only door to the
add-on preferences: the engine path, the tool-call cap and the ADR-019 run
budgets are all behind it. The `.blend` **is** the document (ADR-033) — it
carries the script mirror, the parameter specs and the engine project id — so
`File > Save` saves the model, and this is a missing door rather than a
missing feature.

**Why two menus and not the bar.** Restoring the stock header would have been
a one-line deletion, and it would have put the Blender menu (splash, about,
system), Render, the workspace tabs and the scene/view-layer pickers back on
screen. A CAD app has nothing to render, ships one workspace and shows one
scene, and `File > New` would have offered Blender's app templates — VFX,
Video Editing, Sculpting — as ways to leave the product. Our `New` sets no
`app_template` at all, which `wm_homefile_read_exec` reads as *the template
already in force*, so it reloads the Cadex startup file.

**Where it lives, and what it does not cost.** No upstream file is edited:
`bl_ui/space_topbar.py` is untouched, and `topbar.install()` swaps the
header's draw at runtime, the same re-register trick ADR-037 removed the last
use of. `docs/BLENDER-TREE.md` §2 does not grow — the change is entirely in
§1 files (`mesh_agent/`, the app template), which is the whole reason the
menus are in the add-on rather than in `bl_ui`, exactly as ADR-035 argued for
the editor headers.

The **app template** is what calls `install()`, not the add-on's `register()`.
`mesh_agent` loaded into a stock Blender session — which is how both suites
run, and how a developer who forgets `--app-template Mesh` lands — leaves that
session's top bar alone. The add-on's `unregister()` does call `uninstall()`:
a header pointing at menu classes that are no longer registered draws a row of
errors, and disabling the add-on is exactly when that would happen.

**Everything the menus point at is stock.** `wm.open_mainfile`,
`wm.save_as_mainfile`, `ed.undo`, `screen.userpref_show` and the rest are
Blender's own operators, and Import/Export are Blender's own menus — so a
format registered by an enabled add-on appears without this file knowing about
it. Today that is STL, OBJ, PLY, USD, Alembic, FBX and glTF. The cost is that
an upstream rename on a merge silently turns a menu row red.

**Evidence.** `test_cadex_topbar_is_the_product_bar` in
`shell/tests/python/bl_mesh_agent.py` reads the operator and menu identifiers
out of the module's own source with a regex — a hand-maintained list beside
the menus is exactly what a merge does not update — and checks every one of
them against the running build (`bpy.ops` for operators, `bpy.types` for
menus; `TOPBAR_MT_file_open_recent` is registered from C and is invisible to
both, so it is named as the one exception). It also pins install/uninstall:
registering the add-on must not install the bar, installing twice is a no-op,
and uninstall must return the *same* stock draw function. In the gate,
`test_startup_layout_is_the_shipped_file` calls the **shipped** app template's
`_cadex_topbar()` and checks it installs, which is what catches a stale bundle.
`pixi run gate` ok, slider median 0.625 s. Confirmed in a real window:
`screen.screenshot` of the launched bundle shows `File  Edit` alone on the bar
and the File menu drawing all ten rows.

## ADR-042 — No splash screen (2026-07-26)

**Decision.** Cadex launches straight into its own layout. The Mesh app
template clears `USER_SPLASH_DISABLE` — `preferences.view.show_splash = False`
— from its `load_factory_startup_post` handler.

**Rationale.** ADR-041 put a product top bar on screen and left the largest
identity leak on the startup path untouched: every launch opened Blender's
splash, with the Blender logo, "Support Blender Development", "Donate to
Blender", a *What's New* link into Blender's release notes and a **New File**
column offering 2D Animation, Sculpting and Storyboarding as ways out of the
product. It is the first thing a new user sees, and none of it is ours.

**Why the flag and not the code.** `wm_init_splash_show_on_startup_check`
(`wm_init_exit.cc`) tests `U.uiflag & USER_SPLASH_DISABLE` first, so setting
the flag is a complete answer, and it is a *preference* the shell was always
free to set. Deleting the `WM_init_splash_on_startup(C)` call in `creator.c`
would have been an eighth file in `docs/BLENDER-TREE.md` §2a, which is
documented to stay at seven; this keeps the upstream delta at zero and leaves
`--app-template default` — the stock-Blender escape hatch — with its splash
intact.

**Why the handler and not the timer.** `creator.c` reads the flag immediately
after `WM_init`, which is *before* any timer fires. This is the one piece of
template work that cannot be deferred, so `load_handler` does it inline and
only then registers the 0.1 s timer that installs the top bar.

**The dirty flag is put back.** Preferences auto-save on exit when dirty, so
writing this would reach through the shared profile into the user's stock
Blender sessions as well. `_hide_splash` restores `is_dirty` to what it found
— the product decides what it launches into, the user's `userpref.blend` is
not edited — and it costs nothing, because the handler runs on every startup.
It is also why the flag is re-applied for users whose profile predates this,
which a factory-default change in `blendfile.cc` would not have been.

**Evidence.** `test_startup_layout_is_the_shipped_file` in
`shell/tests/python/bl_mesh_agent_cadex.py` calls the **shipped** template's
`_hide_splash()` and checks both halves: the splash is off and the preferences
are left exactly as dirty as they were found. `pixi run gate` ok.
Confirmed in a real window: `screen.screenshot` four seconds into a launch of
the built bundle shows the three Cadex areas and the `File  Edit` bar, with no
splash over them.

## ADR-043 — External geometry is a first-class input (2026-07-26)

**Decision.** The product gains a complete path for geometry it did not
author: a file the user drops in becomes a named asset in the project store,
the script places it, converts it to BREP, builds against it, and measures
the result. Four changes, all behind the unchanged cadexd protocol shape:

1. **`put_asset`** — a new op (`{source_path, name?}` →
   `{name, bytes, sha256, assets}`), plus **File → Import Geometry…** in the
   Cadex top bar and an `import_geometry` MCP tool. Bounds are the existing
   staging bounds, defined once in `CadexScriptedRuntime`
   (`store_project_asset` / `list_project_assets`): flat directory, known
   mesh suffixes, 64 files, 128 MB — counted *including* the incoming file,
   so a write can never leave a project a later run cannot stage. A new
   `inspect scope="assets"` lists what is importable.
2. **`mesh.transform`** — the same kwargs and the same order of operations as
   `part.transform` (scale about pivot → rotate about pivot → translate),
   composed into one `App.Matrix` because `Mesh` has no `scale`.
3. **`inspect scope="output"`** — per-output facts for any output of the
   accepted revision, read from the pinned accepted attempt.
4. **`part.shape_from_mesh`** — `makeShapeFromMesh` behind the part API,
   yielding a `solid` (or `shell` with `solid=False`) the part, partdesign
   and assembly domains consume.

**Rationale.** Phase 4 (ADR-016) shipped `mesh.import_file`, and then nothing
in the product could reach it. No surface anywhere wrote `assets/` — the only
writer in the whole tree was a test fixture — so the feature was available
exclusively to a user who knew to `cp` a file into
`<blend-dir>/<stem>.cadex/assets/` by hand. And even once a file was in, it
could not be **moved** (the mesh API had no transform), could not enter the
**BREP domains** (`part`'s validator rejected mesh values), and could only be
**measured** on the rebuild that produced it. Each gap is small; together they
made "use this bracket I already have" impossible, which is an ordinary thing
to ask a CAD tool.

**Why `put_asset` is a modeling op and not a read op.** It writes. That alone
would settle it, but the useful part is what membership in `MODELING_OPS`
buys: mutual exclusion against an in-flight rebuild, for free
(`cadexd.py`'s admit/dispatch), so an asset can never land half-copied while
`_stage_project_assets` is reading that same directory. `READ_OPS` is
documented read-only and stays so. The shell's hand-copied `MODELING_OPS`
gains it too, which also gives the copy the 300 s budget rather than the 60 s
read budget — a 100 MB STL is not a read.

**Why a path and not bytes.** The frame cap is 8 MB and the asset budget is
128 MB. Both halves share a filesystem and the protocol already relies on it:
`inspect scope=image` hands back a project-store path for the shell to read.
The shell still never writes the store — `docs/ARCHITECTURE.md`'s "cadexd is
the sole writer and the sole reader" is why this is an op at all rather than
a `shutil.copyfile` in the operator.

**What this supersedes.**

- `docs/XSCRIPT.md`'s "the Phase 4 `mesh` domain is deliberately minimal …
  and *stays* that way for now … a decision rather than an oversight." The
  charter it stated was about *modelling* meshes interactively, and that
  still holds and is still unscheduled. What it incidentally froze was the
  *ingest* path, which nobody decided. The paragraph is rewritten, not left
  standing.
- **ADR-016's mesh-domain charter**, in the same narrow way: the domain's op
  list grows by `transform`, and mesh values now have a consumer outside the
  mesh domain.
- **ADR-041's "everything the menus point at is stock."** No longer true, by
  one row. `MESH_AGENT_OT_import_asset` is the first non-stock operator in
  the Cadex File menu, and it has to be: stock Import loads a mesh into the
  *Blender* scene, which in Cadex is a display mirror of the engine's outputs
  and not the model. Importing geometry *into the model* means writing the
  engine's asset store, which only the engine may do. The invariant ADR-041
  actually protects — no upstream file edited, `docs/BLENDER-TREE.md` §2 does
  not grow — is untouched.

**What this gives up.** `part.shape_from_mesh(mesh.decimate(...))` is
**rejected**, at script-eval time, with a message naming `decimate`. FreeCAD's
decimator is non-deterministic (ADR-016), and a mesh output survives that by
being digest-identified by its canonical definition instead of its geometry —
an escape hatch a BREP output does not have, because a BREP output's identity
*is* its exported bytes, which is what publication verifies byte-for-byte.
Adding a determinism carve-out to `compute_project_digest`'s BREP branch
would weaken the digest contract of all fifty part operations to serve one.
So the guard sits at the API boundary instead
(`payload_tree_is_deterministic`, moved into `cadex_mesh_api` so the part API
can apply it without importing a worker). The cost is exactly the operation
most useful for taming a dense scan; the workarounds are to decimate offline
and import the reduced file, or to publish the decimated value as a `mesh`
output.

**Two more limits, stated in the API docstrings.** A converted STL is a shell
of thousands of planar triangle faces: ADR-029 geometric selectors
(`subshape`, `fillet`, `chamfer`) are near-useless on it and BREP booleans
against it are slow — it is for cutting clearance against, not for
feature-editing. And all of this stands on `Mod/Mesh`/`Mod/MeshPart`, which
ADR-025 slates for replacement by `manifold` (ROADMAP 11b): two more ops on a
substrate already flagged for a swap, which is a known and accepted cost.

**Consequences.**

- *Protocol.* One new op in `OP_ARG_SPECS`, `MODELING_OPS` and
  `OP_RESPONSE_SPECS`; a golden `response_schemas/put_asset.json`; both
  tables in `docs/INTEGRATION.md` (each cross-checked against the code by a
  live-parsing test). `inspect` needed no protocol change at all — its arg
  and response specs already covered two new scopes, which is the pinning
  paying for itself.
- *Root threading.* `build_mesh(payload, root)` needs a root;
  `build_part_shape(payload, *, diagnostics)` has none, and threading one in
  would have touched ~50 call sites. Instead `configure_part_assets(root,
  mesh_ingest)` mirrors the module's existing idiom for host-staged material
  (`configure_part_references`), called from `cadex_project_worker` and
  `cadex_domain_worker`. It binds *two* things, and the second is the
  interesting one: the mesh kernel arrives as a callable rather than an
  import, because `cadex_part_worker` is in cadexd's declared import closure
  and `cadex_mesh_worker` deliberately is not. A static
  `from cadex_mesh_worker import build_mesh` there pulled four staged worker
  modules into the service's closure — `test_engine_purity_guardrails`
  caught it — to serve a call the service never makes. The staged callers own
  that edge; `DECLARED_ENGINE_MODULES` is unchanged.
- *Pin resolution.* `accepted_attempt_dir`, `load_worker_report` and
  `accepted_output_item` are public names now: `inspect scope="output"` reads
  the same pinned report against the same containment checks.
- *Docs.* `INTEGRATION.md` (both tables), `XSCRIPT.md` (store, mesh
  vocabulary, scope list, and the rewritten "stays that way" paragraph),
  `ARCHITECTURE.md` (staging, file map, store layout — which had never
  mentioned `assets/` — and the test count), `BLENDER.md` (thirteen tools),
  `BLENDER-TREE.md` (add-on line count), `ROADMAP.md` (Phase 4, and the op
  counts in 11b/11c: mesh 6 → 7, part 49 → 50).

**Evidence.** `pixi run python -m pytest src/Mod/cadex/cadex_tests` — 226
passed (was 208). New coverage: `put_asset`'s bounds, name rules and
atomicity, and that `list_project_assets` walks exactly as
`_stage_project_assets` does (`test_mesh_domain.py`); `scope="assets"` and
`scope="output"` including paging and the missing-output message
(`test_model_context_contract.py`); the promoted accepted-attempt helpers
and their containment check (`test_pin_resolution.py`); `mesh.transform`'s
contract equality with `part.transform`'s kwargs, and that it does *not*
make its tree approximating; `shape_from_mesh`'s domain crossing, option
validation, and `decimate` rejection.

`test_cadexd_lifecycle.py` now drives `put_asset` (including a rejected
`../escape.stl`), `inspect scope=assets`, and `inspect scope=output` before
and after acceptance, against a real cadexd child — and every frame in that
test is validated against the pinned response spec, so the golden and the
running engine agree by construction.

`test_project_rebuild.py` extends the digest CI with
`mesh.transform`-placed import, `scan_solid = part.shape_from_mesh(scan)`
and `carved = part.cut(plate, scan_solid)`. Its accepted-vs-rebuild and
rebuild-vs-rebuild assertions therefore cover `makeShapeFromMesh`
reproducibility for free. Measured: the imported tetra becomes a BREP
`Solid` of 10.667 mm³ — the mesh's own volume — and cutting it from the
2160 mm³ plate leaves 2149.333 mm³, with one digest across accepted, first
rebuild and second rebuild.

`makeShapeFromMesh`'s calling convention was confirmed against the pinned
`.pixi` build rather than assumed: it **mutates in place and returns
`None`**, and yields a Shell (or a Compound of shells), never a Solid — so
the branch promotes with `Part.makeSolid` and refuses a mesh that sews into
more than one shell.

## ADR-044 — A refused script must not be able to shut the project (2026-07-26)

**Decision.** Six changes, so that no script the engine refuses can cost a
user their model:

1. **A failed candidate is rolled back.**
   `prepare_project_candidate` still writes the candidate source to
   `script.py` before running it — a host that dies mid-run keeps the source
   that was running — but `record_project_candidate_failure` now restores the
   previous source, `working_revision` and `param_values`. The refused source
   stays recoverable in its attempt's `request.json`, which `latest_candidate`
   locates.
2. **A restore that cannot run the stored script retries from the accepted
   revision's own source**, pinned in `accepted_attempt` and read by the new
   `CadexProjectScriptStore.read_accepted_source()`. Success reports
   `restore.repaired_from_accepted: true`. A script that *runs* and produces a
   different digest is untouched by this: that is the user's edit, and it
   stays a hard `CADEXD_RESTORE_FAILED`.
3. **A mismatched restore no longer redefines the accepted model.** The
   restore pass runs through `write_script`, which accepts what it builds, so
   the run that proved the model was also the run that could replace it: the
   *second* open of a hand-edited project came up clean with the edit
   installed as the accepted revision. The mismatch branch now rolls the four
   `accepted_*` fields back before it reports.
4. **`write_script` and `get_script` work on a project whose restore failed**
   (`ensure_open(unrestored_ok=True)` → reopen with `restore: False`, and a
   warning carried on every result until a rewrite lands). Everything else
   still refuses an unproven model.
5. **A caller's own `open_project` is no longer replayed by the client.**
   `CadexdClient.request` ran `_ensure_open` first for every op, which built
   its own args — so an explicit `open_project` was answered by a *different*
   open, and `restore: False` never reached the engine. It also sent every
   open twice.
6. **`stdout` rides the success reply** (`OP_RESPONSE_SPECS`, optional), and
   **`get_script` is capped at 64 KB** rather than the 4 KB that applies to
   other tool results, with a truncation marker that states the numbers.

**Rationale.** Reconstructed from a real modeling session, where all six
failed in sequence. The agent was asked to align an imported
flight controller to the chassis mounting posts. `get_script` served 4,123 of
the script's 8,244 characters, cut mid-line, and the posts were in the half
that was dropped. It added `print()` probes; the revision was accepted and no
stdout came back, because only the *failure* envelope carried it. So it did
the one thing that did work — `{}[str(info)]`, a deliberate `KeyError`
carrying the values in its message. That refused candidate stayed on disk as
the working source. Four minutes later the engine respawned, the restore pass
re-ran the working source, and the project refused every operation from then
on, including the `write_script` its own error message recommended. Nothing
was corrupt: the accepted revision, its digest and its source were all intact
and pinned on disk the whole time.

The chain matters more than any link in it. A truncation with no way to
detect it produced a need to observe; no way to observe produced a
deliberately-failing script; a failing script was durable; a durable failure
was load-bearing at open; and every recovery went through open. Each step is
defensible alone. What makes them a defect together is that the failure was
**silent, deferred, and self-blocking** — the store was poisoned at 16:09 and
did not fail until 16:13, and could just as easily have failed the next
morning.

**Consequences.** `restore.repaired_from_accepted` is new and optional;
`stdout` is new and optional on the four modeling ops; `docs/INTEGRATION.md`
carries both. `_ensure_open` no longer runs for `open_project`, which removes
one full script run from every open.

Seven engine tests in the new `cadex_tests/test_project_store_recovery.py`
pin the rollback (including the first-script and `set_params` cases), the
accepted-source fallback, the mismatch rollback and the `stdout` payload,
without needing a live cadexd. Five gate tests in
`bl_mesh_agent_cadex.py` drive the whole thing through the real tools against
the built bundle: a refused edit leaves the project openable, a broken store
can still be rewritten, a script that will not run is repaired from the
accepted source, a working script's stdout reaches the caller, and a long
script survives `get_script` intact. `test_restore_failure_is_first_class`
gained the second open that catches the silent adoption.

**What this does not change.** `script.py` is still the project's source of
truth and a hand edit that changes the model is still a first-class restore
failure, reported and never silently reverted. The fallback in (2) fires only
for a stored script that cannot execute at all, which is not a state a user
can reach by editing.

## ADR-045 — The script has a history, and write_script cannot silently delete a model (2026-07-26)

**Decision.** Three changes, from one incident:

1. **`script_history/`** — every *accepted* revision's source is kept as a
   plain `.py` file with a `history.json` index (ordinal, revision, time,
   character count, declared outputs). Last `HISTORY_LIMIT = 25`. Text only:
   no BREP, no worker bundle, single-digit kilobytes per entry. Re-accepting
   the revision already at the tip is not recorded, so re-opening a project
   does not fill the trail with itself.
2. **Reading and reverting it** — `inspect scope="history"` lists the
   versions, or serves one by ordinal or revision prefix. Revert is *not* a
   new op: a version is a script, so putting one back is the `write_script`
   that already exists. The shell's `restore_version` tool does the two steps.
   That keeps it honest — a restored version re-runs, re-publishes and is
   re-accepted like anything else, rather than being trusted because it used
   to work.
3. **`write_script` refuses to drop accepted outputs** unless `replace=true`
   (new optional arg). Checked after the run, against the real output
   contract, where the truth is known — a `PROJECT_OUTPUTS_DROPPED` failure
   that names what would have been lost. `edit_script` and `set_params` are
   not checked: one is a targeted replacement, the other does not touch the
   source.

Plus the retention that should always have existed: `prune_artifacts()` drops
stale attempt staging directories on acceptance, keeping the pinned accepted
attempt and `ATTEMPT_KEEP = 3`.

**Rationale.** A user asked "lets create a battery model, it should just be a
64x10x6 rectangle" — an *additive* request. The agent answered with
`write_script` carrying only the battery. It built, it published, it was
accepted, and a drone frame with an imported flight controller stopped
existing. A minute later: "whered the rest of the stuff go".

Nothing malfunctioned. `write_script` replaces THE project script and that is
what it did. But the surface makes the destructive reading of an additive
request a single well-formed call, with no signal at any layer — the run is
indistinguishable from a legitimate rewrite until you look at the viewport.

This is the *opposite* failure to ADR-044 and is not covered by it: that one
protects against runs the engine **refuses**; this was a run that **succeeded**
and was wrong. Both end the same way — work gone, silently — and that is the
property worth defending, not any particular mechanism.

Recovery was possible only by accident. Every attempt's `request.json` still
held its source, because no GC had ever been written (`default_state()` even
documents `accepted_attempt` as pinned "no GC removes it while it is
referenced here", describing a collector that does not exist). So the store
was simultaneously **too big to keep** — 2.3 MB per attempt, a full worker
bundle staged beside each run's BREP, 56 MB for one afternoon — and **too
opaque to use**: no index, no tool, no UI. Recovering the frame meant globbing
`request.json` files and reading millisecond stamps out of directory names.
A history you cannot list is not a history.

**Why the guard fires after the run, not before.** A script's outputs are not
knowable from its text; only running it says what it declares. Checking
after costs one wasted run on the refused path — and the ADR-044 rollback
means that run leaves nothing behind.

**Consequences.** `write_script` gains optional `replace`; `inspect` gains
scope `history`; both are in `docs/INTEGRATION.md`'s op table. New
`restore_version` MCP tool, and `write_script`'s tool description now opens by
saying it replaces the ENTIRE script and to use `edit_script` to add to a
model. Existing projects gain history from their next acceptance onward:
nothing back-fills, because a source that was never run under this engine has
no proof it still builds.

Nine engine tests in `cadex_tests/test_project_store_recovery.py` cover the
trail (ordering, selection by ordinal and by revision prefix, the repeat
suppression, the bound and its file cleanup), the attempt pruning against the
pinned accepted attempt, and the drop guard including its `replace` escape
and its non-application to `edit_script`/`set_params`. Three gate tests drive
the whole thing through the real tools: the battery-shaped mishap is refused
and then allowed with `replace`, a two-version history lists/reads/reverts and
records the revert itself, and pruning leaves `inspect scope=output` working.

## ADR-046 — Save-As carries the geometry you imported (2026-07-26)

**Decision.** Two changes to the Save-As path in the shell, both in
`mesh_agent/`:

1. **Imported geometry comes across.** `cadex_backend.migrate_assets()`
   copies the previous project's `assets/` into the new one when the saved
   script is adopted, one file at a time through the **`put_asset` op** —
   cadexd stays the sole writer of the store, so the 64-file / 128 MB budget
   is enforced where it is defined and nothing lands half-copied. Which
   project to carry from is recorded in `save_pre` (`SOURCE_PROP`, where
   `bpy.data.filepath` still names the old file) and therefore saves *into*
   the new `.blend`, so a duplicate opened in a fresh session knows it too.
   Everything the engine derives — staged artifacts, accepted revisions, the
   `script_history` trail — still does **not** come across.
2. **The offer is reachable.** `orphaned_project()` no longer requires the
   engine to have opened the project first. Before an open there is no
   engine state to ask, so it falls back to whether the root exists at all.

**Rationale.** A user Saved-As `wcv6.blend` to `wcv7.blend` — a drone frame
built on seven imported STLs — and got a file whose model could not be
rebuilt or edited. Both halves of the recovery story were broken, and each
hid the other.

The button was unreachable. `orphaned_project()` was gated on
`state.opened`, but `on_file_changed` calls `close_all()` a moment after the
new name takes effect, so the one file that most needs the offer — the one
just saved under a new name — was the only one that never got it. The chat's
status line was the sole surviving affordance, and starting a new
conversation (`history.clear()`) wipes it. The Text Editor's "Apply to
Model" was reachable the whole time, which is why this survived review: the
path exists, just not where the user was looking.

And pressing it would not have worked anyway. ADR-043 made external geometry
a first-class *input*; the Save-As note was written before it existed and
reasoned only about *derived* state — "copying would duplicate BREP
artifacts behind the user's back and silently fork the model's history",
which is still right. Assets are neither derived nor reproducible: the
script names them, and `write_script` dies on the first `mesh.import_file`
without them. So "re-run the saved script into a new project" was not a
recovery for any model built on geometry the user supplied — the failure
observed verbatim was `DOMAIN_CANDIDATE_FAILED: api.import_file: no staged
mesh asset named 'flight-controller.stl' exists`. The baked mesh stayed in
the viewport, so the file looked fine and was not.

The same hint fixes the first save of an unsaved file, which loses its
assets the same way (temp root → `<stem>.cadex`) and was never noticed.

**Why the shell reads one directory of the store.** `docs/ARCHITECTURE.md`
said cadexd is the sole writer *and the sole reader*. The writer half is
load-bearing and is untouched: every byte still goes in through `put_asset`.
The reader half is now narrowed, and the doc says so — the shell lists
`assets/`, and only in the root it is migrating away from, to hand those
paths back to the engine. What is in there is the one thing in the store the
shell supplied in the first place, and the shell already owns *where* the
store lives (`project_root` derives `<stem>.cadex`). The alternative — a new
op, or an optional `open_project` argument with a migration side effect —
buys layout-independence for a directory whose name the shell already
chooses.

**Consequences.** No protocol change: `OP_ARG_SPECS`, the op table in
`docs/INTEGRATION.md` and the ADR-027 response goldens are all untouched.
`ARCHITECTURE.md`'s store invariant is narrowed to match. New gate test
`test_save_as_carries_imported_geometry` drives the whole path — a model
built on an imported STL, two accepted revisions, Save-As, orphan detected
before any open, adopt, geometry back in the viewport, asset in the new
store, history *not* carried — and
`test_duplicated_file_keeps_its_parameters` gains the pre-open orphan check.

---

## ADR-047 — A joint solves in a headless engine (2026-07-27)

**Decision.** `src/Mod/Assembly/Preferences.py` imports `FreeCADGui` inside
`PreferencesPage.__init__` instead of at module scope, and
`src/Mod/Assembly/CommandCreateView.py` guards its
`from PySide.QtCore import QT_TRANSLATE_NOOP` with the same
`try/except ImportError` shape `JointObject.py` already carries in this
fork. `package/engine/build_engine_payload.sh` also prunes `FreeCADGui.so`,
not only `libFreeCADGui*`.

**Rationale.** `assembly.joint(...)` failed in a headless engine with
`'NoneType' object has no attribute 'preferences'`, and
`assembly.exploded_view(...)` failed with `No module named 'PySide'`. Both
are one bug wearing two hats: a GUI-only import at module scope in a module
whose *other* contents are pure App-level.

`Preferences.py`'s sole GUI dependency is the `PreferencesPage` class, which
nothing headless instantiates; `preferences()` itself is one `ParamGet`.
Because the import sat at module scope, `import Preferences` raised in a
`BUILD_GUI=OFF` engine, `JointObject.py`'s `except ImportError` guard set
`Preferences = None`, and `solveIfAllowed` — which calls
`Preferences.preferences()` unconditionally — died on every joint.
`CommandCreateView.py` is the same shape one level along: the engine's
`exploded_view` builds and reads its `ExplodedView` document object, a pure
App-level feature, but the module could not be imported to reach it.

This is the ADR-022 exception worth making in the conservative zone: both
diffs *reduce* the fork's coupling to the GUI rather than adding logic, and
neither changes behaviour in a build that has Qt.

**Why it survived.** Two independent reasons, and each one alone would have
been enough.

1. **No live test built a joint.** The assembly suites validate arguments
   under a stubbed FreeCAD, so they never reach the FreeCAD import that was
   broken; `test_cadexd_lifecycle.py` and the shell gate had zero `joint`
   hits. `test_cadexd_solves_a_jointed_assembly` is that missing test.
2. **The engines developers run are not the engine that ships.** Three
   trees disagreed. `.pixi/envs/default` — which is what
   `test_cadexd_lifecycle.py` picks by default — carries a `FreeCADGui.so`
   and joints work there. The staged payload carried a *stale* one that the
   prune's `libFreeCADGui*` pattern never matched, because the Python
   extension module has no `lib` prefix, so joints worked in the product
   **by accident**. Only `build/release` (`BUILD_GUI=OFF`) told the truth.
   A joint test written before this ADR would have passed on the default
   engine and proved nothing.

The prune fix is what makes the other two changes load-bearing: with a
stale `FreeCADGui` in the payload the guard is never exercised, and the day
Phase 8 deletes `src/Gui` the product would have regressed with no test
able to see it. A surviving `FreeCADGui` is not inert — it silently changes
which imports succeed.

**Consequences.** No protocol change; no ADR-027 golden moves. New engine
test `test_cadexd_solves_a_jointed_assembly` asserts both that the joint
publishes and that the solver *ran* — `swing` is declared at `[0, 0, 40]`
and must come back on the revolute joint's `[12, 0, 4]` connector offset,
so a run that merely avoids the crash still fails. Verified against a
freshly staged payload with no `FreeCADGui` at all: the test fails without
the `Preferences.py` change (the verbatim `'NoneType' object has no
attribute 'preferences'`) and passes with it, and `exploded_view` goes from
`No module named 'PySide'` to a published output. `docs/FREECAD.md` §5's
`CommandCreateView` question is answered.

Note for Phase 8: the lifecycle test's default engine is still the
GUI-carrying pixi environment. Until that is the shipped configuration, the
packaged run (`CADEX_ENGINE_ROOT=...`) is the one with teeth for any
GUI-coupling regression.

---

## ADR-048 — A simulation publishes (2026-07-27)

**Decision.** `cadex_assembly_worker._execute_native_simulation` emits
`simulation_trace_preview` on the simulation output item: the input, middle
and final frames of the authenticated trace, deduplicated by index and
bounded at three however long the run.

**Rationale.** `_configure_assembly_simulation` reads
`item["simulation_trace_preview"]` and raises
`An Assembly simulation has no authenticated trace summary` when it is
missing. Nothing wrote it — that read was its only occurrence in the
repository — so **every** script containing `assembly.simulation(...)` died
at publication with `DOMAIN_PUBLICATION_FAILED`. The property and its
description already existed and were already right; the producing half was
never written.

**Emitted, not derived.** The obvious alternative is for the publisher to
read the retained trace artifact and slice it. Rejected: the property is an
*authenticated* summary, and the publisher does not otherwise touch that
artifact. Deriving it there would make the publisher a second reader of a
file the worker already has open, and would let a preview exist that the
worker never vouched for. Emitting it in the worker keeps the preview a
verbatim subset of the frames that went into `artifact_sha256`, so it can be
checked against the retained trace rather than merely trusted.

Deduplication matters at the short end: a two-frame trace has
`0`, `count // 2` and `count - 1` all collide, and publishing the last frame
three times would misrepresent the trace as static.

**Consequences.** No protocol change and no ADR-027 golden moves —
`simulation_trace_preview` is a worker→publisher item key, not a response
key. Two new tests, and they cover different halves on purpose:
`test_assembly_simulation_publication.py` drives the publisher under the
stubbed-FreeCAD conftest and pins the preview's shape against
`_simulation_trace_preview` itself, while `test_cadexd_publishes_a_simulation`
runs a driven assembly through a real engine and asserts the trace is a
readable file whose driven component moves and whose grounded one does not.
The unit test alone would not have caught this, because the bug was that
nothing *called* the producing code.

Both were verified to fail before the change with the verbatim publication
error and pass after, against a staged payload.

**What the trace actually looks like**, since the shell's playback (ADR-050)
depends on it and it is easy to guess wrong: `component_placements` maps a
component name to `{"position_mm": [x, y, z], "rotation_xyzw": [x, y, z, w]}`
— a compact position and quaternion, **not** a 4x4 matrix, and in **xyzw**
order rather than Blender's wxyz. Frame 0 is `frame_kind: "input"` with
`nominal_time_s: None`; solver frames carry real times. A 0..1 s run at a
0.05 s step is 22 frames, not 21: both endpoints are included, plus the
input frame.

---

## ADR-049 — A solved assembly is visible (2026-07-27)

**Decision.** A component's display entry names the declared output whose
geometry it places, in a new optional `source_output` key on
`display.<output>`. The shell instances that output's mesh at the
component's `placement` (shell half, same ADR).

**Rationale.** A solved assembly never reached the viewport, and the
response is why. Components carry a `placement` and no geometry; the parts
they instance carry geometry and no placement — visible in the pinned
golden `set_params.json` long before anyone read it that way: `base`/`top`
have `placement: [float]` and `artifact_kind: null`, `plate`/`skin` the
mirror image. `cadex_hydrate.py` skips any entry with no tessellation and
the contract-driven GC then deletes it, so the one thing the user asked for
— the mechanism, arranged — was the one thing that could not appear.

Nothing in the response connected the two halves. The component knew where
to be and not what to draw; the part knew what to draw and not where.
Every consumer had a set of matrices and no way to spend them.

**Why a new key and not a re-use.** Three alternatives were rejected:

- *Give components a `tessellation` of their own.* That is the same
  geometry serialized once per component — 40 screws, 40 meshes — and it
  moves the dedupe the engine already does into the wire.
- *Reuse `display.* {tessellation: null}` as a pose-only marker.* The
  shell's GC deletes exactly those entries; the marker and the delete
  signal would be the same value.
- *Let the shell match components to parts by name or by order.* There is
  no such relation, and inventing one puts a guess on the critical path of
  whether the model appears at all.

The token → output-name map already existed — it is what lets the publisher
rewrite each inline source token to a live published object
(`_resolve_inline_sources`). This ADR only writes it down where the
response can carry it.

**Optional, and absent rather than null.** Only components have a source,
so presence *is* the discriminator, and every other entry keeps byte-for-byte
the shape it had. A consumer that does not know the key is unaffected.

**Consequences.** A protocol change, additive and optional:
`NESTED_RESPONSE_SPECS["display.*"]` gains it in the optional set, four
ADR-027 goldens move (`write_script`, `edit_script`, `set_params`,
`rebuild` — `edit_script` too, which the plan for this work missed), and
`docs/INTEGRATION.md`'s nested-shape prose gains the paragraph that says
what the two entry kinds are. `OP_ARG_SPECS` is untouched, so neither doc
*table* moves and the request contract is unchanged.

**Digest-neutral, verified rather than argued.** `compute_project_digest`
reads named keys off each output item and `source_output` is not one of
them, so the digest cannot move — and the same script through a pre-change
and post-change engine returns the identical digest
`59905ecb52fcffaf7bb2b26f365487894ce14fb39460064431c971cc8d366fc5`.

This fixes static assemblies, not only simulated ones, which is most of why
it is worth a protocol change at all.

**Shell half (B1).** `cadex_hydrate.hydrate_display` gains a second pass,
after the geometry pass and before the GC. An entry with a `placement`, no
`tessellation` and a `source_output` becomes an object that **shares the
source's mesh datablock** — forty screws cost one mesh — found or created by
`OUTPUT_PROP` exactly as the first pass does, so Blender's `.001` name dedup
cannot break the lookup. It gets the solved matrix, a `cadex_kind` of
`component`, a `cadex_source` naming what it instances, and an ` Edges`
child sharing the source's edge mesh and parented to it, so the wire follows
the component for free.

Components join `keep`, so the existing contract-driven GC stays the entire
cleanup story — no second collector to fight, and a shared datablock is
never orphaned by it because the source still uses it.

A source that has at least one instance is **hidden, never deleted**: it is
a declared output and the user may still inspect or pin against it. The
unhide is marked (`cadex_hidden_source`) rather than unconditional, so a
later pass unhides exactly what it hid and never overrides visibility the
user set themselves.

The three `hydrate_display` call sites — the open path, a lifecycle accept,
and the settled refine — collapse into one `cadex_backend.hydrate(payload)`.
They had all been unpacking the same two arguments from the same payload;
anything that must happen on every accepted revision now happens once, in
one place, instead of in whichever of the three someone remembered.
`hydrate_display` keeps its own signature and its own tests.

Two gate tests: a jointed assembly puts each component at its *solved*
placement (not its declared one), tagged, sourced, wire-parented, with the
source hidden and still present; and two components sharing one plate are
one `bpy.data.meshes` datablock, at different placements, collected on a
revision that drops the assembly — which also unhides the source.

---

## ADR-050 — The shell plays a simulation (2026-07-27)

**Decision.** A new `shell/scripts/addons_core/mesh_agent/cadex_animate.py`
bakes an accepted simulation trace into F-Curves on the component instances,
and a `CADEX_PARAMS_PT_simulation` panel in the parameters editor plays it.

**Rationale.** Watching the real motion of a mechanism is the point of
building one, and with ADR-047/048/049 the engine finally produces the
trace and the shell finally has objects to move. Nothing yet moved them,
and a baked action is otherwise reachable only through editors this product
does not show.

**A sibling module, not part of `cadex_hydrate`.** A malformed, missing or
oversized trace must never cost you the geometry. Hydration runs first and
stands alone; the bake runs after and is allowed to fail on its own —
`cadex_backend.hydrate` catches it and reports it without touching the
hydration result.

**Baked, not evaluated per frame.** No `frame_change_post` handler and no
per-frame Python: the poses are known ahead of time, Blender's animation
system plays F-Curves without involving us, and a Python handler on every
frame is exactly the thing that would make playback stutter.

**Five ways to get this wrong, all silent, all verified against a live
Blender rather than assumed:**

1. **Time, not frame index.** `time_step_s` and `frames_per_second` are
   independent. Keying on the frame index plays a 0.05 s / 30 fps
   simulation at 2/3 speed; frames land on *fractional* Blender frames and
   rounding them collapses several samples onto one.
2. **Quaternion order.** The trace is `rotation_xyzw`; Blender is wxyz.
3. **Hemisphere continuity.** The solver returns `q` and `-q` for the same
   orientation and `_compact_placement` normalizes without de-flipping.
   Keyed raw, a linkage swings through a full rotation between two adjacent
   samples and it reads as a solver bug.
4. **`rotation_mode`.** The default `'XYZ'` leaves the quaternion channels
   inert: nothing errors and nothing moves.
5. **Slotted actions.** Stronger than expected — in this Blender (5.3)
   `Action` has **no `fcurves` attribute at all**; code written against
   `action.fcurves.new(...)` raises `AttributeError` rather than silently
   animating nothing. Curves live at
   `action.layers[].strips[].channelbag(slot).fcurves`, and
   `fcurve_ensure_for_datablock` builds the layer, strip and slot — but only
   once the action is already assigned to the object.

Keys are written in bulk (`points.add`, `foreach_set("co"/"interpolation")`,
`fcurve.update()`), never `keyframe_insert`: the engine's ceiling is 10 000
frames × 7 channels. Interpolation is LINEAR, because the poses are already
sampled at the solver's step and Bezier handles between them would invent
motion the solver never produced.

Frame 0 (`frame_kind: "input"`, `nominal_time_s: None`) is skipped: it has
no time, and it is the pose the object already sits at. Units are raw mm
1:1 — 1 BU = 1 mm and both sides are Z-up right-handed, so there is no
conversion anywhere.

**Replacement is clear-then-bake, never edit-in-place**, and the orphaned
actions are removed, mirroring `_replace_data`'s orphan-mesh handling: a
shorter simulation must not leave the tail of a longer one behind. An
unchanged trace (same SHA-256 of the artifact's bytes) is not re-baked.
Mid-drag responses pass `animate=False` — a drag re-runs the whole script,
simulation included, and re-baking on every debounce tick to show a shape
change is the wrong trade. The settled refine bakes.

**Two simulations in one script are refused** with a sentence rather than
silently picking one: two simulations are two timelines and a scene has one.

**The panel.** In the parameters editor, beside the sliders, because that is
where you already are when you want to see the effect of one. No new editor
and no new space type — **ADR-036 stands and `space_action` is not
re-registered.** It is the only panel in this add-on with a `poll`, and the
poll asks about *content* (one custom-property lookup: does this model have
a simulation?) rather than about *where it is drawn*, which is the kind
ADR-035 removed. A model without a simulation sees the editor exactly as
before. Nothing about *authoring* a simulation goes in the panel; that
belongs to `describe_project_api()`, which is the single source of API truth.

**Consequences.** No protocol change and no inherited-tree delta. New tests:
four in the engine-free suite covering the pure trace→curve conversion
(fractional frames, wxyz reordering, a deliberate `q → -q` staying
continuous, mm 1:1, the input frame skipped) plus the panel's poll; and
`test_a_simulation_plays` in the gate, which compares the *played* pose
against the engine's own trace at three frames through the depsgraph —
3/3 — rather than against the F-Curve values, which would only prove the
bake agrees with itself. New gate key
`simulation: {frames, components, bake_seconds, keyframes}`; measured at
21 frames, 2 components, 147 keyframes, 0.578 s.

**Found on the way, not fixed here.** A revision that drops an assembly's
*parts* as well as its simulation is refused by the engine's output
retirement guard — `Cannot retire XScript output 'arm'; ... App::Link ...
LinkedObject` — because the live component still references the part when
retirement runs. An ordering wrinkle in retirement, unrelated to playback;
the gate test drops the simulation and keeps the mechanism, which is the
case that matters here.

---

## ADR-051 — The drag leaves the main thread (2026-07-27)

**Decision.** A slider drag no longer blocks Blender's main thread.
`rebuild_from_sliders` splits into `begin_slider_rebuild(scene)`, which
returns an unwaited `Lifecycle`, and a blocking `rebuild_from_sliders` that
is `.wait()` over it. `model._debounced_rebuild` hands the drag to a pump
(`note_drag` / `_drag_pump`) that keeps at most one request in flight per
project and coalesces the rest.

**Rationale.** Each debounce expiry ran one `set_params` round trip *on the
main thread* — about half a second — so the application froze, repeatedly,
for the whole of a drag. For a hole diameter that was survivable. For an
assembly, where watching the motion is the point, it made the thing
unusable.

`_lifecycle`'s docstring already claimed "one code path underneath"; this
makes it true, with `on_accept` carrying what the blocking form used to do
after `if ok:` so the two callers genuinely share a path rather than being
two that happen to agree.

**Coalescing needs no value queue.** `begin_slider_rebuild` reads the live
PropertyGroup when it *starts*, so restarting after the in-flight request
completes automatically takes the newest values and drops every intermediate
one. A 50-event burst is one in-flight request plus a boolean — measured:
12 events became 2 requests and converged on the final value.

**Cancel in flight only past ~1.0 s.** Below that the in-flight result is
about to arrive and is nearly current, and cancelling it freezes the
viewport for another whole round trip. Above it, a stale request is holding
the client lock while the user has already dragged well past the value it is
computing. One constant, with that reasoning beside it.

**Arbitration.** `begin_lifecycle` supersedes a *queued* drag — the agent is
about to move the revision, so those values are stale — and leaves an
in-flight one alone, since it already holds the client and finishes in a
moment. `note_drag` defers while the agent is busy, because otherwise the
drag's `expected_revision` snapshot goes stale behind the agent's write and
burns the one-shot retry on every drag. The drag pump and the refine pump
stay separate.

**A superseded drag is not a failure** and must not reach
`model._last_error`, which is what the parameters panel displays (ADR-039
state stays in `model.py`). That is what the `superseded` flag is for.

One slot **per project root**, the exact twin of `_refines` and for the same
reason: a drag started in one .blend must not hydrate into another. The pump
re-checks `project_root` before polling, because `Lifecycle.poll` hydrates
unconditionally.

**Background mode is untouched:** `model._schedule_rebuild`'s
`if bpy.app.background` branch still calls the blocking form, so the gate's
`test_params_and_latency` measures the same end-to-end work and its 0.65 s
bar and baseline stay comparable. Verified: 0.576 s after, 0.578 s before.

**Visible consequence.** One undo step per *settled* value instead of one
per debounce expiry. That is an improvement and it matches "one turn = one
undo step", but it is a change a user can see.

**Known limit, not papered over.** `ensure_open` still runs `open_project`
(a full restore pass) plus a `rebuild` synchronously on the main thread, so
the *first* drag of a session still stalls — `open_seconds` is 2.1 s in the
gate. Out of scope here.

**Consequences.** Two new gate tests. `test_main_thread_free_during_a_drag`
drives a 12-event burst and drives the pump by hand — `bpy.app.timers` do
not fire under `--background`, which is also what makes the tick count
meaningful — and asserts one request in flight, one queued boolean, 2 total,
convergence on the final value, and no error.
`test_an_agent_turn_supersedes_a_queued_drag` asserts the queued drag is
dropped and that the supersede never surfaces as a failure. New gate keys
`drag_ticks` (96), `drag_requests` (2), `drag_seconds`.

**Unchanged geometry is not rebuilt (C2).** An object records what its mesh
was built from (`cadex_source_sha`); a hydration whose sidecar describes the
same buffers sets the placement and the revision and skips the binary read,
the mesh build and the face-attribute write entirely. The hash is compared,
never the path: every attempt gets its own staging directory, so paths
differ on every request.

**The measurement says this is not a latency win today, and the ADR should
say so rather than let the numbers imply otherwise.** A0 exists to answer
whether hydration is worth optimising: it is **9.6 ms, 1.7% of a 579 ms
drag**. It is not. Nor does the skip fire on a parameter drag, which is the
case that matters — the geometry genuinely changed, so the key genuinely
moved. What it does fire on today is a repeated rebuild at the same quality
(`rebuild_model`, and the rebuild after a restore on open).

It is kept for what it enables rather than what it saves now: a response
carrying a `placement` with unchanged buffers is indistinguishable from a
pose-only response, which is precisely the shape the warm preview worker
(ADR-055) returns — and at Stage E's ~60-80 ms the same 10 ms is ~14%
instead of 1.7%.

**The key is not `source_sha256`.** That was the obvious mistake and it is
silent: the *same* BREP is tessellated at draft quality during a drag and at
standard quality by the settled refine, with an identical `source_sha256`
both times. Keyed on the SHA alone the refine looks like a no-op and the
viewport keeps the coarse mesh permanently. The key is source + quality +
deflection + whether edges were streamed, and
`test_unchanged_geometry_is_not_rebuilt` asserts exactly that case.

Deliberately **not** built: the general "update in place when vertex counts
match" path. Counts move with the geometry, so on a parameter drag it misses
every time.

---

## ADR-052 — The cold-path diet (2026-07-27)

**Decision.** Four small independent changes to what a request costs before
it reaches any geometry.

1. **The settrace hook stops tracing our own code.**
   `_execute_project_source`'s trace function returned *itself* for every
   frame, so Python line-traced the entire `cadex_*_api`
   payload-construction path on every line of it. It now returns `None` for
   any frame that is not the user's program. The counter is unchanged by
   construction — it only ever incremented for source frames — and a
   callback back into source code still gets a fresh `call` event at the
   global hook.
2. **The process poll loop stops forking `/bin/ps` at t=0**
   (`next_memory_check = started + 0.5`; it was `0.0`, so every run forked
   `ps` while the child was still `dlopen`ing OCCT and could not possibly
   have allocated anything), and sleeps adaptively — 1 ms backing off to
   50 ms — instead of a flat 50 ms that charged every short run up to 50 ms
   of dead time. **Not** a waiter thread: `process.wait()` has to stay
   interruptible for cancellation, which puts you back at a polled loop plus
   machinery.
3. **The two assembly transfer-integrity checks ask for the counts they
   read.** Both passed `max_subelements=32` and then read seven count
   fields, computing 32 face and 32 edge details each time for nothing.
   Counts are unconditional in `part_shape_facts`; only the details are
   bounded, so `0` is the honest argument.
4. **The worker bundle is staged once, not per request.** It was copied into
   every attempt directory — 608 KB and 16 `compile()` calls on every single
   request. It now lives in one content-addressed directory outside the
   project store, populated by `os.link` with a `copy2` fallback and
   published atomically (`.tmp-<uuid>` → `os.replace`), and the
   `runpy.run_path` bootstrap becomes a plain `import` so the entry module
   is cacheable too.

   **The hardlink is the load-bearing detail.** `__pycache__` validates
   bytecode against its source's mtime and size; `shutil.copyfile` does not
   preserve mtime, so a copy would invalidate the cache on every request and
   the compile would come straight back. `PYTHONPYCACHEPREFIX` alone would
   not have fixed that either. Content-addressing is what makes the cache
   safe: an engine rebuild produces a different directory, so a stale bundle
   can never be served.

   Project assets are hardlinked the same way, which also removes a latent
   128 MB-per-drag copy for any project with imported geometry. Safe because
   `put_asset` writes through `replace`, so overwriting an asset makes a new
   inode and never mutates a file a live attempt has linked.

**Measured**, on the 24-hole/fillet/mesh-skin baseline, dev tree and payload
agreeing: **0.505 s → 0.471 s** plain and **0.610 s → 0.529 s** with the
draft display the shell requests mid-drag. The gate's end-to-end slider
median moved 0.578 s → 0.565 s.

**Stage D cannot reach real-time, and this ADR should not let the numbers
imply otherwise.** What remains after this is process spawn, FreeCAD's C++
init, `--safe-mode`'s `QTemporaryDir` setup and the OCCT dylib load — all
invisible to cProfile, none of it removable by making Python cheaper. That
is what ADR-055's warm preview worker is for. This buys roughly 7% of a
drag; it does not change what kind of thing a drag is.

**Consequences.** `_stage_worker_bundle` is replaced by
`shared_worker_bundle`, which returns `(bundle_dir, entry_module)` rather
than a tuple of copied names, and the entry module keeps its real name
instead of being renamed to `worker.py` — it is imported now, so it needs
one. Three tests move with it (`test_tessellation.py`,
`test_modeling_surface_architecture.py` ×2), and a new test asserts the
bundle is built once, is content-addressed, and preserves mtime — the
property the whole item stands on. 250 engine tests pass in the source tree
and against the staged payload; `pixi run gate` green.

---

## ADR-053 — Shared sub-expressions are built once (2026-07-27)

**Decision.** `build_part_shape` memoises by content for the duration of one
worker request, keyed by
`"src-" + sha256(canonical_json(payload))[:24]` — the same construction as
`cadex_project_api.inline_source_token`, so the tree has one content-key
idiom rather than two that drift.

**Rationale.** Assembly components dedupe; nothing else did. A value used
twice — a `plate` fed to two `mesh.from_shape` calls, a sub-assembly cut
against several things — was rebuilt per consumer, measured at **+0.164 s
per extra consumer**.

**Hooked at `build_part_shape`, not `_shape`.** On the latency baseline both
consumers of `plate` are top-level, so a `_shape`-level memo would score
zero hits on the very case it exists for.

**Copies on get and on put**, for three independent reasons, any one of
which alone would justify it:

- `part.repair` calls `shape.fix(...)` **in place** on what it is handed.
  Harmless while nothing was shared; silent cache corruption under a memo.
- `part.transform` already copies, precisely because it mutates.
- **The digest hazard.** `MeshPart.meshFromShape` runs `BRepMesh`, which
  skips faces that already carry a triangulation. Handing `mesh.from_shape`
  a shape `part_shape_facts` had already tessellated would change the PLY,
  its `geometry_sha256` and the project digest — while
  `test_project_rebuild` stayed green, because rebuild would use the memo
  too. `Shape.copy()` defaults to `copyMesh=False`, which is what makes a
  hit indistinguishable from a fresh build.

Measured before building it, as the plan required: `Shape.copy()` is
**0.62 ms against the 42.7 ms** of `cut` + `makeFillet` it replaces on the
baseline part — **68x cheaper**, so the mandatory copy is not what this
costs.

**The reset lives in the request's `finally`, not at its entry.** A warm
worker (ADR-055) that leaked the memo across requests would answer with
geometry built from the *previous* parameter values, under a digest
self-consistent with it — the worst failure this codebase can have. A test
pins the reset's position in the `finally` for exactly that reason.

**Evidence.** Digest equality on four scripts — the latency baseline, a
shared node feeding two `mesh.from_shape` calls, one with `part.repair`, one
with `part.transform` — captured **on the same build** with the memo
reverted and re-applied. All four identical. `test_project_rebuild` alone is
necessary but not sufficient here, because both of its sides would use the
memo.

A methodological note worth keeping: the first attempt at this captured the
"before" digests, then rebuilt the engine, then compared. One script
disagreed and it looked like a memo bug. It was a stale baseline — an A/B
across two builds is not an A/B. The valid comparison reverts only the
change under test, on one build, and it passes.

`test_subshape_enumeration`, `test_subshape_selectors`, `test_pin_resolution`
and `test_project_rebuild` all stay green: face and edge ordering is what the
pin contract stands on.

**Measured payoff.** The shared-node script **0.570 s → 0.376 s**. The
latency baseline **0.471 s → 0.417 s** plain and 0.529 s → 0.496 s with the
draft display; the gate's end-to-end slider median 0.565 s → 0.537 s.

**Deliberately not done.** No `functools.lru_cache`: process-lifetime scope
is exactly the leak that becomes a correctness bug under a warm worker, and
dict payloads are unhashable anyway. The per-node `isValid()` in
`build_part_shape` stays — it names the operation that produced a bad shape,
which is what the agent repairs from, and this halves its count for free on
any script with sharing.

## ADR-055 — The server says what it is declared to say (2026-07-27)

**Decision.** Four keys cadexd sent on server-level failures but
`CadexdProtocol.SERVER_FAILURE_SPEC` did not declare are reconciled: the
`CADEXD_BUSY` sender is corrected to `busy_with` (the spec is the contract,
the sender was wrong), and `exception_type`, `restore_failure` and
`observed` are declared in the optional set.

| sent at | key | was |
|---|---|---|
| `cadexd.py` `_admit` (`CADEXD_BUSY`) | `busy_request_id` | spec says `busy_with` |
| `dispatch`, `_op_inspect` (`CADEXD_PROTOCOL_ERROR`) | `exception_type` | undeclared |
| `_op_open_project` (`CADEXD_RESTORE_FAILED`) | `restore_failure` | undeclared |
| `_op_open_project` (`CADEXD_RESTORE_FAILED`) | `observed` | undeclared |

(The `requested`/`observed` pair in `_op_put_asset` is a `tool_failure`,
correctly declared by `FAILURE_RESPONSE_SPEC` — not a bug.)

**Rationale.** An undeclared key is a key the shell may not read: the whole
value of pinning replies (ADR-025) is that either half can be replaced
against the spec rather than against the other half's source. A sender that
disagrees with the spec makes the spec a description of intent instead of a
contract. `busy_request_id` in particular means a shell written strictly
against `SERVER_FAILURE_SPEC` cannot tell *which* request a refusal was
waiting on, which is exactly what a client needs to decide between waiting
and cancelling.

**Why it survived.** `test_cadexd_lifecycle` shape-checks every frame it
*receives*, but it never drove a BUSY or a restore failure — the happy path
does not collide two modeling requests, and it does not corrupt the store.
The shell gate's `test_restore_failure_is_first_class` drives the digest
mismatch, but it reads the rendered report, not the frame. So four keys were
undeclared for as long as they had existed, and none of the existing suites
could have said so.

**The fix is structural as well as case-by-case.**
`test_every_key_the_server_sends_on_a_failure_is_declared` parses `cadexd.py`
and checks every `failure(...)` call site's keywords against the spec. It
needs no live server, names the file and line, and covers the two
`exception_type` sites that no test drives — a handler made to throw and an
`inspect` capture made to fail are both awkward to provoke and neither
should have to be provoked for the contract to hold. Two live cases back it
up where provoking is cheap:
`test_a_second_modeling_request_is_refused_as_busy` collides a `rebuild`
with an in-flight slow `write_script`, and
`test_a_broken_store_reports_a_declared_restore_failure` drives **both**
restore-failure shapes — a hand edit that runs and reproduces a different
digest (`observed`), and a store whose script does not run at all with its
accepted revision's pinned source removed (`restore_failure`). Each was
confirmed to fail against the unfixed spec before being kept.

**Consequences.** No shell change: nothing read `busy_request_id` — the key
had no consumer, which is its own evidence. This is the precondition for the
resident preview worker: `preview_params` is a `READ_OPS` member and will
collide with in-flight modeling far more often than anything does today, so
a BUSY frame stops being a curiosity the moment previews ship.

### The project worker can answer a preview

**Decision.** The project worker takes `mode: "preview"`. A preview execs the
script at new parameter values, decides whether the change was **pose-only**,
and if it was, builds the component shapes through the ADR-053 memo and runs
`validate_and_solve_assembly`. It returns
`{previewable, placements, definitions_fingerprint, reason?}` and **skips all
serialization**: no `exportBrep`, no `part_shape_facts`, no sha256, no
tessellation, no digest, no publication.

**Why a resident process is the only route left, and why this is safe.**
ADR-052 already took the cold path apart; what remains of the ~0.42 s is
process spawn, FreeCAD's C++ init, `--safe-mode`'s `QTemporaryDir` setup and
the OCCT dylib load. None of it is visible to cProfile and none of it is
reachable by making Python cheaper. What makes a resident process acceptable
is that **it never writes the project store, never publishes, and never moves
a revision or a digest** — it is a read-only oracle. Every accepted byte
still comes from a cold `--safe-mode` run with a fresh attempt directory, so
digest determinism, cross-revision isolation and crash recovery are preserved
*by construction* rather than by argument. Same hybrid ADR-019 already ships
one level down: draft tessellation during a drag, standard `rebuild` at rest.

**Pose-only detection is dynamic, not a static classifier.** Each
non-assembly output's canonical definition is hashed and compared against a
baseline; identical means the geometry is identical, because the definition
*is* the complete build recipe — it is what `compute_project_digest` hashes
for every output with no artifact bytes of its own. A static classifier was
rejected twice over: there is no dependency graph to build one from
(`p.width` evaluates to a bare float and `DomainValue.to_payload()` carries
no parameter provenance), and one would still be wrong for a parameter that
is pose-only at one value and topology-changing at the next.

**Assembly outputs are excluded from the comparison**, and must be: a
component's placement is an argument of its own definition, so including them
would make every moved component read as changed geometry and nothing would
ever be previewable.

**This serves the parameters that drive motion, not every slider.** A
parameter feeding `part.box(p.width, …)` changes that box's definition and is
therefore *never* pose-only — correctly, because the geometry really did
change and a placement-only reply would be a lie. The refusal is returned
before any shape is built, so declining costs 0.8 ms.

**Deviation from the plan, recorded because it is a real one.** The plan
defined pose-only as "definitions identical **and at least one placement
moved**". Shipped as definitions-identical alone. The movement clause adds
nothing to safety — identical definitions already means pose is the only
thing that *can* differ — and it introduces a live bug: a drag that begins at
the accepted parameter value produces a first preview where nothing has moved
yet, which would answer `previewable: false`, and the shell latches previews
off for the remainder of a drag on exactly that answer. The whole drag would
fall back. Whether a placement actually moved is something the caller can see
for free by comparing matrices it already holds.

**The baseline comes from the generation's first exec.** With no baseline
there is nothing to compare against, so the reply is `previewable: false`
carrying the fingerprints — which is how a baseline is acquired at all. The
warm worker establishes it on its `load` frame, at the *accepted* parameter
values.

**The memo's lifetime, stated precisely, because this and ADR-053 pull in
opposite directions.** The accepting path keeps its per-request reset in
`_run`'s `finally`, unchanged. The preview path deliberately does **not**
reset: keeping the memo across the previews of one generation is the point,
since unchanged parts must not rebuild. This is safe because the memo key is
*content* — a different parameter value is a different key, never a stale hit
— and bounded because the warm worker clears it on a generation change and
respawns on a request count.

**Component references bind in-process.** `configure_part_references`
authenticates a BREP by re-reading the file and matching its SHA-256 against
what the host recorded, because the artifact *crossed a process boundary*. In
a preview nothing crossed anything: the shape came out of `build_part_shape`
microseconds earlier in this interpreter, so the round trip would
authenticate a byte stream against a hash of itself and charge an export plus
an import for it. `configure_part_references_from_shapes` binds the shape
directly; validity is still checked, and every model-level bound downstream —
solid count, interface and BOM limits, hierarchy load — is the same code on
both routes, because those check the model rather than the transfer.

**A preview skips the simulation and the exploded views**
(`validate_and_solve_assembly(..., skip_derived=True)`), after validating
their contracts. Neither can move a solved component placement — a simulation
poses components frame by frame *from* the solve, an exploded view reports
offsets from it — so a preview that wants placements would be paying for
outputs it discards. Not a small saving: a driven assembly re-runs native
kinematics over up to 10 000 frames, which would make a pose-only preview of
a simulation script slower than the cold rebuild it exists to front-run
(the ADR-050 hazard, one level up). Playback is baked at settle time by the
accepting run, which is where it belongs.

**PartDesign component sources decline rather than guess.** A PartDesign
source is a native Body history built against a document by
`validate_and_build_partdesign`, not by `build_part_shape`, so there is no
memoised shape to bind. Declining is honest and costs one debounced rebuild.

**Measured, in-process, on a two-component revolute assembly:** a pose-only
preview is **7.9 ms** cold and **4.9 ms** with the memo warm; a refusal is
**0.8 ms**. That is the computation only — the protocol and the resident
process are the next step, and the end-to-end number is theirs to report.

**Evidence.** `test_project_preview.py` drives all of it through a real
FreeCADCmd: the no-baseline reply, a joint offset that moves a solved
placement to the value the parameter names (`swing` is declared at
[0, 0, 40] and the revolute joint puts it on the connector offset, so a run
that merely did not crash is distinguishable), a `part.box` parameter refused
by name, the memo holding steady across previews, and the same answer through
the worker's own entry point so `mode` is honoured where the request is read.
And the invariant the design rests on, asserted the strongest way available
rather than argued: the store's complete file list with sizes and mtimes is
snapshotted before a burst of previews and must be byte-identical after, with
nothing written beside the worker either.

### The resident worker and the `preview_params` op

**Decision.** cadexd owns one `CadexWarmWorker` per open project — a resident
`FreeCADCmd --safe-mode` out of the same content-addressed bundle
(ADR-052), spawned **lazily on the first preview**, and serving the new
`preview_params` read op.

```
preview_params
  args     ({"values": dict, "expected_revision": str}, {})
  response (frozenset({"placements", "revision", "previewable"}),
            frozenset({"reason"}))
```

`placements` is `{output_name: [16 floats]}` — flat arrays, so there is no
nested shape to pin and no `NESTED_RESPONSE_SPECS` entry.

**A `READ_OPS` member, not a `MODELING_OPS` one.** It writes nothing, and
queueing behind an in-flight modeling request is precisely the wanted
behaviour when a drag's preview meets the settle-time `set_params` behind it.
In `MODELING_OPS` the two would refuse each other instead — the shell's
client carries the same table and the same note, because that duplication is
the one place the two halves can silently disagree.

**Generation binding.** The worker holds one
`(source, api_contracts, assets_fingerprint)` generation, established by a
`load` frame that execs once at the *stored* parameter values and records the
definition fingerprints as the baseline. `write_script`, `edit_script`,
`set_params`, `rebuild`, `put_asset` and `open_project` kill it — free,
because the worker is stateless by contract, so the cost of being wrong is
one respawn. Implemented as a kill rather than a rebind: a killed worker
*cannot* answer with the previous generation's geometry, and "cannot" is the
only guarantee worth having here. The kill sits in `_lifecycle_response`,
which is what puts it on all four script-mutating handlers and, deliberately,
*not* on `open_project`'s restore path — that path re-runs the stored script
through `_run_lifecycle` directly and changes nothing.

**Bounds without a process per run.** A 5 s deadline then `SIGKILL` (a
preview that slow has already failed its purpose); cancel is a kill; a memory
ceiling sampled every 16 requests rather than during them, so the common path
pays nothing for it; and a respawn every 200 requests as a leak backstop that
needs no leak detector. `--safe-mode`, the closed environment allowlist, the
AST source policy and the settrace budget are all unchanged: this changes how
often a worker starts, not what a worker may do. The allowlist is now one
function (`worker_environment`) shared by both workers, because two copies of
it would eventually disagree about what "nothing" means.

**Every failure is a declined preview, never a failure envelope.** A stale
revision, an unknown parameter, a worker that will not start, a deadline, a
crash: all of them return `previewable: false` with a reason. An optimisation
that fails loudly is worse than one that fails quietly, because the shell
already has the correct answer in flight behind it.

**Measured over the protocol**, on the latency bar's own baseline part —
24 holes, a fillet, a mesh skin — now in a jointed assembly with a second
slider that drives motion rather than geometry, so both numbers are the same
model asked two ways:

| | dev tree | payload |
|---|---|---|
| accepting `set_params`, draft display | 0.636 s | 0.588 s |
| **preview, median** | **0.0337 s** | **0.0331 s** |
| first preview (spawn + generation load) | 0.305 s | 0.305 s |
| speedup | 18.9× | 17.8× |

Better than the 60–80 ms this was expected to land at, and the first preview
is paid once per drag rather than once per frame. The plain and draft medians
are unmoved (0.417 s / 0.469 s), which is the point: nothing about the
accepting path changed.

`cadexd_latency_integration.py` carries this as a third lane with its own bar
— median ≤ 0.10 s, a frame rate rather than a parity number, because 10 fps
is the floor below which "live" stops being an honest word for it.

**Where the remaining 33 ms is**, since it is worth naming before anyone
optimises further: the exec plus `Document.addObject` for the Assembly object
and its component links, rebuilt per preview. Keeping the candidate
`App::Document` alive between previews is where true real-time lives and
where every determinism guarantee gets hard; it would be its own ADR and its
own decision. 30 fps is a good place to stop and look at it.

**Evidence.** `test_preview_params_answers_a_pose_only_slider_over_the_protocol`
drives the whole thing through a real cadexd: a pose-only slider answered
with the placement the joint offset names, a second preview served by the
same resident worker, a geometry slider refused by name, a stale revision
declined, an ordinary `set_params` afterwards producing exactly what it
always did, and the generation killed by that `set_params` so the next
preview re-loads rather than answering from a model that no longer exists.
And the store snapshot, again at the protocol level this time: not one file
added, not one byte or mtime moved.

### The shell's preview dispatch

**Decision.** The preview gets its **own** dispatch in `cadex_backend`: at
most one request in flight, fired on a ~30 Hz pump, intermediate values
dropped, **never debounced**. The settle-time `set_params` (ADR-051's
coalescing pump) and the standard refine stay exactly as they are — the
preview rides in front of them, it does not replace them.

**Because a 33 ms engine behind a 150 ms debounce is still a 150 ms drag.**
Reusing `model._schedule_rebuild`'s timer would have thrown away the entire
win. `model._on_param_update` now calls both, in that order.

**Applying a preview does not go through hydration at all.**
`preview_params` returns `placements`, not a `display` block, so
`cadex_hydrate.apply_placements` sets `matrix_world` on the component
instances ADR-049 created and stops: no sidecar read, no buffer decode, no
mesh rebuild, no face-attribute rewrite, no GC pass. There is nothing to
hydrate, and that is not an optimisation but the definition of pose-only —
every mesh datablock in the collection is already the right one. Worth
stating plainly because the plan assumed otherwise: **ADR-051's
unchanged-geometry hydration skip is not what makes this work.** It remains
a modest win for repeated same-quality rebuilds and nothing more.

**Degrading cleanly is a requirement, not a nicety**, because most sliders
are not pose-only:

- on `previewable: false`, previews **latch off for the remainder of that
  parameter's drag**. The answer cannot change while the same slider is being
  dragged, so re-asking every 33 ms is pure waste.
- the latch is **per parameter**, and the set it latches on is the sliders
  that were actually moving when the refusal came — not every slider the
  script declares. Moving a different one is a different question and lifts
  it; so does the drag settling, which is also when the engine kills its
  generation.
- a preview failure **never reaches `model._last_error`**. It is an
  optimisation, and the debounced `set_params` behind it is the real answer;
  a panel that reported "not previewable" as a model error would be lying
  about a drag that is about to succeed.
- the pump skips a tick while an accepting run is in flight. The client
  serializes on one lock, so a preview issued behind a `set_params` would
  block for half a second and land after the answer it was trying to
  anticipate.

**Diffing against the accepted values, not against nothing.** "Which slider
moved" is resolved against the model's *effective* accepted values — stored
values over the specs' `num()` defaults, the same resolution `_bridge_params`
uses to seed the sliders. `state.values` alone is not it: a script that has
only ever been written carries no stored values at all, so every parameter
would read as changed, every refusal would latch every slider, and the latch
would never lift. That is exactly the bug the gate caught.

**Measured through the shell**, `--background`, engine from the bundle:
**5.6 ms** median preview against the gate's 0.496 s slider median. The
engine-only number is 31–34 ms on the heavier latency baseline; the gate's
model is smaller. Either way the 30 Hz pump, not the engine, is now the
binding constraint on how often the viewport moves.

**Evidence.** Two gate tests.
`test_a_pose_only_slider_previews_at_interactive_rate`: a 12-event burst
starts exactly one request, the reply poses the viewport, and it carries the
*newest* value — values are read when a request starts, not when it is
queued, the same trick that lets the drag pump coalesce without a queue.
`test_a_shape_slider_falls_back_to_set_params`: the refusal latches, names
`plate`, poses nothing, is not an error, stops re-asking on further drags of
the same slider, lifts when a different slider moves, and the debounced
`set_params` behind it still rebuilds the geometry the preview could not
describe — asserted on the plate's actual dimensions, with the motion
slider's value applied too.

## ADR-056 — Wires route themselves: `part.cable` (2026-07-27)

**Decision.** One new part operation, `part.cable(start, end, *, gauge_mm,
clearance_mm, avoid, slack, min_bend_radius_mm, cell_mm, label)`. It takes
two `(point, direction)` ports, searches a path between them that clears the
declared obstacles, and sweeps a round conductor along it. Output type
`solid`, one per wire. The search lives in a new pure-Python module,
`src/Mod/cadex/CadexRouting.py`, staged into the sandbox by filename like
every other worker module.

**Why an addition, in a tree whose policy is to remove more than it adds.**
The drone project (`wcv8.cadex`) assembles a frame plus nine placed
components and has no way to express the harness between them. The
alternative was Blender curves in the shell, and that is the wrong answer for
the reason ADR-030 deleted the local bpy modes: geometry authored in the
shell is not in the script, so it vanishes on rebuild and does not move when
a slider does. Everything else needed already existed — `part.bspline` is the
path, `part.circle` + `part.wire` + `part.sweep` is the gauge,
`cadex_hydrate.py` turns any output into a viewport row. What did not exist
was the search. This adds the search and nothing else: **no shell code and no
protocol change.** `CadexdProtocol.OP_ARG_SPECS` is untouched, so the op
table in `docs/INTEGRATION.md` and the ADR-027 response goldens are
unaffected.

**Why it is an engine op rather than a script-level helper.** The sandbox
traces every script line against a 400k operation budget and explicitly
declines to trace frames outside the script
(`cadex_project_worker.py`). A search written in the script burns budget per
node; the same search inside the worker costs one operation. That single fact
is what makes obstacle avoidance viable at all.

**Two shape decisions.** *One op returning a solid*, not `route` + `sweep`:
a route is not a thing a model wants to own — it is recomputed every rebuild
and never referred to — and splitting it would invite scripts to cache
waypoints, which go stale the moment a slider moves. *One output per wire*,
not a fused harness compound: each wire is a separate row in the model tree,
separately selectable and separately diagnosable, and fusing seven disjoint
solids buys nothing.

**Determinism is the hard requirement**, because `open_project` re-runs the
accepted script and asserts digest equality. The frontier pushes `(f, g,
cell)` so heap ties break on cost and then lexicographically on integer cell
index; neighbour offsets are a fixed sorted tuple; no step iterates a set or
a dict. Two fresh processes rebuilding the wired drone produce byte-identical
digests, and reopening the project is the end-to-end proof for free.

**`isInside` was the obvious occupancy test and the wrong one.** Measured
against the drone frame — 219 faces, fused and filleted — `Shape.isInside`
costs **3.3 ms per point**, because OCC builds a fresh solid classifier on
every call; batching the same query as a boolean against a vertex compound
only reaches 0.63 ms. The seven cables spent 40 s in it. Part obstacles are
therefore **tessellated once and their surfaces rasterised into the routing
lattice**: 0.10 s to tessellate, ~0.2 s to rasterise a corridor, and the
search itself is 0.02 s. Rasterising the *surface* rather than the volume is
sufficient — a closed shell sampled at half a cell leaves no gap a
26-connected step can cross — and it makes the clearance dilation mean the
right thing, since clearance is measured from a surface. End to end the
drone's seven cables went 268 s → 13 s, against a 7.9 s unwired baseline.

**Mesh obstacles are their bounding box.** An exact triangle test was not
worth a per-cell BVH for v1, and the modules a harness runs between — boards,
motors, packs — are box-shaped. The obstacle where this would be badly wrong
is a frame enclosing the whole model, and that is a `part` solid. Two
consequences the docstring states outright: pass a concave body as the part
solid it is, and **do not list the two components a cable lands on in its own
`avoid`** — a port sits on their surface, so the search would start inside an
obstacle. The drone's flight controller stays out of every list for a second
reason: its board is a square turned 45°, so its bounding box is half air.

**Ports are exempt, but only for the wire.** A port sits *on* a surface, so
its cells and its standoff stub are declared free — otherwise nothing routes.
That punches a channel through the obstacle's rasterised shell, so the search
is separately forbidden from expanding into stub cells: the exemption says
where the wire may be, not where the search may travel. Without that split a
route could wander inside the component it leaves from.

**Not reproducible, not routable.** `avoid` refuses a `mesh.decimate` tree on
the same grounds `part.shape_from_mesh` does (ADR-016, ADR-043): a
non-reproducible obstacle is a non-reproducible route, and the digest is
computed from the geometry.

**Consequences.** `CadexRouting.py` joins the project worker bundle, the
declared engine module set in `test_engine_purity_guardrails`, and the
installed script list; each of those fails loudly if missed.
`cadex_tests/test_cable_routing.py` drives the search against synthetic
occupancy grids — straight run, detour, exact reproducibility, sealed
corridor, budget, clearance, stub exemption, corner-cutting, slack
monotonicity — plus the argument contract for `part.cable`. `wcv8.cadex` is
wired for real: battery→FC, FC→ESP32, ESP32→range finder and four motor
leads that thread the duct notches, all seven measured at **zero**
intersection volume with the frame solid, and re-solving across the whole
`wheelbase` slider range. Selector-anchored ports — so a port rides the
geometry when the part changes, per ADR-029 — are deliberately out of scope;
ports are literals for now, and `resolve_pin` already returns `center_mm` and
`normal`, which is exactly a port.

**Cost that remains.** Seven searches per rebuild, ~0.75 s each on this
model. `build_part_shape`'s content-keyed memo (ADR-053) only helps when a
payload is byte-identical, and moving a slider moves the ports, so drags pay
full price. The lever if that becomes binding is a coarser default `cell_mm`
— the cost is cubic in the reciprocal — not baking waypoints into the script.

### Point pins: picking a port off an imported component

**Decision.** A second pick gesture, `mesh_agent.pick_point` ("Pin Point"),
beside the existing `pick_pin` ("Pin Face") in the chat header. It queues the
ray-cast hit and its surface normal — pushed back through the object's
placement into the output's own space — onto the next chat message, exactly
as a face pin does. Both share one eyedropper modal and one queue.

**Why.** ADR-056 claimed the pick→port loop already worked with no new code,
on the grounds that `resolve_pin` returns `center_mm` and `normal`, which is
a port. That is true and it is not enough: `cadex_pick.face_index_of_polygon`
refuses anything whose hydrated kind is not `brep` —

> Object flight_controller is not a cadex BREP output; pins resolve on BREP
> outputs only.

— and the gate asserts that refusal. A harness lands almost every port on an
*imported component*, which is a mesh output. So on the drone the loop
resolved nothing for thirteen of fourteen ports, and the claim was wrong.

**Why a point rather than mesh picking.** A face pin *names* something: it
resolves to a BREP face the engine can re-find, which is what makes it
survive a rebuild. A mesh output has no such thing to name — a triangle has
no stable identity, and inventing one would be exactly the index-shaped
reference ADR-029 deleted. But a port does not need a name. It needs a place
and a direction, both of which the ray-cast already computes and threw away.
So this resolves nothing, asks the engine nothing, and works on any hydrated
output. A point pin is a literal and goes stale if its component moves —
which is what the ports already are, and what ADR-056 scoped.

**A placement is undone, and not the way a point is.** The hit is in world
space, the script authors in the output's space: a point comes back as
`M^-1 p`, but a normal as `M^T n`. Using the inverse for both is correct for
a translation and silently backwards under rotation — most placements are
translations, so this would have shipped. The gate's placement fixture
rotates for that reason, and it caught it before the first run.

**Consequences.** `spaces.py` gains a second button and the pinned count
moves out of one button's label into its own, because the queue was always
shared. Three gate tests: a mesh output takes a point pin where a face pin is
refused, a rotated placement round-trips on both point and normal, and a
non-output is refused rather than pinned to a name the agent cannot act on.
The two-step gesture the user actually described — pick a point, then pick
*which cable end it belongs to* — is deliberately not built: binding a pick
to a position in script text is a design question, not a coding one, and the
point pin is what unblocks the loop meanwhile.

### The pick buttons never worked from their own button

**Decision.** The eyedropper modal no longer gates on the area it was
invoked from. It starts from anywhere, and the click resolves against the
3D viewport region under the *mouse* (`cadex_pick.viewport_region_at`).

**Why.** Both pins are launched from a button in the `CADEX_CHAT` header, so
`context.area` at invoke is the chat area, never `VIEW_3D` — and the first
thing `invoke` did was::

    if context.area is None or context.area.type != 'VIEW_3D':
        self.report({'WARNING'}, "Use the 3D viewport to pick")
        return {'CANCELLED'}

so the gesture cancelled the instant it started, reporting into the status
bar where it read as nothing happening. There is no keymap anywhere in
`mesh_agent`, so the button is the only way in and `pick_pin` had therefore
never worked from it since it was written; `pick_point` inherited the flaw
by sharing the modal. Found by using it, not by testing it.

**Why the gate missed it.** `test_pin_flow` calls `resolve_polygon`
directly. Every part of the pick was covered except the part that starts it.
The modal needs a real window and cannot run under `--background`, so what
is pinned now is the lookup it depends on: a pixel inside the viewport finds
its window region, one over either header finds nothing, and the bounds are
half-open.

**Two smaller fixes alongside.** A click that is not over a viewport keeps
the modal running rather than cancelling — which is also what absorbs the
release of the very click that started it, since that one lands on the
button. And `CADEX_CHAT` joins the redraw set, because the pinned count is
drawn in its header and a header does not repaint on its own.

## ADR-057 — Wires come in bundles: `part.bundle` (2026-07-27)

**Decision.** One new part operation, `part.bundle(connections, *, gauge_mm,
conductor, style, twist_pitch_mm, left_handed, spacing_mm, up, breakout_mm,
clearance_mm, avoid, slack, min_bend_radius_mm, cell_mm, label)`. It takes
one `(start_port, end_port)` pair **per conductor**, searches **one** route
for all of them, lays the conductors about that shared centreline — twisted
helically or flat side by side — and sweeps the one named by `conductor`.
Output type `solid`. The lay geometry lives in a new pure-Python module,
`src/Mod/cadex/CadexBundle.py`, staged into the sandbox by filename like
`CadexRouting.py` before it.

**Why an addition, in a tree whose policy is to remove more than it adds.**
ADR-056 gave the drone a harness of single wires, and a real harness has
almost none. A battery lead is a red/black pair, a brushless motor takes
three phases, an I2C run is four conductors. Modelled as N independent
`part.cable` calls those route independently, drift apart, cost N searches,
and do not look like the object. The alternative to adding an op was asking
the model to author the lay in the script — N splines with hand-computed
helical offsets — which is exactly the "waypoints baked into the script"
that ADR-056 forbids, and it would go stale the moment a port moved.

Nearly all of it is reuse: the corridor, the obstacle rasterisation, the
search, the spline fit, the sweep and the bend check are `part.cable`'s,
lifted into `_route_corridor` and `_sweep_conductor` in a first commit that
changed no numerics — proved by rebuilding `wcv8.cadex` to the same digest,
`1555d0d5…`. What is genuinely new is a frame along the shared centreline
and the offsets from it: arithmetic, no search, no kernel.

**One row per conductor, not a compound.** A compound publishes as one
`Part::Feature`, tessellates into one mesh with N disconnected islands, and
hydrates as **one** shell row; nothing records which solid a face belongs to,
and `part.subshape` can only pick a solid out of it by `near_point` or area.
Per-conductor rows keep every wire selectable, colourable and measurable, and
match ADR-056's own "one output per wire". Confirmed against a live document:
seven `part.bundle` calls publish seven `Part::Feature` rows.

**The lay radius is solved, not asserted — the plan's closed form was wrong.**
The obvious radius puts N circles of diameter `d` touching on a circle,
`R = (d/2)/sin(pi/N)`. That is the condition for two neighbours to touch
*within one cross-section*, and neighbouring helices do not reach their
closest approach within one cross-section. For phase offset `dphi` and axial
offset `u` the squared centre distance is

    f(u) = 2 R^2 (1 - cos(2*pi*u/P - dphi)) + u^2

and `f'(0) = -2 R^2 (2*pi/P) sin(dphi) < 0`, so `u = 0` is never the minimum.
Measured at the chord radius:

| N | gauge | pitch | closest approach | overlap |
|---|-------|-------|------------------|---------|
| 2 | 1.0   | 10    | 1.000            | none    |
| 3 | 1.0   | 8     | 0.971            | 0.029   |
| 4 | 1.0   | 10    | 0.950            | 0.050   |
| 6 | 1.2   | 15    | 1.096            | **0.104** |

Every `N >= 3` case interpenetrates, by up to 8.7% of the gauge — and two
solids overlapping by 0.1 mm still pass `isValid()` and still render, which
is the worst kind of wrong. `N = 2` is the one exact case, because antipodal
helices *do* pinch at `u = 0`; the twisted pair is free. So `bundle_radius`
bisects for the smallest radius at or above the chord radius that keeps every
pair a gauge apart, with fixed iteration counts so it stays a pure function
of its inputs. As `R` grows the minimum migrates to `u = P/N`, so a lay
exists **iff `twist_pitch_mm > len(connections) * gauge_mm`**; below that the
solve runs away and the op refuses with that floor named.

**A rotation-minimising frame, not Frenet.** Frenet's normal is defined by
the curvature vector, so it is undefined where the path is straight and
reverses at every inflection — and a routed centreline is near-straight runs
with S-bends around obstacles, so inflections are the normal case. Each one
would snap the whole bundle 180 degrees mid-run. The frame is carried by the
double-reflection method of Wang et al.: O(1) per sample, no trigonometry,
exactly reproducible. Measured on one S-bend, Frenet's normal flips three
times where the carried frame turns at most 2.26 degrees per sample, tracking
the path's own bending.

**`up` seeds the ribbon, it does not level it.** A flat lay spreads along
`tangent x up`, so the default `(0, 0, 1)` makes a ribbon lie flat rather
than stand on edge. That cross product has no direction where the run is
parallel to `up` — a vertical run, which is the single most common harness
geometry — so `up` is used once, to seed the frame, and the frame is carried
from there. Levelling pointwise instead would have to be guarded at every
sample and would still spin where the guard fired. It is also what a real
ribbon does: it carries its orientation along and twists as it bends.

**The ends are a blend, not a stub.** The first attempt gave each conductor a
stub from its pad to a stand-off and then jumped to its place in the lay.
That puts a 90-degree corner where the lateral move has no axial room; the
interpolating spline overshoots, and the swept circle around the overshoot
self-intersects into a solid that is closed, valid and **39% short on
volume**. Instead each conductor blends between its own pad and its lay
position over `breakout_mm` of arc, with a raised cosine whose derivative
vanishes at both ends, so it leaves the pad along the run and joins the lay
tangentially and there is no corner anywhere. The blend is exact at both
ends, so a conductor lands precisely on its pad.

**Stand-off and breakout are two different lengths.** The stand-off is how
far off the surface the search starts (`clearance + diameter/2`, as
`part.cable` computes it); the breakout is the arc the fan-out is spread
over, and wants to be much longer. Using one number for both pushes the
search anchors far past the pads, and on a short board-to-board hop the route
has to come back in — a hairpin that measured a 0.075 mm bend radius on the
drone's 5.8 mm battery lead.

**True Frenet in the sweep, contrary to expectation.** `makePipeShell`'s
corrected-Frenet mode (`isFrenet=False`) was the obvious choice for a spine
whose curvature dips through zero. Measured, it collapses helical spines: up
to **51% of the volume missing** on a six-way lay, still returning one closed
valid solid. True Frenet held every measured configuration to within 0.62%.
The section is a circle centred on the spine, so in principle the mode cannot
matter; it does, so the measurement decides and the test pins it.

**One search, by memo.** `_SHAPE_MEMO` is keyed on the whole payload and
`conductor` is part of it, so without a second memo each conductor would
re-route. `_BUNDLE_ROUTES` is keyed on the payload with `conductor` and
`label` stripped — a deny-list, because forgetting a future cosmetic field
costs one wasted search while forgetting a route-affecting one would return
the wrong wire. It is cleared in `reset_part_shape_memo` alongside
`_SHAPE_MEMO`: this holds a *route*, and a route leaking into another request
would place a wire against the previous request's obstacles under a
self-consistent digest. The memo is a cost saving, not a correctness
mechanism — the route is deterministic, so N unmemoised searches would
produce N identical routes.

**Refusals name the wire.** A harness declares many bundles, and a refusal
that does not say which one sends you reading every port literal in the
script. The bundle's label goes in the message, not only in `observed`.

**A hard bend floor at `gauge_mm/2`,** under any declared
`min_bend_radius_mm`. A conductor that doubles back tighter than its own
radius sweeps into a closed, valid, self-intersecting solid; this refuses it
instead. It is what caught both the corner and the hairpin above.

**No protocol change.** `CadexdProtocol.OP_ARG_SPECS` is untouched — a bundle
is a part operation inside the project script, not a new op on the wire — so
the ADR-027 response goldens and `docs/INTEGRATION.md`'s op table are
unaffected.

**Consequences.** `wcv8.cadex` is rewired: the battery lead is a twisted
pair, each motor takes three twisted phases, and both the FC→ESP32 and
ESP32→range-finder runs are four-way flat ribbons. 7 conductors become 22,
across the same 7 routes; outputs go from 21 to 36 and a full rebuild from
13.3 s to 17.0 s — the added cost is sweeps, not searches, which is what the
shared route was for. Reopening the project re-runs the script and matches
its digest, so the whole lay is deterministic end to end.

The rewire needed thinner gauges than the single wires it replaced (0.5 mm
phases, 0.4 mm ribbon conductors) because the corridor is now searched at the
bundle's outer diameter — the lay has to fit the gap, not one wire. That is
the honest answer rather than a special case in the op, and it is the same
trade a real harness makes.

**Found on the way, not fixed here: `CadexRouting._sag` folds a vertical
run.** Sag displaces interior waypoints along −Z regardless of the run's own
direction, so a run parallel to Z is displaced along its own axis and doubles
back — measured on a 60 mm vertical run at `slack=1.05`, the z sequence comes
back `0 → 4.28 → 2.99 → 55.73 → 60`. This is pre-existing and affects
`part.cable` identically, where it is silent because a cable only checks its
bend radius when the caller declares one. Fixing it changes `part.cable`
output and moves accepted project digests, so it needs its own ADR and is not
folded in here. `part.bundle` fails safe on it via the hard bend floor, and
the drone's battery pair declares `slack=1.0` for that reason.

## ADR-058 — Cadex installs like an application (2026-07-28)

**Decision.** Two changes so the product opens from Spotlight, Launchpad and
the Dock rather than from a build command:

1. `blenloader/intern/readfile.cc` resets `UserDef::app_template` on read to
   the **DNA default** instead of to the empty string.
2. `package/app/build_app.sh` gains `install` / `uninstall`, exposed as
   `pixi run install-app` / `pixi run uninstall-app`, which rsync the built
   `Cadex.app` into `/Applications`.

**Why the readfile change.** ADR-024 set the DNA default to `"Mesh"` so a new
user meets the chat-driven layout without finding it in a menu. It did not
work for anyone who had ever launched the shell before. Upstream's
`read_userdef` ends with

```c
/* Don't read the active app template, use the default one. */
user->app_template[0] = '\0';
```

— the comment says *use the default one* but the code hardcodes upstream's
default rather than reading it, so the DNA literal only ever reached a
profile with **no `userpref.blend` at all**. Measured before the fix, on this
machine's own profile: fresh profile → `[Mesh]`, existing profile → `[]`,
i.e. stock Blender, no `mesh_agent`, no Cadex top bar. Finder cannot pass
`--app-template`, so an installed bundle had no way to reach the product.

The edit takes the literal from the DNA member initializer
(`const UserDef userdef_default = {};`, the same pattern as
`space_file/filesel.cc:106`) rather than restating `"Mesh"` — ADR-024's
single source of truth survives. `--app-template default` still escapes to
stock Blender; verified.

**Cost: `docs/BLENDER-TREE.md` §2a is eight files, not seven.** That
invariant was worth breaking exactly once, for the file that makes ADR-024
true; it conflicts as a two-line replacement inside one function, which is
the cheap kind. `creator_args.cc` stays rejected for the reason ADR-024 gave.

**What `install-app` is and is not.** It is a *local* install. `pixi run app`
bundles a **staged** payload, so every Mach-O under
`Contents/Resources/cadex` resolves `@rpath` through
`<repo>/.pixi/envs/default/lib` and `<repo>/build/release/lib` — the bundle
carries its own `lib/` and never looks at it. The installed app therefore
reads its libraries out of the repository and stops modelling if the repo
moves. The command says so on every run. Making the bundle standalone is the
relocated-payload and notarization work already listed as open in
`docs/cadex-release-packaging.md`; nothing here changes that.

`install` refuses to `rsync --delete` into anything at the destination that
lacks a `Contents/Info.plist`, and `uninstall` refuses to remove it, so a
mistyped `CADEX_INSTALL_DIR` cannot eat a directory.

**Evidence.** `CADEX-BLENDER-GATE` green from the build tree and again from
`/Applications/Cadex.app` — `ok: true`, `engine_from_bundle: true`,
`startup_areas: [CADEX_CHAT, CADEX_PARAMS, VIEW_3D]`, 372/372 picks. A plain
launch of the installed bundle under a scrubbed environment reports
`app_template = Mesh` against the pre-existing profile. The bundle's ad-hoc
linker signature is unchanged by the copy (`codesign -v --deep` returns the
same message for the source bundle and the installed one) and no quarantine
attribute is set.

## ADR-059 — The app icon is the Cadex mark (2026-07-28)

**Decision.** `shell/release/darwin/Blender.app/Contents/Resources/cadex_icon.icns`
is regenerated from the logo the README ships, `cadex-logo-white.png`, by a
new `package/app/make_app_icon.py`.

**Why.** The icns in the tree was still the VibeCAD-era mark — the dark
rounded square with the blue/white letterforms — which the Stage C rebrand
(`9c0c7871`) missed because an icns is a binary and a grep for "vibecad"
cannot see inside one. It shipped as the Dock icon of every build, and the
`pixi run install-app` work (ADR-058) is what made that visible: an app you
launch from a build command is a path, an app you launch from the Dock is an
icon.

**`docs/images/cadex-mark.svg` is the same stale art** and is *not* the
source. It is still referenced by nothing in the product, so it is left in
place rather than half-fixed here; regenerating or deleting it is its own
change. The script's docstring says so, because that file is exactly what the
next person will reach for.

**The composition is not the bare logo.** A README mark sits on the page's
own background; a Dock icon is composited against wallpaper, so a
transparent black-on-nothing mark would disappear on a dark desktop. The
script puts the white mark on the shell's own `#0e1116` at Apple's icon grid
— an 824 px body with a 185 px corner radius inside a 1024 px canvas — which
also keeps the Dock silhouette the shape it already was. `--light` composes
`cadex-logo-black.png` on white instead; nothing else changes.

**Derived, not dropped in.** The point of the script is that the binary in
the tree is explainable and reproducible from a source we can read in a diff.
Rerun it when the logo changes.

**Consequences.** `CFBundleIconFile` already pointed at this filename and
`CFBundleIconName` is still absent (ADR-030), so no plist change: the install
step copies the new file and Launch Services picks it up. Verified by
extracting the icns back out of `/Applications/Cadex.app` after
`pixi run install-app`. No behaviour changes; `CADEX-BLENDER-GATE` is
unaffected and was not re-run for the icon alone.

## ADR-060 — The engine runs headless on Linux (2026-07-31)

**Decision.** Five changes, one pass: the engine now builds, tests, packages
and models on a headless Linux box.

1. `src/Mod/Assembly/JointObject.py` imports `Preferences` in its own
   `try/except ImportError`, not in the one guarding `pivy` and
   `SoSwitchMarker`.
2. `package/engine/build_engine_payload.sh` prunes `site-packages/pivy` and
   names `pivy` in its GUI-leak gate.
3. `pytest` is declared in `pixi.toml`. It never was.
4. A `setup-engine` task checks out the two submodules the engine compiles
   and nothing else.
5. `cadex_tests/test_headless_import_guardrails.py` pins the class of bug
   (1) is an instance of.

**Why — the same break three times, behind a gate that never ran.**
`src/Mod/Assembly/JointObject.py` has now broken the headless engine once per
GUI dependency it touches:

1. It imported Qt at module scope. The first payload the
   `CadexEnginePayloadSmoke` gate ever ran could not model at all —
   `No module named 'PySide'` — while every test in the source tree passed,
   because a development environment has Qt installed. Fixed with the
   `try: from PySide import QtCore` guard the file still carries; this is the
   episode `docs/cadex-release-packaging.md` cites for *"a source tree that
   passes proves nothing about a payload."*
2. **ADR-047.** `Preferences.py` imported `FreeCADGui` at module scope, so
   `import Preferences` raised headless, `JointObject`'s guard bound
   `Preferences = None`, and `solveIfAllowed()` died on `'NoneType' object
   has no attribute 'preferences'`. Fixed by deferring the GUI import in
   `Preferences.py` — i.e. in the importee.
3. **This one.** The *block* was never revisited, and it still imported
   `pivy` beside `Preferences`. The payload prunes `libCoin` (as it must;
   nothing headless draws) while carrying pivy, so `from pivy import coin`
   raised `ImportError` and reproduced (2) exactly, symptom for symptom.
   Every joint refused at `native_connector_frames`.

Three fixes, each aimed at whichever import happened to fail that time, and
the shape that produced all three went unaddressed.

This is not a Linux bug. `libCoin*` is pruned unconditionally on every
platform, so every payload ever staged has carried a pivy that cannot
import. It presented as a Linux bug because Linux is where the packaged gate
was first run to completion.

**Which is the more useful finding.** `test_cadexd_lifecycle.py` already
covers this — `JOINT_SCRIPT` exists precisely because ADR-047 taught us to
drive a joint over the protocol — and CI already runs it against the staged
payload. It has never once executed. Both CI jobs fail at the *preceding*
step, `Engine unit suite`, with `No module named pytest`, and every step
after it is skipped. The workflow has been red on every push and every
nightly since at least 2026-07-25. A gate that cannot be reached is not a
gate, and the engine job's value was entirely notional.

**The guardrail is on the block, not the module.** Fixing `Preferences.py`
did not generalise, because the hazard is structural: whatever a workbench
guards behind `ImportError`, it may not guard App-level code along with it.
The new test walks the `try` bodies (not the handlers — `Show/ShowUtils.py`
legitimately imports `FreeCAD` in its `except`) of every workbench the
payload carries, reading that list out of `keep_mods` in the packaging
script so a newly-carried workbench cannot escape the check. It reports one
violation against the pre-fix tree, at the exact line, and none against this
one.

**pivy is pruned for the FreeCADGui reason, not the disk-space reason.** 19 MB
is incidental. A binding whose native library has been deleted does not fail
to exist, it fails to *import*, and an `ImportError` is control flow — the
same sentence the script already carries about a surviving `FreeCADGui.so`.
The leak gate now refuses it, so pruning cannot be undone by an edit to one
`rm`.

**Consequences.** Verified on Ubuntu 24.04 / x86-64: `build-engine` green;
`pytest src/Mod/cadex/cadex_tests` 314 passed; `stage-engine` produces
`cadex-engine-0.0.0-linux-x64`; the packaged gate goes 4 failed → 6 passed.
End to end over raw NDJSON against the payload, a parametric bracket
publishes a BREP output whose detached artifact exports to AP214 STEP
(`Part.Shape.exportStep`) and STL, volume 14575.885 mm³ against 14575.9
computed by hand. macOS is untouched by (1) and (2) in behaviour but not in
effect — its payloads carried the same broken pivy, so its joints were
broken too and its gate was equally unreached. Nothing here fixes CI's
`app` job beyond letting it reach its own gates for the first time; what
those gates then say about macOS is not yet known.

**Not done, deliberately.** The payload copies only `bin lib Mod share`, so
`Ext/freecad` is absent and `init_applications` prints a
`ModuleNotFoundError: No module named 'freecad'` traceback on every cadexd
start. It is cosmetic — the addon namespace package has no user here, the
text goes to stderr, and `CadexdClient` discards stderr — and restoring a
directory to silence a message would be additive. Left as noise, recorded
here so the next person does not re-diagnose it.

## ADR-061 — Cadex has a headless CLI (2026-07-31)

**Decision.** A new top-level `cli/` and a `./cadex` shim: a **third client
of the cadexd protocol**, peer to the Blender shell, with no Blender, no
display and no shell code. Four subcommands over one project —
`cadex -p "<prompt>"`, `cadex params --set k=v`, `cadex script`,
`cadex export` — of which exactly one spends tokens. Documented in
`docs/CLI.md`; `cli/tests` is its suite.

**Why.** Cadex had one front end, macOS-only, and it needed a screen. The
engine underneath it never did: it is a headless NDJSON service, and ADR-060
made it build, test, package and model on a headless Linux box. The thing
the CLI adds is not "the shell without a window" — it is a **cost
asymmetry**. An expensive model turn authors a *parametric* script once;
after that a cheap loop sweeps its parameters and re-exports with no model
in the loop at all, and an external simulator (airflow, FEA, print-time)
feeds its numbers back. The expensive call happens only when the shape has
to change. That loop is not expressible through a GUI chat window, and it is
the reason to build this rather than to port the shell.

It is also the first thing that makes the protocol's second client cheap to
have. Phases 11 and 12 rest on the claim that either half can be replaced
behind an unchanged protocol; until now that claim had one caller and a test
harness. It now has two callers that share no code, and the CLI validates
every reply against `OP_RESPONSE_SPECS` as a hard error, so a drift shows up
as a third client failing rather than as a shell quietly coping.

**The licence boundary, which is a hard constraint and not a preference.**
`cli/` is engine-side and therefore `LGPL-2.1-or-later`; `shell/**` is
`GPL-2.0-or-later` (`docs/PROVENANCE.md` §1, §5). The shell solved four of
these problems already — `cadexd_client.py`, `backend.py`, `mcp_shim.py`,
`modes.py::CADEX_OVERLAY` — and **not one line of them is copied here**.
They were read as reference. Every equivalent derives instead from the LGPL
engine-side precedents that already existed for exactly these jobs:
`cadex_tests/cadexd_latency_integration.py` (the raw-NDJSON client, the
`CADEX_ENGINE_ROOT` manifest resolution) and
`cadex_tests/test_cadexd_lifecycle.py` (ready banner, events vs responses,
response-contract checking). The system prompt is written fresh, and says
different things: it is talking to an agent with no viewport.

**The tension, stated plainly: this is a second turn orchestration.** The
CLI drives the same Claude Code CLI the shell drives, with `--resume` for
continuity, `--strict-mcp-config`, `--tools ""`, and an MCP server relaying
to the engine — and it does so from its own code. There are now two of
those, and two is where drift starts. Three things bound it, and they were
chosen rather than fallen into:

1. **The tool contract is single-sourced.** Tool names *are* op names, and
   their input schemas are generated from `CadexdProtocol.OP_ARG_SPECS`. A
   tool cannot offer an argument the engine does not take, and adding an op
   argument adds it to both front ends by construction. The shell's
   friendlier names were a reasonable answer to a problem the CLI does not
   have (Blender's own vocabulary); a third vocabulary would have been a
   third thing to keep in sync.
2. **Neither front end states the xscript API.** Both paste
   `describe_api`'s live `instructions`, `program_schema` and
   `source_globals` into the prompt. The API has one source and it is the
   engine.
3. **What is duplicated is the cheap half.** Spawning `claude -p`, parsing
   stream-json, and persisting a session id are ~200 lines that will not
   move. What would have been expensive to duplicate — the protocol, the
   authoring contract, the tool surface — is not duplicated at all.

What is *not* claimed: that these two loops will stay identical. They will
not, and should not. The shell's agent can see its work and take a pin from
a click; this one is told, in the prompt, that it cannot, and is pointed at
`inspect scope=output` facts and the script's own stdout instead. Those are
different agents doing different jobs against one engine.

**`expected_revision` is injected rather than asked for.** The protocol
guards every mutation with the revision the caller believes is current. The
guard exists for concurrent writers; a CLI run has exactly one. So the
bridge fills it in from the last reply — **including refusals**, because a
rejected candidate still becomes the working revision, and tracking only
successes would make the retry after a rejection fail with
`STALE_PROGRAM_REVISION` for a reason unrelated to what the model got wrong.
The value used is surfaced in every tool result as `expected_revision_used`,
so the model can still see drift; it simply cannot fail on it. This deletes
an entire class of avoidable tool failures without weakening a guard that
was never protecting anything here.

**Process topology.** `claude` spawns MCP servers as its own children, so
some IPC is unavoidable. The parent owns the single `cadexd` child and a
unix-domain socket in a 0700 temp directory (plus a token); the MCP shim,
spawned by `claude`, relays down it. This is the shell's bridge shape
without the reason the shell needed it — there, `bpy` may only be touched
from Blender's main thread. Here it earns its keep differently: the parent
**observes every tool call**, which is what lets it print progress, know the
final revision without asking, and hold the display block the export reads.
A unix socket rather than the shell's localhost TCP, so the filesystem
enforces what the token asserts.

**Export is a subprocess, not a protocol op, and that is temporary.** The
engine already stages a detached BREP per output and hands back its path;
`export.py` runs a short `FreeCADCmd` job that reads it and calls
`exportStep` / `exportStl` / `exportBrep`. It is structured as one seam —
a plan of `(source, format, destination)` triples — so promoting it to an
`export_model` op is a local change. Two findings worth keeping:

- **STEP is not reproducible.** AP214 writes a wall-clock timestamp into
  `FILE_NAME`, so two exports of an identical model differ byte for byte
  across a second boundary. Pipelines must compare the engine's content
  `digest`, which the `--json` envelope reports for that reason. The BREP
  beside it *is* byte-stable, which is what makes the instability the
  format's and not the model's.
- **`FreeCADCmd -c <code>` has a trap.** The argument is `stat()`ed as a
  path before it is run as Python (`Application::processCmdLineFiles`), so
  any *component* of it longer than `NAME_MAX` — 255 bytes, and newlines do
  not delimit components — dies with a bare "Application unexpectedly
  terminated". The `pixi run cadexd` one-liner survives only because it
  contains slashes. Any real script must be written to a file and named as
  a file; this one is.

**`inspect` is bounded, and a CLI is not.** Worth writing down because it
bit during this work and will bite again. `open_project` returns the whole
`script` block; `inspect scope="script"` returns a *page* of it — mappings
50 keys at a time, and any value over 1 KiB replaced by a stub naming the
path to fetch it from. That is exactly right for an agent reading a page at
a time, and exactly wrong for `cadex script`, which has to print the file.
It fails in the worst possible way: a short script comes back verbatim and
passes every test, and a long one comes back as
`{"type": "string", "characters": 1574, "inspect_path": "/source"}` —
printed, cheerfully, as the script. Every read in `session.py` now follows
the pointer paths and the `next_offset` chain to the end, and a test builds
a 7 KB script with 60 parameters (over both caps) to keep it that way.
Nothing in the engine changed; the paging was doing its job.

**Consequences.** Verified on Ubuntu 24.04 / x86-64 against the dev-tree
engine: `pytest cli/tests` 76 passed; `pytest src/Mod/cadex/cadex_tests`
314 passed, unchanged; the packaged gate
(`CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-linux-x64 pytest
.../test_cadexd_lifecycle.py`) 6 passed, and the CLI suite passes against
that payload too — the same script produces the same digest through the
payload as through the dev tree. End to end, `cadex -p "a 40x25x15 mm bracket with a
6 mm bore…"` produced a parametric script on the first write, verified
itself through `inspect scope=output` (volume 14575.88 mm³ against
15000 − π·3²·15, and 7 faces — six planes and a cylinder, so the bore went
through), and wrote STEP and STL. `cadex params --set` then moved the digest
with no `claude` process spawned at all. `--resume` continued the
conversation, and the second turn reached for `edit_script` rather than
rewriting — it had the first turn's script in context — and added a new
fillet parameter to it. Forcing a stale session id degraded to a fresh
conversation with a note in the report, and still did the work.

Nothing in `src/` or `shell/` changed. The protocol is untouched —
`OP_ARG_SPECS`, the ADR-027 goldens and `docs/INTEGRATION.md`'s op table are
all unmodified, which is the point: a third client that needed the contract
widened would have been evidence against the contract.

**The suite is wired into CI in the same commit**, in both jobs of
`cadex-app.yml`, after the engine build — because half of it skips without
one, and a suite that skips silently is the failure ADR-060 has just
finished writing up. The Linux job runs it twice, build tree and staged
payload. The macOS job is the first time any of this will have run on
macOS at all; if something there is wrong, that job is where it surfaces,
which is the point of putting it there rather than asserting it works.

**`docs/VISION.md` moved, and that is worth flagging rather than burying.**
Its non-goals said "one shell … one model loop" and "no second model loop".
A second front end is a real amendment to that, so the bullet now names the
CLI as a deliberate exception and says what earns it — interactive design
and batch design are different jobs — while the model-loop non-goal is
narrowed to what still holds, which is that there is no second *provider*
stack. If the owner disagrees with the amendment, this ADR and that bullet
are the two places to reverse, and `cli/` is one directory to delete.

**Out of scope, deliberately.** `export_model` as a protocol op;
`resolve_pin` and picking; offscreen rendering so the agent can see its
work; shipping the CLI inside the engine payload; Windows.
