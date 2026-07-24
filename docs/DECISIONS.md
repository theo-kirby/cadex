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
