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

## cadexd protocol sketch `[target — does not exist yet]`

Transport: JSON over stdio or a local socket (same shape as the existing
worker protocol, `WORKER_SCHEMA = "cadex-xscript-domain-worker-v2"` in
`src/Mod/cadex/CadexScriptedRuntime.py`). One cadexd process per project.

Requests (working sketch, to be designed properly in Phase 5):

| Request | Payload | Response |
|---|---|---|
| `open_project` | project slug / path | project manifest, script, params |
| `run` | script source + param values | per-output: BREP bytes, tessellation (verts/tris/normals), face/edge **ID maps**, diagnostics |
| `set_params` | param values only | re-run outputs (same shape as `run`), fast path |
| `rebuild` | — | full deterministic rebuild + content digest |
| `resolve_pin` | pin string (`@face-3`) or picked tessellation element | stable pin ↔ current topology mapping (via fingerprints, `CadexReferenceContracts.py`) |
| `inspect` | bounded query | same contract as today's `core.inspect` |

Every geometry response carries tessellation **and** the BREP so the shell
can both draw immediately and export/measure exactly. ID maps ride along as
per-face/per-edge attributes so shell-side picking round-trips to pins.

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

### Gate status (2026-07-25, engine-side evidence after Phase 4)

Criteria 1–2 need the cadexd→Blender prototype (they measure the shell
half); the engine-side halves were measured now so the prototype only has
to validate the transport and shell side:

1. **Tessellation & ID maps — engine half READY.** Per-face tessellation
   (`face.tessellate`) covers 100% of faces on the probe corpus (box, cone,
   torus, 98-face drilled+filleted plate: 0 faces without triangles), and
   every edge discretizes to a polyline — the per-face/per-edge ID map the
   protocol needs exists engine-side. Pin re-resolution machinery
   (`CadexReferenceContracts.resolve_interface`, fingerprint-based) is in
   place. Remaining: attribute transport into Blender + viewport picking
   fidelity (needs the prototype). Note: deflection 0.3 on the filleted
   plate produced 409k triangles in 1.2 s — the protocol should carry an
   adaptive/coarser deflection for interactive drags.
2. **Slider-drag latency — baseline measured.** Today's in-process path on
   a mid-size part (24-hole boolean + full fillet + mesh skin): ~0.57 s per
   set_params cycle end-to-end, of which ~0.55 s is spawning the fresh
   `FreeCADCmd` worker process. A persistent cadexd process eliminates the
   spawn cost per drag, so matching the baseline is the floor, not the
   ceiling.
3. **Rebuild determinism — PASSED engine-side.** Same script + params →
   identical content digest across process restarts and across two FreeCAD
   builds; 60+ consecutive seed/rebuild worker cycles clean, all five
   domains including mesh (canonical ordering + vertex-set fingerprints +
   definition-identified approximating ops, ADR-016). Each rebuild is a
   fresh process, which is exactly the cadexd-restart condition.

## Open questions

- Exact transport (stdio vs socket) and whether cadexd is per-project or a
  daemon multiplexing projects.
- Where conversation history lives post-split (cadexd project store, as
  today, vs the shell's .blend — leaning cadexd/`$CADEX_HOME`, shell caches).
- Progressive tessellation (stream coarse then refine) for slider latency.
