---
node_id: 2226f5c8-b684-5d93-96d8-4344b897a475
slug: little-shade-0096
title: 'orun1 D4: balancer trial 4 — mounting 12/12 via .mounting(), judge v2 3/5'
created_at: '2026-10-03T08:49:55+00:00'
parents:
- floral-horizon-1217
summary: ''
---
## What
D4 balancer trial 4 (a trial, not a confirmation): a fresh, supervised `orun1-t4-balancer` turn on the frozen balancer prompt at product revision `5c853b0e` (ADR-491–493 in). Published with its fit, its mounting count, whether it used `board.mounting()`, and the frozen v2 judge result. Commit `4875bfd9`.

## Why
The critic asked for exactly this after ADR-493 landed. It was the first design turn since the library changes of ADR-491–493, and the frontier had not moved in 15 iterations. Target: D4 (`salty-fox-7376`), with D3 (`loyal-ocean-0768`) as the thing under test.

## Method
- Turn: `CADEX_EFFORT=medium ./cadex -p "<prompts.PROMPTS['balancer']>" --project ~/cadex-projects/orun1-t4-balancer --model claude-opus-5-5 --json`. Exit 0 after 35 tool calls, and the turn ended on its own. The engine was the dev tree. Its installed files matched source for the ADR-493 changes. The receipt is `orun1-d4/t4-balancer.json` (local).
- Render: `runner/render_set.py` on the copy `orun1-t4-balancer-render`. It re-accepted at the same revision, `e30742e5…`, with render_ok. The hero was downsized to 640 px (117 KB).
- Judge: `runner/versus.py balancer …/orun1-d4/t4-balancer --out docs/probes/orun1/d4/t4-balancer`, $0.19.
- Runner tests: 18 passed. No product code changed, so neither full suite was re-run.

## Result
- **Fit:** static 903 pairs, 0 failing. 38 fixed pairs, all touching. Swept `pass`: 2 of 2 joints complete at ±180°.
- **Catalog:** all 12 purchased parts and 27 bolts are catalog parts. This is the first balancer to use the TB6612 driver (ADR-490).
- **Mounting:** `pass`, 12 of 12 held, 23 threaded.
  - Both N20 motors are screwed 2 of 2.
  - **All four screwed boards (regulator, driver, IMU, ToF) used `.mounting()`** and are fully threaded.
  - ESP32 and battery: `bay`.
- **Judge v2: 3 of 5, a majority, down from trial 3's 4 of 5.** It beat d, f and h. It lost to c (Love) and e (Like). Both losing reasons name the "white block/box with a cut-out window" core and the spoked wheels ("loose-looking", "thin … less resolved").
- **Diagnosis from the renders.**
  - The ADR-489 catalog wheel is now the judge's complaint in two trials running (t3 and t4). It is catalog geometry, not an agent choice.
  - t4 moved its regulator and driver to the rear face, so the hero shows a plain bone core with one window. The guidance does not say to lay ordered electronics out on the shown faces.
- Transcript frictions, with no missing part asked for:
  - `lib.wheel(...).bay()` does not exist.
  - Six `inspect` calls asked for a `/facts/bounding_box` path that is not published.
- **Next, by the critic's rule:** t4 clears mounting and the judge's majority bar, so the queued hexapod change (leg proportion, joint clutter) and hexapod trial 2 come next. Two balancer form fixes are candidates before a balancer confirmation: the wheel's spoke geometry, and a guidance line on putting ordered electronics on the faces the hero shows. Neither was done here.
- The tail now has 2 unreconciled records.

Dispatch closed: 1 unit — balancer trial 4: fit pass, mounting 12/12 with .mounting() on every screwed board, judge v2 3/5 (majority); losses name the spoked wheel and the plain core.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 4875bfd9567bde20449415ac9c0494b66712a8db

## State Impact

- target: salty-fox-7376 — balancer trial 4 (orun1-t4-balancer, rev e30742e5, product 5c853b0e): fit pass, sweep pass, mounting 12/12 with board.mounting() on all four screwed boards; judge v2 3/5 majority (lost to c, e on spoked wheel and plain white core)
