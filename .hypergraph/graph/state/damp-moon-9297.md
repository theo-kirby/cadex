---
node_id: 531acaa2-823d-5218-88ca-dc1043987a63
slug: damp-moon-9297
title: The agent can see its work without a screen
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion: **The agent can see its work without a screen.** One CLI call each, with outputs landing in the project directory: render from named angles, section view through a named plane, list the parts of an assembly with catalog ids, and a clearance and intersection check that names the offending pairs. The lifecycle walk's review step uses them [rec: empty-wolf-3962]. The nt3 operator directive re-seeds the same criterion, unticked, as the second half of this run's frontier ("the lifecycle walk and the eyes it reviews itself with"); its ladder puts the four calls on the medium rung, one CLI call at a time, each wired into the walk's review step as it lands [rec: modest-summit-8554]. Declared target: `gap-agent-can-see-work-without`.

**All four review calls and their walk integration have landed:** inventory, clearance/intersection, named-angle rendering and named-plane sections. Their implementation evidence is now followed by separate fresh arm and carriage complete-review rehearsals [rec: first-branch-9614] [rec: quiet-vine-3426]. The inventory carries catalog ids. `inspect scope="inventory"` joins accepted assembly components to their source outputs, catalog identities, solved placements and source facts, with catalog totals and uncatalogued sources. `cadex inventory` writes the generated project document `docs/inventory.md` without AI or a rebuild. Real-engine assembly tests qualify the inventory; the original engine suite recorded 2070 passed / 52 skipped and the packaged lifecycle gate 15 passed, with no protocol change or `shell/` diff [rec: fair-rose-5950].

**The inventory paging critic rejection is fixed.** The CLI recursively expands nested previews and pages mappings, lists and strings, including catalog totals and uncatalogued sources. Real inspection-pager regressions cover 60 catalog totals, 60 uncatalogued names and oversized component rows, preserving every rendered name, count, pose and volume. The CLI gate recorded 147 passed with no skips; this fix changed only CLI Python and documentation [rec: lawful-ivy-4474].

**Inventory is wired into walk review and project commits.** `docs/inventory.md` lands alongside a `review.json` inventory block with availability, component and catalogued counts, and the project-relative report path. Real arm/carriage walks and local versus remote-flag CPU stand-in parity cover the report and commit. No assembly is unavailable at the review-reader boundary; dynamics/training prerequisites remain. The full CLI gate recorded 150 passed without skips; the documented hinged-arm walk passed in 14.39 s at toy CPU scale [rec: happy-dune-3481].

**`cadex clearance` writes `docs/clearance.md` without a read-time rebuild.** `inspect scope="clearance"` exposes every component pair's exact minimum distance and common solid volume at the initial solved pose, including separated pairs, with names, labels and catalog ids. Finite nonnegative read-time thresholds yield intersection, below-clearance, clear or unknown. Legacy, failed or unsolved measurements never imply clear; missing legacy measurements require rebuilding. The existing inspect operation and complete paged reader suffice, with no `OP_ARG_SPECS` or shell change [rec: falling-birch-1503].

Real three-box tests cover overlap, a separated 1 mm gap and a clear 10 mm gap, pair identity, pagination and threshold changes without a new attempt or digest change. Final warm rebuild medians changed +0.84% (arm) and -0.61% (carriage), below the declared +2 s or +20% stop conditions. A first-request arm spike was retained and did not recur in a quiet repeat. Engine: 2074 passed / 52 skipped; final focused tests: 14 passed; CLI: 159 passed without skips; build and stage succeeded; packaged lifecycle plus clearance: 24 passed without skips. These are recorded implementation checks, not reconcile-time runs or relocatable-release evidence [rec: falling-birch-1503].

**Clearance is wired into walk review and project commits (ADR-238).** The existing inventory inspection session also writes `docs/clearance.md`, a `review.json` clearance summary and a dedicated `PROGRESS.md` counts row, without another rebuild. Accepted revision, initial-pose scope, thresholds (0.1 mm minimum distance; 1e-6 mm³ maximum common volume), offending identities and explicit unknown/unavailable outcomes survive review. Findings do not fail the walk; inspection errors do. The built-engine CLI gate recorded 161 passed without skips, including real arm/carriage walks and local versus remote-flag CPU stand-in parity. Fresh public recipes passed with clean project commits: arm 14.5173 s with one below-clearance pair; carriage 13.1840 s with one clear pair; both had two components and zero unknowns. This is local toy CPU evidence, with no GUI or SSH execution [rec: clear-ash-2884].

**Named-angle product rendering is delivered (ADR-239).** `cadex render --project PROJECT --json` writes front/top/right/iso SVG previews plus `summary.json` under `review/render/`, carrying accepted revision, digest, bounds, camera bases, approximation and timings. Bounded accepted display snapshots retain solved placements once and suppress definition copies; CPU pixel-center depth handles crossing and occlusion. SVG wraps a lossless 512px raster image, not analytic vector drawings. Eight arm/curved-assembly views were inspected; the final built-engine CLI gate recorded 180 passed, zero skipped, including 19 render tests. No graphics dependency, engine/protocol/payload or shell source change [rec: silver-key-8483].

