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
recorded instead of history — `/Users/theo/mesh` @ `ac5af55948d` (branch
`mesh-main`), plus one uncommitted working-tree change to
`source/creator/CMakeLists.txt`. `/Users/theo/mesh` is kept as a read-only
archive.

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

Shell build from a cold build tree: 12 min 53 s for 8,122 targets. Fresh
`git clone` of this repository: 9 s, 2.2 GB working tree.
