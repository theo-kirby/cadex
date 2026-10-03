---
node_id: 66113c3e-bdf8-53f4-816f-4dfb06ed891c
slug: first-eagle-0836
title: 'orun1 D4 balancer trial 2: sweep passes, mounting 5/9 (no M1.6 fastener), v2 3 of 5'
created_at: '2026-10-03T04:06:01+00:00'
parents:
- calm-quill-0693
summary: ''
---
## What
D4 balancer trial 2: the frozen balancer prompt run at product revision `9eac2291` (ADR-487 in) as the fresh project `orun1-t2-balancer`, then judged by frozen v2 through `runner/versus.py`. It is published in `docs/probes/orun1/README.md` § "D4 trial 2" and `docs/probes/orun1/d4/t2-balancer/` (hero 117 KB, pairs, summary), commit `75d831bb`. The same commit adds the ADR-487 record `calm-quill-0693`, which the critic asked for first.

## Why
The critic asked for two things: first a record for ADR-487, then balancer trial 2 from the same frozen prompt at this revision, reporting static fit, swept fit, mounting and frozen v2. I did both, in that order, and deviated from nothing. The trial did not clear the bar, so as the critic instructed I diagnosed it from the renders and the comparisons. The fix is the next unit and is not in this one.

## Method
- Turn: `CADEX_EFFORT=medium ./cadex -p "<frozen balancer prompt, prompts.PROMPTS['balancer']>" --project ~/cadex-projects/orun1-t2-balancer --model claude-opus-5-5 --json`, at HEAD `9eac2291`. Exit 0, and the turn ended on its own. The engine is the dev tree, which matches `build/release` byte for byte on the three ADR-487 files.
- Render: `runner/render_set.py` on the copy `orun1-t2-balancer-render`, which re-accepted at the same revision `496a506e…`. The hero was downsized to 640 px for the repo, as in trial 1.
- Judge: `runner/versus.py balancer ~/cadex-projects/orun1-d4/t2-balancer --out docs/probes/orun1/d4/t2-balancer`.
- Gates at `9eac2291`: `pixi run test-engine` gave **2574 passed, 61 skipped** (5 m 44 s). `pytest src/Mod/cadex/cadex_tests/test_library.py` gave 140 passed. `pytest docs/probes/orun1/runner` gave 18 passed. The CLI suite was not run: this unit changed no code.

## Result
- `orun1-t2-balancer`, accepted revision `496a506eef58…`. Two tall windowed side plates, a battery tray, a sensor shelf and a top deck. ESP32 in a bay, BNO085 and the regulator screwed down, VL53L1X on an orange bracket. No face. All 9 purchased parts are catalog parts.
- **Static fit: 210 pairs, 0 failing. Swept fit: `pass`**, 2 of 2 joints complete at ±180°. ADR-487 worked: the swept fit trial 1 could not get now passes.
- **Mounting: `reported`, 5 of 9 held, so the D4 trial fails.** Both N20 motors are `contact only`. They are press-fitted in split pockets, so both wheels are `held by nothing`. The agent's note: "Screwing the N20 motors with M2 bolts into their M1.6 face holes was rejected (wrong thread, intersecting solids). Catalog bolts start at M2 and the gearmotor has no .bay()". This is a D3 catalog gap with its transcript cited (`t2-balancer.err` NOTE rejected).
- **New defect found in the mounting check (D3):** trial 1 put `lib.bolt("m2", …)` on the 2367's M1.6 hole axes, and it was counted as `screws`. The check matches by axis, not by thread. So trial 1's "9 of 9" included two holds that used the wrong screw. The check is too lenient, and nothing reports it as broken yet.
- **Frozen v2: 3 of 5 (majority)**, the same split as trial 1. It beat the d, f and h Likes and lost to c (Love) and e (Like). Both losses cite plain disc wheels. New this time: "no visible drive motors" and "a small board that looks stuck onto its shelf". Cost $0.18.
- Next units, in order, each a product change and never a prompt change: (1) catalog M1.6 screws and/or a `gearmotor.bay()`, together with a mounting-check rule that a bolt's thread must match the hole's `mount_thread`, with a fixture that passes and one that fails; (2) model the 1430 wheel's rim, hub and tyre so it is not a slab; then balancer trial 3.
- Tail: 2 unreconciled records (calm-quill-0693 and this one).

Dispatch closed: 1 unit — balancer trial 2: sweep pass, static clean, mounting 5/9 (no M1.6 bolt/gearmotor bay; check ignores thread size), v2 3 of 5

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 75d831bb8c5b754acb9136271ebb6916a653396e

## State Impact

- target: salty-fox-7376 — trial 2 orun1-t2-balancer (rev 496a506e, product 9eac2291): static 0 failing, swept pass 2/2, mounting reported 5/9 (N20 motors contact-only: catalog has no M1.6 bolt and no gearmotor bay), frozen v2 3 of 5 losing on disc wheels and hidden motors; does not clear D4
- target: brave-stone-9609 — the D3 mounting check matches a bolt to a hole by axis only, so an M2 bolt in the N20's M1.6 holes counts as held (trial 1); the catalog lacks M1.6 fasteners and a gearmotor bay
