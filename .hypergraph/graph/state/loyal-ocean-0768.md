---
node_id: 1419c6d9-ba7b-5c1e-b128-6f54655ae49c
slug: loyal-ocean-0768
title: D3. The product can design with the parts these robots need, and can tell when a part is not held (orun1)
created_at: '2026-10-02T17:01:59+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Open charter criterion for run orun1: **D3. The product can design with the parts these robots need, and can tell when a part is not held.** - The catalog gains, with a datasheet source, true dimensions, mounting features and a bay, as the existing servos and boards have: - a serial bus servo of the STS3215 class; - a single-board computer larger than the Pi Zero (a Pi 4 or 5 class board or a compute module carrier); - a camera module and a range sensor (time-of-flight class); - a wheel and tyre set and a rubber foot pad; - anything else the D4 transcripts show the agent reaching for and not finding, with the transcript cited. - **A mounting check.** The product reports, for every purchased part, which printed part holds it and by what (screws, a bay, a clip, a horn). A part held by nothing, or held only by being inside a shell, is reported. The product agent sees this report in every build reply. Tests pin it on a fixture that passes and one that fails. [rec: sweet-brook-2725]

Declared target: `gap-d3-product-can-design-parts`. The human owns the charter checkbox; roles report results and do not tick it. Reconcile judgement: earlier runs have criteria with the same letters, so every orun1 gap title carries the run.

**Catalog half landed** (ADR-485, commit `9ea7a4a8`): `sts3215` bus servo with mount points, `pi-5`, `rpi-camera-module-3`, `pololu-vl53l1x-3415` ToF sensor, wheel `pololu-1430`, foot pad `essentra-462178` — each with sources, dimensions, mounting features and a bay. Engine suite at that commit: 2397 passed / 223 skipped [rec: solemn-arbor-0802].

**Mounting check landed** (ADR-486, commit `0b97765c`): `fit.mounting` in every build reply names, per purchased part, the printed holder and how (screws on a hole axis, a bay, press fit, a drive's output), or reports contact only / inside a shell / held by nothing. Pinned by pass and fail real-kernel fixtures. Engine 2573 passed, CLI 1291 passed, packaged gate 38 passed [rec: gentle-badger-9718].

Both D3 halves have evidence. Still open: the transcript-driven catalog clause ("anything else the D4 transcripts show the agent reaching for"), which waits on D4 runs [rec: gentle-badger-9718]. D4 trial 1 already surfaced one catalog defect — the `pololu-1430` wheel is a solid disc and cannot pass a sweep on its catalog gearmotor's static D-shaft — tracked under D4 (salty-fox-7376) [rec: spring-ivy-9833]. Reconcile judgement: status moved open → working because both declared halves have landed with test evidence; the checkbox remains the human's.

**Transcript-driven catalog clause, in progress.** The wheel-and-tyre set is now two real parts — a spoked rim and a separate tyre, with the tyre covered by the mounting check through its wheel's rim (ADR-489) [rec: eager-bluff-0757]. Balancer trial 3's transcript named two gaps: an H-bridge/motor-driver board and an encoder N20 variant [rec: first-dew-3629]. The first is closed by `tb6612-adafruit-2448` (ADR-490, held by two screws, contact-only fixture pinned) [rec: young-orchard-8393]; **the encoder N20 is still missing** [rec: young-orchard-8393].

## Negative knowledge

None yet.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- solemn-arbor-0802 — catalog half: STS3215, Pi 5, camera, ToF, wheel, foot pad (ADR-485)
- gentle-badger-9718 — mounting check in every build reply, pass/fail fixtures (ADR-486)
- eager-bluff-0757 — ADR-489: wheel-and-tyre set is two real parts, tyre held via the rim
- first-dew-3629 — D4 trial 3 transcript names motor driver and encoder N20 as catalog gaps
- young-orchard-8393 — ADR-490: TB6612 motor driver closes one transcript gap; encoder N20 open
