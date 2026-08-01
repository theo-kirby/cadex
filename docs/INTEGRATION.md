# INTEGRATION.md — The Process Contract

Verified against source: 2026-08-01

**This document is the contract between the two halves of the product.**
They live in one repository (ADR-030) and in two processes, under two
licences, and neither is written against the other's source — both are
written against what is written here.

**One repository makes this document more load-bearing, not less.** When the
shell lived elsewhere, distance enforced the boundary; now nothing does
except discipline and the tests below. The reason to keep the boundary
sharp is not tidiness — it is that ROADMAP Phases 11 and 12 replace the
engine and the shell *independently, behind this protocol*. Every shortcut
across it (a direct import, a shared file, a peeked-at internal) is a
Phase 11 blocker bought for an afternoon's convenience. Do not take one.

Three things are therefore enforced by tests rather than trusted:

- the **protocol op table** is asserted equal to
  `CadexdProtocol.OP_ARG_SPECS` by
  `cadex_tests/test_engine_purity_guardrails.py`. Nothing else notices when
  the prose and the code disagree, and a shell calling an op the engine does
  not serve fails at the user, not at a test.
- the **response shapes** are pinned by golden shape-only fixtures per op
  (`cadex_tests/test_response_schemas.py`, ADR-027). `OP_ARG_SPECS` pins
  requests; the shell reads ~50 response keys, and without these nothing
  asserted that half.
- the **engine discovery manifest** (`cadex-engine.json`, ADR-020) is
  validated by ctest `CadexEnginePayloadSmoke`, and by the `app` job's
  bundle check in `.github/workflows/cadex-app.yml`.

The two halves:

- **the engine** (repo root) — FreeCAD fork; the xscript engine, headless.
  Builds `FreeCADCmd` and `CadexGeometryWorker` and **no application**
  (ADR-021/022). LGPL-2.1+.
- **the shell** (`shell/`) — Blender fork; the product UI
  (`docs/BLENDER.md`). Carries the engine payload inside its bundle.
  GPL-2.0+.

- **vibecad** — parent fork; historical reference only (teardown history on
  its `cadex-teardown` branch, at `github.com/theo-kirby/vibecad`).
  **mesh** — the shell's former home; its pre-merge history is at
  `github.com/theo-kirby/mesh` (branch `mesh-main`). Neither has a local
  working copy any more: both were deleted 2026-07-25, remotes verified
  first.

**There is now a third client of this contract**: `cli/`, the headless CLI
(`docs/CLI.md`, ADR-061). It is not a half of the product and it changes
nothing here — it was built against this document without widening it, which
is the strongest evidence the protocol has yet produced for the Phase 11/12
claim that either half is replaceable behind it. Two consequences worth
knowing when editing the tables below: the CLI validates **every** reply
against `OP_RESPONSE_SPECS` as a hard error rather than tolerating an
undeclared key, and it generates its whole model-facing tool surface from
`OP_ARG_SPECS`. An op-table change therefore lands in three places, not two.

## Options considered

| Option | Shape | Assessment |
|---|---|---|
| **A. cadex as base** | Keep the Qt/Coin3D app; invest in its UI until it feels right. | Rejected as endpoint. Coin3D/Quarter is a dead end for Blender-level viewport feel; every hour on Qt chrome is spent on a shell we don't want. |
| **B. Blender as shell** | Blender (mesh fork) is the UI; cadex runs headless as a geometry service. | **Confirmed endpoint.** mesh_agent already prototypes the exact target UX; BMesh solves mesh editing natively; the engine already runs headless (`FreeCADCmd`, worker subprocesses). |
| **C. Two-app bridge** | Both apps stay full apps; a live bridge syncs geometry. | Rejected: two documents of record, two undo systems, permanent sync complexity. |
| **D. Staged** | Keep working engine-side in cadex now; split engine from shell; then adopt a shell endpoint. | **Confirmed path**, with B as the endpoint. Near-term work stays in `src/Mod/cadex/**` and carries over unchanged. |

**Decision: D with B as the endpoint.** Cadex became **cadexd**, a headless
xscript geometry service; the mesh fork is the product shell. The Qt shell
was the interim harness and was **deleted in Phase 7** (ADR-021) — options
A and D's interim state are now history, not plan.

### Why this is safe to commit to now

