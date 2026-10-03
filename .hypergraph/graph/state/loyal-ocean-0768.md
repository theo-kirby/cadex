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

**The one-screw MG90S was the bay, not the catalog.** Hexapod trial 1 held every servo by 1 of 2 tab screws, and the agent blamed a lead block on the catalog MG90S [rec: deep-cove-1130]. The catalog part has none; ADR-443's bay lead room sat over every tabbed servo's lead-side hole. ADR-491 (`00fea49b`) adds opt-in `servo.bay(ledge=4)`: the lead-side screw gets 3.51 mm³ of thread (0 without) on the real kernel, and the overlay tells the agent to use it. It is opt-in because changing a default bay changed the recipe of an accepted design and made it refuse to reopen (F1-class: an uncatalogued library helper's default expansion must stay byte-stable) [rec: hidden-grove-0337].

**The mounting check now requires thread engagement** (ADR-492, `ec6782ad`): a screw holds only if its shank shares ≥0.1 mm³ with a printed part, or the head clamps a printed part while the shank reaches the held part's tapped hole, a nut or an insert; otherwise it is listed `unthreaded`. Static and swept fit allow a `lib.bolt`/print overlap up to the thread ring π/4(d²−minor²)L, counted in `fit.threaded_count`, so a screw in a tap-drill hole passes fit while a bolt through solid still fails. Fixture: plain-bay MG90S 1 of 2, `ledge=4` 2 of 2. Engine 2596 passed / 61 skipped; CLI 1290 passed, 1 load flake [rec: icy-willow-3129]. Open candidate tightening: a tabbed servo seated by its bay with no threaded screw still counts as held [rec: icy-willow-3129]. Reconcile judgement: the 0.5 mm contact leniency named in hidden-grove-0337 is the defect ADR-492 closed.

## Negative knowledge

- [scope: library helpers that expand inline into printed parts (bays, `lib.*` geometry) | confidence: high | evidence: hidden-grove-0337] Changing a helper's default expansion changes accepted recipes, and those projects refuse to reopen; changes must be opt-in or default-byte-stable.

## Provenance

- sweet-brook-2725 — orun1 operator-declared charter gap
- solemn-arbor-0802 — catalog half: STS3215, Pi 5, camera, ToF, wheel, foot pad (ADR-485)
- gentle-badger-9718 — mounting check in every build reply, pass/fail fixtures (ADR-486)
- eager-bluff-0757 — ADR-489: wheel-and-tyre set is two real parts, tyre held via the rim
- first-dew-3629 — D4 trial 3 transcript names motor driver and encoder N20 as catalog gaps
- young-orchard-8393 — ADR-490: TB6612 motor driver closes one transcript gap; encoder N20 open
- deep-cove-1130 — hexapod trial 1: no missing-part asks; MG90S servos held by one screw each (suspected catalog lead block)
- hidden-grove-0337 — ADR-491: the block was the bay's lead room; opt-in servo.bay(ledge=4); default expansion must stay byte-stable
- icy-willow-3129 — ADR-492: mounting check requires thread engagement; fit allows the thread ring
