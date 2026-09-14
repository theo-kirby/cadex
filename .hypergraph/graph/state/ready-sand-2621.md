---
node_id: cba79b00-c24d-5645-a748-33e794aa38d3
slug: ready-sand-2621
title: D7. A two-wheeled balancing robot goes through the lifecycle
created_at: '2026-09-13T21:25:10+00:00'
parents:
- round-sun-8398
summary: ''
---
Status: working

## Current

**Robin has been through the full recorded lifecycle: designed from a prompt, accepted with fits, reopened, trained once (bounded), evaluated over ten seeds, with checkpoint and final videos on the persistent dashboard.** Every clause of D7 has committed evidence and only the owner's checkbox is outstanding — `working` on the same reading D1–D6 carry; one design decision is left open for the next turn on Robin [rec: candid-delta-9314] [rec: frosty-path-5235].

**Accepted revision.** The product-agent-authored candidate was first accepted at revision `71709063d6af…` after an actor repair changed only reset lift from [1,3] to [3,5] mm: 24 valid single solids (five printable, nineteen catalog), 276 measured BREP pairs, 84 passing fit checks, 139.60133 g, pocket gaps 0.30 mm, shaft/hub gap 0.05 mm, no design floor or grounded dynamics component, zero joint residuals (`docs/probes/ot6/robin/ACCEPTED.md`, `repair.json`, `fit.json`, ADR-337) [rec: salty-fox-4449]. That revision could not pass its restore digest check. The mismatch was isolated to the `part.offset` of each catalog D-shaft segment: all 75 output definitions and solved placements matched, only the two wheel BREP artifacts differed, and four fresh-process replays over frozen identical input BREPs produced four hashes per offset call. No correction reproducing the accepted bytes was found (`RESTORE.md`, `restore.json`, `restore_probe.py`) [rec: kind-reef-3852].

**Design correction.** Revision `5ad94d65e61a…` (digest `185f9ccc4f96…`) replaces the offset D-bore with an analytic D-prism at the same declared 0.1 mm diametral clearance, authored in the gearmotor's canonical frame and placed with the same transform `lib.gearmotor` applies. Accepted through normal `cadex script --set`, no output dropped: 84/84 fit checks, wheel/motor 0.05 mm each side, zero overlap, 139.601 g, 24 solids; every inventory row other than each wheel's volume (−0.00104 mm³, sharp prism corners) is byte-identical to the old revision. Three consecutive fresh-process `cadex section` reopens exit 0 with the accepted digest, where the same command exited 1 on the old revision. Revision 71709063 keeps its identity in `script_history/0002-71709063d6af.py` and its failure evidence under `ot6-robin-src/`; the project's `DECISIONS.md` carries the correction (`BORE.md`, `bore.json`, `bore-fit.json`) [rec: odd-orchard-4978].

