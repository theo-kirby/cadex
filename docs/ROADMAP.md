# ROADMAP.md — Phases and Status

Verified against source: 2026-08-01

Living status lives **here** (check the boxes as work lands); decisions land
in `docs/DECISIONS.md`; the destination is `docs/VISION.md` and
`docs/INTEGRATION.md`.

Phases 0–7 built the engine/shell split on two forks. Phases 8–13 reduce
both forks toward one application we own, keeping OCCT (ADR-025).

**Phase 13a came early (ADR-030).** Merging the repositories never depended
on owning the engine or the shell — it was a repo-layout and
build-orchestration job, and doing it first is what turns "clone, build,
run" into one flow. Its consequence is that **11 and 12 are no longer on
anyone's critical path**: they become optional internal swaps behind the
unchanged protocol, unscheduled and unblocked, while 13b — deleting from
both inherited trees, in place — is the work that actually pays down size
and coupling. They are not cancelled; the test-pinned protocol is precisely
what keeps them available.

Dependencies: 0 → 1 → 2 strict; 3 and 4 run in parallel after 2; 5 needs 2;
6 needs 4 + 5; 7 needs 6. Then 8, 9 and **13a** are independent; **10 gates
11**; 12 needs 11; 13b needs 13a and otherwise runs forever.

```
0 truth ─► 1 shrink ─► 2 one-script ─┬─► 3 Qt UX (capped)
                                     ├─► 4 mesh domain ──┐  (gate: confirm
                                     └─► 5 cadexd split ─┴─► 6 Blender shell ─► 7 convergence
                                                                                    │
   ┌────────────────────────────────────────────────────────────────────────────────┘
   ├─► 8 delete src/Gui
   ├─► 13a MERGE (done) ─► 13b source reduction, ongoing ──────────────┐
   └─► 9 one surface ─► 10 probe + characterize ═► 11 our engine ─► 12 our shell
                                    (go/no-go)      └── unscheduled, behind the unchanged protocol ──┘
```

**Every resting place is shippable.** A stall anywhere after 13a leaves a
working, buildable, launchable product; that ordering is the point
(ADR-025, ADR-030).

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
- [x] **External geometry as a first-class input** `(landed 2026-07-26,
      ADR-043)`. Phase 4 shipped an ingest path nothing could reach: no
      product surface wrote `assets/`, an import could not be moved, could
      not enter the BREP domains, and could only be measured on the rebuild
      that produced it. Four changes closed it — the `put_asset` op plus
      **File → Import Geometry…** and the `import_geometry` tool;
      `mesh.transform`; `inspect scope="output"` and `scope="assets"`;
      `part.shape_from_mesh`.
- [x] **Save-As carries imported geometry** `(landed 2026-07-26, ADR-046)`.
      ADR-043's new input class broke the Save-As story it was not written
      for: the new project got no `assets/`, so "re-run the saved script"
      died on the first `mesh.import_file` — and the button offering it was
      unreachable anyway, gated on an engine session Save-As had just
      closed. Assets now migrate through `put_asset` on adopt; derived
      state (artifacts, revisions, history) still does not.

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
the evidence; the boundary was pinned by
`test_engine_shell_split_guardrails.py`, which was folded into
`test_engine_purity_guardrails.py` when Phase 7 deleted the protocol seam
it guarded — that is the file to read today.

## Phase 6 — Blender shell `(landed 2026-07-25, ADR-019)`

*(Built in `/Users/theo/mesh`; that tree is `shell/` in this repository
since ADR-030, and the paths below now read relative to it.)*

**Goal:** `mesh_agent` gets a cadex backend (`docs/BLENDER.md` §5).

- [x] Backend proxying to cadexd (alongside the existing local-exec path) —
      "Cadex CAD" mode; `cadexd_client.py` (GPL NDJSON client, no cadex
      imports) + `cadex_backend.py`.
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
- [ ] **`cadex_assembly_worker.py:2038` imports `CommandCreateView`** —
      GUI-lineage code used headlessly for exploded views, and the one
      import that makes this deletion more than mechanical. Resolve it
      here, not in Phase 11 (ADR-025).
- [ ] Delete, with the `BUILD_GUI` guards that Phase 7 added removed rather
      than left dangling.
- [ ] `docs/FREECAD.md` §1 row moves from "present, not built" to deleted;
      DECISIONS entry.

**Exit criteria:** the tree contains no GUI source, `pixi run configure`
(debug) still configures, and both cadex ctests stay green.

**Not in scope:** re-adding a GUI of any kind. The product's interface is
the Blender shell.

## Phase 9 — One surface, and make the contract real

**Goal:** subtraction, plus three cheap items that everything downstream
depends on. Independent of Phase 8.

