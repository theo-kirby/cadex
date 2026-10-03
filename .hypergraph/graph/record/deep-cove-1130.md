---
node_id: e153a232-56bf-5aa9-8fad-4b3bc60c89f8
slug: deep-cove-1130
title: 'orun1 D4 hexapod trial 1: fit/sweep pass, mounting 49/49, frozen v2 1 of 2'
created_at: '2026-10-03T06:48:49+00:00'
parents:
- young-orchard-8393
summary: ''
---
## What
D4 hexapod trial 1, published. `orun1-t1-hexapod` is the frozen hexapod prompt, one turn at product revision `ef2b0f86` (product code identical to `64026754`), `claude-opus-5-5`, effort `medium`, accepted revision `35193b3e…`. Rendered from the copy `orun1-t1-hexapod-render` (re-accepted at the same revision), judged with frozen v2, and published in `docs/probes/orun1/README.md` § "D4 trial 1: hexapod" and `docs/probes/orun1/d4/t1-hexapod/` (hero 151 KB, pairs, summary), commit `c14ed83a`.

## Why
The critic asked for a supervised hexapod trial 1 (`orun1-t1-hexapod`) at the current product revision, published with fit, mounting, frozen-v2 results and missing-part asks. **Deviation:** that turn already existed. Iteration 24 ran it to completion (exit 0, accepted, about 58 minutes) and then lost its session before judging or publishing, and nothing recorded it. The charter says every attempt is published. Running a second turn and calling it trial 1 would have hidden a completed attempt, and a second turn with no product change between them would teach nothing. So I published the existing turn as trial 1. It ran at `ef2b0f86`, not at HEAD. The only product change since is ADR-490 (a TB6612 row and an overlay line for brushed DC motors), which a servo hexapod does not touch. The quadruped start that iteration 26 left behind (empty reply, killed with its session) is renamed `orun1-t1-quadruped-interrupted`, the way `t3-balancer-interrupted` was. `orun1-t1-hexapod-notools`, where the session gave the agent no tools, is likewise an interruption, not an attempt.

## Method
- The turn (iteration 24): `CADEX_EFFORT=medium ./cadex -p "<prompts.PROMPTS['hexapod']>" --project ~/cadex-projects/orun1-t1-hexapod --model claude-opus-5-5 --json`. Its reply, with fit, mounting and inventory, is the receipt `orun1-d4/t1-hexapod.json`.
- Render: `runner/render_set.py ~/cadex-projects/orun1-t1-hexapod-render …/orun1-d4/t1-hexapod`. Hero plus five looks, render_ok, look revision equal to accepted. Hero downsized to 640 px for the repo.
- Judge: `runner/versus.py hexapod …/orun1-d4/t1-hexapod --out docs/probes/orun1/d4/t1-hexapod`, $0.08. Runner tests: 18 passed. No product code changed, so neither full suite was re-run.

## Result
- **orun1-t1-hexapod @ 35193b3e.** A flat hexagonal deck with six hanging coxa pods. The 2S pack is in a centreline channel under the deck. 2× PCA9685, the ESP32, the BNO085 and the regulator are in top bays, and a VL53L1X sits on a front tab. No face. 18 MG90S servos (the agent chose them over the STS3215 for mass), a 35 mm hub cap on every joint, graphite tapered tibias and orange rubber pads. 49 purchased parts and 18 bolts, all from the catalog.
- **Static fit:** 0 of 3655 failing. **Swept fit:** pass, 18/18 complete at 15°. **Mounting:** pass, 49/49 held (servos by screws, horns by output, pads, boards and battery by bay).
- **Frozen v2: 1 of 2, no majority.** Only b and c qualify as opponents, both Like, so the bar is 2 of 2. It beat b and lost to c. The judge read c as "an ordered two-deck chassis, a clear servo-bracket at each hip" and this design as "crowded clusters of joints, oddly angled links and upturned segments … cluttered and arbitrary". Side by side, the 35 mm hub caps and the femur pods dominate short legs (coxa 34, femur 48, tibia 70 mm), while c has long tapered legs and compact hips.
- **Missing-part asks:** none in the transcript. Concern for D3: every servo carries **one** screw ("1 of 2 mounting holes"), because the agent found the catalog MG90S models a lead block under the lead-side tab. The mounting check passes a single screw. Whether that lead block matches the real MG90S is unverified, and it is a candidate catalog defect.
- Next, for the hexapod: a product change aimed at proportion and joint clutter (guidance on leg-to-joint proportion, or hub caps as optional rather than per-joint), then trial 2. Never a prompt change. Other types still have no trial. Tail: one unreconciled record (this one).

Dispatch closed: 1 unit — hexapod trial 1 published: fit/sweep pass, mounting 49/49, frozen v2 1 of 2 (loses to c on proportions/joint clutter)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun1
- commit: c14ed83a94ba92dad4bb3198252def8768387eef

## State Impact

- target: salty-fox-7376 — hexapod trial 1 orun1-t1-hexapod (rev 35193b3e, product ef2b0f86): static 0/3655, swept pass 18/18, mounting pass 49/49 (one screw per MG90S), frozen v2 1 of 2 (beats b, loses to c on proportions/joint clutter); a trial, not the confirmation
- target: loyal-ocean-0768 — hexapod trial 1 asks for no missing part; candidate catalog defect: MG90S lead block blocks the lead-side tab screw, so servos are held by 1 of 2 holes
