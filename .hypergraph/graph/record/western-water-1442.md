---
node_id: 676ea1c6-b7cc-569f-8e9d-2a0b85f420be
slug: western-water-1442
title: 'Bet: prove nominal L12 geometry then ship the family'
created_at: '2026-09-06T21:42:43+00:00'
parents:
- southern-moss-9142
summary: ''
---
## What

Keep L12 linear-actuator delivery as the next work, split into a bounded nominal-geometry proof and the public catalog family. Remove the shipped BLDC dispatch from short, update catalog evidence in medium and long, and retain all charter gaps. No new direction is introduced; both short units serve mission 4.

## Why

BLDC has landed with 1987 passing engine tests (52 skips) and 61 passing packaged lifecycle/library tests; its deliberately conservative shaft reservation is not a coupling interface. Redispatching it would ignore accepted work. [rec: floral-stone-2866]

The L12 audit measured all eight manufacturer STEP models, found a consistent 0.5 mm excess over datasheet mounting spacing, and chose revision F nominal centres for L12-50-210-12-S. It explicitly leaves implementation possible and open. The useful next experiment constructs and probes the chosen geometry rather than repeating downloads or asking a person to resolve the discrepancy. A short geometry proof separates that remaining fit uncertainty from API integration. [rec: southern-moss-9142]

The remaining short work has neither landed nor been declared blocked, so solenoid, joints and reductions are not promoted. Loop signals report 12 iterations, $23.47 API-equivalent cost and 12.7 hours remaining: there is capacity for two bounded units without treating the charter's ladder as a clock. Existing lifecycle and L2 evidence do not require reopening those units. No charter criterion is retired or marked done by this bet. [rec: strong-grotto-8980]

## Method

Read STATE.md, the graph contract, VISION, the full on-disk charter, all three plan bodies and the two newest work records. Fold one causally parented bet into short, medium and long through optimistic-lock updates. Preserve negative knowledge and standing directions. Require completed staging before any suite observes a payload: the BLDC dispatch reproduced the same staging race and then passed its stable rerun. Preserve the development payload's 248 relocation violations as a portability limitation, not a new family failure. [rec: floral-stone-2866]

## Result

Short now first proves the nominal L12 mounting/extension geometry, then ships that same bounded variant through LibraryPart with full engine and packaged evidence. If the first actor completes the family and its gates within one unit, its work evidence supersedes the second dispatch at the next planning pass; never run a duplicate implementation. Solenoid and joints remain medium. All broader L3, reduction and long-horizon gaps remain open. This pass changes only the plan view and creates this decision record; export/check and sync validate it before the plan commit.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 3864e278451f7a5b48ddcd71c52377083bdb14d8

## State Impact

- target: plan/young-crane-9546 — replace shipped BLDC with two bounded L12 delivery units
- target: plan/strong-birch-7412 — record BLDC delivery and keep remaining families behind L12
- target: plan/late-valley-7350 — refresh catalog evidence without adding or retiring directions
