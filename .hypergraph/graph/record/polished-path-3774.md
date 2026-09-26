---
node_id: f5f3d346-f0d0-5966-8e30-3139b59f88c0
slug: polished-path-3774
title: 'hex1/hex2: one unassisted hexapod, prompt to policy, without Ouroboros'
created_at: '2026-09-26T13:27:19+00:00'
parents:
- terse-forest-4784
summary: ''
---
## What
Owner-directed, un-orchestrated test of the end goal: one `cadex walk` from one
prompt ("Design a hexapod walking robot using MG90S servos from the catalog (two per
leg: hip yaw and knee), a printable body, and the hardware to assemble it. Then
declare a training task that teaches it to walk forward on flat ground."), no
Ouroboros, no coaching, observed but not steered. Two runs: hex1 and hex2.

## Why
The owner wants the product to design and train small robots unattended, and chose to
run it once cold to find the real gaps rather than design another charter first.

## Method
`main` @ `4289ef0f`, on sb1x (RTX 5090). `./cadex walk --project ~/cadex-projects/hexN
--out …/runs/walk1 --prompt "<above>" --iterations 2000 --envs 2048 --timeout 0
--leg-timeout 0 --json`, with `cadex review` serving the project on a Tailscale port.
hex1 used the default effort (`high`); hex2 set `CADEX_EFFORT=medium` and changed
nothing else. Gaps were logged by timestamp while watching, from the walk log, the
project store and the design agent's own Claude transcript. Full logs:
`docs/probes/hex/hex1-GAPS.md`, `docs/probes/hex/hex2-GAPS.md`; summary and
screenshots: `docs/probes/hex/README.md`.

## Result
- **hex1 failed in design.** After two probe parts the model thought for four
  consecutive 32,000-token passes with no tool call (18:17, 18:25, 18:33, 18:41 UTC)
  and Claude Code gave up: design leg exit 1 after 2007.68 s, nothing designed.
  Nothing on the walk log, project or dashboard distinguished this from work.
- **hex2 designed, trained, and does not walk.** Design leg 4638.7 s to accepted
  `6a8ebe73`: 38 components, 12 × MG90S + 12 horns catalogued, sweep pass on 12
  joints, 24/24 welds touching, after ~13 full-script writes and refusals that taught
  the agent three assembly-shape rules, and a suspected engine defect (`hip_pitch=48`,
  inside its declared range, fails MJCF export with "changed body_pos by 1 relative";
  47 passes). Train leg 13,303 s: reward/step −2.1 → ~12.2, but mean episode flat at
  ~215 of 500 steps from iteration 40 on. Declare and rollout passed; the review leg
  died on `render: triangle budget exceeded` (110,688 > 100,000).
- **The rollout tumbles.** Seed 0 runs all 500 steps (only a CoM-height termination):
  body 0 → 5,089 mm in x, yaw swinging ±170°, pitch −64°…+55°, roll to −50°, z
  bouncing 7–74 mm; reward 3,492 (forward +5,053). A +X CoM-velocity reward with no
  upright/heading term pays for flipping forward.
- The owner's review of the design: printed parts crude (flat bars, sharp boxes,
  balls on bars, no fillets); no controller, driver, IMU or power; policy inputs the
  MG90S cannot provide. Those three became ADR-406, ADR-407 and ADR-408.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: dbb082d04496b8a8944973d67295ddc5802091f7

## State Impact

- target: calm-peak-5247 — First unassisted from-prompt run on a 12-servo mechanism (hex1, hex2; docs/probes/hex/): hex1 stalled in design at effort high (four 32k thinking passes, no tool call, walk exit 1 at 2007.68 s, invisible on every product surface); hex2 at effort medium designed an accepted 38-component hexapod in 4638.7 s, trained 2000×2048 on GPU in 13,303 s, and its seed-0 rollout tumbles 5.1 m with ±170° yaw rather than walking; the review leg died on the 100k render triangle cap. The walk completes end to end on this scale but the product cannot yet tell a gait from a tumble.
- target: late-pond-2851 — Negative knowledge: a walk_forward task rewarding +X CoM velocity with only a CoM-height termination trains a tumbling policy on hex2 (reward/step ~12.2, episode length flat at ~215/500 from iteration 40 to 2000); no upright/heading term, no tipping termination, MG90S actuators torque-limited but not speed-limited.
- target: NEW unassisted-robot-to-walking-policy — Frontier opened by hex1/hex2 (docs/probes/hex/README.md, 'Still open'): stalls invisible and unresumable; API contract learned by refusal; rejected candidates not editable; hip_pitch=48 MJCF body_pos defect unreproduced; ~2.7 min per swept build; task pays for tumbling (no upright/heading, no tipping termination, no servo speed limit, no plausibility check); reward-up/survival-flat unsurfaced; world-geometry advisory counted as fit fail; review dashboard Ouroboros-only and refuses a not-yet-created project. Status open.
