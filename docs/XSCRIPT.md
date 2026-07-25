# XSCRIPT.md — The Scripting Model

Verified against source: 2026-07-25

xscript is the single scripted modeling engine: the AI writes ONE
declarative Python project script; the script runs in a sandboxed headless
worker; only validated results reach the live document. The one-script
system below landed in Phase 2 (`docs/ROADMAP.md`, ADR-011..014) and
replaced the VibeCAD-era per-domain multi-program surface `[Cadex-new]`.

---

## Part I — One project script

### THE script and its store

- A project has exactly one script: `<project>/script.py`. It composes all
  five capability domains and is the sole source of truth — the user can
  open it, read it, and diff it; nothing model-shaped exists outside it.
  Mesh assets the script imports live under `<project>/assets/` (flat,
  `.stl`/`.obj`/`.ply`).
- Sidecar state: `<project>/script.json` (schema `cadex-project-script-v1`,
  `CadexProject.py:CadexProjectScriptStore`) — cached `param_specs`,
  `param_values`, working/accepted revision, accepted contract (output
  names/types/domains), `accepted_digest`, latest candidate/failure.
  Writes are atomic; unknown fields are rejected.
- Execution artifacts live under `<project>/script_artifacts/<revision>/`.
- Revision = `project_script_revision` over `{schema, domain: "project",
  source, param_specs, param_values}` (`CadexScriptedDomains.py`) —
  content-addressed, key-order independent. Every mutation tool carries an
  `expected_revision` guard; a mismatch returns `STALE_PROGRAM_REVISION`
  with the observed current revision.

### Script vocabulary

The exec namespace carries the five domain APIs plus the parameter
vocabulary (`cadex_project_api.py`, `cadex_project_worker.py`):

```python
p = params(width=num(100, unit="mm", min=10, max=500, step=1, label="Width"))

profile = sketcher.sketch(...)           # sketcher API
plate   = part.box(p.width, 20, 5)       # part API
body    = partdesign.body(...)           # partdesign API (sketcher/part co-staged)
hull    = mesh.from_shape(plate)         # mesh API (tessellate/import/boolean/decimate)
base    = assembly.component(plate, grounded=True)
asm     = assembly.assembly([base, ...])

result = {"plate": plate, "hull": hull, "asm": asm}  # named outputs, by domain
```

- `params(...)` may be called at most once; `num(...)` declares one numeric
  control (`default`, optional `min`/`max`/`step`, `unit`/`label`/
  `description` — the `CONTROL_FIELDS` vocabulary). Collected specs are
  cached in `script.json`; **values** live there too and are patched by
  `set_params` without touching source.
- `assembly.component()` accepts same-script part/partdesign values: the
  worker records the source payload under a deterministic inline token
  (`document_uid: "xscript-project"`) and requires the value to ALSO be a
  declared output, so publication can bind each live component to a
  published stable object. Cross-document component references are retired;
  v0.0.1 assemblies are rigid, same-script solids (ADR-011).
- `mesh.from_shape()` tessellates a same-script part value (`Mod/MeshPart`);
  `mesh.import_file()` reads one flat asset file; `mesh.union`/`difference`/
  `intersection` and `mesh.decimate` run on the native mesh kernel. Every
  mesh output is rebuilt in canonical vertex/facet order (booleans
  immediately, all outputs before export), and the digest identifies a mesh
  by its exact sorted vertex set (`geometry_sha256`) — the native set
  operations return run-dependent orderings and occasionally re-triangulate
  coplanar regions differently for identical geometry. `decimate` is
  approximating (run-dependent result), so decimate trees are
  digest-identified by their canonical definition instead (ADR-016).
- Outputs are evaluated per domain in fixed order sketcher → part →
  partdesign → mesh → assembly, reusing the per-domain evaluators and
  serializers.

### Lifecycle tools

The provider-facing surface is exactly four tools
(`PROJECT_LIFECYCLE_OPERATIONS`, pinned by
`cadex_tests/test_project_tool_surface.py`; ADR-013):

```
xscript.project.describe_api   composed API description for all domains
xscript.project.write_script   whole-script rewrite
xscript.project.edit_script    unique-match find/replace; whole source re-validated
xscript.project.set_params     values-only patch; re-run without touching source
```

The dissolved per-domain operations (`create_program`, `edit_source`,
`set_inputs`, `set_parameter_controls`, `reconfigure_program`,
`delete_program`, `inspect_program`) stay gone — the guardrail test
asserts no registered tool may carry them again. Reads go through the
bounded **`core.inspect`** tool (`CadexInspection.py`; scopes `document`,
`selection`, `object`, `script`, `api`, `image` — `script` pages the
source and reports specs/values, revisions, accepted contract + digest,
and the latest candidate).

### Sandbox rules

Source is validated before any worker runs (AST policy in
`CadexScriptedRuntime.py` / `CadexScriptedDomains.py`):

- Blocked names include `__import__`, `eval`, `exec`, `compile`,
  `breakpoint`, `globals`, `help`, … (`_BLOCKED_NAMES`); no dunder access;
  size and syntax limits; NUL bytes and unsafe project-relative paths
  rejected.
- Violations return `SOURCE_POLICY_VIOLATION` with offending line numbers —
  structured failure payloads, not exceptions.

### Worker isolation