Warm single samples: arm acquisition 0.4908 s, rendering 0.5269 s, whole call 1.81 s; curved assembly acquisition 0.3293 s, rendering 0.6103 s, whole call 1.62 s. These qualify the measured fixtures, not large assemblies or walk overhead. Subpixel geometry can be missed; transparency, analytic edges, dimensions, engineering-drawing accuracy, shell visibility and motion-envelope review are not claimed [rec: silver-key-8483].

**Named-angle previews are now integrated into walk review and project commits.** One render/inspection session snapshots accepted display before inventory/clearance requests can invalidate buffers. Four images and summary land under `review/render/<accepted-revision>/`; review carries revision/digest, paths, approximation, limits and acquisition/render timings. Inventory and clearance remain intact. Malformed acceptance and a rebuild differing from rollout are refused; failed rendering exposes no new successful review. Real arm/carriage walks and local versus remote-flag CPU stand-in image parity pass. The implementation gate recorded 181 passed, zero skipped, followed by two passing refusal cases [rec: square-path-1173].

**Named-plane sections are delivered (ADR-240).** `cadex section --plane XY|XZ|YZ --offset-mm N` writes committed revision-bearing SVG/JSON under `review/section/` from bounded accepted world-space tessellation. Closed per-object contours use even-odd fill to preserve cavities and solved placements. Plane contacts, open/branched or duplicate/collapsed segments report unsupported; outside cuts report empty. Acquisition, revision, input and write failures remain command errors, and retained old files are not current success. A placed, rotated bored block verifies cavity areas and bounds; all three planes and refusal cases are tested. Full built-engine CLI gate: 188 passed, zero skipped; final section gate: 7 passed. This is a qualified tessellation cut, not an exact solid section or a solid-validity/motion certificate [rec: placid-lily-5624].

**Walk review includes sections from the same accepted snapshot as named views.** The fixed world XZ plane at Y = 3.125 mm gives meaningful interior cuts through both reference mechanisms, without mechanism-specific dispatch. Committed SVG/JSON and review metadata retain status, availability, revision/digest, plane/offset/units, paths, approximation, limits and acquisition/contour timings. Empty is available with no contours; unsupported is unavailable with reasons. Revision and rollout-digest mismatches, acquisition and write failures fail the walk without presenting retained artifacts as success. Documentation, scaffold and shared mode-artifact table agree [rec: copper-timber-8947].

**Separate fresh complete-review rehearsals pass on both mechanisms.** The unchanged public script/walk entry point ran one CPU training iteration with four environments, seed 0 and timeout 600 for each. All four named views and the interior XZ section were visually inspected; accepted identity matches rollout and review, and retained artifacts match clean committed project bytes. Both projects carry comparable reward, witness and review measurements in `PROGRESS.md`. Each inventory truthfully reports two synthetic, uncatalogued components. Arm section areas are 360/640 mm² and carriage areas 360/400 mm². The named base–swing pair remains contact (0 mm distance, 0 mm³ common volume, one offending pair); base–slide is clear (34 mm, 0 mm³, zero offending). Both have zero unknowns [rec: first-branch-9614] [rec: quiet-vine-3426].

Each rehearsal's full built-engine CLI gate recorded **195 passed, zero skipped** (217.22 s arm; 219.10 s carriage). External whole walks took 16.61/16.39 s with sampled process-tree peaks 1,059,241,984/987,168,768 bytes. Runs overlapped their gates: these are observations, not speed benchmarks. Policy witnesses pass, but the carriage falls under gravity and force/torque effort units differ; rewards do not rank useful control. GUI remains documented-only and remote scripted-only with earlier local CPU stand-in parity [rec: first-branch-9614] [rec: quiet-vine-3426].

**Reconcile judgement: `open` → `working`.** The two fresh rehearsals discharge the previously explicit missing evidence unit: inspected named views, meaningful sections, truthful inventory, named-pair checks, accepted identity and committed comparisons. Together with the delivered calls and integration, they cover the headless-review criterion. This assessment follows the declared request for maintainer judgement; it does not claim swept safety, exact solid sections, hardware validation or useful learned control, and it does not edit the charter or select the next plan [rec: first-branch-9614] [rec: quiet-vine-3426].

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
- brave-delta-4193 — fresh bounded arm walk reproduces committed inventory/clearance and verified rollout; CLI 161 passed without skips
- silver-key-8483 — bounded named-angle CPU render delivered and visually inspected; CLI 180 passed without skips; walk integration and sections remain open
- square-path-1173 — walk integrates committed revision-bearing previews; arm/carriage and CPU stand-in parity pass; sections remain unavailable
- modest-sun-6068 — separate fresh arm rehearsal verifies committed previews, preserved clearance and reward; full CLI gate 182 passed with zero skips
- placid-lily-5624 — named-plane cavity-preserving section command and built-engine qualification
- copper-timber-8947 — shared-snapshot walk sections and both-mechanism CPU parity; separate complete-review rehearsal remains open

- first-branch-9614 — fresh arm complete-review rehearsal, inspected artifacts and committed identity audit; CLI 195 passed without skips
- quiet-vine-3426 — fresh carriage completes the paired rehearsal with committed comparisons; evidence supports working status within initial-pose and toy-policy limits