- [x] **ADR-025** — the direction change: one project, OCCT kept, FreeCAD
      and Blender dropped.
- [x] **Delete the local bpy modes**: `cad_api.py` (431), `validation.py`
      (183), `scene_graph.py` (47), most of `model_api.py`, `modes.py`'s CAD
      overlay, the local branches of `tools.py` / `model.py`, and
      `tests/python/bl_mesh_agent_cad.py` (472). `modes.py` collapsed; mode
      dropdown dropped. *Landed 2026-07-25 with the merge (ADR-030): net
      −1,953 lines, and with them the BOOLEAN/BEVEL modifiers, depsgraph,
      BVHTree and `orphans_purge` coupling — the largest single decoupling
      win available on the shell side. Four tests in `bl_mesh_agent.py` that
      drove the deleted path went too.*
- [x] **Delete the app template** (294 lines, then 340) that exists purely to
      suppress Blender's UI. *Landed 2026-07-26 (ADR-037): 340 → 98 lines. The
      layout is now `Mesh/startup.blend`, which only became possible once the
      chat and parameter columns were real editor types (ADR-035) — a saved
      screen can record area types, and until then the area types were lying.
      What survives enables the add-on and sets up the top bar, neither of
      which a `.blend` can carry — and the bar carries the Cadex File and Edit
      menus since ADR-041, having been blank between ADR-037 and it. Guarded by
      `test_startup_layout_is_the_shipped_file` in the gate.*
- [x] **Delete the dead publication paths** in
      `CadexScriptedDomainPublication.py` — the robot / FEM / inspection /
      points branches no live domain can reach. *Landed 2026-07-25
      (ADR-026): 7,012 → 3,613 lines, 48% removed.*
- [x] **Response-schema fixtures.** `OP_ARG_SPECS` pins *requests* only; the
      shell reads ~50 response keys that nothing asserts. A golden
      shape-only fixture per op. This is what makes "replace either side
      independently" true rather than assumed. *Engine side landed
      2026-07-25 (ADR-027); wiring the validator into the live lifecycle
      found three shapes the recording missed.*
- [ ] **Assert the same fixtures from the shell side**
      (`shell/tests/python/`) — the other half of "asserted at both ends".
      More valuable since ADR-030, not less: one repository removed the
      distance that used to enforce the boundary, so the tests are now the
      only thing that does.
- [x] **Pin the OCCT version and gate subshape enumeration.** BOPAlgo's
      ordering is not a documented contract and has changed across OCCT
      releases; today one `pixi update` silently re-indexes every saved
      script. *Landed 2026-07-25 (ADR-027): `occt = "==7.8.1"` + ctest
      `CadexSubshapeEnumeration`.*
- [x] **The target case works at all.** Ahead of any speed work: joints
      failed headless (ADR-047), simulations could not publish (ADR-048),
      and a solved assembly never reached the viewport because nothing in
      the response said which output a component instanced (ADR-049). All
      three were invisible because no live test built a joint. A simulation
      now plays in the viewport (ADR-050).
- [x] **The drag is off the main thread** (ADR-051). One request in flight
      per project, the rest coalesced; a 12-event burst becomes 2 requests.
      *Stated limit:* `ensure_open` still blocks the first drag of a session.
- [x] **The cold-path diet** (ADR-052) and **shared sub-expressions built
      once** (ADR-053). Engine median 0.505 s → 0.417 s plain,
      0.610 s → 0.473 s with the shell's draft display; gate slider median
      0.578 s → 0.537 s.
- [ ] **Subelement details on demand** (would have been ADR-054).
      **Not doing this**, with the measurement on record: computing
      `face_details`/`edge_details` costs **17.7 ms** on the 98-face baseline
      plate (32.9 ms vs 15.2 ms at `max_subelements=0`) — about **4.2%** of a
      0.417 s drag. Not worth moving a computation across a process boundary
      and changing `inspect`'s cost model for. The item stays here with its
      number attached so it can be revived if output counts grow.
- [x] **Warm-standby worker** (ADR-055). cadexd owns one resident
      `--safe-mode` preview worker per open project, spawned lazily on the
      first `preview_params`, bound to one `(source, api_contracts, assets)`
      generation and killed by anything that changes them. It answers a
      **pose-only** parameter change with solved placements and writes
      nothing at all — the invariant is asserted over the store's full file
      list, sizes and mtimes across a burst of previews.
      *Measured on the baseline part in a jointed assembly:* **33 ms**
      median against the same model's **0.588 s** accepting run — 17.8×, and
      better than the 60–80 ms this was expected to land at. First preview of
      a drag is 0.305 s (spawn + generation load), once per drag rather than
      once per frame.
      *Stated limit:* a preview serves the parameters that drive motion and
      by construction cannot serve one that changes a definition, so the
      headline applies to a subset of sliders; the rest fall back to the
      debounced `set_params`, which is still the only thing that makes a
      change real.
