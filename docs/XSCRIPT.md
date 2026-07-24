# XSCRIPT.md — The Scripting Model

Verified against source: 2026-07-24

xscript is the single scripted modeling engine: the AI writes declarative
Python programs; programs run in sandboxed headless workers; only validated
results reach the live document. This document has two halves — **what runs
today** (per-domain programs, `[VibeCAD-era]`) and **the target** (one
project script, `[Cadex-new]`, Phase 2 in `docs/ROADMAP.md`). Keep them
straight: the target is a product decision (`docs/DECISIONS.md`), not yet
code.

---

## Part I — Today: per-domain programs `[VibeCAD-era]`

### Programs and schema

- A program belongs to exactly one domain (`partdesign`, `sketcher`, `part`,
  `assembly`) and lives in the project store:
  `<project>/xscript/<domain>/<program_id>/program.json` plus source and
  revision artifacts (`docs/ARCHITECTURE.md` §3, project store).
- Manifest schema: `cadex-xscript-program-v2`
  (`XSCRIPT_PROGRAM_SCHEMA`, `src/Mod/cadex/CadexScriptedDomains.py:24-27`).
- Program source receives the domain API as the global `x`
  (`XScriptWorkbenchPack.api_global`, `CadexScriptedDomains.py:140`); the
  per-domain APIs are `src/Mod/cadex/cadex_<domain>_api.py`.
- Each program declares named outputs; published objects are tagged with
  `CadexXScriptProgramId/Domain/Workbench/Revision/OutputName` properties so
  ownership is recoverable from the document alone.

### Lifecycle tools

`LIFECYCLE_OPERATIONS` (`CadexScriptedDomains.py:74`) defines eight
operations: `describe_api`, `inspect_program`, `create_program`,
`edit_source`, `set_inputs`, `set_parameter_controls`,
`reconfigure_program`, `delete_program`. The provider-facing mutation
surface per domain is

```
xscript.<domain>.create_program        author a new program (source + inputs + outputs)
xscript.<domain>.edit_source           targeted source edit; whole source re-validated
xscript.<domain>.set_inputs            change input values; re-run without touching source
xscript.<domain>.set_parameter_controls  declare which inputs surface as sliders
xscript.<domain>.reconfigure_program   rename/re-declare outputs, references
xscript.<domain>.delete_program        delete program + owned objects
```

(pinned exactly in
`src/Mod/cadex/cadex_tests/test_tool_surface_guardrails.py:605`), while
reads go through the bounded **`core.inspect`** tool
(`src/Mod/cadex/CadexInspection.py`) — API descriptions, program state,
document inventory, solver diagnostics, all size-capped.

### Sandbox rules

Source is validated before any worker runs (AST policy in
`CadexScriptedRuntime.py` / `CadexScriptedDomains.py`):

- Blocked names include `__import__`, `eval`, `exec`, `compile`,
  `breakpoint`, `globals`, `help`, … (`_BLOCKED_NAMES`,
  `CadexScriptedDomains.py:4082`); no dunder access; size and syntax limits;
  NUL bytes and unsafe project-relative paths rejected.
- Violations return `SOURCE_POLICY_VIOLATION` with offending line numbers —
  structured failure payloads, not exceptions.

### Worker isolation

- One attempt = one windowless `FreeCADCmd --safe-mode -c …` subprocess
  (`CadexScriptedRuntime.py:2163`, runner in `CadexScriptedProcess.py`).
- Attempts are self-contained: only the domain's own bundle files are staged
  (`_DOMAIN_WORKER_BUNDLES`, `CadexScriptedRuntime.py:65`) so a program
  cannot reach another domain's implementation.
- Hard bounds from preferences (`ScriptedTimeoutSeconds`,
  `ScriptedMemoryLimitMB`); a parent-side watchdog kills over-budget workers
  and reports `MEMORY_LIMIT_EXCEEDED` with observed usage.
- The worker produces **detached** results (BREP bytes, meshes, records) on
  the `cadex-xscript-domain-worker-v2` wire schema; it never touches the
  live document.

### Publication, ownership, revisions

- The publisher validates candidates (including BREP checks via
  `CadexGeometryWorker`) and applies them under a document transaction;
  rollback restores accepted state explicitly when FreeCAD's transaction
  rollback is incomplete.
- Revisions are content-addressed: hashes are stable, ignore parameter key
  order, and change with every hashed field; stale artifacts are rejected
  (`MODEL_ARTIFACT_REVISION_MISMATCH`).
- Output identity is durable: an output keeps its object across edits when
  unchanged; removed outputs' identities are never recycled.

### The slider path

`src/Mod/cadex/CadexParametersPanel.py`: inputs declared via
`set_parameter_controls` render as sliders; a drag calls the same
`set_inputs` lifecycle path directly — **no provider turn** — debounced
600 ms. This is the seed of the product's "parameters without the AI" loop.

### Reference pins

`src/Mod/cadex/CadexReferenceContracts.py`: chat and programs refer to
geometry as `@edge-1` / `@face-2`. A pin carries the shared handle, owning
object, subelement hint, and a **geometric fingerprint** (center of mass,
direction/normal/radius/length). The fingerprint is authoritative: when the
document revision has moved since capture, the pin is re-resolved by
fingerprint search (e.g. `partdesign.find_subelements`) rather than trusting
the stored subelement name.

---

## Part II — Target: one project script `[Cadex-new — not yet built]`

Decision (`docs/DECISIONS.md`): the product-level artifact is **one
top-level project script**, `model.py`-style, as prototyped in the mesh
repo's `mesh_agent` (`docs/BLENDER.md`).

- **One script is the whole truth.** It composes the domain APIs (partdesign
  + sketcher + part + assembly, later mesh) in a single readable program.
  The user can open it, read it, and diff it. Nothing exists outside it.
- **Project-level parameters** declared at the top of the script (compare
  `mesh_model.params()`), bound to sliders; per-program
  `set_parameter_controls` folds into this.
- **Document as cache.** The FreeCAD document (later the Blender scene) is a
  rebuildable artifact: a deterministic headless rebuild command re-runs the
  script from scratch and a **content digest** over the produced geometry
  must match the live document. CI test: delete document → rebuild → digest
  matches (Phase 2 exit criterion).
- **Publisher lint** rejects untagged objects; an orphan GC removes objects
  whose owning script region is gone.
- **Pins survive rebuilds** via the existing fingerprint contracts — pins
  bind to fingerprints, not to object names that a rebuild would churn.
- The multi-program runtime may remain **internally** as a staging detail
  (per-domain workers executing regions of the one script), but no
  program-level concept stays user-visible.

### Open questions

- Composition mechanism for assemblies-of-parts within one script (flat
  script vs importable sub-modules under the project root).
- Incremental re-execution: whole-script re-run per slider tick vs cached
  per-region revisions keyed by content hash (today's revision machinery
  points the way).
- Whether `edit_source` survives as a line-targeted edit tool on the one
  script or the AI always rewrites whole script sections.

---

## Historical note

The VibeCAD-era verification record for the retired multi-engine runtime
(build123d/OpenSCAD, 18 domains) is preserved at
`docs/history/RUNTIME_VERIFICATION.md`. Still-current facts from it —
structured failure envelopes, transactional parity, resource budgets,
revision integrity — are folded into Part I above and enforced by
`src/Mod/cadex/cadex_tests/`.
