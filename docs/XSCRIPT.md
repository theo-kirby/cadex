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

### Naming geometry: selectors, not indices `[Phase 10b, ADR-029]`

Five part ops — `subshape`, `defeature`, `fillet`, `chamfer`, `thicken` —
choose subshapes of a shape. They take a **geometric selector**, never an
ordinal:

```python
drilled = part.cut(part.box(40, 30, 10), holes)

rounded = part.fillet(drilled, 0.5,
    edges={"geometry_type": "Circle", "radius": 3.0, "expected_count": 8})
healed  = part.defeature(drilled,
    {"geometry_type": "Cylinder", "radius": 3.0, "expected_count": 4})
top     = part.subshape(drilled, "face", {"normal": [0, 0, 1]})
cup     = part.thicken(part.box(20, 20, 10),
    {"normal": [0, 0, 1], "expected_count": 1}, -1.5)
```

`fillet` and `chamfer` also accept `edges="all"`. Everything else must be a
selector; `subshape` fixes `expected_count` to 1.

**Why the index form is gone.** It named a position in the kernel's
`TopExp::MapShapes` enumeration. ADR-028 proved that ordering is
*reproducible*; it is not *stable across edits*. Any parameter change that
alters topology renumbers every subshape after it, so a saved `edges=[3, 7]`
keeps validating and silently starts filleting different edges. A selector
either keeps meaning the same thing or fails loudly.

Selector keys (the closed set — an unrecognised key is rejected rather than
ignored, because a typo would otherwise widen the match):

| key | matches |
|---|---|
| `expected_count` | **required** — the declared cardinality; a mismatch fails |
| `geometry_type` | `Plane`, `Cylinder`, `Sphere`, `Toroid`, `Line`, `Circle`, … |
| `normal` / `direction` | face normal / edge tangent, within `normal_tolerance_degrees` / `direction_tolerance_degrees` (default 1.0) |
| `radius` | circular edges **and** cylindrical/spherical faces, within `radius_tolerance` (default 1e-6) |
| `min_area` / `max_area` / `min_length` / `max_length` | size bands |
| `near_point` | centre of mass within `max_distance` (default 1e-6) |

This is the same vocabulary `resolve_pin` speaks, so a pin captured from a
click and an argument written into the script name geometry identically
(`CadexSubshapeQuery.py`). When a selector fails, the envelope carries
`expected_count`, `actual_count` and the full `available` list, so the next
attempt is a re-query rather than a guess.

### Lifecycle tools

The tool surface the AI sees is exactly four operations
(`PROJECT_LIFECYCLE_OPERATIONS` in `CadexScriptedDomains.py`, pinned by
`cadex_tests/test_project_tool_surface.py`; ADR-013). They reach the engine
as cadexd ops of the same name (`docs/INTEGRATION.md`), served to Claude
Code over MCP by the shell:

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
`object`, `script`, `api`, `image` — `script` pages the source and reports
specs/values, revisions, accepted contract + digest, and the latest
candidate). There was a sixth scope, `selection`; it read the Qt shell's
selection and died with it (ADR-021), and the engine rejects it.

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
document** (and the headless rebuild driver); the shell receives the
accepted artifacts as a `display` block and draws them however it likes
(the Blender shell hydrates tessellation + ID maps into its scene).
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

The engine's half is `set_params`: a values-only patch, guarded by the
working revision, that re-runs the script without touching source. It is the
same lifecycle the assistant drives — there is no faster private path, and
no AI turn.

The shell's half is `scene.mesh_params`, a PropertyGroup registered from the
engine's `param_specs` (`cadex_backend._bridge_params`). A drag debounces
150 ms (`model._schedule_rebuild`), sends one `set_params` with a `draft`
tessellation preset, and schedules a background `standard` refine at rest.
A failed rebuild leaves the accepted geometry untouched.

*(ADR-014's `CadexParametersPanel.py` implemented this in the Qt shell and
was deleted with it in Phase 7, ADR-021. The contract it committed
through — `set_params` plus the revision guard — is unchanged, which is why
the shell swap did not touch the engine.)*

### Reference pins

`CadexReferenceContracts.py`: a click in the viewport becomes `@face-2` on
the next chat message. A pin carries the shared handle, owning object,
subelement hint, and a **geometric fingerprint** (center of mass,
direction/normal/radius/length). The fingerprint is authoritative: when the
revision has moved since capture, the pin is re-resolved by fingerprint
search rather than trusting the stored subelement name — so pins survive
rebuilds that churn object names.

Pins are the *chat* vocabulary. Scripts do not use them: since ADR-029 a
script argument names geometry with a **selector** (above), resolved through
the same `CadexSubshapeQuery.py` vocabulary. Click and script therefore mean
the same thing by "that face" — but only the selector is durable in a saved
script, which is the point of the split. Nothing in the shell yet *writes* a
selector into a script from a click; that round trip is half built
(`docs/ROADMAP.md` Phase 10b).

---

## Part II — Direction

- **Incremental re-execution**: today every mutation re-runs the whole
  script (one worker attempt). Cached per-region revisions keyed by content
  hash are a possible optimization; the revision machinery points the way.
- **Sub-modules**: whether large projects split into importable sub-modules
  under the project root, or stay one flat script.
- **Interactive mesh editing**: the Phase 4 `mesh` domain is deliberately
  minimal (tessellate/import/boolean/decimate), and *stays* that way for now.
  The plan used to be that interactive editing would arrive via BMesh in the
  Blender shell. It has not, and the route narrowed rather than widened:
  ADR-030 deleted the local bpy modes, which were the only code in the shell
  that authored geometry with BMesh. Editing a mesh interactively would now
  mean either a new engine op or re-opening a second authoring path — and the
  second is a direct contradiction of "nothing happens outside the script".
  Unscheduled, and a decision rather than an oversight.

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