- [x] **The shell's preview dispatch** (ADR-055). Its own ~30 Hz pump, one
      request in flight, intermediate values dropped, never debounced — a
      33 ms engine behind the 150 ms debounce would still be a 150 ms drag.
      The reply is placements, not a display block, so it sets `matrix_world`
      on the component instances with no hydration in the path at all.
      **5.6 ms** median through the gate, against its 0.496 s slider median.
      Degrading is part of the contract: a refusal latches previews off for
      that parameter's drag, lifts when a different parameter moves or the
      drag settles, and never reaches `model.last_error()`.

**Exit criteria:** one script format across the product; both new gates
green; slider median materially below 0.548 s *(met: 0.496 s end-to-end,
0.389–0.42 s engine-only; and 5.6 ms end-to-end for a motion slider, which
is a different path rather than a better number on this one)*;
`CADEX-BLENDER-GATE` still ok.

## Phase 10 — Probe, then characterize `(the go/no-go gate)`

**Goal:** find out, in month 1 rather than month 20, whether Phase 11 has a
known shape — and what it costs.

**10a — The enumeration probe.** `[x] Ran 2026-07-25 — ADR-028.` One
throwaway C++ binary against the OCCT we already link: build
`box → cut(cylinder×4) → fillet` through raw `BRepPrimAPI` / `BRepAlgoAPI` /
`BRepFilletAPI` in three variants (no refine, `ShapeUpgrade_UnifySameDomain`,
vendored `BRepBuilderAPI_RefineModel`), dump `TopExp::MapShapes` order with
per-face `BRepGProp` mass / COM / normal, and diff against today's engine's
`face_details`.

**Outcome: the first branch.** The vendored-refine variant matches
ordinal-for-ordinal — the contract is reproducible, `modelRefine` is the only
special case, Phase 11 has a known shape. Saved scripts are not invalidated
and the pin/index contract stands. Three things the probe turned up:

- The canonical shape above **cannot discriminate between the variants** —
  `removeSplitter` is a no-op on it (cylinders through a box leave no coplanar
  split). A second shape — two boxes fused across a shared face — was needed
  to run the probe at all. `test_subshape_enumeration.py` is still a valid
  OCCT-drift tripwire, but it does not cover refine.
- `ShapeUpgrade_UnifySameDomain` is **not** a drop-in for `modelRefine`: same
  face and edge counts, different ordering (89 differing ordinals). Valid
  shape, reconciling counts, every saved index silently changed meaning.
- `modelRefine.{h,cpp}` vendors cheaply — raw OCCT plus two stub headers, no
  other FreeCAD dependency. Probe output is deterministic across runs.

**10b — Kill index arguments.** `[x] Landed 2026-07-25 — ADR-029.` The five
index-taking ops (`subshape`, `defeature`, `fillet`, `chamfer`, `thicken`)
take a geometric selector; the `Sequence[int]` form is deleted. The
tessellation sidecar gained `face_keys`, one fingerprint per `face_ranges`
span. Worth doing on its own merits, as expected — those indices broke on
any parameter change that altered topology.

Three things the work turned up:

- The vocabulary had to be **extracted first, and there was no choice**:
  `cadex_partdesign_worker` imports `cadex_part_worker`, so the part domain
  could not reach `_query_subelements` without a cycle. That is why the ops
  still took integers. Phase 11a's extraction item is therefore **done** —
  `CadexSubshapeQuery.py` — and `resolve_pin` no longer pulls the partdesign
  feature stack into cadexd to fingerprint one face.
- **Cylindrical faces carried no `radius_mm`**, so "the four 3 mm holes"
  matched nothing while looking reasonable. Fixed; the ADR-027 golden was
  regenerated only after proving the change field-additive.
- **The payload gate did not notice a missing module.** `CMakeLists.txt` is
  hand-maintained and the new module was absent from the shipped payload
  while every source-tree gate stayed green. Now pinned by
  `test_every_engine_module_is_installed_by_cmake`.

Still open on the shell side (`shell/scripts/addons_core/mesh_agent/`):
nothing yet *writes* a selector into a script from a click, so click →
durable argument is half built. `resolve_pin` gives the shell the
fingerprint; turning that into a selector argument in the script is the
missing step.

**10c — Characterization corpus, time-boxed.** Record golden outputs from
the *current* engine before it is touched. Three tiers: ~500 op
characterizations generated mechanically from the API signatures (including
failure envelopes — the agent reads `failure_code` / `observed` /
`correction` and acts on them); ~50 composition scripts with deliberate
index chains; parametric sweeps across declared ranges, which is where the
topology-change boundaries live.