**Training.** Two bounded local GPU runs on revision 5ad94d65, under `systemd-run` with `MemoryMax=20G` and a 3600 s timeout, 1024 environments, episodes of 400 steps at 50 Hz, fall below 46.2 mm, seeds 0–9. `robin1` (trainer default learning rate 3e-4) diverged to non-finite reward and loss at update 128 and is kept on the dashboard as a failed run with its checkpoint-20 video and six retained checkpoints. `robin2` (`--learning-rate 1e-4`, the trainer's own suggestion, nothing else changed) completed 240 updates in 620.8 s, host peak 7.41 GB, GPU peak 15 139 MiB, reward per step 0.127 → 0.688. Over seeds 0–9 the checkpoint-20 policy fell 10/10 at 0.40–0.58 s; the final policy survived the full 8 s on 10/10 by holding a +11.0 to +11.2° lean and driving 1.8 m backward, the equilibrium where the damped gearmotors' steady-speed torque balances gravity's moment. That meets the task's bar and not upright-and-still, recorded as a measured result. Both videos are `cadex-prototype-dark-v1` on the persistent dashboard; the render's impact on training was bounded (one enclosing checkpoint step 34.50 s against 33.3–34.5 s). Receipt `docs/probes/ot6/robin/training.json` and `TRAINING.md` (ADR-338), pinned by a test in `cli/tests/test_review_design.py` [rec: candid-delta-9314].

**Dashboard (historical).** Verified at every experiment start and end of Robin's units: fresh headless browsers at 1400×900 and touch 400×850, no horizontal overflow, real solids by default and nine proxy outlines under the labelled toggle; at the close of the training unit it served `ot6-robin` with five runs and a fresh visit selected `robin2-final` (24 components, 114 344 triangles) [rec: candid-delta-9314]. Under the one-project-per-server rule the operator service has since moved to `ot6-heron`; Robin's five runs stay in its project store and are retrievable by pointing the service back [rec: frosty-path-5235].

**Open.** A velocity or position term in the reward, so a balancer is measured against stationary balance, is the next design decision on Robin; it is left in the project's `DECISIONS.md` and was deliberately not taken during the training unit [rec: candid-delta-9314].

**The owner ticked D7 on 2026-09-14 with the evidence unchanged.** Ticked as worded and knowing the gaps, because the next charter (ADR-341) raises the bar rather than re-running: Robin survives by leaning and driving backward, its fit was checked at one pose only, and the actor edited its script twice — which is exactly what ot7's F6 must do without [rec: nimble-wing-3050].

Charter criterion: **D7. A two-wheeled balancing robot goes through the lifecycle.** The product agent designs it from a prompt in a fresh project (MG90S or another catalog motor, catalog wheels or modelled printable wheels, a body that mounts the board and battery volume), it meets D5's inventory and fit rules, trains once (bounded), and its videos and measurements are on the dashboard. The human owns the checkbox edit [rec: brisk-ledge-9638].

Verification on the current tree: engine suite 2,114 passed / 53 skipped and packaged lifecycle gate 16 passed [rec: kind-reef-3852]; CLI suite 588 passed / 1 skipped, `test_review_design.py` 102 passed. No engine or product code changed in any of the three units [rec: candid-delta-9314].

## Negative knowledge

- [scope: Robin recovery attempts before acceptance | confidence: high | evidence: wise-brook-4842, copper-haven-4303, northern-trail-4014] Initial reset-floor rejection left only the motor probe accepted. Complete-source recovery was provider-refused, including opus, sonnet and haiku selections; those attempts establish no future availability. The later literal repair and acceptance supersede the probe-only state, not the historical failures [rec: salty-fox-4449].
- [scope: `part.offset` of a catalog D-shaft segment, this engine build | confidence: high | evidence: kind-reef-3852] The worker's `makeOffsetShape` call is not byte-reproducible across fresh processes on identical loaded input: 36/40 replayed operations were stable, each shaft offset gave four hashes in four processes, and downstream cuts inherited the variation. Equal volume and topology counts are not geometric equivalence and were not adopted as acceptance criteria; the engine op was left as is [rec: kind-reef-3852, odd-orchard-4978].
- [scope: retained revision 71709063d6af | confidence: high | evidence: kind-reef-3852, odd-orchard-4978] Its accepted bytes were never recovered; the new revision is a design correction, not a recovery of that identity. The store's ADR-045 lifecycle pruned its `script_artifacts`, so the old evidence now lives only under `ot6-robin-src/`. Wheel clearance does not verify press-fit or axial retention, and 0.3 mm motor shoulder clearance is not face registration [rec: salty-fox-4449].
- [scope: Robin training on revision 5ad94d65 | confidence: medium | evidence: candid-delta-9314] The 1e-4 learning rate is the trainer's suggestion, not a diagnosis of robin1's divergence. Three matching reopens are evidence in this environment, not a proof for every process. Reconcile judgement (superseded): status was held `open` while no record declared the criterion evidenced; `frosty-path-5235` declared it, and the stationary-balance reward term stays an open design decision in the project rather than a gap in the criterion [rec: frosty-path-5235].

## Provenance

- brisk-ledge-9638 — the ot6 directive (ADR-328) declared this criterion as gap `gap-d7-two-wheeled-balancing-robot`
- wise-brook-4842 — failed first Robin design attempt and probe-only acceptance
- copper-haven-4303 — recovered complete candidate; provider refused repair, so D9 fallback was taken
- northern-trail-4014 — three alternate model selections also provider-refused; Finch operator checks passed
- salty-fox-4449 — literal reset repair accepted, retained inventory and fits, live Robin dashboard, and restore mismatch blocking training
- kind-reef-3852 — restore mismatch isolated to nondeterministic shaft offsets; accepted identity preserved, no correction established
- odd-orchard-4978 — D-bore revised as an analytic prism, new revision accepted, three fresh-process reopens pass, training unblocked
- candid-delta-9314 — bounded training: robin1 diverged and kept as failed, robin2 completed, ten-seed evaluation, both videos on the dashboard
- frosty-path-5235 — the closing report: D7 evidenced pending the owner's tick, the dashboard claim made historical (the service now serves ot6-heron), the reward term left open in the project
- nimble-wing-3050 — the owner ticked D7 on 2026-09-14; evidence unchanged
