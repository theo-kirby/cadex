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
- Parameter changes are served two ways: a resident read-only preview worker answers a **pose-only** change in 33 ms, and everything else pays the ~0.42 s accepting path [rec: open-dew-7293].
- The engine suite is **1,698 passed / 22 skipped**, measured 2026-08-09, headless and needing no build (`pixi run test-engine`); the skips are MJX-gated by design [rec: even-cliff-3863] [rec: sage-wood-0687].
- The engine carries VibeCAD-era code under its own provenance tags, and the licence boundary that follows from it is one-way and hard: the engine side is LGPL, `shell/` is GPL [rec: lone-haven-0640].

**Gap, unbuilt.** The ADR-027 response fixtures are asserted **engine-side only**. Asserting the same fixtures from the shell side is a ROADMAP Phase 9 item that has never been checked off, and it is more valuable since the merge, not less: one repository removed the distance that used to enforce the boundary [rec: simple-hollow-8675] [rec: merry-eagle-4093].

## Negative knowledge

- [scope: mesh domain outputs | confidence: high | evidence: civic-horizon-2730] Kernel output ordering is not a contract. FreeCAD's native mesh set operations return run-dependent orderings and triangulations, so a mesh output is not digest-stable without canonical vertex/facet reordering plus a vertex-set fingerprint.
- [scope: the 33 ms preview worker | confidence: high | evidence: open-dew-7293] The preview cannot serve a parameter that changes a definition — a placement-only reply for part.box(p.width, ...) would be a lie. The 33 ms headline applies to a subset of sliders only; the rest pay the ~0.42 s accepting path.
- [scope: kernel version pins | confidence: high | evidence: sage-wood-0687, civic-horizon-2730] Neither kernel may float. Reproducibility is asserted on every open, so occt and mujoco are exactly pinned; an unpinned update silently changes what a saved script means.

## Provenance

- lone-haven-0640 — the engine's origin as a FreeCAD fork and the VibeCAD-era code it still carries
- civic-horizon-2730 — one project script, the removal protocol, and rebuild-digest equality
- simple-hollow-8675 — cadexd, the NDJSON protocol, and the test-pinned process boundary
- open-dew-7293 — the preview/accept split and the latency numbers
- sage-wood-0687 — the deferred-import discipline and the MJX-gated skips
- even-cliff-3863 — the measured suite count that replaced the stale documented one
- merry-eagle-4093 — why the shell-side fixture gap got more valuable after the merge
