# INTEGRATION.md — Engine/Shell Split and the Blender Endpoint

Verified against source: 2026-07-25

How the three repos converge into one product. The decision below was
confirmed by the owner on 2026-07-24 (`docs/DECISIONS.md`).

Repos:

- **cadex** (`/Users/theo/cadex`) — this repo. FreeCAD fork; the xscript
  engine; today also a Qt shell.
- **mesh** (`/Users/theo/mesh`) — Blender 5.0.3-alpha fork with the
  `mesh_agent` prototype (`docs/BLENDER.md`).
- **vibecad** — parent fork; historical reference only (teardown history on
  its `cadex-teardown` branch).

## Options considered

| Option | Shape | Assessment |
|---|---|---|
| **A. cadex as base** | Keep the Qt/Coin3D app; invest in its UI until it feels right. | Rejected as endpoint. Coin3D/Quarter is a dead end for Blender-level viewport feel; every hour on Qt chrome is spent on a shell we don't want. |
| **B. Blender as shell** | Blender (mesh fork) is the UI; cadex runs headless as a geometry service. | **Confirmed endpoint.** mesh_agent already prototypes the exact target UX; BMesh solves mesh editing natively; the engine already runs headless (`FreeCADCmd`, worker subprocesses). |
| **C. Two-app bridge** | Both apps stay full apps; a live bridge syncs geometry. | Rejected: two documents of record, two undo systems, permanent sync complexity. |
| **D. Staged** | Keep working engine-side in cadex now; split engine from shell; then adopt a shell endpoint. | **Confirmed path**, with B as the endpoint. Near-term work stays in `src/Mod/cadex/**` and carries over unchanged. |

**Decision: D with B as the endpoint.** Cadex becomes **cadexd**, a headless
xscript geometry service; the mesh fork becomes the product shell. The Qt
shell remains the interim harness until Phase 7 (`docs/ROADMAP.md`).

### Why this is safe to commit to now

- Near-term phases (1–4) are engine-side: source-tree reduction, the single
  project script, a minimal mesh domain. All of it carries over to any shell.
- The decision gate before Phase 5 (below) re-validates the endpoint with
  measurements, not vibes.

## License reasoning

- cadex is LGPL-2.1+ (FreeCAD lineage); OCCT is LGPL-2.1. Blender is GPL-2+.
- Direction of flow is LGPL engine → GPL shell, across a **process boundary**
  (cadexd subprocess speaking a JSON protocol; no linking). This is clean:
  the GPL shell may talk to an LGPL service; neither codebase's license
  contaminates the other.
- The inverse (embedding GPL Blender code inside the LGPL app) would not be
  clean — one more reason the shell endpoint is Blender hosting the service,
  not cadex absorbing Blender code.

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
| `open_project` | `project_root`, `budgets?`, `restore?` | manifest + full script.json state; **restore pass** re-runs THE script into the fresh ephemeral document and asserts digest equality when an accepted digest exists |
| `describe_api` | — | `describe_project_api()` verbatim |
| `write_script` / `edit_script` / `set_params` | today's tool args + optional `display {quality, deflection, edges}` | **byte-identical** to the in-process tool payload (accept payload / `tool_failure` envelope, `STALE_PROGRAM_REVISION` guard included) + per-output `display {artifact_kind, artifact_path (abs), placement, tessellation\|null}` |
| `rebuild` | `display?` | explicit deterministic re-run of the stored script (same payload shape) |
| `resolve_pin` | `output`, `selection` (fingerprint query or `{element_type, index}`) | `{ok, output, revision, subelements, details}` against the accepted revision's staged BREP (`CadexPinResolution.py`) |
| `inspect` | today's `core.inspect` args | same contract; `document/object` serve the ephemeral doc, `script/api/image` the store; `selection` rejected (shell-only) |
| `cancel` | `request_id?` | acks and cancels the in-flight modeling request (`RUN_CANCELLED` flows to that request) |
| `shutdown` | — | graceful exit |

Server failure codes: `CADEXD_PROTOCOL_ERROR`, `CADEXD_BUSY` (one modeling
request in flight; read-only requests queue), `CADEXD_NOT_OPEN`,
`CADEXD_CRASHED` (client-side, on child death), `CADEXD_RESTORE_FAILED`.

Geometry responses carry the BREP artifact path **and** the opt-in
`cadex-tessellation-v1` buffers (f32 vertices / u32 triangles / f32 edge
polylines + sidecar `face_ranges`/`edge_polylines` mapping spans to the
exact 1-based Face/Edge enumeration of `face_details`), so a shell can
draw immediately and export/measure exactly; picking round-trips
triangle → `face_ranges` → `resolve_pin {element_type, index}`. Quality
presets `draft`/`coarse`/`standard`/`fine` (relative deflection 0.05 /
0.02 / 0.005 / 0.001 × bbox diagonal, clamped): `draft` exists for
progressive display — the Blender shell requests it during slider drags
and re-requests `standard` in a background `rebuild` once the drag
settles (ADR-019).

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
way.

### Gate status (2026-07-25, closed with Phase 6 — ALL CRITERIA MET)

Phase 6 (ADR-019) supplied the shell halves in the real Blender shell
(`/Users/theo/mesh`, `tests/python/bl_mesh_agent_cadex.py`, headless
Blender 5.3.0-alpha against release cadexd):

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

Engine-half history (pre-Phase 6 evidence):

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
- Where conversation history lives post-split (cadexd project store, as
  today, vs the shell's .blend — leaning cadexd/`$CADEX_HOME`, shell caches).
- ~~Progressive tessellation (stream coarse then refine)~~ — shipped
  2026-07-25 (ADR-019): drag requests `draft` quality, a cancellable
  background `rebuild` restores `standard` after the drag settles.
- The warm-standby worker for sub-100 ms slider drags (the per-drag
  `FreeCADCmd --safe-mode` spawn still dominates the 0.548 s median).
