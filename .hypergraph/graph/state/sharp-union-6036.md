---
node_id: 17878bbb-7dd9-5fc4-bdcd-f7d802e0c0a6
slug: sharp-union-6036
title: D5. Review history survives a design change
created_at: '2026-09-12T14:51:24+00:00'
parents:
- crisp-sun-1239
summary: ''
---
Status: working

## Current

**The agent's 70→45 mm Lark torso revision and `lark2` retraining preserve all 125 pre-revision run/asset files byte-identically.** `lark1` and `lark2` remain selectable on the persistent dashboard with their own revisions, curves and videos, and all four retained policies were compared on seeds 0–9 from their own retained models, tasks and hash-verified policies (ADR-313) [rec: brave-water-4060]. This is the third fresh project on which a product-agent revision and retraining left the prior design's history intact.

**The agent's 110→90 mm Wren revision and retraining preserve all 465 pre-revision run/asset files.** `wren57-retry`, `wren66-checkpoint20` and `wren66-final` evaluate from their own retained script/model/task/policy on seeds 0–4; seed-zero traces reproduce exactly. Persistent browser selection distinguishes historical retry/checkpoint from the current final, with retained videos and identities [rec: red-jasper-1884]. Wren's earlier 85→105 mm foot revision preserved all 114 original run files and four distinct model/policy/video histories, with twenty common-seed rollouts verifying identities [rec: frosty-birch-2464]; the provider-refused design turns between preserved 228 and then 434 retained files and the accepted design, authoring nothing [rec: smooth-pine-9795] [rec: dawn-bell-5364].

**Review history survives the real 70→90 mm Reed foot edit and GPU retraining.** Both designs remain browser-selectable with distinct model/spec identities, 240-point reward/loss/episode-length curves and playable/downloadable videos; all 250 pre-existing run/asset files remain byte-identical. That edit was actor-authored and did not itself establish D9 product-agent authorship [rec: candid-forest-9800].

ADR-291 retains assembled placements, checked mesh bytes, parameter specs and project documents before training and preserves them through later status writes [rec: quiet-arbor-0259]. ADR-293's real-engine browser regression additionally preserves the prior swept run's mesh bytes, assembled components, revision/digest and specs after a later physical parameter edit while current geometry changes [rec: forest-ledge-2219].

Historical gaps remain explicit: foot90's original unavailable training snapshot is not rewritten from its later working rollout geometry, and the fix is verified on a real-engine fixture rather than another biped GPU run [rec: candid-forest-9800] [rec: forest-ledge-2219]. Complete project copies must include run directories and ignored policies, traces and videos; Git alone is insufficient [rec: light-brook-2640].

Judgement: `working`. Reed, Wren and Lark each show a real design change and retraining with the prior run's identity, curves and videos intact and its files byte-identical; the owner's checkbox is not edited [rec: brave-water-4060].

Charter criterion: **D5. Review history survives a design change** Each run retains the model/script revision, specs, task/training configuration, metrics, policy identity and review/video references needed to interpret it; after a design edit and retraining, both runs remain selectable with their own curves, models and videos. Evidence: before/after identity and artifact checks, and browser assertions that old results have not silently switched to the new design. Declared target `gap-d5-review-history-survives-design` [rec: lucky-comet-0031].

## Negative knowledge

- [scope: `cadex walk` run records written before ADR-289 (commit 7a63fa63), including the real `runs/probe1` | confidence: high | evidence: lucid-journey-6875, lively-gate-6535] A run that failed before its rollout carries no revision or digest, and records are not rewritten after the fact.

## Provenance

- lucky-comet-0031 — the ot5 directive declared this criterion as gap `gap-d5-review-history-survives-design`
- dusty-peak-9330 — the owner's charter revision (ADR-284) that introduced D1–D9, claiming none complete
- wild-cove-4437 — per-run retention contract and containment-checked references
- rapid-crest-8826 — fixture browser historical identity checks, with real retraining/video evidence outstanding
- lucid-journey-6875 — the null-identity defect demonstrated on the real biped's failed first walk
- lively-gate-6535 — ADR-289: identity from the manifest at walk start, kept through failure, moved by design turns
- quiet-arbor-0259 — training-start specs/documents stay frozen and dispatch identity is guarded
- light-brook-2640 — real retained snapshot, preserved prior records and policy-playback history; redesign still outstanding
- candid-forest-9800 — real physical edit/retraining retains both designs, curves and videos with all old run/assets unchanged
- forest-ledge-2219 — parameter-sweep history regression retains original assembly, meshes and specs without backfill
- honest-path-3451 — Wren foot revision preserves 114 files and historical meshes, specs, policy/video identities and browser review
- frosty-birch-2464 — revised-foot retraining and twenty identity-checked rollouts preserve original history
- smooth-pine-9795 — refused design turns preserve all 228 run files and accepted design
- dawn-bell-5364 — refused copy design turn preserves 434 run/assets and accepted/historical review identities
- red-jasper-1884 — agent revision/retraining preserves 465 prior files and separately retained baseline/checkpoint/final identities
- brave-water-4060 — Lark agent revision and lark2 retraining preserve 125 prior files; both runs selectable with their own revisions, curves and videos
