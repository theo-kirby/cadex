---
node_id: 1f8afb46-bc0d-510e-931f-c341516bd1e0
slug: happy-key-3312
title: GUI app parity with the CLI and the review dashboard
created_at: '2026-09-30T06:56:25+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

**Owner direction (2026-09-29):** bring the GUI app up to the CLI and the review dashboard. The app agent lacked look, the design language and measured fit; the app UI lacked run history, per-run curves, renders and videos. The owner chose native panels over the same on-disk files, and engine-side shared code; 8 slices were planned [rec: warm-spire-8762].

**All 8 slices landed**, each gate showing only the 8 pre-existing restore-lockout failures of clean `main` [rec: rough-water-0848] [rec: eager-basin-6116]:

1. Studio renderer is engine code, run beside the service (ADR-445) [rec: fond-dawn-4115].
2. Agent guidance is engine data both front ends paste in (ADR-446) [rec: strong-sail-2579].
3. Fit and inventory blocks are engine code (ADR-447) [rec: upright-glacier-1185]; the app's agent sees and measures its design as the CLI's does (ADR-448) [rec: crimson-trail-6068].
4. The viewport paints each part in its appearance role (ADR-449) [rec: rough-water-0848].
5. The Training editor lists the project's runs (ADR-450) [rec: restless-fjord-9059].
6. A selected run's curve is drawn (ADR-451) [rec: staid-nest-0170].
7. The app shows and makes studio renders, and plays run videos (ADR-452) [rec: peaceful-sail-5197].
8. The chat shows the running turn and the session's cost (ADR-453) [rec: eager-basin-6116].

Detail lives in the engine, CLI and shell nodes. Status is `working` rather than the `open` the direction declared, because every planned slice has since landed (derived from the slice records above) [rec: warm-spire-8762] [rec: eager-basin-6116].

## Negative knowledge

None yet.

## Provenance

- warm-spire-8762 — owner direction: GUI app up to CLI and dashboard; native panels, engine-side shared code; 8 slices
- fond-dawn-4115 — slice 1, ADR-445
- strong-sail-2579 — slice 2, ADR-446
- upright-glacier-1185 — slice 3a, ADR-447
- crimson-trail-6068 — slice 3b, ADR-448
- rough-water-0848 — slice 4, ADR-449
- restless-fjord-9059 — slice 5, ADR-450
- staid-nest-0170 — slice 6, ADR-451
- peaceful-sail-5197 — slice 7, ADR-452
- eager-basin-6116 — slice 8, ADR-453
