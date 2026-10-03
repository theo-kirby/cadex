---
node_id: 40f410c6-84f7-532c-945a-642fc95f75a7
slug: eager-bluff-0757
title: 'orun1 D3/D4: ADR-489 catalog wheel is a spoked rim, tyre a part of its own'
created_at: '2026-10-03T04:50:43+00:00'
parents:
- honest-ledge-9020
summary: ''
---
## What
The record for ADR-489 (commit `3b301c57`), which landed without one. `lib.wheel("pololu-1430")` is now a spoked rim taken from Pololu's STEP model (hub tube, cone shoulder, flange, six ribbed spokes, a rim from Ø67 to Ø76.5, six Ø3.1 holes on the Ø19.1 circle, round bore kept per ADR-487). `wheel.tyre()` is a separate catalog part (`tyre/pololu-1430`, Ø76.5 to Ø80, 10 wide). The 19.8 g is split by kernel volume: tyre 4194.8 mm³ at 1100 kg/m³ = 4.61 g, wheel 14715.5 mm³ for the rest. The mounting check gains a `rim` row: a tyre that touches a held wheel is held, and a tyre is freed along with its wheel.

## Why
The critic asked for this record first, parented on honest-ledge-9020. Both balancer trials lost their frozen-v2 comparisons against sweep c and e, and both judge transcripts cite plain disc wheels (first-eagle-0836).

## Method
The tests and their fail-before results are in ADR-489's "Measured" paragraph. `test_library.py::test_the_catalog_wheel_is_a_spoked_rim_and_a_separate_tyre` runs on the real kernel and checks the pinned volumes, that the gap between spokes is air, that the tyre is a valid Ø80.00 solid touching the rim without overlapping it, and that the total is within 3% of the STEP model's 19220.1 mm³ (measured: within 1.6%). `test_mounting_check.py` covers three tyre cases: on a held wheel (held, `rim`), on a wheel whose motor is loose (held by nothing), and off any wheel. On the old source the recipe test, the kernel test and the mounting fixture all fail.

## Result
- True now: the catalog wheel is drawn as the real part, and the tyre is its own component, so it can have its own role. No fourth appearance role was added.
- Consequence: an accepted design that uses the 1430 wheel rebuilds that output once and reopens by the recipe path with it named (ADR-476). Until it places `wheel.tyre()`, it shows a bare rim. The tread is still not modelled.
- Not yet measured: whether the new wheel changes the frozen-v2 balancer result. That needs balancer trial 3.

Dispatch closed: 1 unit — record for ADR-489 (spoked catalog wheel, separate tyre part, mounting `rim` row)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 640267543c41f82d71f41e60df7c782576ad76ea

## State Impact

- target: brave-stone-9609 — ADR-489 (3b301c57): pololu-1430 wheel is a spoked rim from the STEP model; wheel.tyre() is catalog part tyre/pololu-1430 with mass split by kernel volume; mounting check gains 'rim' (tyre held by a held wheel)
- target: loyal-ocean-0768 — D3 catalog wheel-and-tyre set is now two real parts (spoked rim + separate tyre, ADR-489) and the mounting check covers the tyre via its wheel's rim
