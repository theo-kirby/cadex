---
node_id: 1f7416c4-32e4-5197-967e-b10855f40332
slug: young-orchard-8393
title: 'orun1 D3: ADR-490 TB6612 motor-driver board for the N20s (record for #25)'
created_at: '2026-10-03T06:27:41+00:00'
parents:
- first-dew-3629
summary: ''
---
## What
ADR-490 (commit `bf830509`, landed by iteration 25 without a record): the catalog gains `lib.board("tb6612-adafruit-2448")`, Adafruit's TB6612FNG dual H-bridge breakout, as a `boards` row. Outline 19.05 × 26.67 mm, both Ø2.5 holes, 18 pads with nets and the chip body are parsed from Adafruit's EAGLE board file at a pinned commit (the ADR-407 precedent); ratings, 3 mm height and 1.8 g from the product page. The overlay's complete-machine list names it for brushed DC motors such as the N20, one board per two motors, motor supply straight from the 2S pack. `docs/PROVENANCE.md` and `docs/INTEGRATION.md` carry the source and the SKU.

## Why
The critic of iteration 26 asked for this record first: iteration 25 committed ADR-490 but minted no node ("ouroboros #25: no record"). The work itself answers D3's clause "anything the D4 transcripts show the agent reaching for and not finding": trial 3's transcript (`t3-balancer.err`) says the N20s "need a dual H-bridge driver to run, and the catalog doesn't have one", naming the TB6612FNG [rec: first-dew-3629]. The Adafruit breakout was chosen over Pololu's DRV8833/TB6612 carriers (713, 2130) because those show no mounting holes, so the mounting check could only report a bay hold.

## Method
Recorded from the commit and ADR-490's own Measured section; not re-run in this record's iteration beyond the suite runs the following unit does.
- `test_library.py::test_motor_driver_manufacturer_pins` pins outline, holes, every signal, the chip centre at (9.906, 14.986), the 3 mm height, 1.2 A ≥ the N20's 0.67 A stall, a 2S pack inside 4.5–13.5 V.
- `test_mounting_check.py::test_the_motor_driver_is_held_by_its_two_screws_on_the_real_kernel`: two M2 bolts into tapped holes → `held` by `screws` ("2 of 2 mounting holes"); no bolts → `contact only`. On the old source the build fails with `Unknown board 'tb6612-adafruit-2448'`.

## Result
- The catalog has a motor driver; every N20 design now has a real way to drive its motors, and the mounting check covers the board unchanged (screws through its own holes, ADR-486/488).
- Both holes sit on the JP3 edge; the catalog note says the far edge needs a ledge or slot in its bay. The terminal block is not modelled (ships loose). No protocol or response-shape change.
- Still open from the same transcript: an encoder N20 variant (not taken).

Dispatch closed: 1 unit — record for ADR-490, TB6612 motor-driver board in the catalog (fix-first, critic's order)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: bf830509a5bdb36b792e380fced739d0303da656

## State Impact

- target: loyal-ocean-0768 — ADR-490: catalog gains tb6612-adafruit-2448 motor driver (board-file source, held by 2 screws / contact-only fixture pinned); encoder N20 still missing
- target: brave-stone-9609 — boards family gains the TB6612 motor-driver breakout (ADR-490)
