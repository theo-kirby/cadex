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
      per-program controls tool is gone, ADR-013). The Parameters-panel
      slider rewire to `param_specs` lands in Phase 2.5.
- [x] Publisher lint: reject any untagged object; orphan GC for objects with
      no owning script region. (`publish_project_candidate` — one
      transaction, `CadexScriptedOwnership` closure/lint/orphans, ADR-012.)
- [ ] Headless rebuild command with content digest over produced geometry.
- [ ] CI test: delete document → rebuild from script → digest matches.

**Exit criteria:** the digest CI test passes; no user-visible multi-program
concept remains.

## Phase 3 — UX convergence (capped Qt investment)

**Goal:** the interim Qt shell approximates the product layout. **No Coin3D
rendering work** — this shell is disposable (`docs/INTEGRATION.md`).

- [ ] Finish the 50/50 layout in `CadexExperimentalMode.py` /
      `CadexGui.py`: left viewport; right chat + sliders + tree + script
      view.
- [ ] Remove every route to native modeling tools and workbench switching.

**Exit criteria:** a user session touches only chat, sliders, tree, script
view, viewport.

## Phase 4 — Minimal mesh domain

**Goal:** the fourth-plus capability area, through the same pipeline.

- [ ] `src/Mod/cadex/cadex_mesh_api.py` / `cadex_mesh_worker.py` on
      `Mod/Mesh` + `Mod/MeshPart`: import, tessellate, boolean, decimate,
      export. No interactive mesh editing (that waits for BMesh in the
      Blender shell).
- [ ] Register the domain pack + worker bundle; guardrail tests updated.

**Exit criteria:** mesh programs run/publish/rebuild like the other domains.

> **Decision gate before Phase 5:** re-confirm the Blender-shell endpoint
> against the measured criteria in `docs/INTEGRATION.md` (tessellation and
> picking fidelity, slider-drag latency, rebuild determinism).

## Phase 5 — Engine/shell split (`cadexd`)

**Goal:** the engine runs as a headless service.

- [ ] Extract project store + runtime + workers behind a JSON stdio/socket
      protocol (`docs/INTEGRATION.md` protocol sketch: `open_project`,
      `run`, `set_params`, `rebuild`, `resolve_pin`, `inspect`).
- [ ] Responses carry BREP + tessellation + face/edge ID maps.
- [ ] The Qt shell becomes the first protocol client (proves the boundary).

**Exit criteria:** the Qt app drives all modeling through cadexd with no
in-process fallback.

## Phase 6 — Blender shell (in `/Users/theo/mesh`)

**Goal:** `mesh_agent` gets a cadex backend (`docs/BLENDER.md` §5).

- [ ] Backend proxying to cadexd (alongside the existing local-exec path).
- [ ] Tessellated outputs into the Model collection with ID-map attributes.
- [ ] Params bridged to `scene.mesh_params`; slider drags → `set_params`.
- [ ] Viewport picking → ID map → BREP pins (`resolve_pin`).
- [ ] One `undo_push` per chat turn (already mesh_agent policy).

**Exit criteria:** the decision-gate fidelity/latency criteria pass in the
real shell.

## Phase 7 — Convergence

**Goal:** one product.

- [ ] Blender shell is the product; Qt shell demoted to engineering harness
      or removed (open question in `docs/VISION.md`).
- [ ] Packaging, onboarding, and docs follow the shell.

**Exit criteria:** a new user only ever sees the Blender shell.