- Near-term phases (1–4) are engine-side: source-tree reduction, the single
  project script, a minimal mesh domain. All of it carries over to any shell.
- The decision gate before Phase 5 (below) re-validates the endpoint with
  measurements, not vibes.

## License reasoning

- The engine is LGPL-2.1+ (FreeCAD lineage); OCCT is LGPL-2.1. The shell is
  GPL-2+ (Blender lineage).
- Direction of flow is LGPL engine → GPL shell, across a **process boundary**
  (cadexd subprocess speaking a JSON protocol; no linking). This is clean:
  the GPL shell may talk to an LGPL service; neither codebase's license
  contaminates the other.
- **One repository does not change this.** What matters for the GPL is
  linking and derivation, not directory layout: the two halves are separate
  programs communicating over a documented protocol, exactly as before. The
  concrete rules that keep it that way — nothing under
  `shell/scripts/addons_core/mesh_agent/` imports from `src/`,
  `cadexd_client.py` stays a plain NDJSON client with no cadex imports, and
  the payload is carried as data — are unchanged and are why they are worth
  keeping.
- The inverse (embedding GPL Blender code inside the LGPL engine) would not
  be clean. The engine must never gain a `shell/` import.

## cadexd protocol `cadex-cadexd-v1` `[Cadex-new — implemented, ADR-017]`

Transport: newline-delimited JSON over stdio, 8 MB frame cap, one cadexd
child (`FreeCADCmd`, no `--safe-mode`) per open project, spawned/owned by
the shell. `pixi run cadexd` starts one by hand. Binary artifacts are
referenced by filesystem path, never inlined. Codec + op registry:
`src/Mod/cadex/CadexdProtocol.py`; server: `src/Mod/cadex/cadexd.py`.