- One attempt = one windowless `FreeCADCmd --safe-mode -c …` subprocess
  (runner in `CadexScriptedProcess.py`). The project bundle stages all five
  `cadex_<domain>_{api,worker}.py` modules with entry
  `cadex_project_worker.py` (`_DOMAIN_WORKER_BUNDLES["project"]`,
  `CadexScriptedRuntime.py`), plus the project's flat mesh `assets/`
  directory (bounded: 64 files / 128 MB, known suffixes only).
- Hard bounds from preferences (`ScriptedTimeoutSeconds`,
  `ScriptedMemoryLimitMB`); a parent-side watchdog kills over-budget
  workers and reports `MEMORY_LIMIT_EXCEEDED` with observed usage.
- The worker executes the script ONCE, evaluates outputs per domain, and
  produces **detached** results (BREP and mesh artifacts, records, collected
  `param_specs`, per-output validations, the content digest) on the
  `cadex-xscript-project-worker-v1` wire schema; it never touches the live
  document.

### Publication, ownership, lint, GC

Since Phase 5 (ADR-017/018) publication runs inside **cadexd's ephemeral
document** (and the headless rebuild driver) — the Qt shell hydrates the
accepted artifacts into the document of record as tagged display objects
(`CadexShellHydration.py`, one transaction, contract-driven GC).
`publish_project_candidate` (`CadexScriptedDomainPublication.py`) applies
one validated candidate under **ONE** document transaction — one undo step:

- Per-domain sub-publishes run through the existing domain publishers with
  `manage_transaction=False` (the project publisher owns the transaction
  and runs the document-revision guard once, before opening it).
- Inline assembly source tokens are rewritten to the live object names
  published earlier in the same pass.
- Published objects are tagged
  `CadexXScriptProgramId/Domain/Workbench/Revision/OutputName`; ownership
  is recoverable from the document alone (`CadexScriptedOwnership.py`,
  closure over Group+OutList).
- **Lint**: any document object outside the owned closure aborts the
  transaction with `PUBLICATION_UNTAGGED_OBJECT` (ADR-012).
- **GC**: owned objects whose outputs left the accepted contract are
  deleted in the same transaction and recorded in the result.
- Output identity is durable: an output keeps its object across edits when
  unchanged; removed outputs' identities are never recycled.

### Digest and headless rebuild

- **Content digest** (D8): SHA-256 over the name-sorted output entries
  `{output_name, domain, output_type,
  shape_sha256|mesh_sha256|payload_sha256, placement (rounded 1e-9)}`,
  schema `cadex-project-digest-v1`, computed
  worker-side from serialized artifacts; recorded as `accepted_digest` on
  accept. `CadexDigest.py:document_digest` recomputes a diagnostic digest
  from the live tagged objects (schema `cadex-document-digest-v1`; a
  different quantity — do not compare across schemas).
- **Headless rebuild** (D9): `cadex_rebuild.py` re-runs THE script into a
  fresh document under FreeCADCmd and compares digests
  (`pixi run rebuild <project_root>`; exit 0 match / 2 mismatch / 1
  failure).
- **CI** (Phase 2 exit criterion): `cadex_tests/test_project_rebuild.py`
  (ctest `CadexProjectRebuildDigest`) seeds a multi-domain project, accepts
  it, deletes the document, rebuilds twice, and asserts
  rebuild-vs-accepted AND rebuild-vs-rebuild digest equality.

### The slider path

`CadexParametersPanel.py` (ADR-014): the panel renders the script's
declared specs as sliders (declaration order; declared fields win, missing
bounds get a value-bracketing band). A drag commits through
`xscript.project.set_params` with the working-revision guard — the same
rebuild path the assistant uses, debounced 600 ms, **no provider turn**. A
failed rebuild reverts the row; accepted live geometry is untouched.

### Reference pins

`CadexReferenceContracts.py`: chat and scripts refer to geometry as
`@edge-1` / `@face-2`. A pin carries the shared handle, owning object,
subelement hint, and a **geometric fingerprint** (center of mass,
direction/normal/radius/length). The fingerprint is authoritative: when
the document revision has moved since capture, the pin is re-resolved by
fingerprint search rather than trusting the stored subelement name — so
pins survive rebuilds that churn object names.

---

## Part II — Direction

- **Incremental re-execution**: today every mutation re-runs the whole
  script (one worker attempt). Cached per-region revisions keyed by content
  hash are a possible optimization; the revision machinery points the way.
- **Sub-modules**: whether large projects split into importable sub-modules
  under the project root, or stay one flat script.
- **Interactive mesh editing**: the Phase 4 `mesh` domain is deliberately
  minimal (tessellate/import/boolean/decimate). Interactive mesh editing
  waits for BMesh in the Blender shell (`docs/BLENDER.md`,
  `docs/INTEGRATION.md`).

---

## Historical note

The VibeCAD-era per-domain multi-program surface (eight lifecycle
operations × four domains, program manifests `cadex-xscript-program-v2`)
was dissolved by the Phase 2.4 tool-surface swap (ADR-013); existing v2
program stores were not migrated (ADR-011 — conversations preserved,
scripts start empty). The verification record for the still-earlier
multi-engine runtime is preserved at
`docs/history/RUNTIME_VERIFICATION.md`. Still-current facts — structured
failure envelopes, transactional parity, resource budgets, revision
integrity — are enforced by `src/Mod/cadex/cadex_tests/`.
