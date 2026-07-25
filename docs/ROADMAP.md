# ROADMAP.md — Phases and Status

Verified against source: 2026-07-24

Living status lives **here** (check the boxes as work lands); decisions land
in `docs/DECISIONS.md`; the destination is `docs/VISION.md` and
`docs/INTEGRATION.md`.

Dependencies: 0 → 1 → 2 strict; 3 and 4 run in parallel after 2; 5 needs 2;
6 needs 4 + 5; 7 needs 6.

```
0 truth ─► 1 shrink ─► 2 one-script ─┬─► 3 Qt UX (capped)
                                     ├─► 4 mesh domain ──┐  (gate: confirm
                                     └─► 5 cadexd split ─┴─► 6 Blender shell ─► 7 convergence
```

---

## Phase 0 — Truth & hygiene `(this run, 2026-07-24)`

**Goal:** a repo whose docs and code tell the truth, so future agents start
from facts instead of re-exploration.

- [x] Documentation set written (`README.md`, `CLAUDE.md`, `docs/*.md`).
- [x] Stale `_DOMAIN_WORKER_BUNDLES` entries deleted (14 culled domains) —
      `src/Mod/cadex/CadexScriptedRuntime.py:65`.
- [x] Dead lazy imports of deleted `xscript_*` workers pruned from
      `src/Mod/cadex/CadexScriptedDomains.py`.
- [x] `AGENTS.md` retired; change policy now in `CLAUDE.md`.
- [x] Stale docs moved to `docs/history/` with superseded banners
      (`vibescript-system-design-feasibility.md`, `RUNTIME_VERIFICATION.md`).

**Exit criteria:** build green, cadex_tests green, no doc outside
`docs/history/` describes the 18-domain/multi-engine state as current.

## Phase 1 — Source-tree reduction

**Goal:** `src/Mod/` contains only what the product uses.

- [x] Dependency audit of removal candidates (`docs/FREECAD.md` §3) against
      kept trees; record order — grid de-Drafted first (Phase 1.3), assembly
      BOM dropped (ADR-008), then batch A / batch B.
- [x] Per tree, two commits: (1) disable in `src/Mod/CMakeLists.txt`, verify
      build + launch + tests; (2) delete the tree, verify again — ADR-007
      (batch A), ADR-009 (batch B).
- [x] Log each removal in `docs/DECISIONS.md` — ADR-007…ADR-010.
- [x] Sweep the dead culled-domain branches inside `src/Mod/cadex/`
      (`CadexScriptedDomainPublication.py`, domain-name checks in
      `CadexScriptedRuntime.py` / `CadexScriptedDomains.py`) — ADR-010.

**Exit criteria:** every tree under `src/Mod/` is listed as "kept" in
`docs/FREECAD.md`; full build, launch, and test pass.

## Phase 2 — One project script

**Goal:** a single top-level script is the sole source of truth
(`docs/XSCRIPT.md` Part II).

- [x] Design: script layout, project-level params, domain-API composition,
      assembly composition (ADR-011).
- [x] Runtime: execute the project script (one multi-domain worker; the
      per-domain tool surface dissolved in the Phase 2.4 swap, ADR-013) —
      `CadexScriptedRuntime.py`.
- [x] Project-level parameters declared and bound (`params`/`num` in the
      script, values patched via `xscript.project.set_params`; the retired
      per-program controls tool is gone, ADR-013). Parameters-panel sliders
      read `param_specs` and commit via `set_params` (ADR-014).
- [x] Publisher lint: reject any untagged object; orphan GC for objects with
      no owning script region. (`publish_project_candidate` — one
      transaction, `CadexScriptedOwnership` closure/lint/orphans, ADR-012.)
- [x] Headless rebuild command with content digest over produced geometry
      (`cadex_rebuild.py`, `pixi run rebuild <root>`).
- [x] CI test: delete document → rebuild from script → digest matches
      (`test_project_rebuild.py`, ctest `CadexProjectRebuildDigest`;
      rebuild-vs-accepted and rebuild-vs-rebuild equality verified).

**Exit criteria:** the digest CI test passes; no user-visible multi-program
concept remains.

## Phase 3 — UX convergence (capped Qt investment)

**Goal:** the interim Qt shell approximates the product layout. **No Coin3D
rendering work** — this shell is disposable (`docs/INTEGRATION.md`).

- [x] Finish the 50/50 layout in `CadexExperimentalMode.py` /
      `CadexGui.py`: left viewport; right chat + sliders + tree + script
      view (read-only `CadexScriptView.py`; `resizeDocks` event filter,
      ADR-015).
