---
node_id: 1f5544a8-2dd4-5eb9-ad69-db1e746d463d
slug: shady-rose-6292
title: Unassisted robot, one prompt to a walking policy
created_at: '2026-09-26T13:29:56+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

**One prompt to a walking robot, unattended, is the product's end goal, and the first cold attempt measured what stands between them [rec: polished-path-3774].** hex1 and hex2 (2026-09-25, `docs/probes/hex/`) ran one `cadex walk` of a hexapod prompt with no orchestration. hex2 reached a verified, rolled-out policy that tumbles rather than walks. Three of its gaps are closed: the agent can see its design [rec: light-hill-1224], robots carry their electronics [rec: smooth-heron-8904], and policies read only sensor-grounded channels [rec: nimble-meadow-6874]. Still open, each measured on hex1/hex2:

- **The task pays for tumbling.** No upright or heading term, no tipping termination, MG90S actuators torque-limited but not speed-limited, and no plausibility check on 0.5 m/s for a 20 cm robot. [rec: polished-path-3774]
- **Reward-up/survival-flat goes unsurfaced.** Mean episode sat at ~215 of 500 steps from iteration 40 to 2000 while reward/step climbed; the walk's only behavioural readout is total reward, and no video was produced. [rec: polished-path-3774]
- **Stalls are invisible and unresumable.** hex1's 33 minutes of max-token thinking looked like work on every surface; the failed walk left no session id and no commit. [rec: polished-path-3774]
- **The API contract is learned by refusal.** `import`, `repr`, `getattr`, horn style names, `/facts/bounding_box` and three assembly-shape rules, deterministically on both runs; a rejected candidate cannot be edited, only resent whole (~10 min per 12 KB on hex2). [rec: polished-path-3774]
- **`hip_pitch=48`**, inside its declared range, fails MJCF export verification ("changed body_pos by 1 relative") while 47 passes. Suspected engine defect, not yet reproduced in isolation. [rec: polished-path-3774]
- **Each swept build costs ~2.7 min** on 38 components and 12 joints, most of the design phase. [rec: polished-path-3774]
- **Smaller:** the floor's advisory world-geometry row reads as `fit fail`; the persistent dashboard follows Ouroboros runs only; `cadex review` refuses a project before its first run. [rec: polished-path-3774]

Next measurement: hex3, the same prompt on the ADR-406/407/408 product, compared against hex2 [rec: polished-path-3774].

## Negative knowledge

- [scope: hexapod walk_forward, +X CoM-velocity reward with only a CoM-height termination | confidence: high | evidence: polished-path-3774] Such a task trains a policy that tumbles forward rather than walks; a reward number and an untripped termination do not distinguish the two.
- [scope: cadex walk design leg at CADEX_EFFORT=high on a 12-servo prompt | confidence: medium | evidence: polished-path-3774] The design agent can spend its whole output budget thinking without a tool call and end the turn with nothing designed (n=1).

## Provenance

- polished-path-3774 — hex1/hex2 measured the gaps between one prompt and a walking robot
- light-hill-1224 — ADR-406 closed the agent's blindness
- smooth-heron-8904 — ADR-407 closed the missing electronics
- nimble-meadow-6874 — ADR-408 closed ungrounded policy inputs
