---
node_id: 7d924e2d-984f-5f41-93c5-53f90cecf2c0
slug: smooth-heron-8904
title: 'ADR-407: BNO085 IMU, D36V50F6 regulator and 2S LiPo catalogued; robots carry their electronics'
created_at: '2026-09-26T13:27:50+00:00'
parents:
- polished-path-3774
summary: ''
---
## What
ADR-407: the catalog gains a robot's missing electronics, and the overlay requires a
self-moving design to carry them. Commit `bdda55cb`.

## Why
hex2 had twelve servos and no controller, driver, IMU or power, though an ESP32, a Pi
Zero 2 W and a PCA9685 were already catalogued (polished-path-3774). The owner chose
the parts: BNO085 IMU, 2S LiPo through a 6 V regulator, ESP32 as default brain.

## Method
- `lib.board("bno085-adafruit-4754")`: outline 25.40 × 22.86, four Ø2.5 holes, JP1/JP2
  pads and the chip centre parsed from Adafruit's EAGLE board at commit `be9dc998`;
  2.5 g from the product page.
- `lib.board("pololu-d36v50f6")`: 25.4 × 25.4 × 1.57, three Ø2.18 holes and the pin grid
  from Pololu drawing 0J1732; pin signals from the labelled photo (approximate).
  The first-proposed D24V90F6 does not exist; this one holds 6 V to about 7 V in.
- New `batteries` family, `lib.battery("gensace-gea2s100045d")`: 72 × 36 × 13 mm, 64 g,
  45C, Deans + JST-XH from the manufacturer's store; density 1899.3 kg/m³ = stated
  mass over envelope. `describe_api` library catalog gains `batteries` (golden shape
  +6 lines). Sources in `docs/PROVENANCE.md` §8a/§8b.
- Overlay "A ROBOT IS A COMPLETE MACHINE" names the SKUs; a test checks every SKU the
  overlay names resolves in the catalog.

## Result
`test_library.py` 101 passed (incl. new board rows and the battery test); the
`describe_api` page budget test still passes with the new rows; engine suite 2200
passed, CLI 950 passed. Sourcing was done by a research subagent and transcribed with
the approximations listed in each row's `approximate`.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: dbb082d04496b8a8944973d67295ddc5802091f7

## State Impact

- target: brave-stone-9609 — Catalog gains a batteries family (lib.battery, Gens Ace GEA2S100045D 2S 1000 mAh, 64 g, density from stated mass) and two lib.board rows, Adafruit 4754 BNO085 and Pololu 4092 D36V50F6, each manufacturer-sourced with approximations listed (ADR-407, commit bdda55cb). The agent overlay requires a self-moving design to carry controller, servo driver, IMU and battery-through-regulator, or to say why not in a DECISION.
- target: ready-falcon-6286 — Boards family extends from three to five rows (BNO085 IMU from Adafruit's EAGLE board at be9dc998; D36V50F6 regulator from Pololu drawing 0J1732, pin signals approximate); _board_pin takes a pad height for a 1.57 mm board.
