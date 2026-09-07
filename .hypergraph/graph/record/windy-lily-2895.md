---
node_id: 91edb83e-5e83-52e5-9bd4-8659e07b1207
slug: windy-lily-2895
title: Verify N20 shaft and mounting bores independently in actual workers
created_at: '2026-09-07T01:52:43+00:00'
parents:
- late-pond-3758
summary: ''
---
## What

Added one actual-worker N20 interface test to test_library.py: independent
OCCT shaft/flat and mounting-bore surface measurements plus material/void
probes, repeated after a cyclic rotation and translation. Updated ADR-205,
L3-COVERAGE and the ROADMAP verification checkbox. No runtime code, catalog
values, API, inherited files or source qualifications changed.

## Why

Plan short item 2 and the overseer select this unit after late-pond-3758's
GSL cleanup. It strengthens rising-banner-4325 and brave-stone-9609:
publication and recipe-input assertions did not independently measure the
N20 interfaces. Existing PROVENANCE 8b is the dimension contract; no new
outside source was consulted. The reversible choice is evidence-only tests.
Assumed 1 mm blind-bore depth and the sharp flat transition at Z=1 remain
explicit, with no screw-engagement or installed-fit permission inferred.

## Method

Build lib.gearmotor("pololu-2367").body via build_part_shape in FreeCADCmd,
using the source or CADEX_ENGINE_ROOT-selected worker. Read actual cylinder
and plane surfaces against literal expected dimensions independent of
catalog/recipe metadata. Check canonical and origin=(100,30,20),
direction=(1,0,0), roll=90 instances. Independently map probe coordinates
(x,y,z) to (100+z,30+x,20+y), and invert by a -120-degree (1,1,1) rotation
for surface measurements. Require valid single solids and equal volume.
Probe both sides of four bore walls, the blind bottom, shaft circle, flat,
transition and tip. No new physical hardware measurement is claimed.

Commands: pixi run python -m pytest src/Mod/cadex/cadex_tests/test_library.py
-k gearmotor_real_worker -s; pixi run stage-engine; pixi run python -m pytest
src/Mod/cadex/cadex_tests; then CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64
pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py
src/Mod/cadex/cadex_tests/test_library.py -s. Staging finished before either
suite. Source and payload bytes match for CadexCatalog.py,
cadex_library_api.py and cadex_part_worker.py. No build needed for this
test/doc-only unit. Ephemeral logs: /tmp/cadex-n20-{stage,engine,packaged}.log.

## Result

Source focused test: 1 passed, 75 deselected, 0.26 s. Full engine:
2023 passed, 52 skipped, 254.80 s, exit 0. Freshly staged lifecycle/library:
91 passed, no skips, 19.44 s, exit 0, including all four actual-worker
interface tests and canonical/placed library publication.
Both N20 instances measure bore tuples (x,y,r,zmin,zmax) in mm:
(-4.5,0,0.8,-1,0), (4.5,0,0.8,-1,0); shaft diameter 3 mm,
flat-to-opposite 2.5 mm, flat axial extent 1..10 mm. 80 material/void
probes per instance pass, 160 total. Surface tolerance 1e-7 mm (bore tuples
rounded to 1e-6), equal-volume tolerance 1e-6 mm^3.
Local stage-only payload is 2.4 GB; stage exits 0 while relocation audit
reports 144 external-path violations. It is not shippable; packaged gates
prove local behavior only. No GUI, training, remote machine or full build.
Next: plan short item 3's bounded additional-BLDC source audit and named
acceptance set. Full L3 remains open. This record brings the observed tail
to three; a separate maintainer should reconcile. No reconcile, state,
PLAN or .ouroboros edits were made under the work-iteration prohibition.
Dispatch closed: 1 unit — independently verify N20 shaft and mounting interfaces in source and packaged workers.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: ab0b8b5fb960a8dae442ce0e4c549edc4615b211

## State Impact

- target: rising-banner-4325 — N20 now has independent actual-worker surface measurements and 160 canonical/placed material probes; full engine 2023 passed/52 skipped and fresh packaged lifecycle/library 91 passed. Assumed bore depth and flat transition persist; full L3 stays open. Next is the bounded BLDC candidate audit.
- target: brave-stone-9609 — N20 D-shaft and mounting-bore geometry independently verified in source and staged workers: diameter 3, flat-to-opposite 2.5, flat Z=1..10, bore radius 0.8 at X=±4.5 and Z=-1..0 mm. No new SKU or installed-fit claim; local payload has 144 relocation violations.
