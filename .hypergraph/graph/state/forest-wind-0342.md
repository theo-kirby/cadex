---
node_id: a1a6a16f-c8a2-5ce2-914c-fd5166436dc5
slug: forest-wind-0342
title: The engine — cadexd and the xscript pipeline
created_at: '2026-08-09T15:21:41+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

The engine is a FreeCAD fork at the repository root, stripped to one AI-native modelling engine. A release build produces `FreeCADCmd` and `CadexGeometryWorker` and **no application** [rec: simple-hollow-8675].

- It runs as **cadexd**: one headless `FreeCADCmd` child per open project, speaking `cadex-cadexd-v1` NDJSON over stdio, with serial dispatch, a `CADEXD_BUSY` refusal for a second modelling request, mid-run cancel, and a digest-verified restore pass on every open [rec: simple-hollow-8675].
- **One project script is the sole source of truth.** Five domains — partdesign, sketcher, part, mesh, assembly — execute in one sandboxed `--safe-mode` worker that produces detached BREP, publishes into an ephemeral document under a single transaction with an ownership lint and orphan GC, and accepts a content digest [rec: civic-horizon-2730].
- **Rebuild-digest equality is the load-bearing property**, and it is asserted on every `open_project` rather than once per audit: delete the document, re-run the script, digests match [rec: civic-horizon-2730].
- The process boundary is pinned by tests, not by convention: `OP_ARG_SPECS` pins requests, ADR-027 goldens pin responses, and `test_engine_purity_guardrails.py` asserts cadexd's transitive import closure equals a declared list [rec: simple-hollow-8675].
- **Projects compose through files, not through code.** A project stays one flat script; a part built in another project arrives as a `.cxpart` container in this project's `assets/`, carrying an exact OCCT solid plus the script that made it. `link_part` (a `MODELING_OP`) pulls it out of the other project's pinned accepted attempt by **pure file reading — no FreeCAD, no worker, no OCCT call, and the source project never opens** — and `part.import_part` reads it back as the exact solid, so the part is feature-editable rather than the triangle shell the STL route produced. Refresh is the same call again, and `changed` is what says the source moved [rec: ancient-current-9419] [rec: rising-chart-1564].
- **An output need not be geometry.** `part.measurement` declares a dimension — `distance` between two selected subshapes, `diameter` of one circular edge or cylindrical face, `extent` along an axis of the bounding box — and publishes two exact anchor points in the measured shape's own frame plus a number already formatted to text. `distance` comes off `distToShape`, which returns the value *and* both closest points in one call, so there is no per-geometry special case; `diameter` publishes the circle, because its legible endpoints are a per-frame question and belong to whoever is drawing. It is anchored by ADR-029 selector and **recomputed rather than remembered**, which is what makes a dimension follow the parameter that moves its part [rec: forest-wind-3489].
- The part domain went **56 → 57 operations** with `link_part`/`import_part` and **57 → 58** with `measurement`; each cost no new op on the wire, no new `artifact_kind` and **no change to `compute_project_digest`** [rec: ancient-current-9419] [rec: rising-chart-1564] [rec: forest-wind-3489].
- Parameter changes are served two ways: a resident read-only preview worker answers a **pose-only** change in 33 ms, and everything else pays the ~0.42 s accepting path [rec: open-dew-7293].
- The engine suite is **1,730 passed / 22 skipped**, measured 2026-08-09, headless and needing no build (`pixi run test-engine`); the skips are MJX-gated by design [rec: forest-wind-3489] [rec: even-cliff-3863] [rec: sage-wood-0687].
- The engine carries VibeCAD-era code under its own provenance tags, and the licence boundary that follows from it is one-way and hard: the engine side is LGPL, `shell/` is GPL [rec: lone-haven-0640].

**Gap, unbuilt.** The ADR-027 response fixtures are asserted **engine-side only**. Asserting the same fixtures from the shell side is a ROADMAP Phase 9 item that has never been checked off, and it is more valuable since the merge, not less: one repository removed the distance that used to enforce the boundary [rec: simple-hollow-8675] [rec: merry-eagle-4093].

## Negative knowledge

- [scope: mesh domain outputs | confidence: high | evidence: civic-horizon-2730] Kernel output ordering is not a contract. FreeCAD's native mesh set operations return run-dependent orderings and triangulations, so a mesh output is not digest-stable without canonical vertex/facet reordering plus a vertex-set fingerprint.
- [scope: the 33 ms preview worker | confidence: high | evidence: open-dew-7293] The preview cannot serve a parameter that changes a definition — a placement-only reply for part.box(p.width, ...) would be a lie. The 33 ms headline applies to a subset of sliders only; the rest pay the ~0.42 s accepting path.
- [scope: kernel version pins | confidence: high | evidence: sage-wood-0687, civic-horizon-2730] Neither kernel may float. Reproducibility is asserted on every open, so occt and mujoco are exactly pinned; an unpinned update silently changes what a saved script means.
- [scope: using one project's part in another | confidence: high | evidence: ancient-current-9419] Sub-scripts and Python imports are the wrong answer, and not because the sandbox forbids them. Either would make a rebuild here depend on another project's current state, its assets and its engine version. A content-addressed container makes the rebuild deterministic from this project's own `assets/` alone. The cost, stated rather than discovered later: a linked part is a snapshot and not a live link, and an ADR-029 selector naming a face of it can break on refresh — correctly and loudly.
- [scope: counting a domain's operations | confidence: high | evidence: rising-chart-1564] Three places plausibly hold the count — the API class, the workbench pack tuple, and the capability listing the model reads. Count `PartDomainAPI.exported_names`; quoting from memory is how a wrong number gets published.
- [scope: artifact-less outputs and the digest | confidence: high | evidence: forest-wind-3489] `compute_project_digest` keys on *having* an artifact, so a declared output with no geometry falls through to `payload_sha256` — the hash of its own declaration — and needs no digest code at all. This is a property rather than luck, and it is the right one: a measurement's identity is which selectors it names, not what today's parameters make it read.
- [scope: a domain pack's output-type constant | confidence: high | evidence: forest-wind-3489] `_PUBLISHABLE_TYPES` was serving as both the pack's output-type contract and the validator for a caller's `output_type=` argument. Those are the same set only for as long as every output is a shape; the first artifact-less output splits them (`_PACK_OUTPUT_TYPES`).
- [scope: what a measurement will not do | confidence: high | evidence: forest-wind-3489] Stated rather than discovered later: `distToShape` returns a *minimum*, which is the thickness for two parallel planes but the closest approach for two angled faces; one subject shape per measurement; faces and edges only, with viewport picking still faces only; and a selector that a parameter change removes fails the rebuild — correctly, naming the selector.

## Provenance

- lone-haven-0640 — the engine's origin as a FreeCAD fork and the VibeCAD-era code it still carries
- civic-horizon-2730 — one project script, the removal protocol, and rebuild-digest equality
- simple-hollow-8675 — cadexd, the NDJSON protocol, and the test-pinned process boundary
- open-dew-7293 — the preview/accept split and the latency numbers
- sage-wood-0687 — the deferred-import discipline and the MJX-gated skips
- even-cliff-3863 — the measured suite count that replaced the stale documented one
- merry-eagle-4093 — why the shell-side fixture gap got more valuable after the merge
- ancient-current-9419 — linked parts: the `.cxpart` container, `link_part`, `part.import_part`, and the suite count they moved
- rising-chart-1564 — the corrected part-domain operation count
- forest-wind-3489 — `part.measurement`, the first output carrying no geometry: its three kinds, the `_PUBLISHABLE_TYPES` split, why the digest did not move, and the suite at 1,730