> **Gate.** Characterize 10 of the deepest ops (`loft`, `sweep`, `thicken`,
> `offset2d`, `slice`, `project`, `repair`, `defeature`, `general_fuse`,
> `sew`) and **time it**. If 10 ops take a week, 94 take 2–3 months of
> archaeology before a line of the new engine exists. That number — not the
> size of the binding — decides whether Phase 11 starts.

## Phase 11 — The engine becomes ours `(unscheduled since ADR-030)`

**Goal:** direct-OCCT workers behind the **unchanged** protocol, one domain
at a time. Each domain ships on its own; the shell never notices.

**Not cancelled, and not scheduled.** Phase 13a removed the reason to hurry:
the product builds and ships from one repository on the inherited engine, so
this is now an internal swap taken when the 10c gate says the economics
work, not a milestone anything waits on. Everything below stands; only the
deadline pressure is gone.

- [ ] **11a — Binding + oracle.** A pybind11 module over the ~120 OCCT
      symbols actually used. The differential oracle is built from
      `CadexGeometryWorker.cpp`'s BVH and includes a **two-sided Hausdorff
      check** — the only thing that catches the compounding-index failure
      mode, where counts, volume and COM all match while a face is in the
      wrong place. Vendor `modelRefine.{h,cpp}` here as an explicit
      deliverable — ADR-028 confirmed it is load-bearing, not housekeeping,
      and that the oracle must include a **refine-firing shape** or it will
      not detect a wrong refine. ~~Extract `_subshape_geometry` /
      `_query_subelements` out of `cadex_partdesign_worker`~~ — **done in
      Phase 10b** (`CadexSubshapeQuery.py`, ADR-029); 10b could not proceed
      without it. Both implementations run in-process in `FreeCADCmd`, so
      the harness is a pytest fixture, not a pipeline.
- [ ] **11b — `mesh` (7 ops).** The cheapest place to prove the process.
      Swap to **manifold**; ADR-016's determinism workaround layers 1 and 3
      become unnecessary. *Contract change to flag:* manifold requires
      manifold input, and `mesh.import_file` accepts arbitrary user
      STL/OBJ/PLY. ADR-043 widened the blast radius rather than narrowing
      it — `part.shape_from_mesh` now feeds imported meshes into the BREP
      domains, so this swap has to keep `makeShapeFromMesh`'s ingest
      reproducible too, not merely the mesh outputs. A known, accepted cost.
- [ ] **11c — `part` (50 ops).** Proves the binding. Not "nearly all direct
      OCCT": `removeSplitter` (default-on for every boolean), `slice`,
      `offset2d` and the angular-deflection constant are FreeCAD-original —
      ~2,200 lines to vendor or re-derive.
- [ ] **11d — `sketcher` (12 ops, 32 constraint variants).** Vendor
      planegcs; rewrite the translation layer. *The oracle is weaker here by
      nature:* underconstrained sketches have no unique solution, and the
      redundant/conflicting index sets come from an ordering-sensitive
      rank-revealing QR. Compare DoF exactly, solver-code category, solved
      geometry only for fully-constrained sketches, and set **cardinality**
      rather than membership.
- [ ] **11e — `partdesign` (19 ops).** Hard-depends on 11d
      (`cadex_partdesign_api.py:311` instantiates `SketcherDomainAPI`; the
      worker imports from `cadex_sketcher_worker`). ~6k lines of new
      feature-history semantics plus a documentless execution model.
- [ ] **11f — `assembly` (8 ops, 13 joints).** The largest. Vendor
      OndselSolver; rewrite the 2,218-line bridge and ~4,900 lines of
      FreeCAD Python whose joints are `App::FeaturePython` proxies driven by
      the document's recompute graph. *Oracle:* compare **joint residuals**
      and relative transforms, never absolute placements — with residual DoF
      the solution is gauge-free.
- [ ] **STEP import/export.** `file.export_model` / `file.import_model` are
      named in `CadexModelingSurface.py` with no implementation and no
      cadexd op; the only export today is `bpy.ops.wm.stl_export` of
      *display tessellation*. First-class engine deliverable (ADR-025).

There is no "11g". Removing `App::Document` is not a final phase — 11d, 11e
and 11f each carry their own "invent a documentless execution model" clause.
Only the publication residue is left over at the end.

**Exit criteria:** no `import FreeCAD` anywhere under `src/Mod/cadex/`; the
differential harness green per domain; `CADEX-BLENDER-GATE` still ok on the
unchanged protocol.

## Phase 12 — The shell becomes ours `(unscheduled since ADR-030)`

**Goal:** Rust + wgpu + egui against the now-ours engine, over the
**unchanged** protocol.

