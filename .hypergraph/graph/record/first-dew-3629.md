---
node_id: 4517393c-09ad-5a23-ae69-03cac508a7c1
slug: first-dew-3629
title: 'orun1 D4 balancer trial 3: mounting 11/11, sweep pass, frozen v2 4 of 5'
created_at: '2026-10-03T05:05:16+00:00'
parents:
- eager-bluff-0757
summary: ''
---
## What
D4 balancer trial 3. I ran the frozen balancer prompt as the fresh project `orun1-t3-balancer` at product revision `64026754` (ADR-488 and ADR-489 in), then judged it with frozen v2. The trial is published in `docs/probes/orun1/README.md` § "D4 trial 3" and `docs/probes/orun1/d4/t3-balancer/` (hero 140 KB, pairs, summary), commit `1cf0d3dd`. Before the unit I did what the critic asked first: the ADR-489 record (`eager-bluff-0757`), and the missing comma in the guidance's press-fit clause (commit `64026754`).

## Why
The critic named this as the next unit: trial 3 on a fresh `orun1-t3-balancer`, reporting fit, mounting and frozen-v2 results against c and e, and naming what the judge cites if the design still loses. I did that and deviated from nothing. One thing came up first. A `orun1-t3-balancer` already existed: the previous iteration had started the turn at `3b301c57` and then lost it when its session ended. Its lock holder was dead and its JSON reply was empty. The charter treats a killed turn as an interruption, not an attempt, so I renamed it `orun1-t3-balancer-interrupted` (receipts `t3-balancer-interrupted.{err,json}`) and ran trial 3 fresh. This time I kept the session blocked on the turn until it exited.

## Method
- Turn: `CADEX_EFFORT=medium ./cadex -p "<prompts.PROMPTS['balancer']>" --project ~/cadex-projects/orun1-t3-balancer --model claude-opus-5-5 --json`. Exit 0, and the turn ended on its own after about 10 minutes.
- Render: `runner/render_set.py` on the copy `orun1-t3-balancer-render`. Both `cadex render` and `look` re-accepted at the same revision, `e2b1b506…`. The hero was downsized to 640 px for the repo.
- Judge: `runner/versus.py balancer ~/cadex-projects/orun1-d4/t3-balancer --out docs/probes/orun1/d4/t3-balancer`, $0.18.
- No code changed in this unit beyond the one comma in the guidance. Neither suite was re-run.

## Result
- `orun1-t3-balancer`, accepted revision `e2b1b506150c…`. It has two chamfered side plates with slotted windows, the ESP32 in a framed bay, the BNO085 on an orange top deck, and a screwed regulator and VL53L1X. Two N20 gearmotors are screwed by their faces with M1.6×3. The spoked 1430 wheels carry separate tyres. No face. All 11 purchased parts and all 19 bolts are catalog parts.
- **Static fit: 561 pairs, 0 failing. Swept fit: pass**, both joints complete at ±180°. **Mounting: pass, 11 of 11.** Motors are held by `screws` with the thread checked. Wheels are held by `output`, tyres by `rim`. This is the first balancer trial where every hold is real.
- **Frozen v2: 4 of 5, a majority**, up from 3 of 5 in trials 1 and 2. It now also beats e (Like). It still loses to c (Love). The judge's reason: "odd cross-barred spoke wheels look arbitrary and its internals feel less clearly resolved", set against c's "solid hubbed wheels" and "bolted orange board carrier". So the disc-wheel complaint is gone, and the new spoke geometry from ADR-489 (twin 1.1 mm ribs with root and tip blocks) is what the judge holds against the design. Looking at the hero, the wheel is all one dark `mechanism` colour, the rim and tyre do not separate, and the spokes read as crossbars.
- By the D4 bar (a majority against the same-type Likes and Loves), trial 3 would pass. It is a trial and not the pre-registered confirmation, so it does not count toward D4.
- Catalog gaps the agent named (D3, cited from `t3-balancer.err` NOTE actuators and NOTE sensors): an H-bridge or motor-driver board ("the H-bridge part that is still missing"), and an encoder variant of the N20 ("the N20 2367 has no encoder").
- Next, as the critic's order has it: start the hexapod trials, the worst-rated type. For the balancer, the candidate product changes before its confirmation are: check the spoke geometry against the STEP model, since the judge reads it as arbitrary; and add the motor driver and an encoder N20 to the catalog. Both are product changes, never prompt changes.
- Tail: two unreconciled records, `eager-bluff-0757` and this one.

Dispatch closed: 1 unit — balancer trial 3: static/sweep pass, mounting 11/11, frozen v2 4 of 5 (loses only to Love c, on spoke look)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: 1cf0d3ddb1312ac6fa973b92c1af0cc7ad18cb45

## State Impact

- target: salty-fox-7376 — trial 3 orun1-t3-balancer (rev e2b1b506, product 64026754): static 0 of 561 failing, swept pass 2/2, mounting pass 11/11, frozen v2 4 of 5 (beats d,e,f,h; loses to Love c citing cross-barred spoke wheels); a trial, not the confirmation
- target: loyal-ocean-0768 — D4 trial 3 transcript names two catalog gaps: an H-bridge/motor driver board and an encoder N20 variant