Frames: request `{schema, id, op, args}`; response `{id, ok, ...payload}`;
progress event `{id, event}` (the pipeline's `_emit` events, verbatim). A
ready banner event is emitted on startup. fd 1 is hijacked to a private
protocol fd at entry (FreeCAD chatter lands on stderr); stdin EOF is the
lifetime signal.

| Op | Args | Response payload |
|---|---|---|
| `open_project` | `project_root`, `budgets?`, `restore?` | manifest + full script.json state; **restore pass** re-runs THE script into the fresh ephemeral document and asserts digest equality when an accepted digest exists; a script that will not run at all is retried once from the accepted revision's pinned source (ADR-044) |
| `describe_api` | — | `describe_project_api()` verbatim |
| `write_script` / `edit_script` / `set_params` | today's tool args + optional `display {quality, deflection, edges}`; `write_script` also takes `replace?` (ADR-045); `set_params` also takes `nets?` — the **complete** replacement row list for the connections a script declares with `nets(...)`, each row `{name, a, b, gauge_mm, solder, enabled}` with `a`/`b` addressed `<port>.<terminal>` (ADR-065). A full list rather than a patch, so the wiring editor can add and drop rows; a nets-only edit sends `values: {}` | **byte-identical** to the in-process tool payload (accept payload / `tool_failure` envelope, `STALE_PROGRAM_REVISION` guard included) + per-output `display {artifact_kind, artifact_path (abs), placement, tessellation\|null}` |
| `rebuild` | `display?` | explicit deterministic re-run of the stored script (same payload shape) |
| `put_asset` | `source_path`, `name?` | copies **one file the project store accepts** into `assets/` under a validated name (overwrite = re-import), returns its `{name, bytes, sha256}` plus the full listing. Accepted suffixes are `.stl`/`.obj`/`.ply` — geometry a script imports with `mesh.import_file` or `part.shape_from_mesh` — **and `.cxpolicy`**, a trained control policy `assembly.policy` names by file and digest (ADR-084). The op performs no suffix check of its own: it passes the path through and lets the engine refuse, which is exactly why widening what the store holds cost no protocol change and no `shell/` diff. A **modeling** op: it writes the store, and exclusion against an in-flight rebuild is what stops a half-copied asset being staged. A path, not bytes — the asset budget is 128 MB against an 8 MB frame cap |
| `resolve_pin` | `output`, `selection` (fingerprint query or `{element_type, index}`) | `{ok, output, revision, subelements, details}` against the accepted revision's staged BREP (`CadexPinResolution.py`) |
| `inspect` | today's `core.inspect` args | same contract; `document/object` serve the ephemeral doc, `script/api/image/assets/history/wiring` the store; `selection` rejected (shell-only). `wiring` is the harness as a graph (ADR-065): the terminals the accepted run resolved, joined to the connection table, with `editable: false` and `source: "derived"` for a script written before `nets(...)` |
| `preview_params` | `values`, `expected_revision` | solved component placements for a **pose-only** parameter change, from a resident read-only worker (ADR-055) — no BREP, no tessellation, no digest, no publication, **no store write**. A **read** op: it queues behind an in-flight modeling request rather than refusing one. Answers `previewable: false` with a `reason` whenever the change was not pose-only, the revision is stale, or the worker is unavailable; the debounced `set_params` behind it is the real answer either way |
| `cancel` | `request_id?` | acks and cancels the in-flight modeling request (`RUN_CANCELLED` flows to that request) |
| `shutdown` | — | graceful exit |

### Response shapes

The table above says what an op *means*; this one says what its reply
*contains*. Pinned in `CadexdProtocol.OP_RESPONSE_SPECS`, recorded as
shape-only golden fixtures in `cadex_tests/response_schemas/`, and enforced
by `cadex_tests/test_response_schemas.py` — which also asserts this table
and the code agree. Added in Phase 9 (ADR-025): the request half of the
contract was already tested, the half the shell actually consumes was
prose. Every response also carries `id` and `ok`.

| Op | Response keys (success) |
|---|---|
| `open_project` | `schema`, `project_root`, `budgets`, `restore`, `script`, `manifest`? |
| `describe_api` | `domain`, `domains`, `engine`, `instructions`, `program_schema`, `result_contract`, `revision_rule`, `source_globals`, `parameters`, `connections`, `mutation_selection` |
| `write_script` / `edit_script` / `set_params` / `rebuild` | `tool`, `revision`, `accepted_revision`, `digest`, `model_state`, `outputs`, `live_outputs`, `removed`, `display`?, `stdout`? |
| `put_asset` | `name`, `bytes`, `sha256`, `assets` |
| `resolve_pin` | `output`, `revision`, `subelements`, `details` |
| `inspect` | `scope`, `target`, `path`, `value`, `page`, `document`, `surface`, `result_json_bytes` |
| `preview_params` | `placements`, `revision`, `previewable`, `reason`? |
| `cancel` | `cancelled` |
| `shutdown` | `shutting_down` |

`restore` reports what the open re-proved. A stored script that runs but
produces a different digest is a **restore failure** — the user changed the
script, and saying so is the point. A stored script that will not run at all
is not that: it is a store left broken by something with no business writing
it, so the pass retries once from the accepted revision's pinned source and,
if that reproduces the accepted digest, reports
`repaired_from_accepted: true` and leaves the store consistent (ADR-044).

`stdout` is the script's own printed output. It is sent on success as well
as on failure (ADR-044): a `print()` that only reaches the caller when the
run breaks makes a deliberately-failing script the cheapest way to read a
value out of a working one. It is marked optional so a shell written
against the pre-ADR-044 shape still validates.

Nested shapes the shell reads by name are pinned too
(`NESTED_RESPONSE_SPECS`): `display.<output> {artifact_kind,
artifact_path, placement, tessellation}` plus optional `source_output`, its
`tessellation {artifact_kind,
artifact_path, sidecar_path, counts, deflection, quality}` and that block's
`counts {faces, edges, triangles, vertices, edge_vertices}`; `model_state
{status, accepted_is_current, next_write_expected_revision,
verification_goal}`; `live_outputs.<output>`; `script`; `restore`;
`budgets`.

**A display entry is one of two kinds, and `source_output` is how you tell
them apart.** An output that owns geometry carries `artifact_kind` /
`artifact_path` (and a `tessellation` when one was requested) and a null
`placement`. An assembly **component** is the mirror image: a solved
`placement` — 16 floats, row-major — and no geometry at all, because the
shape it places is a *different* declared output. `source_output` names
that output (ADR-049).

It is present only on component entries, so its presence is the test; a
consumer that does not know the key sees exactly the shape it saw before.
A client rendering a solved assembly instances `source_output`'s geometry
at the component's `placement` — without it, an entry with no tessellation
looks like nothing to draw, which is what made solved assemblies invisible.

**`artifact_kind` is an open set, and a client must treat it as one.** The
kinds a shell may see today:

| Value of `artifact_kind` | What the file is | Since |
|---|---|---|
| **`brep`** | an exported BREP shape — the geometry outputs | Phase 2 |
| **`mesh`** | a triangle mesh | Phase 4, ADR-016 |
| **`assembly_simulation_json`** | a `cadex-assembly-simulation-trace-v1` time series. **Three different things produce it** — `assembly.simulation` (kinematics), `assembly.dynamics` (MuJoCo), and `assembly.rollout` (a trained policy) — and that is deliberate: a script has exactly one simulation whichever produced it. A **rollout** additionally carries `actuator_channels` at the top level and `actuator_commands` on each `solver_output` frame; the other two producers carry neither, and a reader must treat both as optional (ADR-096) | ADR-048, ADR-077, ADR-085, ADR-096 |
| **`assembly_mjcf_xml`** | a self-contained MJCF model file | ADR-081 |
| **`assembly_training_task_json`** | a `cadex-training-task-v1` bundle | ADR-083 |
| **`assembly_policy_receipt_json`** | the engine's receipt for a verified policy | ADR-084 |

**The rule the table exists to state:** a client selects on the kinds it
knows and must **ignore, not fail on, an `artifact_kind` it has never heard
of**. The shell's `cadex_animate._simulation_entries` is the worked example
— it selects `assembly_simulation_json` and leaves the other four alone, and
because a policy rollout reuses that kind rather than inventing one, the
shell bakes a learned gait without knowing policies exist. Inventing a new
kind for a rollout would have made a `shell/` change mandatory, which is the
cost ADR-085 was avoiding.

Note also that these are `artifact_kind` values, not output *types*: the
protocol's output-type set is separate and did not grow for the rollout at
all.

**`inspect` is a bounded reader, and a client that wants a whole value has
to say so.** It caps a reply at 32 KiB: containers are paged (`page.kind`,
`page.next_offset`, `offset`/`limit` args, `limit` <= 50) and any single
value over 1 KiB is replaced by a marker — `{"type": "array",
"item_count": 11, "inspect_path": "/params/specs"}` — naming the JSON
Pointer that reaches it. So `value` is a *view*, never a promise of the
whole; read to the end of the pages and follow the markers, or accept a
sample. The shell does the former in `cadex_backend._inspect_full()`
(ADR-038). The bound is the point of the op — do not remove it to save a
caller the walk.

**Failures are one envelope for every op**, because the model reads it and
acts on it: `tool`, `error`, `failure_code`, `failure_stage`, `observed`,
`normalized`, `requested`, `retry`, `candidates`, `allowed_values`,
`native_diagnostics`, `state_change`, and `model_state` when the op has
one.

Server failure codes: `CADEXD_PROTOCOL_ERROR`, `CADEXD_BUSY` (one modeling
request in flight; read-only requests queue), `CADEXD_NOT_OPEN`,
`CADEXD_CRASHED` (client-side, on child death), `CADEXD_RESTORE_FAILED`.

**A server-level failure is a smaller envelope**, deliberately: there is no
tool, no pipeline stage and no document state to report, so it carries
`error` and `failure_code` and nothing else is required. Optional, and the
whole set — a key the server sends that is not named here is a bug in the
server, and a test reads cadexd's `failure(...)` call sites to say so
(ADR-055): `op` and `request_id` name what was refused, `busy_with` names
the in-flight modeling request a `CADEXD_BUSY` is waiting on (read it to
decide between waiting and cancelling), `detail` and `exception_type` are
diagnostics, and `restore_failure` / `observed` are the two ways an open's
restore pass fails — the payload of a stored script that would not run, and
the digests that disagreed.

Geometry responses carry the BREP artifact path **and** the opt-in
`cadex-tessellation-v1` buffers (f32 vertices / u32 triangles / f32 edge
polylines + sidecar `face_ranges`/`edge_polylines` mapping spans to the
exact 1-based Face/Edge enumeration of `face_details`), so a shell can
draw immediately and export/measure exactly; picking round-trips
triangle → `face_ranges` → `resolve_pin {element_type, index}`.

Since Phase 10b (ADR-029) the sidecar also carries **`face_keys`**: one
geometric fingerprint key per `face_ranges` span, same length and same
order. The span index locates a face *in this artifact*; the key describes
the face itself. A shell that wants a click to become something durable —
a script argument rather than a transient highlight — reads `face_keys[i]`
alongside the `resolve_pin` details and writes a selector, because the
five index-taking part ops no longer accept ordinals at all. Purely
additive: `face_ranges` and the index picking path are unchanged. Quality
presets `draft`/`coarse`/`standard`/`fine` (relative deflection 0.05 /
0.02 / 0.005 / 0.001 × bbox diagonal, clamped): `draft` exists for
progressive display — the Blender shell requests it during slider drags
and re-requests `standard` in a background `rebuild` once the drag
settles (ADR-019).

## The engine payload and its discovery `cadex-engine-v1` `[Cadex-new — ADR-023]`

The shell does not build the engine; it carries a payload built here
(`package/engine/build_engine_payload.sh`, ctest
`CadexEnginePayloadSmoke`):

```
cadex-engine-<version>-<os>-<arch>/
  cadex-engine.json     {schema, version, protocol, freecadcmd, module_dir}
  bin/{freecadcmd,CadexGeometryWorker,python}
  lib/                  Qt6 Core/Xml/Concurrent/Network only — no Qt GUI,
                        no PySide, no Coin
  Mod/{cadex,Part,PartDesign,Sketcher,Assembly,Mesh,MeshPart,Import,
       Material,Measure,Show}
```

**Finding the manifest is the whole of discovery.** `freecadcmd` and
`module_dir` are manifest-relative with forward slashes on every platform,
so no shell guesses at a layout. A manifest whose `schema` or `protocol` a
shell does not recognise must be **refused**, not attempted: a version
mismatch should fail at preflight with a sentence, not mid-request with a
protocol error.

Shell-side resolution order: explicit preference → `MESH_FREECADCMD` →
bundled manifest → `PATH`. Install locations:
`Cadex.app/Contents/Resources/cadex` on macOS, `<install>/cadex` in a
portable install, `<install>/<version>/cadex` in a system install.

The payload is **built in this repository** by `pixi run stage-engine` and
installed by the shell's own CMake (ADR-030). There is no download and no
digest pin: both existed to guard a payload crossing a repository boundary,
and there is no such crossing. What survives is the part that was never
about transport — one bundle, discovery by manifest, and a payload gate that
runs the lifecycle test against the *packaged* tree, because a source tree
that passes proves nothing about a payload.

Non-GUI Qt (Core, Xml, Concurrent, Network) is unavoidable — FreeCAD's App
layer links it and `FreeCADCmd` inherits that. Qt **GUI**, PySide and Coin
are absent, and asserted absent by the payload build.

## Decision gate (before Phase 5 commits to the split)

Measured with a real cadexd prototype streaming into Blender:

1. **Tessellation & picking fidelity** — face/edge ID maps survive into
   Blender attributes; picking a face in the viewport resolves to the correct
   `@face-N` pin ≥ 99% of the time on the test-part corpus.
2. **Slider-drag latency** — param change → updated mesh in viewport fast
   enough to feel live on mid-size parts (target: comparable to today's
   in-process slider path; measure both).
3. Rebuild determinism — same script + params → identical content digest
   across cadexd restarts.

If the gate fails, the fallback is continuing on the Qt shell (Phase 3
result) while the gaps are fixed — the engine work is endpoint-neutral either
way. *(Historical: the gate passed, and the Qt shell no longer exists.)*

### Gate status (2026-07-25, closed with Phase 6 — ALL CRITERIA MET)

**Re-confirmed after the merge (ADR-030).** The same gate, against
`Cadex.app` built entirely from this repository, with `MESH_FREECADCMD`,
`MESH_CADEXD_MODULE` and `MESH_CADEX_ENGINE` all unset: `ok: true`,
`engine_from_bundle: true`, picking 372/372 (fidelity 1.0), slider-drag
median **0.576 s**, restore performed and digest-matched, cancellation
answered, 127 main-thread ticks during a 1.59 s rebuild. The pre-merge
baseline measured on the same machine in the same session was 0.629 s, so
nothing regressed; the spread between 0.548, 0.572, 0.576 and 0.629 across
runs is machine load, not change, and a comparison should be made against a
number measured the same day.

Phase 6 (ADR-019) supplied the shell halves in the real Blender shell
(then `/Users/theo/mesh`, now `shell/tests/python/bl_mesh_agent_cadex.py`,
headless Blender 5.3.0-alpha against release cadexd):

1. **Tessellation & picking fidelity — PASSED.** ID maps land as
   `cadex_face` INT face attributes, byte-identical to the sidecar
   ranges, 100% face coverage; 372/372 ray-cast picks (bar ≥ 99%)
   resolved through `resolve_pin {element_type, index}` to faces whose
   tessellation aggregates (area, centroid, planar residual) match the
   engine's geometric truth on the corpus (box, cone, torus,
   drilled+filleted plate); mesh-domain outputs refuse pins.
