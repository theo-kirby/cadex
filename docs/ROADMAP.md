# ROADMAP.md — Phases and Status

Verified against source: 2026-08-05

Living status lives **here** (check the boxes as work lands); decisions land
in `docs/DECISIONS.md`; the destination is `docs/VISION.md` and
`docs/INTEGRATION.md`.

Phases 0–7 built the engine/shell split on two forks. Phases 8–13 reduce
both forks toward one application we own, keeping OCCT (ADR-025). **Phase 14
is the dynamics and control vertical** — closed, and the reason this branch
exists (ADR-086). **Phase 15 is the organic-modelling vertical**, opened by
the measurement ADR-123 asked for (`docs/ORGANIC.md`).

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
11**; 12 needs 11; 13b needs 13a and otherwise runs forever. **14 depends on
nothing after 9 and nothing depends on it** — which is exactly what made it
a separable vertical rather than a fork in the roadmap.

```
0 truth ─► 1 shrink ─► 2 one-script ─┬─► 3 Qt UX (capped)
                                     ├─► 4 mesh domain ──┐  (gate: confirm
                                     └─► 5 cadexd split ─┴─► 6 Blender shell ─► 7 convergence
                                                                                    │
   ┌────────────────────────────────────────────────────────────────────────────────┘
   ├─► 8 delete src/Gui
   ├─► 13a MERGE (done) ─► 13b source reduction, ongoing ──────────────┐
   ├─► 9 one surface ─► 10 probe + characterize ═► 11 our engine ─► 12 our shell
   │                                (go/no-go)      └── unscheduled, behind the unchanged protocol ──┘
   └─► 14 dynamics + control (M0–M9, closed) ── independent of 0–13, in main since ADR-102
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
      `src/Mod/cadex/CadexScriptedRuntime.py:38` (`_DOMAIN_WORKER_BUNDLES`).
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
      had no third-party Python dependency left. *(True until M0. Phase 14
      added exactly one, `mujoco == 3.10.0`, deferred-imported inside
      `CadexDynamics.py` so `cadexd`'s own closure still has none — ADR-075,
      ADR-076.)*
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
- [ ] **`cadex_assembly_worker.py:2553` imports `CommandCreateView`** —
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
- [ ] **11f — `assembly` (21 ops, 10 output types, 13 joints).** The
      largest, and larger here than on `main`: Phase 14 put nine of those
      ops on it. Vendor
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

## Phase 14 — Dynamics and control `(ADR-075, ADR-102; 14a closed 2026-07-31, 14b closed 2026-08-01)`

**This phase stands apart in the dependency graph** at the top of this file
for a reason rather than an oversight: it depends on nothing in Phases 0–13
beyond what already shipped, and nothing in Phases 0–13 depends on it. That
independence is what let it live on its own branch, `MJC`, for two days; it
is also why merging it back cost nothing structural. ADR-102 records the
merge and the measurements behind it.

**Goal:** rigid-body dynamics on MuJoCo, and then the whole arc that
capability opens — a mechanism designed in Cadex, exported, trained, and
played back walking. The framework, the slices, the hazards and the measured
facts are `docs/MUJOCO.md`; only status lives here.

Slices are numbered **M0–M9** rather than sub-phases, to avoid colliding
with the phase numbers above. Every slice is a resting place.

**14a is M0–M8** — closed at M8 (ADR-085, 2026-07-31), and the arc's exit
criteria are recorded as met below. **14b is M9**, and it exists because
*reading* what 14a produced found the arc had shipped a policy that stands
by bracing (ADR-096, hazard 15) and a task that could not have told the
difference (hazard 16). 14b is not a defect fix and not scope creep: an arc
that ends at "it moves" and never asks "could a machine do that" is an arc
missing its last question, and the answer needed a new authoring surface, a
new trainer capability and a re-rated mechanism.

- [x] **M0 — Decide, depend, deliver** (ADR-075, ADR-076). Scope approved
      including the M5–M8 direction change; `mujoco-python` 3.10.0 exactly
      pinned. The dependency could not be added as conda — the manifest has
      not been re-solvable since conda-forge moved past `occt ==7.8.1` — so
      it arrives as a pypi wheel carried by name through
      `CARRIED_PYPI_PACKAGES`. The payload's import gate failed on its first
      run and found a **dangling `bin/python` symlink** the payload had been
      shipping for as long as the prune has existed, unnoticed because
      discovery goes through `cadex-engine.json` and names `freecadcmd`.
      ADR-023 paying out exactly as written.
- [x] **M1 — Prove the seam** (2026-07-30). A double pendulum, chosen over a
      falling box because its links pass through full rotations and so
      exercise the quaternion-hemisphere flip `cadex_animate` lists as one of
      its five silent failure modes. Trace played in the shell, unmodified.
- [x] **M2 — `assembly` → `mjSpec`** (ADR-077). `api.dynamics` / `api.body`,
      exact OCCT inertia, a breadth-first spanning forest from the grounded
      components, loop closures against sites, and gear/belt/screw couplings
      whose laws were **measured against OndselSolver** rather than derived.
      `rack_pinion` refused. Collision deferred to M3 (`model.ngeom == 0` is
      a test). No protocol change, no `shell/` diff.
- [x] **M3 — Dynamics for real** (ADR-079). `api.collision` with four
      primitives plus `mesh`/`hull`; friction, restitution, `condim`, margin
      and collision groups; gravity and the solver step as script
      parameters; and the determinism gate, which holds across cadexd
      restarts with contact doing real work. A mast topples, lands, bounces
      twice and stops. **Three of this line's own words were wrong.** Convex
      decomposition is not in it and was not needed — a concave part is
      *refused*, naming its volume error, because MuJoCo hulls a collision
      mesh silently. "Forced single-threaded" was never a flag: islands are
      a *disable* bit that was on by default, and the risk was constraint
      ordering, not threads. And the solver step was already split from the
      trace step in M2, so what M3 owed was the budget — which became two
      budgets, one for what leaves the engine and one for what the engine
      does. No protocol change, no `shell/` diff.
- [x] **M4 — Actuators and closed loop** (ADR-080). `api.actuator` in three
      kinds — `motor`, `position`, `velocity` — plus `api.joint_dynamics` for
      the damping, armature and friction loss MuJoCo defaults to zero. A
      two-link arm holds a commanded 30° and settles at 30.44, the 0.44 being
      the load's torque over the gain; the same script with no actuators
      falls to 75°. **Two of this line's own words were wrong.** There is no
      control callback: MuJoCo's position actuator *is* the PD loop, closed
      in C, so what a script supplies is a setpoint — a whitelisted formula
      of `time`, which keeps arbitrary Python out of the determinism gate.
      And joint damping was not a later slice: a stiff gain on an undamped
      joint rings at sixty degrees peak to peak forever. Units are in the
      parameter names and the wrong one is a refusal. No protocol change, no
      `shell/` diff.
- [x] **M5 — MJCF export** (ADR-081). `assembly.mjcf(assembly, bodies, ...)`
      writes one self-contained MJCF file — collision meshes inline, no
      sidecars — carrying exact OCCT inertia and a keyframe at the pose the
      assembly solver produced. It loads in a stock MuJoCo whose interpreter
      cannot import Cadex and integrates to the engine's own trajectory.
      **Two of this line's own words were wrong.** "No determinism problem":
      `to_xml()` writes six significant figures with no precision knob, so
      inertia round-trips to 2.4e-6 and "matches the in-engine simulation"
      is a measured tolerance rather than an identity. And "the cheapest
      slice" was right about the physics and wrong about the work — the
      cheap part was calling MuJoCo's writer; the slice was proving the file
      is the model. The export verifies its own output before returning it
      and refuses rather than writing. No protocol change, no `shell/` diff;
      the packaged gate is 9 tests. **ADR-078's deferred merge-back question
      is answered by ADR-082: no — and M5 is the reason rather than the
      exception.** The export calls MuJoCo's own writer, so the capability is
      not separable from the 53.5 MB dependency, and the round-trip proof that
      makes the file trustworthy only means anything while the writer and the
      compiler are the same pair.
- [x] **M6 — A task is part of the script** (ADR-083).
      `assembly.task(model, ...)` writes one JSON bundle beside the model it
      references, describing observation channels, an action space, a
      reward, termination rules, an episode and domain randomisation — all
      data, all declarative. A process with no Cadex on its path reads the
      bundle, opens the model beside it and runs a full episode, producing
      the engine's numbers step for step. **The measurement that changed the
      design before it was written:** MuJoCo's frame sensors take an
      `objtype` that reads as one thing and is two — `body` is the inertial
      frame and `xbody` the frame the assembly solver placed, a half turn
      apart on a plain box — so a reward naming a component's position would
      silently have been handed its centre of mass. Action bounds are
      derived from the mechanism or **refused**: a velocity actuator's
      control is a speed and a FreeCAD joint states no speed, and a
      one-sided limit's filled-in endpoint is a hundred turns of solver
      convenience rather than a bound anybody designed. No protocol change,
      no `shell/` diff; the packaged gate is 10 tests.
      `cadex_tests/dynamics_task_episode.py` is the environment, so M7 is
      dispatch rather than debugging.
- [x] **M7 — Training happens elsewhere** (ADR-084).
      `assembly.policy(task, weights=..., sha256=...)` names a trained
      policy by file and digest, verifies it against the task it claims, and
      publishes a receipt whose bytes join the project digest. The trainer is
      `training/cadex_train.py` at the repository root — Cadex-free, never
      installed by CMake, in no payload, four exactly-pinned dependencies,
      and **nothing entered `pixi.toml`**. Offboard by design turned out to
      make the *engine* simpler: it verifies a policy and never produces one,
      so it needs no optimiser, no accelerator and — measured — no numpy.
      **The three questions ADR-082 named as M7's are answered:** training
      runs on the user's own GPU box dispatched by the agent's shell; the
      policy extends `put_asset` rather than getting its own op, because a
      new op would cost the `shell/` diff ADR-078 says the branch rests on
      not having; and there is **no train button and nothing to press**.
      **Four phase 0 findings changed the design**, including one that
      contradicted the plan outright — `np.savez` *is* byte-deterministic —
      and one that prevented an import rather than justifying one: a
      pure-Python forward pass runs at 4 564 Hz against a 50 Hz control rate,
      so numpy stayed out of `CadexDynamics`. The container carries a
      **witness** the engine re-computes, so a policy whose weights survived
      but whose architecture the engine reads differently is a refusal rather
      than a bad gait. No protocol change, no `shell/` diff; the packaged
      gate is 11 tests. The CI training gate converges a one-hinge swing-up
      on CPU (1.10 → 2.487 reward per step, ceiling 2.5) and is honest that
      it does not prove the GPU path.
- [x] **M8 — The policy comes home** (ADR-085).
      `assembly.rollout(policy, frames_per_second=..., seed=...)` plays the
      verified policy against the model its task bundle names and emits a
      `cadex-assembly-simulation-trace-v1` — **a new operation and no new
      output type**, so the "exactly one simulation" rule, the `api.motion`
      incompatibility and the shell's bake all apply for free. It was the
      *swap* M7 left rather than a discovery: `evaluate_episode` gained one
      keyword-only `sample` callable and nothing else, so one episode loop
      stays one episode loop. **Two phase 0 findings mattered** — reloading
      the exported model turned out to be load-bearing rather than tasteful
      (the writer's six significant figures become a different trajectory
      within a hundred closed-loop steps), and the float32/float64 gap
      compounds five orders of magnitude over an episode while the reward
      total survives it, so a trace's digest is a claim about this engine's
      arithmetic and not about anybody else's inference of the same weights.
      `frames_per_second` must divide the task's `control_hz` exactly and
      defaults to it. No protocol change, no `shell/` diff; the packaged gate
      is 12 tests, and the shell — unmodified, from the shipped bundle —
      bakes a rollout trace into 357 keyframes a component.

**Exit criteria (the arc's, not a slice's) — met at M8.** "Design me a
quadruped and teach it to walk" is a sequence of chat turns that terminates
in a viewport playing a learned gait: the mechanism is designed through the
ordinary assembly surface, `assembly.mjcf` exports it, `assembly.task`
defines the problem, `training/cadex_train.py` solves it on a machine we do
not ship to, `assembly.policy` verifies what comes back, and
`assembly.rollout` plays it. Each slice carries its own "done when", in
`docs/MUJOCO.md` §4. **The whole arc M0–M8 landed with an empty `shell/`
diff**, which is what ADR-078 said the branch rested on; the protocol diff
is still empty and stays that way. The `shell/` diff was spent afterwards,
deliberately and once, on the collision overlay (ADR-091) — and only inside
`mesh_agent/` and the gate suite, with the inherited Blender tree untouched.

**After the arc closed**, three things the first real model asked for, in
the order they had to happen:

- [x] **Remote training dispatch** (ADR-089). `training/remote_train.sh`
      sends a run to a GPU box and `training/SETUP.md` documents the four
      ways to train. Dispatch machinery only — nothing enters `pixi.toml`,
      no CMake rule references it, no new op, and the engine still cannot
      train. It refuses a run that silently fell back to CPU and a box whose
      pinned versions do not match, because both otherwise show up only as a
      number nobody compares.
- [x] **The hopper's leg re-sized, and ADR-088 corrected** (ADR-090). The
      leg was under-actuated: 26.9 N·m to hold a crouch against 12 given, so
      **0 of 27** scripted push-offs left the ground and no policy could have
      hopped. ADR-088 §2 read that collapse as a deliberate tuck. At 60 N·m
      it is **27 of 27**, best 304 ms of flight. A feasibility gate now runs
      before any GPU time is bought. Exposed and fixed one engine defect —
      `MJCF_MASS_TOLERANCE` at 1e-12 against a writer that emits six
      significant figures, which refused every body whose mass was not a
      short decimal.
- [x] **The collision overlay** (ADR-091). Two of two dynamics bugs on this
      branch were collision geometry that nothing drew, so it is drawn now.
      Zero engine change and zero protocol change — every number it shows
      was already published. **This is what spent the `shell/` diff**, and
      only inside `mesh_agent/` and the gate suite.
- [x] **The Policy Outputs panel** (ADR-096). Each actuator's command
      against its own derived limit, at the current frame. It found hazard
      15 in one glance — a policy that plays as a clean stand while holding
      three motors above 95 % of stall on 100 % of frames — which is what
      opened 14b.

### 14b — M9: the episode stops starting in the same place `(closed 2026-08-01; follow-ons M9b ADR-100, M9c ADR-101)`

- [x] **M9 — Reset variation, disturbance, checkpoints, and a re-rated
      mechanism** (ADR-097, ADR-098, ADR-099). Three findings, one slice,
      because they are the same finding: `mg-legs` braced rather than
      balanced, and it did so because 216 N·mm of *stall* torque was
      available, bracing was cheap under the reward, and **nothing ever
      disturbed it**.
      - **The mechanism (ADR-097).** `assembly.reset_variation` and
        `assembly.disturbance`, two intermediates beside `assembly.randomise`
        and passed to `assembly.task` the same way. A reset variation moves
        the floating base **rigidly** — a drawn tilt, a lift, a spin — and
        **never touches joint angles**, because the reset pose is the solved
        one with the soles on the floor and a few degrees at a knee is a
        contact impulse (hazard 17). The lift that pays for the tilt is
        *measured*: the engine applies the widest declared tilt at the
        smallest declared lift at sixteen azimuths and refuses the pairing
        that does not clear, which immediately caught its author out by
        5.13 mm against a 3 mm estimate. A disturbance is one event per
        entry, applied at the body's centre of mass in the world frame —
        both measured in phase 0, not assumed. Two seeding algorithms, both
        stated in the bundle and deliberately different. **No protocol
        change and no `shell/` diff**: `assembly.*` is the xscript surface,
        not the op table.
      - **Visibility (ADR-098).** `--checkpoint-every N` writes complete,
        witness-checked `.cxpolicy` files mid-run plus `<out>.best`;
        `progress.json` is rewritten atomically every iteration and is the
        one artifact everything downstream reads; `remote_train.sh` gained
        `train --detach`, `watch`, `pull` and `stop`. Two silent bugs
        surfaced and were fixed: `train.pid` held the wrapping subshell
        rather than the trainer (so `stop` reported success while a
        4000-iteration run carried on), and `shquote` mis-escaped embedded
        single quotes in bash 3.2.
      - **The shell's Training panel.** State, iteration, elapsed, ETA,
        reward, best-so-far and where it happened, and the checkpoints
        pulled — polled from the local `training-progress.json` that `watch`
        writes. **No ssh, no protocol change, no engine change, no mujoco**;
        its module imports `json`, `os` and `bpy` and a gate check asserts
        exactly that. Zero lines to the inherited Blender tree, so
        `docs/BLENDER-TREE.md` §2a stays eight files.
      - **The re-rating and the gate re-spec (ADR-099).** 216 → **86 N·mm**,
        ~40 % of stall, an engineering judgment stated rather than buried.
        `feasibility.py`'s arithmetic column stops gating and stays printed
        (hazard 14), and what gates in its place took three attempts — two
        of which ran, printed a table, and measured nothing (hazard 18).
        What survived is statics: the righting moment the worst declared
        shove needs, against what the footprint and the ankles can supply.
        **62.8 N·mm needed, 117.4 available, 1.87× margin, the foot
        binding.**
- [x] **M9b — a shove that makes it stumble, and a reward that lets it
      recover** (ADR-100). **No engine, trainer or shell change** — every
      change is in the project script beside the repo, which is the finding
      as much as the numbers are. The M9 run stood and never moved its feet,
      and three measurements say why: the shove put the **capture point** at
      19.5 mm inside a 45.5/24.5 mm polygon so nothing was asked of the
      knees; the reward cost **−4.2/step** during a stumble against a +1
      alive bonus, so falling immediately beat recovering; and `--discount
      0.97` at 100 Hz is a 0.33 s horizon against a 1–2 s recovery. So the
      shove is sized by capture point instead (`[0.4, 2.0]` N → ξ 22–111 mm,
      a curriculum *inside* the distribution), `over_feet` becomes a
      saturating `tanh` plus a small linear `drift` term, `stillness`,
      `spin`, `posture` and `height` come down, `splay` prices the ADR-096
      brace where it lived, and the discount goes to 0.99. **`feasibility.py`
      check 3 is re-specified a third time** — not for being wrong, as the
      first two were, but because the task changed from "reject in place" to
      "catch it however you can"; it gates on capture point against
      support + `195 mm × sin(swing)` and reads **1.57× / 1.38× / 1.09×**
      forward / backward / lateral. `compare.py` splits survival by shove
      azimuth, because without ankle roll or hip yaw lateral recovery is
      capped by the **mechanism** and an aggregate count would hide it.
- [x] **M9c — the trainer never ended an episode** (ADR-101). **Trainer
      only**: no engine change, no protocol change, no new dependency,
      nothing into `pixi.toml`, and one label row inside `mesh_agent/`.
      M9b reproduced M9's reward-versus-survival anti-correlation on a task
      sharing nothing with it, which made the instrument the suspect — and
      reading it found `horizon = int(episode["max_steps"])` read and never
      used again. `done` was the task's termination terms and nothing else,
      so **an environment whose policy did not fall over never reset**: past
      the last shove window it was never pushed again, never re-drawn, and
      stood still collecting the `alive` bonus. The rollout now truncates at
      the bundle's own horizon, a **timeout is bootstrapped and a failure is
      not** (`terminated` cuts the bootstrap, `done` cuts the GAE carry —
      collapsing the two trades one bias for another), and **mean episode
      length is reported** in the stderr line, `progress.json`, the policy
      header's curve rows and the shell's Training panel, which is the
      metric that would have shown M9b's 170 → 30 live. **Every reward
      figure recorded before this is non-comparable** — +0.391, +0.5118,
      +0.2149 — because they were measured against an unbounded episode;
      the survival numbers are unaffected. **The rerun was done and refuted
      the hypothesis**: on the fixed trainer, same bundle and
      hyperparameters, reward rose to +0.175 and trainer-measured episode
      length to 149 while the engine measured 0/12 survival and episode
      length collapsing 162 → 39. So the never-ending episode was a real
      defect and not the cause of hazard 19 — but the fix is what makes the
      remaining question answerable, because **the same quantity now moves
      in opposite directions on the two sides of the seam**. `docs/MUJOCO.md`
      §6 stays open with two candidates; sampled-versus-mean is the cheap
      one and goes first, MJX-versus-MuJoCo the expensive one.
    - [x] **Both candidates measured (ADR-103).** MJX-versus-MuJoCo is
      **answered and localised**: the two engines agree to float64 machine
      epsilon with collision disabled and with a `plane` floor, and differ
      only about **box against box** — which is what `export_mjcf` writes
      for every grounded body, so it is the only contact any Cadex model
      has. Nine orders of magnitude on the median single step, contact
      counts disagreeing on a fifth of all steps from an identical state,
      and not the integrator, the solver iterations or float32.
      Sampled-versus-mean is **measured and partial**: σ falls rather than
      running away (0.3000 → 0.2973 over 50 iterations) but sampled play is
      five times the torque of mean play. `log_std` now reaches the policy
      header (`exploration`) and mean σ the progress row, so both are
      readable live. `test_dynamics_mjx_agreement.py` pins the result.
    - [x] **ADR-101's inversion is withdrawn — it was the instrument
      (ADR-103 §9).** `evaluate_episode` applies domain randomisation by
      multiplying in place into the model it is handed and never restores
      it, and `compare.py` reused one model for a whole table: after 72
      episodes link masses and inertias stood at 0.23×–3.9× their exported
      values, drifting the same way down every table. Given a fresh model
      per episode, m9c reads 65 → 174 → **201** steps and reward −0.234 →
      **+0.190**, both rising and both in the same direction as the
      trainer's 58 → 149. **Survival numbers are unaffected** (0/12 is 0/12
      on any model) and so is ADR-086's no-headroom finding — peak torques
      of 76–84 N·mm of 86. Both engine call sites run one episode per model,
      so the shipped product is not exposed; a looping evaluator is.
      Hazard 19 keeps its rule and loses its central evidence.
- [x] **The task was out of range, and the mechanism could not answer it**
      (ADR-104, ADR-105, ADR-106). `~/cdx-mjc/capability.py` sweeps a scale
      factor over a task's declared shove band, split by azimuth, with the
      termination mix: m9c reads **0/12 at the declared 0.40–2.00 N and
      11/12 at 0.06–0.30 N**, standing on 2–5 N·mm of mean torque against a
      limit of 86. It was not failing to learn. Three consequences, all
      landed: the surface gained `azimuth_degrees` on a disturbance and
      `linear_velocity_mm_s` on a reset variation (**a stumble**), plus
      `"plane"` as a collision primitive, in four implementations of one
      draw stream (ADR-104); the machine gained **ankle roll** — two more
      MG90S, 302.01 g, centre of mass 144.210 mm, 10 joints, 52 of 64
      channels, and a plane floor MJX and MuJoCo agree about (ADR-105); and
      the task's band moved to 0.15–0.90 N aimed ±60° with the second shove
      over the whole circle, windows at 0.3–1.5 s and 1.8–3.6 s, and
      `collapsed` at 0.5·Z0 on the direct evidence that 8 of 12 deaths were
      upright and sinking (ADR-106). `feasibility.py` passes on the new
      machine with lateral reach at 3.72× where it was the collapsed column.
- [x] **The frame was read 90° wrong** (ADR-107). `azimuth_degrees` is about
      **world +X** and the engine has no concept of which way a mechanism
      faces; mg-legs faces **+Y**, so `compare.py`'s `fwd`/`back` columns
      held the *lateral* pushes and `lat` the *sagittal* ones. That inverts
      ADR-105's motivation (lateral is the **strong** axis: 7/7 against 3/5
      at ×0.50 on iteration 250) and makes ADR-106's `[-60, 60]` a lateral
      band rather than the sagittal one it was written to be. Words only —
      re-aiming the band is a digest change and would make
      `stand5.cxpolicy` unloadable. The instrument now **measures** its own
      forward axis off the model's toes and refuses a table whose frame the
      model disagrees with. The foot-lift claim was the same class of error
      and is corrected: the left foot lifts **5.91 mm at 2.090 s**.
- [x] **Four Cadex editors** (ADR-108). Environment, Policy, Training and
      Live become space types 27–30. Reverses `docs/BLENDER.md`'s "no new
      editor and no new space type" for these panels — right for a readout,
      wrong for four independently arrangeable workspaces — and ships the
      sixteen-touch-point recipe as a checklist in `docs/BLENDER-TREE.md`
      §2b so the next one is mechanical. §2a is untouched and still eight
      files.
- [x] **Live mode** (ADR-109): a running mechanism you can push, in the
      viewport, with the policy answering. Three read ops
      (`live_open`/`live_step`/`live_close`), a resident `--safe-mode`
      worker running **the same** `evaluate_episode`, and one new seam —
      `forces=(step, data, time_s)`, additive and not a digest input, needed
      because `apply_disturbance` rewrites `xfrc_applied` from zero every
      step. The shell owns the clock. Measured: **344 µs a control step**
      (29× real time) and a **1.72 ms** median `live_step` round trip
      against a 33 ms bar, identical from the staged payload. Driven end to
      end on mg-legs it runs at real time, takes 1.5 N from three sides, and
      goes over at 8 N.
- [x] **A live session you can analyse** (ADR-110). The instrument was still
      unreadable: every session opened with the whole declared episode
      running, so a hand push landed on top of four other forces. Three
      changes. **Calm mode** is one `variation` boolean on `live_open` and
      nothing else — it reaches `evaluate_episode`'s existing *unseeded*
      episode, which live mode could never ask for because the seed was
      coerced to `0`; the op defaults it on, the panel's checkbox defaults
      off. **The force arrow** is drawn from the `xfrc_applied` a frame
      carries back, at `xipos`, so it is measured rather than intended — and
      it is a **sum**, so a user's shove and the task's wind on one body are
      one arrow. First draw handlers in the add-on, with the lazy-shader rule
      that keeps the headless gate green. **Hold to push** needed no engine
      change: re-sending a 0.15 s push every tick is a continuous force.
      Fixed on the way: ADR-109's `forces` guard read one half of its
      condition and let a push accumulate 4, 8, 12… N on an unseeded episode
      of a task that declares disturbances. Measured through the shell
      against the bundle: a calm episode runs 600 steps with **zero**
      applied forces and stands; a 0.75 N push reports **0.7500 N at
      90.00°** at the pelvis centre of mass; a held push is constant across
      26 ticks and stops **0.142 s** after release.
- [ ] **The GPU run and the policy it produces.** Blocked, not skipped: the
      training box runs its **own** checkout of `training/cadex_train.py`
      and it predates ADR-104, so a dispatch would silently ignore both new
      draws while recording the new algorithm string in the policy header.
      The CPU sanity run is green (50 iterations, σ 0.3006, witness
      4.07e-08).
- [x] **The reward learns where the feet are** (ADR-112). Five runs — m9c,
      B2, B3, B4, B5 — produced a machine that stands, absorbs a shove with
      its joints and never lands a recovery step. B3/B4/B5 each changed the
      *disturbance*; B5 settled it. Measured across fifteen checkpoints at
      twelve seeds, stepping **peaks at iteration 750 (7/12) exactly where
      reward bottoms (+0.060)** and falls to 1/12 as reward climbs to +0.245
      — correlation **−0.870** over the whole climbing phase — while foot
      *lifts* rise monotonically to 23. The machine was never refusing to
      move its feet; it was **stepping in place**, because a lift is free
      and a displacement was charged −0.57/step forever. Survival never
      exceeded 2/12 at any checkpoint. The reason was the objective, unchanged since M9b: `ft_l_*` and
      `ft_r_*` were bought in M9b because *"where a foot is relative to the
      centre of mass IS the state variable a stepping recovery is written
      in"*, and **no reward term named them** — both spatial terms measured
      the centre of mass against the fixed floor point the machine stood on
      at t=0, so moving a foot changed the reward by nothing and a
      *completed* step cost −0.57/step forever. Two changes, one engine and
      one task. **The engine gains a ninth observation kind**,
      `centre_of_mass_velocity` (`mjSENS_SUBTREELINVEL`) — one table row,
      no protocol change, no trainer change — because the capture point
      needs a whole-body CoM velocity and the pelvis *frame* velocity
      already declared is out by 19%, which is 9–18 mm against a 24.5 mm
      support margin. **The task re-references both spatial terms to the
      foot centroid** and adds `capture`, `tanh(ξ/40)` at −0.8, which turns
      a survival payoff arriving 1–2 s later into a cost of −0.61/step that
      a step zeroes immediately. Verified before dispatch: 55 channels, both
      new terms **0.000** at the reset keyframe (hazard 9), and the
      expression's ξ agreeing with `subtree_com + subtree_linvel/ω₀` out of
      MuJoCo to **0.000000 mm** at eight disturbed states — where the same
      expression on the pelvis frame is out by 20–39 mm.
- [x] **B6, the run — it steps and it lands** (ADR-112). 2500 iterations,
      3.9 h, witness 2.82e-07, with a horizon that can see a recovery
      (γ 0.99 → 0.995, λ 0.95 → 0.97, unroll 20 → 40: at 100 Hz the old pair
      gave a GAE credit chain of 0.17 s for a recovery that takes 1–2 s).
      **Checkpoint 2400 scores 6/12 on "stepped AND survived" — a number
      that had been zero in every run this project has ever done**, across
      five prior runs and every one of their checkpoints. Survived 6/12,
      stepped 10/12, longest step 83.5 mm, and the steps land 0.08–0.11 s
      after a push. On `capability.py` it beats the policy it replaces at
      every level: 12/12 unshoved (`stand5` 11/12), 11/12 at ~0.40 N (11/12),
      **10/12 at ~0.60 N (6/12)**, and 6/12 at the full declared 0.30–0.80 N
      band where B5 managed 1/12. **Zero `collapsed` terminations at any
      level** — the squat risk was checked at iteration 100 as ADR-112
      required (mean `com_z` 149.2 mm against a 144.2 mm standing pose: it
      stands *taller*) and never materialised, so `height` was not touched.
      Installed into `~/cdx-mjc/mg-legs.cadex` together with the B6 script,
      since the reward and the channel count both changed. Selection was **by
      stepping-and-surviving, not by reward**, for the third measured time:
      `stand8.best.cxpolicy` scores 1/12 where checkpoint 2400 scores 6/12.
- [x] **A tenth observation kind: the machine's own angular momentum**
      (ADR-116). `centroidal_angular_momentum` (`mjSENS_SUBTREEANGMOM`), in
      **N·mm·s** — one table row, a new unit converter, no protocol change
      and no trainer change. **Every B6 death is `tipped` and not one is
      `collapsed`**, so the failure this project keeps measuring is
      rotational; and the reward had no channel for rotational momentum at
      all. `tilt` prices the pelvis's *orientation* and `spin` its *frame*
      angular rate, and neither is the whole machine's angular momentum
      about its own centre of mass: it can be upright, still, and already
      going over. Measured on the arm fixture, kicking the child link alone:
      the parent's frame angular velocity is **exactly 0.0** where the
      subtree carries **18.89 N·mm·s**, and the ratio between the two moves
      by a factor of six over one swing — so it is not a constant a weight
      could absorb. MJX asked separately, because an unimplemented sensor
      returns **zeros rather than an error**: non-zero, and agreeing with
      stock MuJoCo to **6.5e-07 relative in float32** over six randomised
      poses. The MJX coverage test that should have caught ADR-112's ninth
      kind was counting to eight; it now compares against
      `OBSERVATION_KINDS` as a set.
- [ ] **Still not a standing machine.** Half the episodes at the declared band
      still end `tipped`, and backward remains the worst direction (3/6). B7
      is the run that spends the tenth kind: a shove band past what ankles
      can answer, `capture` split across two scales, and new `arrest` and
      `swirl` terms.

**Standing constraints for this phase**, both from ADR-077 and both cheap to
lose by accident:

- **Nothing in `shell/` imports mujoco, ever.** A physics authoring path in
  the shell violates "nothing happens outside the script" the same way the
  deleted bpy modes did.
- **`CadexDynamics.py` is reachable from the sandboxed worker and never from
  `cadexd`.** `test_engine_purity_guardrails` asserts the import closure
  equals `DECLARED_ENGINE_MODULES` exactly; a service whose job is reading
  NDJSON off a pipe does not need 53.5 MB of physics engine resident. M3 added
  `scipy.spatial` to that module and it is imported the same deferred way
  `mujoco` is, for the same reason.
- **A default is a promise, not a decision** (ADR-079). Every MuJoCo option
  the translator depends on — the island and sleep flags, the integrator,
  the compiler's inertia handling — is set explicitly and re-asserted on the
  *compiled* model, which is where a release changing a default would land.
  Moving one is a measurement, not an edit.

## Phase 15 — Organic modelling and the CAD/mesh interface `(open; O0 closed 2026-08-05, ADR-124)`

**Goal:** make the shapes a person asks for — a body, a limb, a skin over a
mechanism — buildable by the agent, and shapeable by the user without a chat
turn. The measurement it is sized from, the slices, the hazards and the
benchmark log are `docs/ORGANIC.md`; only status lives here.

**Depends on nothing after Phase 9**, and nothing depends on it. It does not
need Phase 11 or 12, and it does not block them: O0 and O3's shell halves
keep their pure arithmetic `bpy`-free precisely so Phase 12 re-binds them
rather than re-designing them. O1–O3's engine work is behind the unchanged
cadexd protocol.

**Why now.** ADR-123 closed by asking for the robot wolf to be re-run
against the repaired API surface. It was (`~/arch/woof.cadex`, read-only)
and the result sizes this phase: the agent builds **entirely in `part`** —
sixteen lofted solids, no mesh op — so the gap is not "CAD is the wrong
paradigm for organic shapes". It is four specific things, one per slice.

This phase **answers `docs/VISION.md`'s open question** about interactive
mesh editing: it arrives as engine ops on a declared table, with the shell
supplying only the gesture (O3).

- [x] **O0 — The agent can see what it built** (ADR-124, 2026-08-05).
      `render_views`: four cameras fitted to the Model collection — front,
      right, top, three-quarter — composited 2×2 into one image, with the
      user's session isolated out of it. No engine change; no authoring.
      Verified by driving the built application, because the gate runs
      `--background` and `draw_view3d` needs a real VIEW_3D — the ADR says
      so rather than implying coverage the gate does not have.
- [x] **O1 — Blends that survive, and the ops that make muscle** (ADR-125,
      2026-08-05). `part.fillet` bisects a failing edge set and reports what
      it found (`on_failure` = refuse / skip / reduce); `part.fuse(blend=...)`
      names the seam edges because it made them; plus a variable-radius
      fillet, `part.sweep(scale_law=...)` and
      `part.ellipse(x_direction=...)`. The wolf's weld lands — 25 of 48
      seams at 8 mm, 25.04 s against a 13.61 s baseline — and the probe cost
      is measured, capped by wall-clock, and reported when the cap binds.
      **Sweep guide curves are not in it**: they need a new binding in
      inherited `src/Mod/Part`, which is a decision about the fork's delta
      rather than a fix.
- [ ] **O2 — Mounts.** `mounts()` / `mount()` on `CadexBoards`'s row
      machinery, `part.mate(...)`, and a static interference check that
      refuses with millimetres. Exit: a mechanism mates into a skin with no
      copied numbers, and a stored row naming a dropped mount is pruned, not
      refused (the ADR-120 drift rule).
- [ ] **O3 — The section cage.** `CadexCage.py` and `part.loft_cage`, an
      edge-only ring overlay in a sibling collection, and Apply through
      `wiring.py`'s single-slot pump. Exit: drag a ring, press Apply, and
      the accepted revision moves — **without a new space type**
      (`docs/BLENDER-TREE.md` §2b budget is not this slice's to spend).
- [ ] **O2b — Swept-volume clearance.** Parked by decision, not dropped: it
      roughly doubles O2.
- [ ] **O4 — subD.** Parked, unscheduled. It reuses O3's table, overlay and
      apply path, which is the argument for doing sections first.

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

# new in Phase 14 — the dynamics vertical (39 test_dynamics_*.py suites)
pytest src/Mod/cadex/cadex_tests -k dynamics       # headless, no build, no GPU
#   naming convention across the arc, four files a slice:
#     *_api       the authoring surface and its refusals
#     *_model     what reaches the compiled mjSpec
#     *_measured  numbers checked against a reference, not against ourselves
#     *_live      the whole path through a real worker
pytest src/Mod/cadex/cadex_tests/test_dynamics_units.py          # the one conversion boundary
pytest src/Mod/cadex/cadex_tests/test_engine_purity_guardrails.py  # the three invariants
#   the packaged gate is 12 tests at M8, up from 6 at M0:
#   CADEX_ENGINE_ROOT=<payload> pytest .../test_cadexd_lifecycle.py
#   MJX-gated tests (phase 0 measurements, real training runs) SKIP in the pixi
#   env by design — 12 skips is the expected count. To run them, use a venv
#   built from training/requirements.txt; the suites run from either interpreter.

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
that consumes this is ADR-066 and is not built.

What makes them experimental, and what would settle it:

- [x] **Ports are literals** — **settled by ADR-062 (2026-08-01).**
  `part.terminals` / `mesh.terminals` name a component's attachment points
  from its geometry: a `holes=`/`pads=` selector on a BREP board, a declared
  layout on an imported STL, ordered by a *direction* rather than by kernel
  enumeration. Terminals ride their component's placement, so one spec places
  four motors. `CadexTerminals.py` is the new pure-Python module; no shell
  code, no protocol change, and literal ports are unchanged, so a script that
  uses none rebuilds byte-identically. **A hole terminal landed on its *far*
  face until ADR-117 (2026-08-03) reversed it**: it lands in the near rim's
  plane now, with a zero stand-off floor and the bore left empty, because the
  solder is what closes the gap and it is at the mouth on both ends — and
  because "the rim on top of the hole" is the only end of it a user can point
  at. `depth` therefore sizes nothing and `hole_dia` is what classifies a
  declared row. Every project carrying a bore terminal must be re-accepted.
  **A pick writes the terminal itself since ADR-120/121 (2026-08-04)**, into
  the `boards(...)` table rather than into the script text — which is what
  Phase 10b was asking for and is a better answer than it: a row is data and
  needs no author. Still not built: mesh hole detection, which is deferred by
  decision rather than pending.
- [x] **The harness is invisible** — **settled by ADR-065 (the engine),
  ADR-066 (the editor) and ADR-067 (the pick), all 2026-08-01.** `nets(...)`
  declares the connections, `set_params(nets=)` edits them with no AI turn,
  `inspect scope="wiring"` publishes the terminals the run resolved, and the
  Wiring editor draws all of it as a node graph in Blender's stock node
  editor — re-registered for exactly one Python tree type, so the editor menu
  gains "Wiring" and stays short. Selecting a hole rim in Edit Mode fits a
  terminal and hands the measurement to the assistant to transcribe. **Since
  ADR-117 (2026-08-03) the pick fits two models** — a circle and a
  minimum-area enclosing rectangle by rotating calipers — because a pad is
  usually square and a circle fit is meaningless on one. One ring is enough
  for a bore, `AUTO` takes whichever model wins on its own normalised
  residual, and a tie (four corners are concyclic, so both score zero) is
  refused with both fits named rather than guessed at.
  **Built and green end to end**, shell included: the editor menu test now
  asserts "Wiring" is on it and the four stock node trees are not, the graph
  survives a `.blend` round trip with its layout and socket identities
  intact, and `pixi run gate` passes against the bundled engine. The one
  thing no test covers is dragging a link with a mouse — **done by hand on
  `wiring-test-2` on 2026-08-02 and it works**: deleting the SIG link on the
  canvas re-executed the project and re-accepted it with that wire and its
  joints gone. Still no automated coverage of the gesture itself.
  **The first real session found two of it broken anyway, both fixed by
  ADR-113 (2026-08-02):** the published registry dropped the two fields the
  endpoint join is made of, so a script predating `nets()` drew every board
  and not one wire; and the solder checkbox notified nobody, because
  `NodeTree.update()` fires on topology and never on a property written into
  a socket, so it could neither be pushed nor turned off. The suite now
  drives the real producer rather than a hand-built registry, which is what
  the fixture hid. **The second session found the third, fixed by ADR-115
  (2026-08-02):** a node is one *terminal set*, and a board with two headers
  is two sets that shared the component's name, so the canvas gave one set's
  sockets to the other and every declared wire lost an end — two boards, no
  links, and `applying…` stuck in the header for the life of the `.blend`.
  Node labels are now unique with declared port names reserved first; the
  canvas refuses to be pushed while it is not a whole projection; and a
  cable or bundle the script built outside the table is drawn read-only
  rather than left off the picture. **A routed wire can be corrected since
  ADR-118 (2026-08-03)**: `part.cable(waypoints=…)` states a path the search
  cannot be asked for and skips the search entirely, each wire row publishes
  the route its run followed, and the shell opens it as a real Blender curve
  to drag and Confirm. Only the interior is authored, so both ends still ride
  their terminals; the middle does not follow a parameter, and the note the
  gesture queues instructs the assistant to say so. **And naming a board is a
  click since ADR-119 (2026-08-03)** rather than a chat turn of description:
  Define Board queues the *engine's output key* as a port for
  `nets(ports=…)` — it is the one gesture that starts from a click on the
  mirror, so it is the one that converts — and stamps the object, so every
  later terminal pick on it says which board it is on. **And the boards themselves became a
  table on 2026-08-04 (ADR-120), which is what made the pick a write
  (ADR-121).** `boards({...})`/`board(...)`/`term(...)` in a new pure module
  `CadexBoards.py`: the terminals of each board declared as rows,
  `board_specs`/`board_values` in `script.json`, `set_params(boards=)` to
  edit them, and one optional protocol arg. A declared board now draws
  whether or not anything is wired to it — before, a `TerminalSet` that
  nothing consumed reached the canvas as *nothing at all*, which is why
  `cdx-chassis-v06` showed an empty editor while declaring six of them. The
  rows are millimetres in the board's own frame whatever the script's
  `units=` says, so one project can no longer carry two unit systems. A
  terminal measured in the viewport is written straight into that table: it
  goes out in world coordinates and the *engine* inverts the placement chain
  it resolved, which is the paper arithmetic V06's magic literals came from.
  A board-free project keeps a byte-identical revision; V06 itself was
  migrated on a copy and re-accepted. **And it became editable more than once
  in ADR-122 (2026-08-04).** The push started a `Lifecycle` and nobody polled
  it, so the revision guard never advanced and every apply after the first was
  refused `STALE_PROGRAM_REVISION` in silence — twenty wires dragged built one
  cable, and the next refresh wiped the other nineteen off the canvas. It has
  the single-slot pump the slider drag has had since Phase 6; the 150 ms
  leading-edge debounce, which turned a drag burst into a pile-up on the
  client lock, is replaced by an explicit **Apply** and **Revert**, so ten
  wires cost one re-execute and a refusal no longer throws the canvas away.
  Solder is on by default and `WireValue` carries both endpoint addresses, so
  a script can finally size the joints it builds — `part.solder` needs
  `pad_dia_mm` on a declared pad, and that number is the board's. Still not
  built:
  `part.bundle` as an
  editable graph concept (deferred by decision — changing a bundle's
  membership is a script edit; since ADR-115 its conductors at least *draw*,
  marked read-only).
- [x] **A wire ends in mid-air** — **settled by ADR-063 (2026-08-01), and the
  joint stopped reading as a cone in ADR-064 (2026-08-01).** `part.solder`
  builds the joint a terminal implies, with a concave meniscus that flattens
  into a short collar around the wire — and, since ADR-114 (2026-08-02), a
  crown that rounds that collar over onto the wire rather than stopping dead
  across it in a flat annulus. **ADR-117 (2026-08-03) made it one outline for
  both kinds**: the cap cone, barrel and entry annulus described a lead
  ending at the bottom of the bore and nothing lands there any more, so a
  bore joint and a pad joint are byte-identical profiles and `bore_dia_mm` is
  removed. Still not built: colouring solder differently from wire, which
  needs an appearance vocabulary the part domain does not have. The
  underside-cap question is closed rather than deferred — there is no
  underside cap.
- [x] **A joint and its wire share a sliver** — **settled by ADR-114
  (2026-08-02).** ADR-074 pointed the wire out along the axis and floored the
  stand-off past the joint, which left 0.038 mm³ shared on the probe plate;
  what it did not do is make the *interpolated* wire straight, because a
  spline through a one-segment stub is tangent to it only at the port. Each
  stub is now written as collinear knots: drift through the joint fell from
  0.041 mm to 0.001 mm on the probe plate and from 0.20 mm to 0.013 mm on
  `wiring-test-2`, and the shared sliver from 0.038 mm³ to 3.5e-6 — with five
  of that project's seven joints no longer pierced by their own wire at all.
  The joint is still built from the terminal and never from the wire, so this
  stays a bound rather than an equality.
- **Terminals cannot ride a non-uniform placement.** Refused rather than
  silently skewed (ADR-062). A pad has no radius and no depth, so a
  relaxation carrying only its point and normal is available and unbuilt; it
  is what keeps `wcv8`'s battery pair on literal ports.
- **Mesh obstacles are bounding boxes.** Fine for boards and motors, wrong
  for anything concave; the workaround is to pass such a body as a part
  solid. Two consequences measured on `wiring-test-2.cadex` (ADR-113):
  **a component cannot avoid itself as a mesh** — its own pad is inside its
  own box, so the wire is refused at its own port with `blocked` — and the
  workaround needs an import that converts, which the ESP32's does not:
  **`shape_from_mesh` has no output type for a multi-shell import** (42
  shells there), so `solid=True` refuses and `solid=False` fails the
  output-type check with a compound. That board cannot be an obstacle at all
  today, and its wires clear it on stand-off alone.
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
- **A bundle conductor's sweep frame is a coin flip.** True Frenet takes its
  normal from the curvature, and on a lay that normal spins: at fixed
  geometry the swept solid measures between **0.75x and 1.47x** of
  `pi r^2 L` as `twist_pitch_mm` and `slack` move a few percent, while
  staying closed, valid and one solid. The three-phase probe currently lands
  on a good roll, which is all the pinned 2% tolerance is really asserting.
  ADR-074 fixed the same class of fault for `part.cable` by sweeping in the
  corrected frame; a lay cannot take that mode (ADR-057: up to 51% missing),
  so the fix here is a frame of our own — the spine's own binormal carried
  along the run rather than recomputed per sample. Not scheduled; it moves
  digests, and the visible fault so far has been on cables.

## Later — identified, not scheduled

- **A1: `display` on `open_project`.** Would fold the restore pass and the
  hydration rebuild into one script run; measured cost of not having it is
  0.49 s on the first engine request against a project.
- **Nothing hydrates when a file is opened** (ADR-073). Distinct from A1 and
  larger than it: `load_post` → `on_file_changed` closes the old sessions and
  returns, and no caller queues a rebuild, so opening a `.blend` beside an
  existing `.cadex` leaves the viewport empty — measured
  `model_objects_on_open = 0` in the shipped bundle — until an agent tool
  call, a slider drag, or **Rebuild Model** provokes the first request. A1
  makes that request cheaper; it does not cause one. Landing hydrate-on-load
  is a `shell/` diff and wants the asynchronous lifecycle, so it is a
  decision — ADR-073 §5.
- **A digest-moving engine change locks a project out of the UI, with no
  visible way back in.** ADR-064 called a friendlier migration path "worth
  having and not built here"; ADR-074 is the first change to make a user hit
  it, and it is worse than that note reads. The failure is at *open*, not at
  the next edit: `ensure_open` runs the restore pass, `CADEXD_RESTORE_FAILED`
  comes back, and every operation that would fix it is behind the same call.
  **Rebuild Model cannot be the remedy** — `begin_rebuild_model` passes
  `unrestored_ok=False`, correctly, because re-running a model whose script
  no longer reproduces it is exactly what the guard exists to stop. The
  operation that *is* the remedy is `write_script`, which already passes
  `unrestored_ok=True` and re-accepts on success; what is missing is a
  **button that reaches it in this state**. `adopt_script` is drawn only when
  the engine project is *empty* (`orphaned_project`) or the script buffer is
  *dirty* — and a project that opened fine yesterday under a different engine
  build is neither, so nothing is drawn at all.

  Measured on `wiring-demo/harness.cadex` after ADR-074: accepted
  `7e073ae6…`, restored `25fdf64f…`, four cables. Recovered by hand with
  `open_project restore=false` then `write_script`, which is precisely what
  the missing button would do. The shape of the fix: cache the failure code
  from the last open on the per-root state, and let the chat panel draw the
  re-accept box it already draws for an orphan, saying the model was accepted
  under a different engine build. That is a `shell/` diff and a decision, so
  it wants its own ADR. Until it lands, **every digest-moving change ships
  with a manual recovery** — a solver bump, a sweep-frame fix, the next one.
- **Linux and Windows shell bundles.** The engine payload builds for both;
  only macOS arm64 has shell CI. Moot once Phase 12 lands — revisit then.
