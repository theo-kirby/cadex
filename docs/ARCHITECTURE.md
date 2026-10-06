# ARCHITECTURE.md — What Exists Today

Verified against source: 2026-10-06

This document describes the code as it **is**, not as it will be. Targets live
in `docs/VISION.md`, `docs/XSCRIPT.md` (direction section),
`docs/INTEGRATION.md`, and `docs/ROADMAP.md`.

Provenance tags: `[FreeCAD-inherited]` upstream FreeCAD code we build on;
`[VibeCAD-era]` built during the VibeCAD phase and still current;
`[Cadex-new]` added or reshaped since the cadex import.

## 1. The one-paragraph picture

Cadex is **three things** in **one repository** (ADR-030, ADR-500): the
engine, the dashboard and the agent. The **engine** is a FreeCAD fork at the repo root, stripped to a
single AI-native modeling engine and building `FreeCADCmd` and
`CadexGeometryWorker` and no application of its own (ADR-021/022). It runs
as **cadexd** — a persistent headless `FreeCADCmd` service, one child per
open project, speaking `cadex-cadexd-v1` NDJSON over stdio (ADR-017/018).
cadexd owns the script store, executes **ONE declarative xscript project
script** in a sandboxed windowless worker that produces detached BREP (and
mesh) artifacts for all five capability domains — **partdesign, sketcher,
part, mesh, assembly** — in one pass, validates the result, and publishes
it into its own *ephemeral* `App::Document` (lint, contract GC, output
identity) with an accepted content digest. The assembly
domain also carries the **dynamics and control vertical**: rigid-body
simulation on MuJoCo, MJCF export, training-task bundles and rollouts of
verified policies, all through that same worker and that same digest
(ADR-086, `docs/MUJOCO.md`). Every `open_project` re-runs the
accepted script and asserts digest equality, so restart determinism is
proven on every open rather than once per audit — and where the kernel
re-serializes one model to different bytes (`part.offset`), the two retained
attempts are re-measured instead of refused (`CadexGeometryDigest.py`,
ADR-389). On the other side of the
protocol is `cli/` (ADR-061), which carries the other two. **The
dashboard** (`review_server.py` and `review_static/`, served by `./cadex
app`) is the only UI: a standard-library server and vanilla JS over the
project directory, read-only (ADR-537), where a person watches the design
while their agent works it; its spec is `docs/DASHBOARD.md`. **The agent**
is the person's own: `cadex mcp` (`mcp.py` for the wire, `McpSession` in
`__main__.py` for the engine) serves one tool surface (`tools.py`, run by
`bridge.py`) and one guidance source (`CadexAgentGuidance.md` plus
`guidance.py`) to any MCP client, and the `cadex` commands cover the rest;
Cadex has no model loop of its own (ADR-538). The CLI spawns `cadexd` per
project and finds the engine as a payload by manifest
(`docs/INTEGRATION.md`, ADR-023) or in the build tree. The Blender shell
that used to sit on this side is deleted (ADR-498), and with it
`mesh.blender` (ADR-496); the tag `v1-blender-shell` is the last tree that
has either.

The boundary between them is a **process boundary, not a repository
boundary**, and it did not move when the repositories merged. Nothing links
across it; nothing shares memory; the only thing that crosses is the
protocol. That is what keeps either half replaceable (ROADMAP Phase 11, and
a desktop app that copies the dashboard) and it is what the tests pin.

## 2. The xscript pipeline `[Cadex-new]`

```
 cli/  (the dashboard and the agent)     cadexd child (per project)
 ────────────────────────────           ─────────────────────────────────────────────
 ./cadex mcp / params / app            cadexd.py → CadexScriptedRuntime
 cadex_cli/mcp.py (any agent)  ═══NDJSON═▶ (serial dispatch; persist source, spawn ONE
 cadex_cli/client.py                     --safe-mode worker, validate, publish into the
 cadex_cli/review_server.py  ◀══════════ ephemeral App::Document, accept, tessellate)
 (dashboard: viewer, renders,
  reports, in a browser)
```

The whole left-hand column lives under `cli/cadex_cli/`. What crosses the
boundary is the protocol in `docs/INTEGRATION.md` and nothing else: no
shared code and no shared process (`docs/PROVENANCE.md` §7). Being in one
repository does not relax that — the left column may not `import` anything
from `src/` (ADR-061).

- **cadexd** (`src/Mod/cadex/cadexd.py`, protocol
  `src/Mod/cadex/CadexdProtocol.py`): one `FreeCADCmd` child per open
  project (no `--safe-mode` — trusted engine code), spawned/owned by the
  CLI (`cli/cadex_cli/client.py`);
  `pixi run cadexd` for a standalone instance. Serial dispatch, `CADEXD_BUSY` refusal for a second
  modeling request, mid-run `cancel`, stdin-EOF lifetime, fd-1 hijack so
  only protocol frames reach the parent. Hosts the persistent ephemeral
  document and runs a digest-verified **restore pass** on every open.
- **Runtime** (`src/Mod/cadex/CadexScriptedRuntime.py`): the project
  lifecycle, engine-side. `run_project_lifecycle` (shared by cadexd and
  `cadex_rebuild`) captures bounded state (`capture_project_state`; budgets
  from `service.scripted_budgets()` with preferences fallback), persists
  source + values + revision to the script store BEFORE execution
  (`prepare_project_candidate`; stale-revision guard), stages the worker
  bundle, executes (`execute_candidate`), validates geometry host-side
  (`validate_project_result`), publishes into the ephemeral document,
  accepts (`accept_project_candidate` — records the accepted contract +
  digest + `accepted_attempt` locator). `edit_script` reuses unique-match
  find/replace (`_apply_replacements`); `set_params` patches values only.
  Opt-in per-request `display` produces `cadex-tessellation-v1` buffers +
  face/edge ID maps per output (`cadex_tessellation.py`, digest-neutral);
  `CadexPinResolution.py` resolves pins headlessly against the accepted
  staged BREP.
- **Worker module snapshots** (ADR-244): shared bundles are named from module
  bytes read once and copied from that snapshot, never hardlinked to mutable
  engine sources. Reuse compares every member's bytes and rejects symlinks and
  legacy hardlinks. Corrupt or incomplete bundles are replaced as complete
  directories, dropping their bytecode; matching bundles keep their files and
  warm bytecode. A lost publication race validates the winner before returning.
  This is not a lock against concurrent cache mutation or a transaction across
  an engine installation; readers of a bundle being repaired may fail and retry.
  Project assets retain their separate atomic-replacement/hardlink contract.