2. **Slider-drag latency — PASSED.** Median **0.548 s** over 10
   `set_params` drags on the 24-hole/fillet/mesh-skin baseline through
   Blender → cadexd → worker → tessellation → hydration (bar ≤ 0.65 s) —
   *including* the display streaming the Qt 0.479 s measurement did not
   carry, via the `draft` drag preset + background standard refine
   (1.38 s at rest).
3. **Rebuild determinism — PASSED** (unchanged; re-proven continuously by
   the restore pass and ctest `CadexdLifecycle`).

Engine-half history (pre-Phase 6 evidence). Two of the drivers named below
no longer exist: `cadexd_shell_switchover_integration.py` drove the Qt shell
and died with it (ADR-021); its role — measuring slider-drag latency over
raw NDJSON — is `cadex_tests/cadexd_latency_integration.py` today.

1. **Tessellation & ID maps — engine half SHIPPED (ADR-017).**
   `cadex-tessellation-v1` display artifacts ride every lifecycle response
   on request: per-face triangle ranges + per-edge polylines mapping to
   the exact 1-based Face/Edge enumeration, 100% face coverage asserted on
   the corpus CI (`tessellation_id_map_integration.py`), adaptive
   deflection `clamp(rel × bbox_diagonal, 0.05, 5.0)` with
   coarse/standard/fine presets (the 409k-triangle fixed-deflection
   failure mode is designed out). Headless `resolve_pin` resolves
   fingerprints and picked indices against the accepted staged BREP
   (`pin_resolution_integration.py` proves fingerprint↔index↔face_details
   agreement and re-resolution across a `set_params` move). Remaining:
   attribute transport into Blender + viewport picking fidelity (needs the
   prototype).