Same status as Phase 11, and the same reasoning. Note one thing the merge
*did* change here: the exit criterion used to end "then delete
`/Users/theo/mesh`". The Blender shell is now `shell/` in this repository,
so finishing this phase means deleting `shell/` — a much larger and more
visible act than dropping a sibling checkout, and correspondingly one that
needs the gate ported first, not promised.

Beyond the obvious (mesh upload with a face-ID channel, camera navigation,
chat / sliders / transcript, Claude Code subprocess + MCP bridge, protocol
client), the items that are secretly expensive:

- [ ] **Undo is a distributed subsystem, not a widget.** Today one
      `bpy.ops.ed.undo_push` covers script, params, geometry and transcript.
      In Rust, undoing a parameter change must push `set_params` back
      through the engine's `expected_revision` guard without tripping
      `STALE_PROGRAM_REVISION`.
- [ ] **Headless mode, architected from day one.** The gate suite runs today
      only because `blender --background --python` exists. Offscreen wgpu, a
      scriptable driver and deterministic frame stepping must precede the
      first widget; retrofitting this is painful.
- [ ] **Parameter panel (~2–3k lines).** Unit-aware formatting,
      drag-vs-commit feeding the draft/standard two-tier request,
      persistence by id across script edits, and the debounce +
      background-refine state machine.
- [ ] **Picking via an ID-buffer pass, not a BVH raycast.** We already ship
      a per-triangle face ID; render it to an `R32Uint` attachment and
      picking is one texel read — exactly consistent with what is on screen
      (a BVH is not, at silhouettes and thin faces), plus free hover
      highlight, in ~50 lines.
- [ ] Depth-biased wireframe (Blender's `display_type='WIRE'` child hides
      z-fighting silently), streaming transcript text layout, file dialogs,
      image pipeline + clipboard paste, preferences store, engine-crash UI.
- [ ] **An MCP shim with no bundled Python** — point the MCP `command` at
      our own binary with a `--mcp-server` flag (~150 lines).
- [ ] **One document.** A directory or zip replacing `.blend` + `.cadex`
      sidecar. `on_file_changed` exists solely to apologise when those two
      diverge; it dies here.

**Exit criteria:** `CADEX-BLENDER-GATE` ported — fidelity ≥ 0.99, median
≤ 0.65 s. Then delete `shell/`.

## Phase 13a — One repository `(landed 2026-07-25, ADR-030)`

**Goal:** clone, build, run — one flow.

Pulled to the front. It needed neither Phase 11 nor Phase 12: the seam
between the two repositories was already a process boundary (NDJSON, pinned
on requests *and* responses), so this was a repo-layout and
build-orchestration job, not an architecture one.

- [x] The shell imported under `shell/` as a squashed snapshot of
      the `mesh` repository @ `ac5af55948d`. `lib/*` stay submodules; the
      FreeCAD tree stays at the root, so no CMake path, pixi task, test or
      doc reference moved. Pre-merge history at
      `github.com/theo-kirby/mesh` (branch `mesh-main`); local working copy
      deleted 2026-07-25.
- [x] One build: `pixi run setup && pixi run app`, via `setup` /
      `build-engine` / `stage-engine` / `build-shell`. The shell configures
      in a **scrubbed environment** (`package/app/build_app.sh`) — the one
      real technical risk in the merge, since conda on `PATH` resolves the
      wrong zlib/png/OpenSSL/Python. Verified by construction: the shell's
      `CMakeCache.txt` is identical to a pre-merge one apart from the source
      path.
- [x] The cross-repo payload machinery deleted: `fetch_cadex_engine.py`,
      `cadex_engine.txt`, and `mesh-build.yml` + `cadex-engine.yml` folded
      into one in-tree `cadex-app.yml`.
- [x] One application identity: `Cadex.app`, product name and bundle id.
- [x] Docs reconciled: `docs/INTEGRATION.md` is the *process* contract,
      `docs/BLENDER-TREE.md` is the shell's inherited-tree ledger,
      `README.md` is clone-and-build.

**Exit criteria.** A fresh clone plus `pixi run setup && pixi run app`
produces a launchable application, and `CADEX-BLENDER-GATE` reports
`ok:true` with `engine_from_bundle: true`, picking ≥ 0.99, slider median
≤ 0.65 s, and no `MESH_*` set. **Met 2026-07-25**, measured on an actual
fresh clone rather than inferred: ~21 min end to end (warm ccache), then
`ok: true`, `engine_from_bundle: true`, picking 372/372, median 0.579 s.
Numbers and caveats in ADR-030.

## Phase 13b — The source reduction `(ongoing)`

**Goal:** what the merge exists to enable. Both inherited trees shrink in
place, under the two-commit protocol (`docs/FREECAD.md` §3), one tree per
pair of commits, each independently verifiable against the same gates.

Not a phase that "completes" — a standing mode of work.