- **Worker**: `FreeCADCmd --safe-mode -c <bootstrap>` subprocess launched
  via `src/Mod/cadex/CadexScriptedProcess.py` (`run_process`: no console
  window, new session, stdin closed, hard timeout + memory watchdog;
  budgets from `open_project`'s `budgets` per field, else the engine's
  defaults, 300 s and 6144 MB (the CLI sends the project's, stored in
  `agent.json`, ADR-517; no preference group, ADR-530), carried into the worker again as `RLIMIT_CPU`
  and `RLIMIT_AS` in different units — see `docs/XSCRIPT.md` and ADR-250).
  Its environment is a closed allowlist (`worker_environment`) that pins
  `PYTHONHASHSEED` and the BLAS thread pool, so a worker's address-space
  footprint does not vary with the host's core count; `_resource_limits`
  pins the worker to four CPUs for the same reason, so its CPU-second
  charge does not either (ADR-418). The project bundle
  (`_DOMAIN_WORKER_BUNDLES["project"]`, `CadexScriptedRuntime.py:44`) stages
  all five domain api/worker modules with entry `cadex_project_worker.py`
  — **and seventeen more modules by filename**, which is the pattern worth
  knowing: `CadexRouting.py`, `CadexBundle.py`, `CadexTerminals.py`,
  `CadexSolder.py`, `CadexNets.py`, `CadexBoards.py`, `CadexMounts.py`,
  `CadexCage.py`, `CadexLinkedPart.py`, `CadexDynamics.py`,
  `CadexEvaluation.py`, `CadexStress.py`, `CadexSubshapeQuery.py`,
  `CadexGeometryDigest.py`, `CadexScriptedProcess.py`,
  `cadex_tessellation.py`, and `cadex_preview_worker.py`
  are copied in rather than imported, so a worker
  module can `import` them inside the sandbox while `cadexd`'s own module
  closure never reaches them. For `CadexDynamics.py` that is not a
  convenience but the invariant `test_engine_purity_guardrails` asserts
  exactly: a service reading NDJSON off a pipe does not need 53.5 MB of
  physics engine resident. `CadexStress.py` is the case where that argument
  had to be made differently (ADR-145): it *is* reachable, because
  `cadex_part_worker` imports it and that module is in the closure — so
  what is asserted is that nothing imports it at **module scope** and that
  it defers numpy and scipy into its own functions. Reachable and loaded are
  different questions. The script
  executes once, outputs are grouped by domain and evaluated sketcher →
  part → partdesign → mesh → assembly. Mesh assets (`assets/*.stl|obj|ply`
  under the project root) are staged beside the worker for
  `mesh.import_file` — and, since ADR-043, for `part.shape_from_mesh`, which
  materializes a nested mesh value inside the part build through the entry
  point `configure_part_assets` binds. Trained policies
  (`assets/*.cxpolicy`, ADR-084) are staged the same way and read by
  `assembly.policy`, and parts built in another project
  (`assets/*.cxpart`, ADR-138) the same way again, read by
  `part.import_part` — which authenticates the container against the digest
  in its own header before importing the BREP, the check
  `configure_part_references` performs on a host-staged snapshot one step
  further out. Wire schema: `cadex-xscript-project-worker-v1`.
- **Publisher** (`src/Mod/cadex/CadexScriptedDomainPublication.py`,
  `CadexScriptedPublication.py`): `publish_project_candidate` applies all
  domains under ONE transaction (per-domain sub-publishes with
  `manage_transaction=False`), rewrites same-script assembly component
  tokens to live names, garbage-collects owned objects whose outputs left
  the contract, and aborts on any untagged document object
  (`PUBLICATION_UNTAGGED_OBJECT`). Undo is on for that one transaction
  and cleared after it, so any refusal rolls the document back to the
  accepted revision (ADR-434). Failed candidates stay inspectable
  without replacing the accepted revision. Since Phase 5 publication runs
  **only inside cadexd's ephemeral document** (and `cadex_rebuild`) — the
  split is process-level, so the pipeline modules stay in-tree, but no
  client may import them (ADR-018).
- **Display, not hydration.** The engine's side of the process boundary
  ends at the response: each accepted output carries a `display` block with
  absolute artifact paths and, on request, `cadex-tessellation-v1` buffers
  plus face/edge ID maps (`cadex_tessellation.py`, digest-neutral, quality
  presets `draft`/`coarse`/`standard`/`fine`). What a client does with them
  is its own business: the dashboard's viewer draws the accepted attempt's
  sidecars in three.js. The Qt hydration that used to live here died with
  the Qt shell (ADR-021), and the Blender scene hydration with the Blender
  shell (ADR-498).
- **Geometry checks**: `src/Mod/cadex/CadexGeometryWorker.cpp` — an
  isolated C++ helper (built to `build/release/bin/CadexGeometryWorker`)
  for BREP validation (`BOPAlgo_ArgumentAnalyzer`) and exact
  minimum-distance queries; JSON job schema `cadex-geometry-job-v1`.

Published objects are tagged (`src/Mod/cadex/CadexScriptedDomains.py`):
`CadexXScriptProgramId` (= `"project"`), `CadexXScriptDomain`,
`CadexXScriptWorkbench`, `CadexXScriptRevision`, `CadexXScriptOutputName`.
Ownership closure, lint, and orphan queries live in
`CadexScriptedOwnership.py`.

## 3. File map of `src/Mod/cadex/`

### Engine core

