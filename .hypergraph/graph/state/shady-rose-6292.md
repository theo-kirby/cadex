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

**One prompt to a walking robot, unattended, is the product's end goal. Three cold attempts have measured what stands between them [rec: polished-path-3774] [rec: late-sky-2627].** hex1, hex2 and hex3 (2026-09-25/26, `docs/probes/hex/`) each ran one `cadex walk` of the same hexapod prompt with no orchestration, and no run has yet produced a walking policy.
- hex2 tumbled [rec: polished-path-3774].
- hex3 designed a complete, sensor-grounded robot in 41 min, against hex2's 76, and then trained a policy that ends its own episodes [rec: late-sky-2627].

Closed so far:
- The agent is told how to see its design [rec: light-hill-1224], and since the render decimates, it can [rec: scarlet-summit-7670].
- Robots carry their electronics [rec: smooth-heron-8904].
- Policies read only sensor-grounded channels [rec: nimble-meadow-6874].
- The walk judges gait rather than total reward, and servo speed comes from the datasheet [rec: fond-light-6196].
- Tasks must pay for survival, a walk stops a training run whose episodes collapse, and a render failure no longer loses the review [rec: scarlet-summit-7670].

Still open:

- **Design quality has never been seen by the agent.** Every `look` failed on hex3 and hex2 predated `look`, so ADR-406's design language has not yet acted on a model. hex3 is still a flat deck of plates with bare boards. [rec: late-sky-2627] [rec: scarlet-summit-7670]
- **No task has yet been trained under the alive-bonus rule**, so whether the walking-task guidance now produces a gait is unmeasured. [rec: scarlet-summit-7670]
- **Stalls are invisible and unresumable.** hex1's 33 minutes of max-token thinking looked like work on every surface. [rec: polished-path-3774]
- **The API contract is learned by refusal.** The horn style names and the assembly-shape rules were refused deterministically on all three runs. A rejected candidate cannot be edited, only resent whole; accepted revisions can be edited, which made hex3's refinement fast. [rec: polished-path-3774] [rec: late-sky-2627]
- **`hip_pitch=48`**, inside its declared range, fails MJCF export verification ("changed body_pos by 1 relative") while 47 passes. Not yet reproduced in isolation. [rec: polished-path-3774]
- **There is no rollout video**, so the gait verdict is numbers only. [rec: fond-light-6196]
- **Smaller:** the floor's advisory world-geometry row reads as `fit fail`; the persistent dashboard follows Ouroboros runs only; `cadex review` refuses a project before its first run. [rec: polished-path-3774]

Next measurement: hex4, the same prompt on ADR-406 to 410, compared against hex3. It is awaiting the owner's go-ahead [rec: late-sky-2627].

## Negative knowledge

- [scope: hexapod walk_forward, +X CoM-velocity reward with only a CoM-height termination | confidence: high | evidence: polished-path-3774] Such a task trains a policy that tumbles forward rather than walks; a reward number and an untripped termination do not distinguish the two.
- [scope: hexapod walk_forward with terminations and a net-negative reward per surviving step | confidence: high | evidence: late-sky-2627] PPO learns to trip a termination at once (hex3: 28 → 2 of 200 steps). Upright and bounded-speed terms do not help while the sum per step is below zero.
- [scope: cadex walk design leg at CADEX_EFFORT=high on a 12-servo prompt | confidence: medium | evidence: polished-path-3774] The design agent can spend its whole output budget thinking without a tool call and end the turn with nothing designed (n=1).

## Provenance

- polished-path-3774 — hex1/hex2 measured the gaps between one prompt and a walking robot
- light-hill-1224 — ADR-406 closed the agent's blindness
- smooth-heron-8904 — ADR-407 closed the missing electronics
- nimble-meadow-6874 — ADR-408 closed ungrounded policy inputs
- fond-light-6196 — ADR-409 judged gait instead of reward and derived servo speed from the datasheet
- late-sky-2627 — hex3 measured the ADR-406 to 409 product: faster design, early-termination hacking, look still refused
- scarlet-summit-7670 — ADR-410 closed the render refusal, lost reviews, and unguarded episode collapse