- [ ] Shell side (`docs/BLENDER-TREE.md` §4), where the disable commit is
      nearly free because these are already CMake options: `WITH_CYCLES`
      (`shell/intern/cycles`), the VSE, grease pencil, the compositor,
      `shell/locale/` (80 MB), most of `shell/tests/files/` (784 MB), the
      unused `shell/release/datafiles`.
- [ ] Engine side: Phase 8 (`src/Gui`, 66 MB) is unchanged and still
      pending (Phase 9's warm-standby worker landed as ADR-055). Two more
      found while
      documenting: `src/Mod/{Start,Test,Help}` build but are in no shipped
      payload (`docs/FREECAD.md` §1), and the staged payload is **2.3 GB**
      of which ~2.1 GB is development environment — two copies of LLVM,
      node, clang, CMake's docs (`docs/cadex-release-packaging.md`). The
      payload's "no GUI" gate also has a hole: it greps `Mod/` for
      `*Gui.so` and misses stale ones in `lib/`.
- [ ] One installer, one name; NOTICE file carries the vendored LGPL
      attributions (ADR-025).
- [x] Delete `/Users/theo/vibecad` — the dead predecessor of cadex
      (5.9 GB), together with `/Users/theo/mesh` (5.4 GB) now that the shell
      is in-tree. Both branch tips were pushed and verified against their
      GitHub remotes first (`cadex-teardown` was local-only until then);
      history is recoverable, the disks are not carrying it.

## Verification

Every phase keeps the existing gates green and adds one.

```bash
# unchanged throughout
pixi run python -m pytest src/Mod/cadex/cadex_tests
pixi run stage-engine && \
  CADEX_ENGINE_ROOT=build/engine/cadex-engine-<v>-<os>-<arch> \
  pixi run python -m pytest -q \
  src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py

# new in Phase 13a — the whole thing, from one place
pixi run setup && pixi run app       # builds engine + payload + shell, launches
pixi run gate                        # CADEX-BLENDER-GATE against the built bundle
#   -> {"ok":true, "engine_from_bundle":true, picking>=0.99, median<=0.65}
#   and no MESH_FREECADCMD / MESH_CADEXD_MODULE / MESH_CADEX_ENGINE set

# new in Phase 9  (also ctest CadexResponseSchemas / CadexSubshapeEnumeration)
pytest src/Mod/cadex/cadex_tests/test_response_schemas.py      # golden per-op response shapes
pytest src/Mod/cadex/cadex_tests/test_subshape_enumeration.py  # OCCT ordering fingerprint

# new in Phase 10b
pytest src/Mod/cadex/cadex_tests/test_subshape_selectors.py    # selectors resolve, indices rejected
#   the real-kernel case also runs against a payload:
#   CADEX_ENGINE_ROOT=<payload> pytest .../test_subshape_selectors.py

# new in Phase 11 — the differential harness, both engines in one FreeCADCmd
pytest src/Mod/cadex/cadex_tests/differential/ --domain=<mesh|part|sketcher|partdesign|assembly>
#   volume (rel 1e-9) / area (rel 1e-6) / COM / bbox, counts, ordering,
#   two-sided Hausdorff; tolerances reported, not asserted
```

## Risks

| Risk | Mitigation |
|---|---|
| **Unverifiability** — 84% of the `part` surface has no recorded behaviour | Characterization corpus recorded *before* porting; the Phase 10c time-box is the go/no-go |
| Subshape enumeration not reproducible | **Retired 2026-07-25 (ADR-028)** — the probe ran; raw OCCT reproduces it ordinal-for-ordinal with `modelRefine` vendored |
| A *substituted* refine silently re-indexes every saved script | ADR-028: `UnifySameDomain` matches counts but not order. Vendor `modelRefine`; the Phase 11 oracle must include a refine-firing shape |
| Index arguments silently build wrong geometry | **Retired 2026-07-25 (ADR-029)** — the five ops take geometric selectors; the index form is deleted |
| Phase 11 grind with no "done" signal | Per-domain gates; each domain ships behind the unchanged protocol |
| Response shape is unpinned | Golden fixtures in Phase 9 |
| Assembly is the biggest single item | Scheduled last; oracle on joint residuals, not placements |
| OCCT version drift re-indexes saved scripts | Pin the version; gate the enumeration |
| Stall midway | Order chosen so every resting place is shippable: engine done + Blender shell is a product |

## Off-phase — `cli/`, a headless CLI (ADR-061, 2026-07-31)

A second front end landed on **no phase**, for the same reason `part.cable`
did: it is new scope, not a work item any phase declared.

What shipped: `cli/` plus a `./cadex` shim — a third client of the cadexd
protocol, no Blender and no display, with four subcommands
(`-p`, `params`, `script`, `export`) of which exactly one spends tokens. No
engine change and **no protocol change**: `OP_ARG_SPECS`, the ADR-027
goldens and `docs/INTEGRATION.md`'s op table are untouched, which is the
point — a third client that needed the contract widened would have been
evidence against the contract. Documented in `docs/CLI.md`; suite in
`cli/tests` (76 tests, the engine-needing half skipped without a build).

- [x] `cli/` scaffolded; `pixi run python -m pytest cli/tests` green
- [x] the engine suite unchanged at 314
- [x] end to end on Linux: a fresh `-p` run produces a parametric script,
      STEP + STL and a `--json` envelope; `params --set` moves the digest
      with no `claude` spawned; `--resume` continues the conversation and
      the second turn edits the first turn's script
- [x] CI: `cli/tests` runs in both jobs of `cadex-app.yml`, after the engine
      build (half of it skips without one). The Linux job runs it twice —
      build tree and staged payload — on the ADR-023 argument.
- [ ] macOS: never run there **by hand**. Nothing in it is macOS-hostile —
      POSIX `flock`, a short unix socket path, `FreeCADCmd` — but "should
      work" is not evidence, and the `app` job above is where the evidence
      will first appear. Expect that job to be the one that finds anything.

**What it is for, and what it is not.** The point is a cost asymmetry, not a
GUI-less GUI: one expensive turn authors a parametric script, and a cheap
loop then sweeps it while an external simulator feeds results back. It is
also the first *second* caller the protocol has ever had, which is direct
evidence for the Phase 11/12 claim that either half is replaceable.

**Known gaps**, all deliberate and all recorded in ADR-061: export runs as a
`FreeCADCmd` subprocess rather than an `export_model` op; BREP outputs only,
with mesh and component outputs reported `skipped`; no `resolve_pin`, no
offscreen rendering, so the agent verifies through `inspect` facts and
script stdout and is told so in its prompt; the CLI does not ship inside the
engine payload; Windows is not supported.

## Off-phase — the harness ops, experimental (ADR-056, ADR-057, ADR-062, ADR-063, ADR-065, 2026-07-27 → 2026-08-01)

Procedural wire routing landed on **no phase**. It is new scope, not a work
item any phase declared, and it is recorded here as experimental rather than
checked off against something it does not belong to.

What shipped: two part ops, `part.cable` and `part.bundle`, plus
`CadexRouting.py` and `CadexBundle.py`; no shell code and no protocol change
(`OP_ARG_SPECS` untouched, so the goldens and `docs/INTEGRATION.md`'s op
table are unaffected). `wcv8.cadex` is wired with 22 conductors across seven
routes: a twisted battery pair, three twisted phases per motor, and two
four-way flat ribbons.

`part.bundle` (ADR-057) lays N conductors about one shared centreline and
publishes one row per conductor. It reuses `part.cable`'s corridor, search,
spline fit and sweep wholesale — the extraction that made them shared changed
no numerics, proved by rebuilding the drone to an unchanged digest. What is
its own is the frame and the offsets, in `CadexBundle.py`.

**Then ports stopped being literals (ADR-062, 2026-08-01).**
`part.terminals` / `mesh.terminals` and `CadexTerminals.py`: a third
pure-Python module, still no shell code and still no protocol change. It
settles the first gap below and changes nothing for a script that does not
use it — literal ports take the same path and produce the same digest.

**Then the wires stopped ending in mid-air (ADR-063, 2026-08-01).**
`part.solder` and `CadexSolder.py`: a fourth pure-Python module, and a third
operation in a row with no shell code and no protocol change. One call is one
joint and one `solid` — the filled bore, the meniscus and the far-face cap,
with the lead cut out of them — sized entirely from a terminal, which is why
it takes a terminal and never a literal: a literal carries no radius, no
depth and no face. `wcv8.cadex` migrated onto terminals plus 42 joints, which
cost 0.21 s against the 18.1 s its 22 conductors already take, and which
removed thirteen hand-written `1/sqrt(2)` factors and six frozen world
constants. The migration also found that the drone's four motor leads were
never one spec placed four times — see ADR-063.

**Then the joint stopped looking like a cone (ADR-064, 2026-08-01).** The
meniscus became a concave arc, and with it the whole joint became **one solid
of revolution**: a closed outline, one face, one `revolve`, and no boolean at
all. That deleted the fuse, the cut, `CUT_OVERSHOOT_MM` and every kernel
hazard ADR-063 documented — nine OCC calls per joint down to three, and eight
joints on the probe plate from 54 ms to 20.9 ms. The risk moved out of OCC and
into pure Python, where a simple, correctly-wound closed loop is decidable
headless over a parameter sweep. No new parameters, no payload change, no
protocol change; the cost is one new refusal (a fillet shorter than the pad it
spans would undercut the board, and the default sits exactly on that floor)
and that **existing accepted projects must be re-accepted**, which is one
click or one `pixi run rebuild`. Both affected projects were re-accepted here.

**Then the harness became something you can see (ADR-065, 2026-08-01).**
`nets(ports=..., wires=...)` and `wire(...)` in a new pure module
`CadexNets.py`: connections declared as a table, on exactly the terms
`params()` already had — a declaration in the script whose current values live
in `script.json`. `set_params` grew one optional `nets` argument, and
`inspect scope="wiring"` publishes the harness as a graph: every terminal the
accepted run resolved, joined to its port and its output, plus the connection
table over them. The terminals were previously resolved inside the isolated
worker and **discarded**, which is why the shell saw `wiring-test.cadex`'s
seven components, ten cables and twenty joints as exactly two outputs. Scripts
predating `nets()` answer the scope read-only, reconstructed from the
`cable`/`bundle`/`solder` calls they made. No re-accepting: the digest hashes
outputs only, and the revision covers nets only when non-empty. The editor
that consumes this is not built.

What makes them experimental, and what would settle it:

- [x] **Ports are literals** — **settled by ADR-062 (2026-08-01).**
  `part.terminals` / `mesh.terminals` name a component's attachment points
  from its geometry: a `holes=`/`pads=` selector on a BREP board, a declared
  layout on an imported STL, ordered by a *direction* rather than by kernel
  enumeration. A hole terminal lands on its far face and carries the bore's
  depth as a stand-off floor, which is what made `route_path` take one
  stand-off per end. Terminals ride their component's placement, so one spec
  places four motors. `CadexTerminals.py` is the new pure-Python module; no
  shell code, no protocol change, and literal ports are unchanged, so a
  script that uses none rebuilds byte-identically. Still not built: writing a
  terminal into a script from a viewport click (Phase 10b), and mesh hole
  detection, which is deferred by decision rather than pending.
- [x] **The harness is invisible** — **settled engine-side by ADR-065
  (2026-08-01).** `nets(...)` declares the connections, `set_params(nets=)`
  edits them with no AI turn, and `inspect scope="wiring"` publishes the
  terminals the run resolved — which were previously resolved inside the
  isolated worker and discarded, so the shell saw `wiring-test.cadex`'s seven
  components, ten cables and twenty joints as exactly two outputs. Still not
  built: the wiring editor itself, which is what turns this from a readable
  payload into a window; and `part.bundle` as an editable graph concept,
  which is deferred by decision — changing a bundle's membership is a script
  edit.
- **A joint and its wire share a sliver above the board.** Zero *inside* it —
  the lead runs straight down the radius the joint's outline leaves empty —
  but the wire is a spline fitted through a searched route and starts to turn
  before the meniscus tops out. ~6% of the joint on the probe plate, and a
  wider stand-off makes it worse. Structural: `part.solder` takes a terminal,
  not a wire, and a joint must build whether or not a cable was routed to it.
- **Terminals cannot ride a non-uniform placement.** Refused rather than
  silently skewed (ADR-062). A pad has no radius and no depth, so a
  relaxation carrying only its point and normal is available and unbuilt; it
  is what keeps `wcv8`'s battery pair on literal ports.
- **Mesh obstacles are bounding boxes.** Fine for boards and motors, wrong
  for anything concave; the workaround is to pass such a body as a part
  solid.
- **Cost is not yet interactive.** ~0.75 s per cable on the drone, and a
  slider drag pays full price because moving a port invalidates the memo.
  Bundles help rather than hurt: the drone's 22 conductors rebuild in 17.0 s
  against 13.3 s for the 7 single wires they replaced, because a bundle is
  one search and N sweeps and a sweep is the cheap half.
- **A bundle's conductors do not fan out by port position.** Conductor `k`
  takes lay position `k`, so a `connections` list ordered against the pad
  layout crosses once near the breakout. Reordering the list fixes it; doing
  it automatically is not possible in general, because on a twisted run the
  phase rotates along the route and the two ends cannot both be matched.
- **`CadexRouting._sag` folds a run that is parallel to Z**, because sag is
  applied along −Z regardless of the run's own direction. Pre-existing and
  shared with `part.cable`, where it is silent; `part.bundle` refuses on it
  via its bend floor. Fixing it moves accepted digests, so it needs its own
  ADR — see ADR-057's closing note.

## Later — identified, not scheduled

- **A1: `display` on `open_project`.** Would fold the restore pass and the
  hydration rebuild into one script run; measured cost of not having it is
  0.49 s per project open.
- **Linux and Windows shell bundles.** The engine payload builds for both;
  only macOS arm64 has shell CI. Moot once Phase 12 lands — revisit then.
