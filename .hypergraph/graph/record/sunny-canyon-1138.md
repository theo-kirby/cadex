---
node_id: 53f61f44-b406-599d-8341-3d1062a63a2d
slug: sunny-canyon-1138
title: Qualify assembly source visibility with headless camera rendering
created_at: '2026-09-07T03:52:50+00:00'
parents:
- tidy-sea-8308
summary: ''
---
## What

Qualified the assembly camera render defect through actual source hydration
and headless EEVEE rendering. Added ASSEMBLY-VISIBILITY-AUDIT.md, ADR-228,
corrected the IDEAS proposal and ticked the audit-only ROADMAP item.

## Why

The short plan from tidy-sea-8308 targets wild-comet-8096 as mission 1
maintenance enabling headless review. Choose the reversible documentation
and experiment unit before a fix. The overseer reconciliation request is
stale relative to the supplied checkpoint/plan; this contributor dispatch
explicitly forbids reconciliation. No state, plan or charter was edited.

## Method

Temporary /tmp/cadex-52-probe.py loaded source mesh_agent in built Cadex via
package/app/build_app.sh exec, with --background --factory-startup and
--python-exit-code 1. Real tessellation sidecar buffers hydrated a square
source at x=-2, ordinary square at zero and shared-mesh posed component at
x=2. EEVEE rendered transparent 256x128 orthographic images. Counted alpha
pixels in separate source/ordinary/component bands; audited edge flags,
repeat hydration, explicit unrelated hides, component removal and a
pre-hidden source. The committed audit specifies fixture reconstruction.
Temporary probes/images/logs remain outside git as the plan requires.
Ran pixi run gate against the bundled engine and source shell application.

## Result

Before: 1024/1024/1024 pixels; source-only render-hide intervention:
0/1024/1024. EEVEE probe exit 0. Cycles attempt exit 1 because that renderer
is absent from the bundle; no missing EEVEE prerequisite. Source solid/edges
carry viewport markers and remain render-visible; ordinary explicit hides
survive repeated hydration. Existing viewport ownership does not preserve
a source's prior viewport hide after removal. Qualify independent render
ownership to avoid importing this limitation into render restoration.
Full baseline gate exit 0, ok true, engine_from_bundle true, picking 372/372,
slider median 0.523 s (bar .65), model_objects_on_open 1. No full build and
no runtime change. The render defect remains open. Next: implement only the
qualified source/edge render ownership, add old-source-failing regression
and run full headless gate. Broader review/video and fork-delta criteria
remain open; inherited files and manifest were untouched.
Dispatch closed: 1 unit — qualify headless assembly render visibility and its minimal fix boundary

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: c28675c84dd79f5d32f9d80f57d077fdba1af1e5

## State Impact

- target: wild-comet-8096 — Actual hydration and EEVEE reproduce raw-source camera leakage; independent render-hide ownership and regression boundary qualified in ADR-228, implementation remains open.
- target: shy-crane-2573 — Baseline headless product gate passes; audit records source/edge marker transitions and pre-existing viewport restoration limitation.
