---
node_id: 90adae41-7dd7-5767-b9a7-732ae6203165
slug: true-basin-5562
title: 'Guidance: short domain-neutral base, principles not hard rules, three provisional styles (ADR-650..655)'
created_at: '2026-10-10T13:43:02+00:00'
parents:
- golden-flame-1650
- tidy-aspen-4976
summary: ''
---
## What

Rewrote the agent guidance to be short, domain-neutral and principle-based
(ARCHITECTURE-REVIEW recommendations 5 and 6; ADR-650..655):

- Base `CadexAgentGuidance.md`: 5,807 -> 2,493 words of body. Keeps the
  design loop, measured-not-guessed, the build reply's blocks as floors (one
  line each, "read the `note`"), and a new SAY WHAT IS UNFINISHED. The
  walking task became A LEARNED MOTION PAYS FOR THE MOTION, NOT THE DISTANCE.
- Family material moved to styles (ADR-652): the servo kit to
  `printed-legged-robot`, the animal anatomy rule and QDD tiers to
  `creature`, the small wheel/gearmotor kit to the new `vehicle`.
- Hard taste rules became principles with a check and a starting point
  (ADR-651): the foot ratio, leg length, leg taper, fillet size, second disc.
  Kept numbers say why (FDM wall and overhang, two sweep steps).
- Three provisional styles (ADR-653): `gantry-machine` (494 words),
  `vehicle` (531), `product` (373). The overlay's style choice names each
  family by example and says to choose by how the machine moves.
- Placeholders (ADR-654): COVERS AND PANELS and MOTION PARTS, each under a
  `<!-- placeholder: ... -->` line that `guidance.agent_guidance` drops.
- Anatomy -> moving regions in language only (ADR-655); code name kept;
  `CadexAnatomy.SUGGESTED_REGIONS` (dead creature vocabulary) deleted.

## Why

Owner, 2026-10-10: "we shouldnt have hard rules like that. we need to be more
open and flexible." Breadth briefs (printers, CNCs, mowers, tractors, loaders,
rovers, lab robots) all read the base first, and it had drifted legged.

## Method

Read the review, the base, both styles, guidance.py and the guidance tests;
rewrote; read `cadex guidance` and each style's output in full as an agent;
`pixi run build-engine`; both suites CPU-only.

## Result

Word counts (body): base 5,807 -> 2,493; creature 905 -> 1,058; printed-legged-
robot 1,609 -> 1,623 (each absorbed base material); new gantry-machine 494,
vehicle 531, product 373. Whole printed guidance with no style: about 30,000
characters (was about 48,000). Commit 96d4420b.
test-engine 2,790 passed / 62 skipped; cli/tests 1,261 passed / 1 skipped (CPU-only). A first engine run under load failed one timing test (test_a_cpu_killed_pass_leaves_the_document_as_accepted: wall-clock timeout before the CPU limit); it passed in the full rerun.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-aad79e98bd1d4aa49
- commit: 96d4420b09eaa9ee038ea950d167e7bd2a192a1c

## State Impact

- target: pale-arrow-4660 — base cut to ~2,500 words and domain-neutral (ADR-650); rules are principles with checks (ADR-651); family material in styles (ADR-652); styles now creature, printed-legged-robot and provisional gantry-machine, vehicle, product, chosen from the brief by family (ADR-653); marked placeholders for panels and motion parts (ADR-654); anatomy described as moving regions, code name kept (ADR-655)
