---
node_id: 02e06146-11b7-512e-8177-14dd57905481
slug: cold-clover-8123
title: Dispose of updater audit before maintainer and planner handoff
created_at: '2026-09-07T04:55:01+00:00'
parents:
- eager-garden-8009
summary: ''
---
## What

Complete short rank 2's evidence-only disposition of the translation-updater audit. Extend TRANSLATION-UPDATER-AUDIT.md with the exact future source/test/doc scope, retained App/Base behavior, compatibility cost, separate disable/delete stages and gates; append ADR-232 and tick only the disposition ROADMAP item. No implementation bet or product change.

## Why

Follow eager-garden-8009 and the overseer's explicit disposition instruction for mission 3, round-glacier-2865 and green-sea-3991. The deleted GUI translator writer is the sole qualified boundary. Assume unmeasured external maintenance users may exist; retire only that GUI-registration behavior in a later authorized pair. The overseer reports three unreconciled records while the supplied snapshot lists two; adding this record reaches the threshold either way. Route the actual tail to the maintainer, then the later implementation bet to the planner; do not reconcile as an actor.

## Method

Read actor and hypergraph-record skills, STATE, PLAN, hypergraph contract, VISION, prior audit/record, ADR and ROADMAP. Verify the already-audited dispatch boundaries by static source read; do not expand the dependency audit or execute/import the updater. Pin src/Tools/updatecrowdin.py as the only future inherited edit and test_translation_updater.py as isolated regression coverage. Specify retained credential startup, App/Base TS installation/mapping, Qt translation consumers and resources. Document each stage's isolated tests, full engine suite, licensing/notice/manifest checks at committed HEAD, at most one release build, baseline CTest comparison, retained translation hashes/generated resources/runtime probe, and conditional fresh packaged gate. No source, state, plan, charter, manifest, resource or shell edits.

## Result

Exactly one boundary accepted for a later bet: updateTranslatorCpp, its two dispatch sites and exclusive PySide import. Disable call paths first while retaining helper/import; preserve an explicit retired-command diagnostic. Delete the unreachable helper/import only after verified disable evidence. App/Base and other updater behavior remain in scope for preservation, not removal; external GUI-registration and direct-helper users bear the stated compatibility cost. No whole-updater deletion or measured fork-delta reduction follows.

Validation: documentation-only licensing suite 10 passed, 1 skipped in 0.16 s; packaged-license test skipped because CADEX_ENGINE_ROOT was unset. git diff --check passed. Export and explicit graph check passed with zero violations and warnings; the checker confirms three unreconciled records against the state high-water mark. No full engine suite, build, inherited CTest, packaged lifecycle, runtime translation probe or shell gate ran; none is claimed for this evidence-only change. Next: maintainer reconciles the actual accumulated tail, planner writes a later bounded disable bet, then an actor may implement. Separate delete-stage dispatch remains required.

Dispatch closed: 1 unit — dispose of the updater audit and hand off the sole qualified GUI writer boundary to maintainer and planner.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: d3f9eee86695cb8a6aaefdd1851140df521e2f57

## State Impact

- target: round-glacier-2865 — Evidence-only disposition pins the sole deleted GUI writer boundary, exact future files, preserved App/Base behavior, compatibility cost and separate disable/delete gates; maintainer then planner must act before implementation.
- target: green-sea-3991 — Disposition changes documentation only; inherited source and manifest are unchanged and no fork-delta saving is claimed.
