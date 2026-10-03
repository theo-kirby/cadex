---
node_id: 702a01ee-aff4-5e49-84f2-afb80a8de9c3
slug: solemn-arbor-0802
title: 'orun1 D3 catalog half: STS3215, Pi 5, camera, ToF sensor, wheel, foot pad (ADR-485)'
created_at: '2026-10-03T02:44:57+00:00'
parents:
- golden-bay-7992
summary: ''
---
## What

The record iteration 14 did not write: orun1 D3's catalog half, landed in
commit `9ea7a4a8` ("ouroboros #14: no record") as ADR-485. Six catalog rows,
each with datasheet sources, true dimensions, mounting features, a bay and an
`approximate` list:

- `servo("sts3215")` — Feetech STS3215 C001 bus servo, a new `bus` servo
  family with `mount_style: "case_holes"` and `spec['mount_points']` (eight
  M2 holes on the output and rear faces, each with its screw axis); its bay
  keeps both faces reachable. Actuator and joint dynamics from Feetech's
  6 V / 7.4 V ratings. Tab servos' recipe unchanged, so no digest moved.
- `board("pi-5")` — Raspberry Pi 5, outline/holes/ports from the Pi 5
  drawing, port heights from the Pi 4 drawing; J8_1-40 pads.
- `board("rpi-camera-module-3")` — lens centre and FOV in the spec; the
  back-face FPC block as `underside_components_mm`, which `board.bay` now
  never stops short of (a behaviour change only for boards carrying the
  field; no earlier board does).
- `board("pololu-vl53l1x-3415")` — time-of-flight range sensor (Pololu's
  annotated photos + ST's datasheet; range and FOV in the spec).
- `wheel("pololu-1430")` — new `wheels` family, 80 x 10 mm, 3 mm D bore that
  matches `gearmotor("pololu-2367")`'s shaft (test-pinned); bay = swept disc.
- `foot_pad("essentra-462178")` — new `foot_pads` family; bay = keep-out plus
  the M3 tapping hole.

`describe_api.library.catalog` gained `wheels` and `foot_pads` (golden and
`docs/INTEGRATION.md` moved with it; no request op changed). Overlay names
each part where the machine needs it. Provenance in `docs/PROVENANCE.md` §8h.

## Why

Critic fix-first for iteration 15: iteration 14 committed ADR-485 with no
hypergraph record, so the work was invisible to the state graph. This
record carries it, causally parented on the D2 record, with its impact on
the D3 node.

## Method

Read the commit (`git show --stat 9ea7a4a8`: CadexCatalog.py,
cadex_library_api.py, test_library.py, describe_api.json golden,
INTEGRATION.md, PROVENANCE.md, the overlay, DECISIONS.md) and ADR-485.
Ran the engine suite at exactly that revision in a separate worktree
(`git worktree add /tmp/orun1-head 9ea7a4a8`, the main repo's pixi
environment) so that no later edit could leak into the result.

## Result

What is true now: D3's catalog half has landed — every part the charter
lists (STS3215-class bus servo, a Pi 5, a camera module, a ToF range
sensor, a wheel and tyre, a rubber foot pad) is in the catalog with sources,
dimensions, mounting features and a bay. D3's mounting check was still open
at this commit (it is the next record's unit). The charter's "anything else
the D4 transcripts show the agent reaching for" cannot be done before D4
transcripts exist.

Test evidence at `9ea7a4a8`: `python -m pytest src/Mod/cadex/cadex_tests`
→ **2397 passed, 223 skipped, 0 failed** (160 s). The worktree had no
engine build, so its real-kernel tests were among the skips; the next
record's full run in the built main tree covers those, ADR-485's included.

Concerns: the STS3215's raised cover and rear bump (35 mm envelope vs 29 mm
modelled case) are scaled from a drawing and not modelled; the foot pad's
density is rubber's nominal value.

Dispatch closed: 1 unit — the missing record for ADR-485's catalog additions (D3 catalog half)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 9ea7a4a8b09aeb30bd9ca6d1874ba34315767461

## State Impact

- target: loyal-ocean-0768 — Catalog half landed (ADR-485, commit 9ea7a4a8): sts3215 bus servo with mount_points, pi-5, rpi-camera-module-3, pololu-vl53l1x-3415, wheel pololu-1430, foot_pad essentra-462178, each with sources, dimensions, mounting features and a bay; engine suite at that commit 2397 passed / 223 skipped. Mounting check still open at that commit.
