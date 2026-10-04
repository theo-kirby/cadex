---
node_id: 7b1f256d-f8e7-543f-ae77-506bf070f79e
slug: narrow-orchard-5878
title: 'Quasi-direct-drive actuators join the catalog: lib.qdd (ADR-540)'
created_at: '2026-10-04T15:56:11+00:00'
parents:
- still-ivy-2146
summary: ''
---
## What

A quasi-direct-drive actuator family joins the catalog (ADR-540). `lib.qdd(sku)` returns a `QddPart` for the CubeMars AK70-10 KV100 and the AK80-9 V3.0 KV100. Each carries a sourced coaxial envelope, front and rear M3 stator bolt circles (published as mount axes for `fit.mounting`), the output bolt circle, and an effective density that reproduces the catalog mass. On top of that:
- `.actuator(joint, rating=peak|rated)`: a `kind="motor"` torque actuator at the datasheet output torque.
- `.joint_dynamics(joint)`: the peak-to-no-load torque-speed line as damping, the rotor inertia × ratio² as armature, and the back-drive torque as friction loss.
- `.bay()`.

`qdd` joins `DRIVE_FAMILIES`, and the agent guidance names it for torque-controlled legged robots.

## Why

Owner direction (2026-10-04): the next end-to-end test is a Mini Cheetah-class quadruped on actuated BLDCs, trained to balance and walk. Before this, the only BLDC was a drone motor with no torque model (ADR-206), and the only torque-limited joint actuators were hobby servos.

## Method

Commit `2830658d`.

Specs came from the manufacturer's product pages and 2D drawings, accessed 2026-10-04 (PROVENANCE §8i). The hole clocking was read off the drawings.

Verification:
- `test_library.py -k qdd`: 9 tests, including a real-kernel FreeCADCmd test (one valid solid per SKU, bounds, catalog mass from the kernel volume, every hole empty, placement) and a stock-MuJoCo flat-out test.
- End to end on a scratch project, an AK80-9 holding a 251 g steel leg: `cadex script --set`, then `cadex smoke --mode zero` (all checks pass), then the exported MJCF loaded in stock MuJoCo.

## Result

- **Exported MJCF:** `armature="0.00905842" damping="0.368569" frictionloss="0.51"`, `forcerange` at the chosen rating, motor body 0.49 kg.
- **Without the speed line**, the leg driven flat out reached 3,260 rpm in 0.5 s, six times the 570 rpm no-load speed. A policy could learn to exploit that, and no motor can deliver it. That is why the line is the default.
- **With the line**, flat out settles at 570 rpm ±1 %. The line passes within about 2 N·m of each SKU's rated point (AK70-10: 8.8 vs 8.3 N·m at 310 rpm; AK80-9: 7 vs 9 N·m at 390 rpm).

Not modelled, and stated in `spec`:
- no thermal model and no corner speed;
- the AK70-10's own chart starts near 380 rpm, not the tabulated 480;
- inertia is a uniform-solid estimate;
- the catalog has no 48 V pack and no CAN transceiver.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: qdd-and-docs
- commit: 2830658d4536fcba5e4afb0867a6137187221bab

## State Impact

- target: brave-stone-9609 — the catalog gains a quasi-direct-drive family (ADR-540, commit 2830658d): lib.qdd with the CubeMars AK70-10 and AK80-9 V3.0. Each is a torque motor at the datasheet peak or rated torque, with the peak-to-no-load torque-speed line as damping, rotor inertia × ratio² as armature, and back-drive friction. Without the line a flat-out joint reached 6× the no-load speed; with it, 570 rpm ±1 %. Gaps: no 48 V pack, no CAN transceiver, no thermal model or corner speed.
