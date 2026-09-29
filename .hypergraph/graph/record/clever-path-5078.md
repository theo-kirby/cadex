---
node_id: c01ecbc0-9aef-58f0-ae61-d9f6452617ce
slug: clever-path-5078
title: 'ot10: electronics bays — lib.battery/lib.board carry .bay() (ADR-442)'
created_at: '2026-09-29T06:15:32+00:00'
parents:
- honest-stream-0109
summary: ''
---
## What

Electronics bays got a product surface (ADR-442). `lib.battery(...)` now returns a `BatteryPart` and `lib.board(...)` a `BoardPart`, and both carry `.bay(clearance=, lead_room=[, underside=])`. It is a keep-out box built in the part's own frame and placed with the part's own placement, and a printed part cuts it: `part.cut(body, pack.bay())`.
- **Battery bay.** The envelope plus 1 mm clearance on the sides and top, plus 15 mm of lead room beyond the +X end. Nothing is added below the seat.
- **Board bay.** The PCB and marker footprint (it covers the ESP32 module's overhang) plus 1 mm, from 2 mm of underside below the PCB to 8 mm of lead room above the tallest component.
- **Not hardware.** A bay is never registered as catalogued hardware, so it cannot count as purchased in `look`'s proxies.
- **Refusals.** Bad allowances are refused by name (`board.bay: underside must be ...`).
- **Teaching.** The CLI overlay's ENCLOSE rule and its complete-machine paragraph now name `.bay()` and say not to cut to `.body`. The docstrings, which `describe_api` serves, and the `lib` listing notes say the same. `docs/XSCRIPT.md` gains a battery-and-bays section, and `REPORT.md` item 7 is updated.

## Why

The critic named this unit. It is long-term rung 2's last hex gap before stalls: electronics bays shaped around their parts, delivered as product surface because the actor authors no robot geometry. It needed a callable envelope, overlay teaching, a regression that fails before the change, and a read-only measurement on an existing design. All four were done as asked. No A5 turn was run, so none needed pre-registering.

## Method

- **Implementation.** `cadex_lib_api`: a `_BayPart` base holding the frame from `_frame`. `_place` was split so a stored frame can place the bay (`_place_frame`), and `BoardPart` and `BatteryPart` subclass `_BayPart`.
- **Tests.** Eleven cases were added to `test_library.py`: battery bay extents and placement, the board bay for all five boards, the ESP32 overhang, refusals by name, and not-catalogued checks. All eleven fail with the old `cadex_library_api.py` stashed and pass with it restored. `test_turn_loop.py` gained an overlay test.
- **Measurement.** Taken read-only on `ot10-quadruped-4`, the highest counted A5 design:
  - copied to a scratch dir outside the repo;
  - `cadex export --format brep`;
  - bay boxes computed from the stub `lib` at the script's own placements (H = 95.335 mm);
  - FreeCADCmd `common` of each bay against chassis, shell and visor.
  The original project is untouched.

## Result

**What the measurement found on `ot10-quadruped-4`.** All five housed parts clear every printed part: 0 mm³ of body interference, so their fit checks pass.
- **Battery.** The pocket leaves only 0.4 mm clearance. The bay intrudes into the chassis by 2,884 mm³ at clearance only and 4,001 mm³ with lead room.
- **Boards.** All four boards sit flat on the deck with no underside allowance. Their bays intrude into the chassis by 2,044 (IMU), 4,899 (ESP32), 5,059 (PCA9685) and 2,202 (regulator) mm³. The shell above them adds 1,362–3,569 mm³ each once lead room is included.

So hand-cut bays pass the fit checks and still leave no room for leads or solder joints. That is the gap `.bay()` closes at the source.

**Verification.** Suites, build, stage and packaged gate: see the Verification line below.

**Assumptions and limits.**
- Battery leads exit at +X. This is a convention, not a datasheet fact.
- Fitted connectors (USB, HDMI, headers) are not modelled; `underside` is the knob for headers.
- No A5 design has used `.bay()` yet. Whether the agent adopts it is unmeasured.

**For the next iteration.** The tail holds 2 unreconciled records (`honest-stream-0109` plus this one). The critic's next unit is stalls.

Verification: `pixi run test-engine` 2277 passed, 53 skipped; `pytest cli/tests` 1076 passed, 1 skipped; `build-engine` + `stage-engine` exit 0, and the staged payload carries `def bay`; packaged `test_cadexd_lifecycle.py` against the payload: 23 passed.

Dispatch closed: 1 unit — lib.battery/lib.board carry `.bay()`, taught in the overlay, measured on ot10-quadruped-4 (ADR-442)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot10
- commit: 422a4ac6211e77d6f19e9f379a75edb1a7a0148e

## State Impact

- target: brave-stone-9609 — lib.battery and lib.board parts carry .bay(clearance, lead_room[, underside]): a keep-out box of the part's extents plus clearance and lead room, placed with the part, never catalogued (ADR-442, commit 422a4ac6); measured read-only on ot10-quadruped-4, every housed part's hand-cut bay is intruded (battery 0.4 mm clearance, 2,884 mm³; boards flat on the deck, 2,044–5,059 mm³ each)
- target: chilly-union-8972 — the overlay's ENCLOSE rule and complete-machine paragraph tell the agent to cut a board's or battery's bay with its .bay(), never to its .body (ADR-442); no A5 turn has used it yet
