---
node_id: d3fb7ddf-e2b6-5705-ae57-e7269d618eeb
slug: civic-walrus-3405
title: Regions follow couplings; lids, doors and walls close a frame (ADR-665, ADR-666)
created_at: '2026-10-11T09:57:30+00:00'
parents:
- little-ash-2582
summary: ''
---
## What

Two verification gaps the first breadth wave found (little-ash-2582), fixed in
the engine: the regions (anatomy) block now follows belts, lead screws and
couplings (ADR-665), and the panel check has a closing panel -- a lid, door or
enclosure wall -- declared `role="panel", covers=[...], closes=[frame]`
(ADR-666).

## Why

`wave1-liquid-handler` drove all four axes through `assembly.coupling` from
catalog-driven pulley and screw revolutes, and the regions block read all four
slider regions `passive only` (verdict incomplete). `wave1-rover` declared its
tub lids `role="housing"` and `wave1-printer` its walls `frame` and its doors
and lid `housing`, because the panel check judges a panel by its gap to what
it covers and fails one past ~8 mm p90: every closing part went unjudged.

## Method

- `CadexAnatomy.anatomy_summary`: a fifth drive, `coupled`. Coupled joint
  kinds (screw, gears, belt, rack_pinion) relate the mobile joints on the
  spanning-tree path between their components' rigid bodies; an
  `assembly.coupling` the joints it names (stamped by `_anatomy_stamp` as
  `couplings`, only when declared). Fixed point with loop drive. Rows carry
  `driver` and `through`; block counts `coupled_joints`; no `driven_dof`.
  Also: of two coaxial catalog motors, the nearer drives the joint.
- `assembly.component(closes=...)` (panel only; `covers`/`closes` unannotated
  to keep the assembly describe_api page under budget: 21,463 of 21,500).
  Worker: 3,000 points over the closed frame near the panel
  (`CadexPanels.sample_triangles`), `seam_statistics` (frame within 15 mm whose
  outward normal points at the panel, cos >= 0.7). `panel_summary`: no
  floating/egg; `unseated` (pair distance > 1 mm) and `open seam` (seam
  median > 2 mm or none) fail.
- Guidance COVERS AND PANELS paragraph teaches `closes=` at exactly 2,700
  words; component and anatomy docstrings, XSCRIPT.md, DESIGN-LANGUAGE.md,
  DECISIONS.md updated.
- Probes under the 25 GB cap with the rebuilt engine: a probe tub/lid +
  leadscrew axis; scratch copies of the liquid-handler and rover scripts
  (rover lids switched to `closes=[chassis]`).

## Result

- Liquid handler copy: anatomy `complete`, `coupled_joints: 4`; `y_axis`,
  `x_axis`, `z_axis`, `p_axis` coupled through their couplings;
  `y_pulley_r_turn` now driven by `y_motor_r` (was `y_motor_l`).
- Probe lid: seated passes (seam 0.0 mm, 75 samples); lifted 0.5 mm seated;
  lifted 11 mm `unseated`; tilted 7 deg `open seam` (median 4.37 mm).
- Rover copy: both lids pass seat and seam (median 0.0 mm) with only advisory
  bed/fastener findings. Dead end recorded: reading the frame normal in
  either sense counted the rover's 2 mm lip underside and put the median at
  exactly 2.0 mm; the outward sense (FreeCAD tessellation winds outward,
  checked) fixed it.
- Limits: a tray shallower than 15 mm reads its floor as open seam; a hinged
  door is still mounted only by bolt or weld. The fit sweep's `passive`
  (ADR-644) is sweep coverage, left unchanged and consistent.
- Suites at 4e5efe80: engine 2847 passed, 62 skipped (capped); cli/tests 1260 passed, 1 skipped, 1 failed -- a dashboard scrubber colour test (test_review_checkpoints dark), unrelated, which passed in the first full run and passes 10/10 rerun alone.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a657d7b3f98cbc922
- commit: 4e5efe8094c8e6a8a8776ffdeeff0dc528abba70

## State Impact

- target: forest-wind-0342 — The regions (anatomy) block reads a joint tied to a driven joint by a screw, gears, belt, rack_pinion joint or assembly.coupling as coupled (driver, through), so belt- and screw-driven axes read articulated (ADR-665); the nearer of two coaxial catalog motors drives a joint. Live: the wave1 liquid handler reads complete with four coupled axes.
- target: idle-lantern-9094 — A lid, door or enclosure wall is a closing panel, role="panel", covers=[...], closes=[frame] (ADR-666): judged seated on its frame (unseated past 1 mm) with no open seam (frame facing it within 15 mm, outward normal, median past 2 mm), floating and egg off. Proved on a probe tub (seated/lifted/tilted) and the wave1 rover's lids. Limit: a tray shallower than 15 mm reads its floor as open seam.
