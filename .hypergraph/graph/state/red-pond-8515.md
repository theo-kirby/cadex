---
node_id: 9d7f39a5-0b47-5ee2-b664-17053c144edd
slug: red-pond-8515
title: F1. A project that was accepted always reopens (orun1)
created_at: '2026-10-02T17:01:45+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun1: **F1. A project that was accepted always reopens.** Three sweep projects (`digestbug-balancer-b-motors-in-body`, `digestbug-balancer-d-product-shell`, `digestbug-hexapod-h-free`) refused to open with "The restore pass digest does not match the accepted digest". The criterion asks for a diagnosis, a product fix with a regression that fails before it, and all three opening and rendering at their accepted revision on `orun1-*` copies, originals read-only [rec: sweet-brook-2725]. The human owns the checkbox; roles report results and do not tick it. Reconcile judgement: status `working` because the fix and its evidence have landed; the residuals below are not hidden by it.

**Diagnosed and fixed (ADR-476, commit `9989b45c`; amended by ADR-477, commit `3d17000e`).** Inputs were identical: `script.py` byte-equal to the accepted source, no engine commit since acceptance, every output's definition hash equal; only the kernel fingerprint differed [rec: idle-loom-0473]. Two causes:
1. a capped partial `fillet(..., on_failure="skip")` depends on the kernel's per-process edge order (balancer-b `tub` kept 20, 19 and 31 of 165 edges across three runs, the 48-call cap binding, not the 15 s clock);
2. `part.offset` moves vertices a few µm between processes (hexapod `shell`: 3 of 92 vertices by 4.5–4.9 µm), breaking ADR-421's exact-vertex-set assumption.
Resumed turns were **not** a cause: restore runs the accepted source and the drift reproduces with no session; load changes only how often it shows [rec: idle-loom-0473].

The fix that stands is **recipe-level restore**: when byte and geometry digests disagree but source, settings and every output's name/domain/type/definition match the accepted attempt, `open_project` succeeds with `matched_by: "recipe"` and names `drifted_outputs`; a changed script or missing evidence still refuses [rec: idle-loom-0473]. ADR-476's second part — a measured-order partial-blend search — was itself a regression: held-out reopens went from 25/26 to 20/26 (arm3's sort put every unblendable B-spline edge first and blended 0 of 244), so ADR-477 reverted it to kernel order with a regression red on ADR-476's source [rec: forest-sun-0304].

**Evidence.** All three `orun1-*` copies opened and rendered at accepted revisions `2fb82493` / `68c37ac1` / `94759ef5` through the recipe path [rec: idle-loom-0473]. After ADR-477, **58 of 58** sweep and digestbug projects reopen when opened one at a time. Gates at `3d17000e`: engine 2545 passed / 61 skipped, `cli/tests` 1290 / 1 skipped (GPU hidden), packaged lifecycle 24 passed [rec: forest-sun-0304].

**Still open.**
- Under load a reopen can still fail: at eight opens in parallel with the engine suite running, two hit the 300 s domain timeout and `digestbug-balancer-d` hit the blend probe's **15 s wall clock** (10 calls, no edge probed); all three opened when rerun alone. A wall-clock-bounded partial blend is load-dependent; ADR-477 did not change it [rec: forest-sun-0304].
- `cadex render`'s accepting display `rebuild` re-accepts a drifted model at the same revision (balancer-d's accepted digest alternated `c01707f1` / `4b2126ce` over three renders); every open still succeeds via recipe. Whether a display rebuild should re-accept is undecided [rec: idle-loom-0473].
- The CLI's open-failure message still drops cadexd's `observed` detail [rec: idle-loom-0473].

## Negative knowledge

- [scope: a capped partial skip-blend searched in a sorted (curve-type-first) edge order | confidence: high | evidence: forest-sun-0304] Sorting makes which edges are kept process-independent but front-loads unblendable B-spline edges, so the bisecting search spends its cap rejecting them: 6 of 26 held-out designs refused to reopen. Reverted; kernel order plus recipe-level restore is the fix.
- [scope: canonical edge order as a cure for capped partial-blend drift | confidence: medium | evidence: idle-loom-0473] Even in a canonical order balancer-b `frame` kept 36 edges in one process and 37 in the next: the kernel's verdict on a marginal subset is itself not reproducible, so "same recipe" rather than "bit-reproducible" is what restore can prove.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- idle-loom-0473 — ADR-476: cause diagnosed (kernel-order partial blends, part.offset µm drift, resumed turns not a cause); recipe-level restore; three orun1-* copies open and render
- forest-sun-0304 — ADR-477: the sorted blend search refused 6/26 held-out designs and was reverted; 58/58 reopen unloaded; under load the 15 s blend clock still refuses