2. **Slider-drag latency — parity MEASURED THROUGH THE PROTOCOL.**
   10 `set_params` drags on the 24-hole/fillet/mesh-skin baseline part
   through the full client → cadexd → worker → hydrate path: **median
   0.479 s** (`cadexd_shell_switchover_integration.py`; bar ≤ 0.65 s,
   in-process baseline 0.57 s). Protocol framing + shell hydration cost
   less than the in-process publication they replaced. The per-drag
   `FreeCADCmd --safe-mode` worker spawn (~0.4–0.5 s) still dominates; a
   **warm-standby worker** inside cadexd is the identified (not yet
   built) lever for sub-100 ms drags.
3. **Rebuild determinism — PASSED, now re-proven continuously.** Same
   script + params → identical content digest across process restarts and
   across two FreeCAD builds (ADR-016 evidence stands). Since Phase 5
   every `open_project` runs a restore pass that re-executes THE script
   and asserts digest equality against the accepted digest, and ctest
   `CadexdLifecycle` kills cadexd with SIGKILL and verifies the respawned
   restore digest — restart determinism is exercised on every open, not
   once per audit.

## Open questions

- ~~Exact transport (stdio vs socket); per-project vs multiplexing~~ —
  decided 2026-07-25 (ADR-017): stdio NDJSON, one cadexd per project,
  spawned/owned by the shell.
- ~~Where conversation history lives post-split~~ — decided 2026-07-25
  (ADR-020, decision 4): **the `.blend`**, together with the Claude Code
  `session_id`. This **reverses** the `$CADEX_HOME` lean recorded here
  earlier. The conversation is shell state — the engine has no notion of a
  turn — and one file a user can move, copy and mail beats a second store
  beside it. The engine's conversation store was deleted with the Qt shell
  (ADR-021).
- ~~Progressive tessellation (stream coarse then refine)~~ — shipped
  2026-07-25 (ADR-019): drag requests `draft` quality, a cancellable
  background `rebuild` restores `standard` after the drag settles.
- The warm-standby worker for sub-100 ms slider drags (the per-drag
  `FreeCADCmd --safe-mode` spawn still dominates the 0.548 s median).
