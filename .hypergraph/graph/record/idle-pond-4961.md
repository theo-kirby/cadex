---
node_id: 454ff5e9-2b4d-53ac-a850-97b53d4f8ef6
slug: idle-pond-4961
title: Walk review names missed section objects and their rollout movement
created_at: '2026-09-09T01:32:28+00:00'
parents:
- restless-wave-7376
summary: ''
---
## What

The walk review now names every uncut section object in section.missed_objects
and reports whether its exact rollout component moved. Both translation and
rotation count; stationary measurements are false, unavailable evidence is
null with a reason. The CLI guide, project scaffold, ADR-277 and ROADMAP carry
the contract. Standalone section summaries remain geometric.

## Why

Advances the charter criterion **The agent can see its work without a screen**
(damp-moon-9297), mission 6 and short item 2 explicitly selected by the overseer.
A count alone did not identify the missing moving arm. Published object and
trace component keys share stable instance identities; the reversible choice
is exact matching only, never labels or shared source geometry. Ambiguous
source matches stay unknown. No capacity probe or new walk was attempted;
the fresh crank-slider refusal evidence is preserved.

## Method

One helper joins the section and motion blocks already assembled by write_review.
Fixture regressions exercise persisted output with rotation alone (178.8334 deg
and zero mm), translation, stationary components, unsupported sections, shared
source instances, unavailable motion and incomplete/nonfinite travel. Existing
integration assertions keep the standalone section summary equal apart from
the added walk-only field and summary path.

Replay the stored cadex-projects/ot4-swing2/runs/baseline/review.json and its
rollout/assembly-simulation-trace.json through motion_from_trace and write_review,
writing only /tmp/cadex50-swing-review/review.json. The old review predates the
motion block, so motion is derived from its own saved trace. No project edits,
geometry rebuilds or generated evidence committed.

## Result

pixi run python -m pytest cli/tests: exit 0, 285 passed, no skips in 227.87 s.
Full output is local at /tmp/cadex50-cli.log. The five focused regression cases
also passed. git diff --check passed. CLI-only change needs no full build.
Stored swing replay: five missed objects, three moving, two stationary, zero
unknown. cmp_swing_arm, cmp_pinch_bolt and cmp_pinch_nut each traveled
1.3237905704302508 mm and rotated 0.8203757175696758 deg; cmp_mount_nut_left
and cmp_mount_nut_right had zero travel in both channels. All five had empty
section status. This uses the stored baseline cut, not a newly derived plane.

The headless-eyes criterion already has four working calls; this unit closes
its remaining report join, with no additional requirement for that join before
criterion assessment. Initial-pose section misses remain real; this does not
add swept coverage or claim clearance. Next is the plan's conditional fresh
mixed-joint walk: one permitted readiness probe or new availability evidence,
then the walk on success; no polling campaign. The unreconciled tail reaches
three records with this node; reconciliation belongs to the separate maintainer.
Dispatch closed: 1 unit — name section misses and their measured rollout movement

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 2218c90be8c2f19dbd6df350fdd0213df0b136ef

## State Impact

- target: damp-moon-9297 — ADR-277 adds section.missed_objects with exact instance matches and translation plus rotation movement; missing or ambiguous evidence stays unknown. Stored swing baseline: five misses, three moving, two stationary. CLI gate 285 passed with no skips; no swept-coverage claim.
- target: chilly-union-8972 — Walk review joins existing section and motion blocks without new measurement; standalone section summary stays geometric. Guide and project scaffold document the join.
