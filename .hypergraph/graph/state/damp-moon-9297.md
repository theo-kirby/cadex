---
node_id: 531acaa2-823d-5218-88ca-dc1043987a63
slug: damp-moon-9297
title: The agent can see its work without a screen
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Open charter criterion: **The agent can see its work without a screen.** One CLI call each, with outputs landing in the project directory: render from named angles, section view through a named plane, list the parts of an assembly with catalog ids, and a clearance and intersection check that names the offending pairs. The lifecycle walk's review step uses them [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the same criterion, unticked, as the second half of this run's frontier ("the lifecycle walk and the eyes it reviews itself with"); its ladder puts the four calls on the medium rung, one CLI call at a time, each wired into the walk's review step as it lands [rec: modest-summit-8554]. Declared target: `gap-agent-can-see-work-without`.

**Two of the four calls have landed: inventory (ADR-236) and clearance/intersection (ADR-237).** The inventory carries catalog ids. `inspect scope="inventory"` joins accepted assembly components to their source outputs, catalog identities, solved placements and source facts, with catalog totals and uncatalogued sources. `cadex inventory` writes the generated project document `docs/inventory.md` without AI or a rebuild. Real-engine assembly tests qualify the inventory; the original engine suite recorded 2070 passed / 52 skipped and the packaged lifecycle gate 15 passed, with no protocol change or `shell/` diff [rec: fair-rose-5950].

**The inventory paging critic rejection is fixed.** The CLI recursively expands nested previews and pages mappings, lists and strings, including catalog totals and uncatalogued sources. Real inspection-pager regressions cover 60 catalog totals, 60 uncatalogued names and oversized component rows, preserving every rendered name, count, pose and volume. The CLI gate recorded 147 passed with no skips; this fix changed only CLI Python and documentation [rec: lawful-ivy-4474].

**Inventory is wired into walk review and project commits.** `docs/inventory.md` lands alongside a `review.json` inventory block with availability, component and catalogued counts, and the project-relative report path. Real arm/carriage walks and local versus remote-flag CPU stand-in parity cover the report and commit. No assembly is unavailable at the review-reader boundary; dynamics/training prerequisites remain. The full CLI gate recorded 150 passed without skips; the documented hinged-arm walk passed in 14.39 s at toy CPU scale [rec: happy-dune-3481].

**`cadex clearance` writes `docs/clearance.md` without a read-time rebuild.** `inspect scope="clearance"` exposes every component pair's exact minimum distance and common solid volume at the initial solved pose, including separated pairs, with names, labels and catalog ids. Finite nonnegative read-time thresholds yield intersection, below-clearance, clear or unknown. Legacy, failed or unsolved measurements never imply clear; missing legacy measurements require rebuilding. The existing inspect operation and complete paged reader suffice, with no `OP_ARG_SPECS` or shell change [rec: falling-birch-1503].

Real three-box tests cover overlap, a separated 1 mm gap and a clear 10 mm gap, pair identity, pagination and threshold changes without a new attempt or digest change. Final warm rebuild medians changed +0.84% (arm) and -0.61% (carriage), below the declared +2 s or +20% stop conditions. A first-request arm spike was retained and did not recur in a quiet repeat. Engine: 2074 passed / 52 skipped; final focused tests: 14 passed; CLI: 159 passed without skips; build and stage succeeded; packaged lifecycle plus clearance: 24 passed without skips. These are recorded implementation checks, not reconcile-time runs or relocatable-release evidence [rec: falling-birch-1503].

**Clearance is wired into walk review and project commits (ADR-238).** The existing inventory inspection session also writes `docs/clearance.md`, a `review.json` clearance summary and a dedicated `PROGRESS.md` counts row, without another rebuild. Accepted revision, initial-pose scope, thresholds (0.1 mm minimum distance; 1e-6 mm³ maximum common volume), offending identities and explicit unknown/unavailable outcomes survive review. Findings do not fail the walk; inspection errors do. The built-engine CLI gate recorded 161 passed without skips, including real arm/carriage walks and local versus remote-flag CPU stand-in parity. Fresh public recipes passed with clean project commits: arm 14.5173 s with one below-clearance pair; carriage 13.1840 s with one clear pair; both had two components and zero unknowns. This is local toy CPU evidence, with no GUI or SSH execution [rec: clear-ash-2884].

**Named-angle feasibility is measured; product rendering is still missing (ADR-239).** With the fresh staged-engine override, accepted hydration succeeds but valid front/top/right/iso blueprint calls and `render_views` refuse background rendering. Independently authored standard-library CPU projection of accepted tessellation produced four inspected, placement-correct SVGs from two components / 24 triangles, using solved placements once and excluding unposed definition copies. Display acquisition took 1.73 s and projection 0.20 s in warm single samples. The selected route needs bounded buffers, revision-safe snapshots, visibility handling and broader fixtures before delivery; the probe's centroid painter ordering and triangle diagonals do not qualify production occlusion, curves or large assemblies. Sections still need clipping, contours/caps and approximation labels [rec: zesty-aspen-6846].

**Still missing before the criterion can be ticked:** product named-angle render and named-plane section calls, each integrated into walk review. Reconcile judgement: retain `open`; clearance wiring closes its declared gap, while four probe SVGs establish feasibility only. Clearance remains initial-pose-only and quadratic all-pair cost is unqualified for large assemblies [rec: falling-birch-1503] [rec: clear-ash-2884] [rec: zesty-aspen-6846].

## Negative knowledge

- [scope: named-angle probe using the existing background Blender renderer after accepted hinged-arm hydration | confidence: high | evidence: zesty-aspen-6846] All four valid blueprint views and `render_views` explicitly refuse background mode. The override probe's exit 0 records returned errors, not a rendered PNG. CPU projection must snapshot revision-dependent display buffers before another rebuild invalidates their paths.

- [scope: inventory inspection replies exceeding the 1 KiB per-key budget | confidence: high | evidence: lawful-ivy-4474] Paging only `/components` is insufficient: catalog totals, uncatalogued sources, component rows and nested strings can also be previews. The former reader failed converting `/catalog_counts` to an integer and could lose oversized names; recursive expansion is required and regression-tested.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- modest-summit-8554 — nt3 operator directive re-seeds the criterion unticked; the four calls sit on the medium rung
- fair-rose-5950 — ADR-236: the assembly inventory with catalog ids as `inspect scope="inventory"` plus `cadex inventory` writing docs/inventory.md; real-engine qualified; three calls and the review-step wiring remain
- lawful-ivy-4474 — fixes the inventory paging critic rejection with real inspection-pager regressions; remaining review calls and walk wiring stay open

- happy-dune-3481 — inventory report and review metadata committed by the walk; arm/carriage and CPU stand-in parity verified
- falling-birch-1503 — ADR-237: complete initial-pose clearance/intersection reporting; bounded recipe rebuild cost and packaged gates verified; remaining review work stays open
- clear-ash-2884 — ADR-238: clearance findings, explicit unknowns and comparable counts committed by the walk; full CLI gate and fresh public recipes pass
- zesty-aspen-6846 — ADR-239: background refusal measured; accepted-tessellation CPU route selected with four inspected SVG probes; product rendering and sections remain open
