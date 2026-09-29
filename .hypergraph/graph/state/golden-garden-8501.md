---
node_id: 57ef9ebf-21ac-59dc-8596-2d58e433ff5a
slug: golden-garden-8501
title: W2. The ADR-410 walking task is measured end to end
created_at: '2026-09-27T15:18:35+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run ot10: **W2. The ADR-410 walking task is measured end to end.** One A5 design goes through `cadex walk` training with the unchanged ADR-410 overlay and `--stop-on-collapse`, with its settings and stop rule recorded before it starts. The policy is installed through the supported path, and its gait verdict, W1 video and training curve are published. The bar is `walked = true`. A miss is an honest incomplete result with a diagnosis and a recorded next step. The gait thresholds are not weakened to pass it [rec: damp-dusk-8045].

**`walked = true` evidence exists, but the owner's verdict is that `w2-2` shuffles rather than walks** [rec: mild-lily-4405] [rec: glad-oak-4897]. REPORT.md records it: `walked = true` is a false positive for gait quality, and W2 is presented as a measured result, not as a walking robot. The owner ticks the box [rec: glad-oak-4897].

- **Run `w2-2`** [rec: kind-loom-7489]. Pre-registered (commit `1c4600e1`) as a warm start (`--init-from`) from `w2-1`'s policy on the byte-identical ADR-410 task bundle (`b0913fa0…`): 1000 × 2048, seed 0, `--timeout 10800`, `--stop-on-collapse`, grounding enforced, thresholds unchanged. The rollout went 1,443.8 mm forward over the full 10 s episode, never tipped, upright 100% of the time. Verdict, curve and W1 video (153.9 s/300 s) published (commit `4bfe59e1`) [rec: kind-loom-7489]. Re-reviewed under ADR-433 it has no findings: training survival median 500/500 over iterations 950–999 against the unchanged 0.90 bar, cross-checked at 489.5; the corrected verdict is `runs/w2-2/gait-adr433.json` in the project copy [rec: mild-lily-4405]. A dark-floor re-render of its video exists (ADR-444) [rec: keen-comet-6140].
- **Run `w2-1`: walked = false, diagnosed** [rec: bold-reef-1724]. From scratch at 1000 × 2048, seed 0, on a local RTX 5090: exited 0 in 2,241.7 s, reward/step 1.16 → 2.62, then tipped past 45° at 4.36 s after 97.7 mm with a −52° heading — it learned to stand. Stays walked = false under ADR-433 [rec: mild-lily-4405]. Its W1 video is published [rec: calm-mesa-1063].
- **What the gait check cannot see** (REPORT.md subsection) [rec: glad-oak-4897]. `gait_from_trace` (`cli/cadex_cli/walk.py`) sets `walked = not findings` over four findings — tipped past 45°, heading past 90°, terminated, training survival under 0.90 — all read from the free base body's placement. Travel is reported but never judged, and no foot or contact is read, so it cannot see stepping, foot clearance, slip or duty factor. The trace carries per-component placements (so foot positions exist) but no contacts. The probe log's "the feet step rather than slide" rested on foot-centre crossings of a 3 mm lift line, which chatter also produces, and is withdrawn [rec: glad-oak-4897].

## Negative knowledge

- [scope: ADR-410 reward weights on ot10-quadruped-3, from scratch, 1000×2048, seed 0 | confidence: medium | evidence: bold-reef-1724, kind-loom-7489] Standing out-earns walking under these weights (about +2/step standing against at most +1 more for walking), and a from-scratch run of this size converged on standing. A second 1000-iteration warm start on the unchanged task produced forward travel, which the owner judges a shuffle. One run of evidence each, not a general claim about the overlay.
- [scope: training survival read off a single trainer iteration | confidence: high | evidence: kind-loom-7489, mild-lily-4405] The trainer's episode length is `unroll*envs/endings`, with truncations counted. With unroll 20 and horizon 500, every 25th batch is a horizon boundary, and iteration 999 always is. A last-iteration read therefore fails healthy runs. ADR-433 reads a trailing-window median instead.
- [scope: `gait_from_trace` as of ot10 | confidence: high | evidence: glad-oak-4897] `walked = true` does not establish gait quality: the check reads only the base body, so an upright robot that shuffles — or stands still — passes it. Foot-crossing counts of a lift line are not evidence of stepping.

## Provenance

- damp-dusk-8045 — ot10 operator-declared charter gap
- bold-reef-1724 — W2 run w2-1: pre-registered, trained 1000×2048 on a copy of ot10-quadruped-3, walked=false, diagnosed
- calm-mesa-1063 — w2-1's W1 video published; rollout seed null; next is the pre-registered warm start
- kind-loom-7489 — W2 run w2-2: warm-started, 1.44 m forward upright, walked=false on a horizon-boundary survival artifact, diagnosed
- mild-lily-4405 — ADR-433 re-review: w2-2 walked=true, w2-1 still walked=false
- keen-comet-6140 — w2-2's studio video re-rendered on the dark floor (context only)
- glad-oak-4897 — owner's verdict: w2-2 shuffles; walked=true is a gait-quality false positive; the gait check reads only the base body