- [x] Remove every route to native modeling tools and workbench switching
      (minimal menu, shortcut strip, tree lockdown, edit watchdog —
      ADR-015).

**Exit criteria:** a user session touches only chat, sliders, tree, script
view, viewport.

## Phase 4 — Minimal mesh domain `(landed 2026-07-24, ADR-016)`

**Goal:** the fourth-plus capability area, through the same pipeline.

- [x] `src/Mod/cadex/cadex_mesh_api.py` / `cadex_mesh_worker.py` on
      `Mod/Mesh` + `Mod/MeshPart`: import (`mesh.import_file` from the
      project `assets/` dir), tessellate (`mesh.from_shape`), boolean
      (`union`/`difference`/`intersection`), decimate; export via the
      existing `file.export_model` mesh path. No interactive mesh editing
      (that waits for BMesh in the Blender shell).
- [x] Register the domain pack + worker bundle; guardrail tests updated
      (`test_mesh_domain.py`; tool surface unchanged — capability packs
      carry no tools).

**Exit criteria:** mesh programs run/publish/rebuild like the other domains.
Verified 2026-07-24: mixed part/assembly/mesh scripts (tessellate, boolean
union, decimate, STL import) publish `Mesh::Feature` objects and rebuild
digest-stable across repeated headless runs on both FreeCAD builds — via
canonical vertex/facet reordering plus a vertex-set digest fingerprint,
since the native mesh set operations return run-dependent orderings and
triangulations (ADR-016; the digest CI now seeds mesh outputs too).

> **Decision gate before Phase 5:** re-confirm the Blender-shell endpoint
> against the measured criteria in `docs/INTEGRATION.md` (tessellation and
> picking fidelity, slider-drag latency, rebuild determinism).
> Status 2026-07-25: engine-side evidence gathered (determinism passed;
> latency baseline and ID-map readiness measured — `docs/INTEGRATION.md`
> gate-status section). Owner decision: **hold at Phase 4**; the two
> shell-side criteria await a cadexd→Blender prototype when Phase 5 opens.

## Phase 5 — Engine/shell split (`cadexd`)

**Goal:** the engine runs as a headless service.