| File | Role |
|---|---|
| `CadexScriptedRuntime.py` | The project lifecycle: store persistence, source policy, worker staging/exec, validation, acceptance. `shared_worker_bundle` is the content-addressed worker bundle — keyed by the bytes of every member, and since ADR-390 refusing to publish or trust one whose members cannot import each other: an engine module beside the members, imported by one of them at module scope and not itself a member, raises and names the skew instead of caching a bundle that fails identically for the life of the session. `[Cadex-new]` |
| `CadexScriptedDomains.py` | `PROJECT_PACK` + the five capability packs (worker/publication contracts), project tool specs, `project_script_revision`, object-tag constants, source sandbox rules. `[Cadex-new]` |
| `cadex_project_api.py` / `cadex_project_worker.py` | The project domain: `params`/`num` vocabulary, inline assembly-source tokens, multi-domain exec namespace, per-domain evaluation, worker-side content digest. `[Cadex-new]` |
| `CadexGeometryDigest.py` | The digest material both halves share: the byte digest the worker computes, and the geometry digest `cadexd` falls back to when a kernel re-serializes one model to different bytes (ADR-389) or a fixed exporter re-derives one from it (ADR-396). One `_entries` builds both; they disagree only about how a BREP output is identified and whether a derived output's artifact bytes are read at all. `[Cadex-new]` |
| `CadexScriptedDomainPublication.py` / `CadexScriptedPublication.py` | Project publication (one transaction, lint, GC) over the per-domain apply routines. Publishes the five live domains only — the robot/FEM/inspection/points/reverse-engineering/meshpart/surface paths were deleted in Phase 9 (ADR-026), halving the module. `[VibeCAD-era]`, reshaped `[Cadex-new]` |
| `CadexScriptedOwnership.py` | Ownership tagging, owned closure, untagged/orphan queries. |
| `CadexScriptedProcess.py` | Bounded subprocess runner (timeout, memory watchdog, cancellation). `[VibeCAD-era]` |
| `CadexDigest.py` | Document-side diagnostic digest (`cadex-document-digest-v1`). `[Cadex-new]` |
| `cadexd.py` | The headless engine service: per-project `FreeCADCmd` child, serial dispatch, ephemeral document, restore pass, cancel (`pixi run cadexd`, ADR-017). `[Cadex-new]` |
| `CadexdProtocol.py` | `cadex-cadexd-v1` NDJSON codec, op registry + arg schemas, **response schemas** (`OP_RESPONSE_SPECS`, `NESTED_RESPONSE_SPECS`, the tool-level and server-level failure envelopes, `validate_response`), server failure codes; pure Python, zero FreeCAD imports. `[Cadex-new]` |
| `cadex_tessellation.py` | Phase 5.1 display tessellation: adaptive deflection, per-face triangle ranges + `face_keys` fingerprints + per-edge polylines (`cadex-tessellation-v1` buffer + sidecar), digest-neutral. Staged into the worker bundle. `[Cadex-new]` |
| `CadexSubshapeQuery.py` | **The one subshape vocabulary** (Phase 10b, ADR-029): `subshape_geometry` fingerprints, `query_subelements` / `resolve_selected_subshapes` resolve a selector against a shape, `SELECTOR_KEYS` is the closed key set, `fingerprint_key` is the sidecar handle. Kernel-neutral — no FreeCAD import — and staged into the worker bundle. Extracted from `cadex_partdesign_worker` (Phase 11a's item, forced forward: the part domain could not reach it without an import cycle). `[Cadex-new]` |
| `CadexPinResolution.py` | Headless pin resolution against the accepted revision's staged BREP: `CadexSubshapeQuery` fingerprints or direct `{element_type, index}`. Its three accepted-attempt readers (`accepted_attempt_dir`, `load_worker_report`, `accepted_output_item`) are public since ADR-043 — `inspect scope="output"` reads the same pinned report. `[Cadex-new]` |
| `cadex_rebuild.py` | Headless rebuild + digest comparison (`pixi run rebuild <root>`); drives the shared `run_project_lifecycle`. `[Cadex-new]` |
| `cadex_{partdesign,sketcher,part,assembly}_{api,worker}.py` | The original four domain APIs (staged into the project worker) and worker implementations. `[VibeCAD-era]` |
| `cadex_mesh_api.py` / `cadex_mesh_worker.py` | The Phase 4 mesh domain on `Mod/Mesh`+`Mod/MeshPart`: tessellate/import/transform/boolean/decimate, plus `mesh.check` — the one export that publishes no geometry, four integers about whether a mesh is sound (ADR-144), canonical vertex/facet ordering + vertex-set digest fingerprint (ADR-016). The api also owns `payload_tree_is_deterministic`, which `part.shape_from_mesh` applies at script-eval time (ADR-043); the worker's `canonical_mesh_from_payload` is the BREP-ingest entry point the part worker is *handed* rather than imports, because the part worker is in cadexd's closure and this one deliberately is not. `[Cadex-new]` |
| `CadexRouting.py` | The wire router behind `part.cable` (ADR-056, ADR-118, **experimental**): lazy 26-connected A* on an integer lattice, clearance by lattice dilation, line-of-sight shortcut, sag, bounded by a probe budget. Kernel-neutral — no FreeCAD import, occupancy arrives as an `occupied(i, j, k)` callback — so the whole algorithm is unit-testable headless; staged into the worker bundle. The part worker backs that callback with obstacle surfaces rasterised from one tessellation, because `Shape.isInside` measured 3.3 ms a point. Split by ADR-118 into `route_interior` (the searched middle plus the two anchors) and `assemble_spine` (the stub knots, the dedup and the at-least-three floor), so an **authored** `waypoints=` can replace the middle and nothing else and still meet the interpolator's input contract; `route_path` is the composition and is unchanged. `[Cadex-new]` |
| `CadexBundle.py` | The multi-conductor lay behind `part.bundle` (ADR-057, **experimental**): a rotation-minimising frame carried along the shared centreline by double reflection (Frenet flips at every inflection, and a routed path is full of them), twisted and flat conductor offsets from it, a numeric solve for the lay radius at which no two conductors interpenetrate, and the raised-cosine fan-out that lands each conductor on its own port without a corner. Kernel-neutral and FreeCAD-free like `CadexRouting.py`, unit-testable headless, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexTerminals.py` | Named, geometry-anchored ports behind `part.terminals` / `mesh.terminals` (ADR-062, **experimental**): the declared and selector layouts, ordering along a *direction* rather than by kernel enumeration, the near-face landing rule for a through-hole (ADR-117: the terminal is in the mouth's plane, the bore behind it is left empty, and `hole_dia` rather than `depth` is what classifies a declared row), and the placement arithmetic that carries one asset-frame spec onto four placed components (points by the whole matrix, directions by its rotation part; non-uniform scale refused). Kernel-neutral and FreeCAD-free like the two above, unit-testable headless, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexSolder.py` | The joint behind `part.solder` (ADR-063, ADR-064, ADR-117, **experimental**): from a terminal's `metrics` plus three numbers it derives the bore, pad, collar and fillet, refuses the ways they can fail to describe a joint, and returns a closed *outline* in the `(r, z)` half-plane — the annulus from the lead to the pad rim, a concave meniscus arc solved to be tangent to the lead, the collar, the crown's round-over, and the lead's own radius back down — which the worker turns into one wire, one face and one `revolve`. **One outline serves a bore and a pad alike** since ADR-117: the cap cone, bore wall and entry annulus described a lead ending at the bottom of the barrel, and a terminal lands in the mouth now, so what a bore still contributes is its radius (the pad's default width, and the floor a stated `pad_dia_mm` must clear) and nothing else. No fuse and no cut, so no boolean at all. Also the contour-integral volume (`V = π ∮ r² dz`) the kernel probe asserts against, and the stated radial basis that fixes where the BREP seam lands. Kernel-neutral and FreeCAD-free, staged by filename. `[Cadex-new]` |
| `CadexNets.py` | The connection table behind `nets(...)` / `wire(...)` (ADR-065, **experimental**): the declaration, its refusals, the `"<port>.<terminal>"` endpoint grammar, the canonical row shape shared by the declared table and the stored overrides, and the two rules the wiring editor rests on — a stored row list *replaces* the declaration rather than patching it, and a row whose port a rewritten script no longer declares is pruned rather than raised on (ADR-039). Kernel-neutral and FreeCAD-free like the four above, unit-testable headless, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexBoards.py` | The board table behind `boards(...)` / `board(...)` / `term(...)` (ADR-120, **experimental**): the declaration and its refusals, the canonical terminal row (`board`, `name`, `origin`, `axis`, `hole_dia`, `depth` — always **millimetres in the board's own frame**, so `units="m"` is a declaration-time convenience and never a second unit system in the store), the header form expanded to explicit rows at declaration, the same two editor rules `CadexNets` rests on (a stored row list replaces the declaration; a row naming a board the script no longer declares is pruned), and `row_from_world`, the arithmetic that carries a terminal *measured in the viewport* back into its board's frame through the inverse of the placement chain the run resolved. Returns a mapping of `TerminalSet`, so `nets(ports=b)` takes it unchanged. Kernel-neutral and FreeCAD-free like the five above, unit-testable headless, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexLinkedPart.py` | The `.cxpart` container behind `link_part` and `part.import_part` (ADR-138): `CXPART1\n | <u64 LE header length> | <canonical JSON> | <raw BREP>`, deliberately isomorphic to `CadexDynamics`' `.cxpolicy` and for its reasons — a length-prefixed header and a byte range are readable inside the `--safe-mode` sandbox by fifteen lines that parse no archive format. `build_linked_part` reads one project's pinned accepted attempt (`CadexPinResolution`'s three public helpers plus `read_accepted_source`) and returns the container bytes; `decode_linked_part` verifies magic, schema, every declared length and the BREP's own SHA-256 before a shape is built from it. The header carries the source project's script, params and param specs — **carried and not yet read**, which is what a parameter override needs and what makes a linked part rebuildable rather than baked. FreeCAD-free and kernel-neutral: building a container needs no worker, no OCCT call and no open source project. The one module both staged into the worker bundle *and* in `cadexd`'s import closure, which is `CadexNets.py`'s standing exactly. `[Cadex-new]` |
| `CadexStress.py` | The linear-elastic solve behind `part.stress` (ADR-145): a C3D8I hex element with Wilson incompatible modes statically condensed at element level, a scanline parity voxelisation with the two defences ADR-141 measured the need for, Jacobi-preconditioned CG above 10k free degrees of freedom, and a report whose safety factor divides by **p99 von Mises rather than the peak**, because a held face is a stair-stepped singularity that does not converge. It imports **no FreeCAD at all** — `cadex_part_worker` resolves the ADR-029 selectors, tessellates the named faces and samples them, and what crosses into here is triangles and point clouds. That is what makes it the same species of thing as `analysis/cadex_stress.py` and therefore comparable to it: the two are independent implementations of one algorithm and a test solves the same cantilever through both. numpy and scipy are imported inside functions. `[Cadex-new]` |
| `CadexDynamics.py` | **The dynamics and control vertical**, 10,824 lines, and the largest single module in the tree (ADR-077, ADR-079…081, ADR-083…085; **experimental**). Five things, in the order the arc built them. **(1) The translator** behind `assembly.dynamics`: the joint table, a breadth-first spanning forest with loop closures as equality constraints, exact OCCT inertia converted to SI, the `mjSpec` build and the stepping loop that emits a `cadex-assembly-simulation-trace-v1`. **(2) Collision and contact** (M3): the convexity measurement that refuses a part MuJoCo would silently hull (`scipy.spatial.ConvexHull`, imported the same deferred way `mujoco` is), restitution to a damping ratio, collision groups to bitmasks, full extents to half-extents, and the solver flags, integrator and two step budgets that make a trace reproducible across processes. **(3) Actuation** (M4): `motor`/`position`/`velocity` actuators, joint damping/armature/friction-loss, and a whitelisted formula-of-`time` compiler for setpoints — arbitrary Python would leave the determinism gate. **(4) MJCF export** (M5): `export_mjcf` calls MuJoCo's own `MjSpec.to_xml()`, then reloads the file and diffs it field by field against the model it just wrote, refusing rather than emitting past tolerance — the writer's six significant figures are why that check is a measured tolerance and not an identity. **(5) Tasks, policies and rollouts** (M6–M8): the `cadex-training-task-v1` bundle, the `cadex-policy-v1` container reader, a **pure-Python forward pass** (4,564 Hz against a 50 Hz control rate — measured, and the reason numpy is not imported here), the witness re-computation that turns an architecture mismatch into a refusal, and the episode loop whose one keyword-only `sample` callable is the whole difference between verifying a policy and rolling one out. **A task may say where to go** (ADR-462): `assembly.goal` declares a value, a commanded speed or a reachable point, written into the bundle as `goal` with the `goal_algorithm` that draws it; `draw_episode_goals` continues a seed's stream after its shoves, the episode loop shows the goal to the policy and lets the reward name it, a rollout's frames record it, and `evaluate_success` reads the commanded speed and the reach targets from the episode's own draw, by kind. The trainer carries a copy of the draw and a test holds the two to the same numbers. Kernel-neutral and FreeCAD-free like `CadexRouting.py`, staged into the worker bundle by filename -- and the only module in the tree that may import `mujoco`, which it does inside functions so `cadexd`'s closure never reaches it. The worker does every FreeCAD read; this does every arithmetic operation including every unit conversion, and a test greps to keep that true. `[Cadex-new]` |
| `CadexMounts.py` | The mount table behind `mounts(...)` / `mount(...)` and `part.mate` (ADR-126, **experimental**): a named frame on a component with a roll, a fastener and a clearance, in `CadexBoards`' row shape (millimetres in the component's frame, stored overrides as a full row list, drift pruned). FreeCAD-free, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexCage.py` | The section cage behind `cage(...)` / `ring(...)` and `part.loft_cage` (ADR-127): a shape as a declared table of superellipse rings, in the same declared-table shape as `nets`, `boards` and `mounts`. FreeCAD-free, staged into the worker bundle by filename. `[Cadex-new]` |
| `CadexCatalog.py` | The parts-library catalog (ADR-181): one spec row per part number, one table per family, each pinned against its standard or datasheet; interface-exact, cosmetically simple, millimetres and N*mm. FreeCAD-free. `[Cadex-new]` |
| `cadex_library_api.py` | The `lib` script namespace (ADR-181): generators that compose ordinary part-domain recipes from `CadexCatalog` rows, each returning a `LibraryPart` with `.body`, `.spec` and helpers such as `.bay()`; also the `library` section of `describe_api`. FreeCAD-free. `[Cadex-new]` |
| `CadexBlueprints.py` | The blueprint store (ADR-150, ADR-157): the sheets under `blueprints/` and their `cadex-blueprint-v1` index, written by the `put_blueprint` op and read by `inspect scope=blueprint`. FreeCAD-free. `[Cadex-new]` |
| `CadexPrintables.py` | What `export_printable` needs (ADR-156, ADR-158): the roster of an accepted run's outputs that have a surface, validation of the caller's list, and the file names under `print/`. Stores no marks. FreeCAD-free. `[Cadex-new]` |
| `cadex_preview_worker.py` | The resident preview worker's entry point (ADR-055): a read-only oracle that answers a pose-only parameter change with solved placements in 33 ms and writes nothing at all. In the worker bundle rather than beside `cadexd`, because it runs in the same `--safe-mode` sandbox out of the same content-addressed directory and must never be importable by the service. `[Cadex-new]` |
| `CadexWarmWorker.py` | cadexd's side of that: one resident worker per open project, spawned lazily on the first `preview_params`, bound to one `(source, api_contracts, assets)` generation and killed by anything that changes them. `[Cadex-new]` |
| `cadex_domain_api.py` / `cadex_domain_worker.py` | Shared domain API/worker plumbing (`_execute_source` is the composition substrate). `_serialize_output` is where an output type decides what it *is*: a BREP type exports an artifact, `mesh` writes a PLY, and `points`, `solver_diagnostics`, `measurement` (ADR-139) and `stress` (ADR-145) attach a dict and **no `artifact_kind` at all**; `mesh_check` (ADR-144) does the same from the mesh domain's own serializer, which is where that branch belongs. That branch is the whole cost of a non-geometric output: `compute_project_digest` keys on *having* an artifact, so an artifact-less output falls through to `payload_sha256`, the hash of its own declaration. A measurement's identity is therefore which selectors it names, not what today's parameters make it read — and a stress check's is which faces it holds and what material it declares. `[VibeCAD-era]` |
| `CadexGeometryWorker.cpp` | Isolated C++ BREP validation / distance worker. `[VibeCAD-era]` |

### No UI in the engine

There is no UI under `src/`. `CadexGui`, `CadexSession`,
`CadexProvider`, `CadexCore`, `CadexAuth`, `CadexCodex`, `CadexPreferences`,
`CadexTransactions`, `CadexEditState`, `CadexGrid`, `CadexParametersPanel`,
`CadexScriptView`, the `tool_impl` package, `CadexdClient` and
`CadexShellHydration` were all deleted in Phase 7 (ADR-021). The front end
is `cli/`, and it speaks the protocol in `docs/INTEGRATION.md` — a different
process, not a different import path.

`test_engine_purity_guardrails.py` keeps it that way: nothing under
`src/Mod/cadex/**` may import `PySide*`, `FreeCADGui`, `tool_impl` or
`jsonschema`, and cadexd's transitive module closure must equal a declared
list. Phase 14 added two more invariants to the same file — **`mujoco` never
enters that closure** (it is reachable only from the sandboxed worker), and
**no `jax` or `mjx` appears anywhere under `src/Mod/cadex` or in a staged
payload** (ADR-084: training is offboard, and the engine verifies a policy
but never produces one).

### The CLI `[Cadex-new — ADR-061]`

`cli/` is the only front end and the client of the protocol: no display
needed, and no code from the deleted shell (`docs/CLI.md`). It is on the engine's
side of the licence line (LGPL) and lives outside `src/` because it is a
*client*, not part of the engine — it spawns `cadexd` and imports nothing
from it except `CadexdProtocol`, loaded by path out of whichever engine it
resolved. Its whole model-facing tool surface is generated from
`OP_ARG_SPECS`, so it cannot drift from the contract it drives.

### Contracts and surfaces `[Cadex-new]`

| File | Role |
|---|---|
| `CadexdProtocol.py` | The wire protocol: NDJSON codec, op registry (`OP_ARG_SPECS`), failure codes. Its op table is asserted equal to `docs/INTEGRATION.md`'s. |
| `cadexd.py` | The service: serial dispatch, cancel, busy, the ephemeral document, the restore pass, the per-output `display` block. |
| `CadexTools.py` | `FAILURE_STAGES`, the `tool_failure` envelope every refusal is shaped as (and every client parses), `unchanged_state`, `ToolSpec` as a declaration. |
| `CadexEngineSettings.py` | The sandbox budget defaults and their per-field resolution against the project's (ADR-517). Reads no preference group (ADR-530). |
| `CadexStudio.py` | The studio renderer (ADR-445): accepted tessellation to lit, antialiased review views, the 1024 px hero, the concept sheet, the agent's `look` and the dimensioned blueprint sheet its `draw_blueprint` stores (ADR-516), the print-bed hero that lays every printed part flat on as many beds as it takes beside the purchased hardware list (ADR-569); `cadex evaluate` draws the hero and the print bed of a design whose evaluation passes (ADR-570), plus the dark scene `PALETTE` every image stands on and the design proxies P1-P3. Pure standard library. **Not in the service's closure**: the CLI and the dashboard load it by path (`docs/INTEGRATION.md`), because cadexd dispatches serially and a render takes seconds. Its child-process entry served only the shell and is gone (ADR-529). Moved from `cli/cadex_cli/{render,sheet,scene}.py`. `[Cadex-new]` |
| `CadexFitReport.py` | The `fit` and `inventory` blocks every build reply carries (ADR-447): pure functions from the published `inspect scope=clearance` and `scope=inventory` values to the static fit, the swept fit, what the fixed joints hold, catalog identity, appearance and printed edges. Outside the service's closure, on `CadexStudio`'s terms: the CLI loads it by path. Moved from `cli/cadex_cli/{clearance,inventory}.py`. `[Cadex-new]` |
| `CadexEvaluation.py` | **What a rollout did, as numbers** (ADR-455): a rollout trace read into behaviour metrics, none of them the reward. Three families, asked for by what the caller names and not by a task kind — *posture* (tilt, heading, drift, recovery time from a shove), *gait* (steps as opposed to chatter, step share, foot clearance, stance slip, duty factor, foot depth, commanded-speed tracking) and *reach* (final error, time to target, overshoot) — plus `check`, which holds a flat metric table against `{id, metric, min, max}` predicates, so a success spec is data, and `METRICS`, the whole vocabulary an `assembly.success` predicate may name with what measuring each needs (ADR-456) — `CadexDynamics` resolves a declared spec against it inside the worker and writes the task bundle's `success` block. Pure standard library, millimetres and degrees. The model's half arrives as plain numbers from `CadexDynamics.evaluation_rig`, the one place `mujoco` is imported and a unit converted. **Not in the service's closure**, on `CadexStudio`'s terms: a client loads it by path. Pinned metric by metric in `cadex_tests/test_evaluation_metrics.py`, with ot10's `w2-2` shuffle as a failing fixture. **`measure` and `summarise` are what an evaluation is made of** (ADR-457): `measure` reads one rollout into the one flat table a predicate may bound, choosing families by what the rig carries and never by a behaviour's name, and `summarise` folds the seeds without averaging a verdict. `CadexDynamics.evaluate_success` plays a task's `success` block with them — one rollout per frozen seed on a model compiled afresh for that seed, under the spec's own horizon, randomisation, reset variation and disturbances (ADR-458), a seed whose simulation raised a solver warning marked void — and `cadex evaluate` (`docs/CLI.md`) runs it over the retained accepted artifacts and writes `evaluation.json` into the project, then draws a filmstrip and a video of its seeds from their traces with `CadexStudio`, on the dark prototype floor (`cli/cadex_cli/film.py`, ADR-459); the dashboard's server still serves the report, though the page has had no panel for it since ADR-533. `[Cadex-new]` |
| `CadexAgentGuidance.md` | The agent guidance (ADR-446), the domain-neutral **base** (ADR-560): proof by measured facts, the design language's base (form follows function), a complete self-moving machine, grounded policy inputs, a walking task's reward. Engine **data**, read by the CLI's `guidance.py`, which fills its tool-name placeholders and wraps it in the situation for an external agent with a shell; `cadex guidance` prints the whole text and `cadex mcp` points the agent at it (ADR-538). `[Cadex-new]` |
| `CadexAgentStyle.<name>.md` | A named, optional style of the agent guidance (ADR-560), today `printed-legged-robot`: the rules for one kind of machine and its look. Same format as the base; `cadex guidance --project` appends the one the project chose in `agent.json` (`cadex style`). Engine **data**. `[Cadex-new]` |
| `CadexInspection.py` | The bounded `inspect` read surface (scopes `document`, `object`, `script`, `api`, `image`, `output`, `assets`, `history`, `wiring`, `inventory`, `clearance`, `contacts`, `blueprint`; `output`/`assets` added in ADR-043 — per-output facts from the pinned accepted attempt, and the importable-asset listing — `history` in ADR-045, the accepted-revision undo trail `restore_version` reads, and `blueprint` in ADR-150, the stored drawing sheets: the listing, or one entry plus its containment-checked store path, never pixels. `selection` was shell-only and is gone). |
| `CadexReferenceContracts.py` | Geometry pins: shared handle + owner + subelement hint + geometric fingerprint, and fingerprint re-resolution when the revision moved. |
| `CadexPinResolution.py` | Resolves a pick or fingerprint against the accepted revision's staged BREP. |
| `CadexSubshapeQuery.py` | The selector vocabulary a pin *and* a script argument both speak — since Phase 10b the five index-taking part ops resolve through it, so naming geometry means the same thing in a pin and in the script. |
| `CadexModelingSurface.py` | The global project surface id (any workbench, one script). |

### Project store `[Cadex-new]`

`src/Mod/cadex/CadexProject.py`. Root: `$CADEX_HOME` if set, else the
appdata dir + `Cadex` (e.g. `~/Library/Application Support/cadex/Cadex` on
macOS). Layout:

```
<root>/projects/<slug>-<hash8>/
  project.cadex.json            project manifest
  script.py                     THE project script (sole source of truth)
  script_history/               last 25 accepted sources + history.json (ADR-045);
                                each entry also keeps the values and the
                                geometry digest it was accepted with (ADR-506)
  script.json                   schema cadex-project-script-v1: param specs
                                cache + values, net specs cache + stored
                                connection rows (ADR-065),
                                working/accepted revision,
                                accepted contract, accepted_digest,
                                accepted_attempt (staged-artifact locator;
                                that attempt dir is pinned, Phase 5.2),
                                latest candidate
  script_artifacts/<revision>/  staged worker attempts + serialized outputs
                                (+ display/ tessellation buffers when
                                requested). Retained artifacts live under
                                <attempt>/outputs/ — brep, mesh, and four
                                kinds that are files rather than geometry:
                                assembly_simulation_json (a trace, from
                                kinematics OR dynamics OR a policy rollout),
                                assembly_mjcf_xml, assembly_training_task_json
                                and assembly_policy_receipt_json. Every one
                                of the four has its bytes hashed into the
                                project digest (ADR-068), on a rule keyed on
                                *having an artifact* rather than on a roster
                                of kinds — which is why M5's and M7's
                                artifacts joined without a line of code
  review/revisions/             the CLI's, not the engine's (ADR-546): each
                                accepted revision's tessellation, kept after
                                the engine prunes its attempt. parts/ holds
                                <sha256>.tess.bin/.tess.json, one per
                                distinct part buffer; index.json maps each
                                history ordinal to its part digests and
                                placements, and "unrebuilt" why a backfill
                                could not reproduce one. Bounded by
                                script_history/. The dashboard's revision
                                timeline reads it (ADR-547); `cadex revision
                                backfill` fills it for revisions accepted
                                before it existed (ADR-548)
  assets/                       flat .stl/.obj/.ply the script imports by
                                name (mesh.import_file, part.shape_from_mesh)
                                plus .cxpolicy trained policies
                                (assembly.policy, ADR-084) with the
                                .json/.xml their provenance travels as
                                (ADR-135), plus .cxpart parts built in
                                another project (part.import_part, ADR-138);
                                bounded at 64 files / 128 MB, written only by
                                the put_asset op (ADR-043) and, for a
                                .cxpart, the link_part op that builds one
  blueprints/                   rendered blueprint sheets (ADR-150):
                                {ordinal:04d}-{slug or revision[:12]}.png +
                                blueprints.json (cadex-blueprint-v1), each
                                entry attached to the accepted (revision,
                                digest) pair it documents; newest 25 kept,
                                written only by the put_blueprint op (the
                                agent's draw_blueprint, ADR-516), read
                                back through inspect scope=blueprint.
                                Since ADR-157 an entry may carry a name and
                                a version: a name is an IDENTITY, so storing
                                again under it appends the next version,
                                resolves to the newest (name@2 pins one),
                                survives the prune, and names the file. The
                                recipe the sheet can be re-rendered from
                                rides the entry's free-form meta
  print/                        the print job (ADR-156): one <output>.stl per
                                output the CALLER named (ADR-158 -- the
                                engine stores no marks), written off the
                                ACCEPTED brep/mesh artifact rather than the
                                display tessellation, each at its own
                                origin. Written only by the export_printable
                                op. NOT pruned and not indexed — unlike every
                                other directory here this one is a
                                deliverable, so the user owns what is in it;
                                re-exporting asks whether to overwrite or to
                                keep both (<name>-002.stl)
```

**cadexd is the sole writer.** Every byte that lands in the store goes
through an op; the agent asks the engine what is in there (`inspect`) and
hands it files through `put_asset` (a mesh, a trained policy), which is why
the store's layout is not part of the contract in `docs/INTEGRATION.md` —
and why it must not become one now that both halves are in one tree.

The dashboard reads the store and never writes it: the manifest's accepted
attempt, that attempt's `result.json` and its `display/*.tess.json`
sidecars, which is how the viewer shows the accepted model without asking
an engine (`review_server.py`). It has no write route (ADR-537): every
change is the agent's, through `cadex mcp` or a `cadex` command, and the
page follows on its next poll. `cadex revision reject|restore` writes a
stored version from `script_history/` back through `write_script`, then its
recorded values through `set_params` (ADR-506). Until ADR-498 the Blender shell also read
`assets/` on Save-As to carry them into a new root through `put_asset`
(ADR-046); a project is now copied as a directory.

In practice the root is chosen by the caller, not by `$CADEX_HOME`: the CLI
passes its `--project` directory as `project_root`, so the store lives in
the project directory the dashboard serves.

`CadexProjectScriptStore` (`CadexScriptStore.py`, split out of
`CadexProject.py` in C1) owns `script.py`/`script.json` with atomic,
schema-checked writes. A candidate is written before it runs and rolled back
if it fails, so `script.py` only ever holds a source that executed; the
accepted revision's own source stays pinned in its staging directory and is
readable with `read_accepted_source()`, which is what the restore pass falls
back to when the working script will not run at all (ADR-044). **Conversation history is not here**: the
person's agent keeps its own (ADR-538). `CadexProject.py` still defines a
conversation store, unused by any engine or CLI path since ADR-020 moved
conversation history to the shell. VibeCAD-era
per-domain program stores are not migrated (ADR-011).

### Support

`CadexDigest.py`, `CadexScriptedOwnership.py`, `cadex_tessellation.py`,
`cadex_rebuild.py` (the headless rebuild entry), `Init.py`. No icons, no
`InitGui.py`: this module registers no workbench.

### `training/` — outside the engine on purpose `[Cadex-new]`

`training/cadex_train.py` (2,993 lines) is the offboard PPO trainer, and it is
the one top-level directory in this repository that is **not part of the
product** (ADR-084). CMake never installs it, no payload carries it, nothing
in it enters `pixi.toml`, and it cannot import Cadex — it reports whether
`CadexDynamics` was importable so a test can assert the negative. Its four
dependencies (`jax`, `mujoco`, `mujoco-mjx`, `flax`) are exactly pinned in
`training/requirements.txt` and installed into a venv **on whatever machine
trains**, which is a machine with a CUDA GPU and no Cadex on it.

That boundary is what keeps the engine simple rather than what compromises
it. The engine **verifies** a policy and never **produces** one, so it needs
no optimiser, no accelerator and — measured — no numpy. Two implementations
of one format therefore exist by design: `encode_policy` here and
`CadexDynamics.encode_policy` there, with a test comparing their bytes,
because this file cannot import the engine. Three implementations of the
reward whitelist exist for the same reason (`CadexDynamics`,
`cadex_tests/dynamics_task_episode.py`, and this under `jax.numpy`), and a
test asserts all three agree. Read `training/README.md` before touching it.

### Tests

`src/Mod/cadex/cadex_tests/` — 146 Python files, of which 132 are `test_*.py`
modules (the rest are fixtures, reference implementations and
integration drivers run by hand); `conftest.py` stubs `FreeCAD`/`FreeCADGui`
so most of the suite runs headless without a built FreeCAD:

```
pixi run python -m pytest src/Mod/cadex/cadex_tests
```

**2,634 collected**, counted 2026-10-04; the last full run recorded here was
**1,730 passed, 22 skipped** (1,752 collected), measured 2026-08-09. The count
fell from 425 to 226 across Phases 7 and 13a — the Qt shell, the provider
stack and the shell's deleted local bpy path took their suites with them —
rose to 1,105 at the close of Phase 14's M8, and has climbed to 1,730 across
M9, the organic vertical, live mode, linked parts and measurements; 56 of the files are
`test_dynamics_*.py`. **The skips are by design, not breakage:** they are
the MJX-gated tests (phase 0 measurements, real training runs), which need a
venv built from `training/requirements.txt` rather than the pixi environment.
The suites are written to run from either interpreter.

The arc's naming convention is worth knowing because it is uniform, four
files a slice: `*_api` for the authoring surface and its refusals, `*_model`
for what reaches the compiled `mjSpec`, `*_measured` for numbers checked
against a reference rather than against ourselves, `*_live` for the whole
path through a real worker.

**The contract guardrails.** `test_project_tool_surface.py` pins the exact
`xscript.project.*` tool surface and asserts dissolved per-domain operations
and culled modules stay gone. `test_engine_purity_guardrails.py` pins the
process boundary — nothing under `src/Mod/cadex/**` may import `PySide*`,
`FreeCADGui`, `tool_impl` or `jsonschema`, cadexd's module closure must equal
a declared list, and `docs/INTEGRATION.md`'s op table must equal
`OP_ARG_SPECS`. `test_cadexd_protocol.py` pins the op list itself and
`test_response_schemas.py` the reply shapes (ADR-027).

**The integration drivers**, all headless under FreeCADCmd:
`project_xscript_api_integration.py` (the full lifecycle),
`tessellation_id_map_integration.py`, `pin_resolution_integration.py`,
`cadexd_latency_integration.py` (the slider-drag bar over raw NDJSON),
`dynamics_inertia_integration.py`, and `rollout_review_integration.py` — the
last one writes a rollout trace from a live `cadexd` and then reads it
through the review dashboard's own trace reader (`review_server`'s
`_first_frame_placements` and `_placement`, every frame). That is the
evidence ADR-077's shared output type exists to demand: a trace the engine is
happy with and the UI declines to read is exactly the failure the decision
prevents. Until ADR-495 the reader was the Blender shell's bake.

**The five ctests**, in `tests/CMakeLists.txt`:

| ctest | Proves |
|---|---|
| `CadexProjectRebuildDigest` | delete the document, rebuild from the script, digests match — rebuild-vs-accepted *and* rebuild-vs-rebuild |
| `CadexdLifecycle` | open → mutate → inspect → resolve_pin → `kill -9` → respawn → restore digest equality → mid-run cancel |
| `CadexSubshapeEnumeration` | the OCCT ordering fingerprint, so a version bump cannot silently re-index saved scripts (ADR-027) |
| `CadexResponseSchemas` | the golden per-op response shapes |
| `CadexEnginePayloadSmoke` | the *packaged* payload answers the protocol through its own manifest (ADR-023) |

The ones needing a binary skip themselves when no FreeCADCmd is available.
ctest overall has ~160 pre-existing environmental failures — diff against
`build/ctest_baseline_failures.txt`, never expect 100%.

The dashboard's and the agent's suite lives on the other side of the boundary:
`pixi run python -m pytest cli/tests`, whose engine-needing half skips
without a built engine.

## 4. The substrate

### 4.1 FreeCAD `[FreeCAD-inherited]`

What the engine stands on (details and the removal ledger in
`docs/FREECAD.md`):

- `src/App` — `App::Document`, properties, expressions, **transactions** —
  the persistence and undo model the publisher relies on.
- `src/Gui`, eleven workbench Gui directories and their tests are deleted
  (Phase 8, ADR-214). Retained headless metatypes live in `App/MetaTypes.h`;
  all presets are headless and explicit GUI-on requests are rejected.
- `src/Base` — units, vectors, persistence primitives.
- `src/Mod/{Part,PartDesign,Sketcher,Assembly}` — the original capability
  areas; `src/Mod/{Mesh,MeshPart}` — the Phase 4 mesh domain substrate.
- Support trees: `Import`, `Material`, `Measure`, `Show`, `Test`.
- The 17 unused workbench trees were removed in Phase 1 (ADR-007..010).
  `docs/FREECAD.md` §3 records the Phase 8 directory deletion and the
  remaining GUI-lineage sources outside that boundary, still to audit.

### 4.2 MuJoCo `[Cadex-new dependency, upstream and unmodified]`

The dynamics kernel, and the only third-party Python package the engine
carries. It is in the **OCCT category** — a kernel we keep, not a tree we
fork (`docs/MUJOCO.md`) — and it is what makes dynamics a product
vertical rather than a feature bolted on.

- **`mujoco == 3.10.0`, exactly pinned**, for the same reason
  `occt == 7.8.1` is: MuJoCo's own `VERSIONING.md` disclaims cross-version
  numerical reproducibility, and `open_project` asserts digest equality on
  every open.
- **It arrives as a pypi wheel, not conda.** Adding any conda package forces
  a full re-solve, and the manifest has not been re-solvable since
  conda-forge moved past our `occt` and `qt6-main` pins.
  `CARRIED_PYPI_PACKAGES` in
  `package/rattler-build/scripts/relocate_conda_environment.py` carries it
  into the payload by name (ADR-076); the name exists so the exception is
  easy to find and delete the day the manifest is repaired.
- **53.5 MB in the payload, measured** — about 30 MB of which is
  `mujoco/experimental/`, the studio viewer the engine never imports.
  Pruning it is known and deferred (ADR-082 §4, ADR-102 §5).
- **`scipy.spatial`** joins it as `CadexDynamics`'s second deferred import
  (M3, for the convex-hull volume that refuses a part MuJoCo would silently
  hull). Both are imported inside functions, and both are therefore outside
  `cadexd`'s asserted module closure.
- **Nothing else.** No `jax`, no `mjx`, in the tree or in a staged payload —
  training is offboard (ADR-084) and a test asserts the negative.

## 5. Build & run

`pixi run setup-engine && pixi run build-engine` builds everything there
is: the engine, in the pixi/conda-forge environment (OCCT 7.8.1, conda
compilers, a conda sysroot). The dashboard and the CLI that runs the agent
are pure Python and vanilla JS under `cli/`, and need no build step. No step needs git-lfs or Xcode (ADR-498).

| Task | Builds | With |
|---|---|---|
| `pixi run setup-engine` | — | `git submodule update` for `src/3rdParty/OndselSolver` |
| `pixi run build-engine` | `build/release/bin/{FreeCADCmd,CadexGeometryWorker}` | pixi env, `BUILD_GUI=OFF` |
| `pixi run stage-engine` | `build/engine/cadex-engine-<v>-<os>-<arch>/` + its manifest | pixi env |

- Artifacts, engine: `build/release/bin/FreeCADCmd` and
  `build/release/bin/CadexGeometryWorker`. **There is no `FreeCAD` binary
  in any build** — that is the point of Phase 7: every preset is headless
  and `BUILD_GUI=ON` is rejected at configure (ADR-022, ADR-214).
- Run the engine's own tests with `pixi run test-engine` (equivalently
  `pixi run python -m pytest src/Mod/cadex/cadex_tests` — no build needed;
  FreeCAD is stubbed). Note that `pixi run test` is the *inherited FreeCAD
  ctest*, which is a different and much noisier thing.
  `pixi run python src/Mod/cadex/cadex_tests/cadexd_latency_integration.py`
  is the slider-drag latency bar, driven over raw NDJSON.
- **`training/` is built by nothing and installed by nothing.** It is not a
  step in this table and never will be; it is copied to a GPU box and run
  there with its own venv (ADR-084). `test_dynamics_policy_trainer` asserts
  that no CMake rule references the path.
- Packaging: `docs/cadex-release-packaging.md` — one bundle. The payload
  build **hard-fails if it cannot `import mujoco` and get exactly 3.10.0**
  out of the payload's own interpreter (`build_engine_payload.sh:323`), which
  is the gate that caught the dangling `bin/python` symlink the payload had
  been shipping for as long as the prune existed.

## 6. Open questions

- ~~**The warm-standby worker.**~~ **Closed by ADR-055.** cadexd owns one
  resident `FreeCADCmd --safe-mode` preview worker per open project, spawned
  lazily on the first `preview_params`, and it answers a pose-only parameter
  change with solved placements in **33 ms** against the accepting path's
  0.59 s on the same model. It is safe because it is a read-only oracle: it
  never writes the project store, never publishes, and never moves a
  revision or a digest, so every accepted byte still comes from a cold run
  with a fresh attempt directory.

  What is *not* closed is the accepting path's own ~0.42 s. A preview serves
  the parameters that drive motion — a component placement, a joint offset, a
  motion formula — and by construction cannot serve one that changes a
  definition, because a placement-only reply for `part.box(p.width, …)` would
  be a lie. Those sliders still pay a cold spawn, and the next lever for them
  would be keeping the candidate `App::Document` alive between runs, which is
  where every determinism guarantee gets hard and would be its own ADR.
- **`display` on `open_project`** (A1). Would fold the restore pass and the
  hydration rebuild into one script run; the measured cost of not having it
  is 0.49 s, paid on the first engine request against a project.
- Whether `CadexModelingSurface.py`'s surface resolution collapses further
  now that one global project surface exists and no provider consumes it.
- What remains of `CadexProject.py` once the conversation store is gone —
  the script store already moved to `CadexScriptStore.py`.