- [x] Extract project store + runtime + workers behind a JSON stdio
      protocol (`cadex-cadexd-v1`, `docs/INTEGRATION.md`: `open_project`,
      `describe_api`, `write_script`/`edit_script`/`set_params` (the
      sketch's `run` dissolved into the real lifecycle ops), `rebuild`,
      `resolve_pin`, `inspect`, `cancel`, `shutdown`). ADR-017.
- [x] Responses carry BREP + tessellation + face/edge ID maps
      (`cadex-tessellation-v1`, digest-neutral, adaptive deflection;
      headless `resolve_pin` closes the loop). ADR-017.
- [x] The Qt shell becomes the first protocol client (proves the
      boundary): `CadexdClient` + one-transaction `CadexShellHydration`;
      in-process path removed and guardrailed. ADR-018.

**Exit criteria:** the Qt app drives all modeling through cadexd with no
in-process fallback. **Met 2026-07-25** — ctest `CadexdLifecycle`
(kill -9 → respawn → restore digest equality, mid-run cancel) and the
switchover integration (median set_params drag 0.479 s ≤ 0.65 s bar) are
the evidence; `test_engine_shell_split_guardrails.py` pins the boundary.

## Phase 6 — Blender shell (in `/Users/theo/mesh`) `(landed 2026-07-25, ADR-019)`

**Goal:** `mesh_agent` gets a cadex backend (`docs/BLENDER.md` §5).

- [x] Backend proxying to cadexd (alongside the existing local-exec path) —
      "Cadex CAD" mode; `cadexd_client.py` (GPL NDJSON client, no cadex
      imports) + `cadex_backend.py` in the mesh repo.
- [x] Tessellated outputs into the Model collection with ID-map attributes
      (`cadex_hydrate.py`: `cadex_face` INT face attribute, edge-wire
      children, placement, contract-driven GC).
- [x] Params bridged to `scene.mesh_params`; slider drags → `set_params`
      (revision-guarded, draft-quality display while dragging + background
      standard refine — engine gained the `"draft"` tessellation preset).
- [x] Viewport picking → ID map → BREP pins (`resolve_pin`) —
      `cadex_pick.py`; pins attach to the next chat message.
- [x] One `undo_push` per chat turn (verified through the real bridge in
      cadex mode).

**Exit criteria:** the decision-gate fidelity/latency criteria pass in the
real shell. **Met 2026-07-25** — `tests/python/bl_mesh_agent_cadex.py`
(headless Blender against release cadexd): picking fidelity 100%
(372/372, bar ≥ 99%) with per-face aggregates matching engine truth;
slider-drag median 0.548 s ≤ 0.65 s including tessellation streaming;
restart rehydration. Evidence in ADR-019 and
`docs/INTEGRATION.md` gate status.

## Phase 7 — Convergence `(landed 2026-07-25, ADR-020…024)`

**Goal:** one product.

- [x] **Blender shell gaps closed** (mesh repo, M1–M8): manifest-based
      engine discovery + `preflight()`; deferred tool replies so a rebuild
      no longer freezes Blender, with cancellation reaching the engine;
      sandbox budgets; an engine project that follows Save-As and does not
      leak across files; the restore pass on every open; `describe_cad_api`
      replacing a hand-written API listing in the prompt; `edit_script`,
      `inspect_model`, and a `scene_summary` that reports engine truth;
      conversation history and Claude session id in the `.blend`.
- [x] **Qt shell deleted** (C1–C7, ADR-021): the UI layer, the provider and
      session stack, and the protocol seam. 57 Python modules → 34; 36 test
      files / 425 tests → 20 / 154. `requirements.txt` deleted — the engine
      has no third-party Python dependency left.
- [x] **GUI build off** (C6b, ADR-022): `BUILD_GUI=OFF` for release and
      package configs; `isVibeExperimentalModeSession` reverted to stock,
      which *reduces* the fork's delta against upstream FreeCAD.
- [x] **One bundle** (P1–P4, ADR-023): an engine payload with a
      `cadex-engine.json` discovery manifest, gated by ctest
      `CadexEnginePayloadSmoke`; the Qt app packaging retired; the mesh
      repo carries, verifies and installs the payload, and gained its first
      CI.
- [x] **Onboarding** (O1–O3, ADR-024): Mesh is the default app template,
      Cadex the default mode, the engine needs no configuration, and engine
      failures reach the user.
- [x] Docs follow the shell: `docs/INTEGRATION.md` becomes the two-repo
      contract (its op table is now test-enforced against
      `CadexdProtocol.OP_ARG_SPECS`), `docs/BLENDER.md` the primary
      integration reference, `docs/cadex-release-packaging.md` the
      engine-payload doc.

**Exit criteria:** a new user only ever sees the Blender shell.
**Met 2026-07-25** — with `MESH_FREECADCMD`, `MESH_CADEXD_MODULE` and
`MESH_CADEX_ENGINE` all unset, against an engine payload placed where the
bundle carries it: Cadex-mode preflight is green with zero configuration,
and `tests/python/bl_mesh_agent_cadex.py` reports `CADEX-BLENDER-GATE` ok
with `engine_from_bundle: true` — picking 372/372 (bar ≥ 99%), slider-drag
median 0.572 s (bar ≤ 0.65 s), restore performed and digest-matched,
cancellation answered `RUN_CANCELLED`, and 120 main-thread ticks during a
1.52 s rebuild. This repository no longer builds a product: `bin/` is
`FreeCADCmd` and `CadexGeometryWorker`.

## Phase 8 — Remove the `src/Gui` tree

**Goal:** delete what Phase 7 stopped building.

`BUILD_GUI=OFF` was the **disable commit** for `src/Gui` under
`docs/FREECAD.md` §3's removal protocol (ADR-022). The delete commit is
this phase.

- [ ] Dependency audit: `src/Gui` (66 MB, 729 files) plus every
      `src/Mod/*/Gui`, `tests/src/Gui`, and the `setup_qt_test` helper.
- [ ] Delete, with the `BUILD_GUI` guards that Phase 7 added removed rather
      than left dangling.
- [ ] `docs/FREECAD.md` §1 row moves from "present, not built" to deleted;
      DECISIONS entry.

**Exit criteria:** the tree contains no GUI source, `pixi run configure`
(debug) still configures, and both cadex ctests stay green.

**Not in scope:** re-adding a GUI of any kind. The product's interface is
the Blender shell.

## Later — identified, not scheduled

- **Warm-standby worker.** The per-drag `FreeCADCmd --safe-mode` spawn
  (~0.4–0.5 s) dominates the ~0.55 s slider median. A warm worker inside
  cadexd is the named lever for sub-100 ms drags.
- **A1: `display` on `open_project`.** Would fold the restore pass and the
  hydration rebuild into one script run; measured cost of not having it is
  0.49 s per project open.
- **Linux and Windows shell bundles.** The engine payload builds for both;
  only macOS arm64 has shell CI.
- **macOS notarization of the embedded engine.** Hardened runtime and
  per-binary entitlements for a `freecadcmd` that spawns subprocesses and
  dlopens OCCT.
