---
node_id: 40297bc6-347e-5c46-80b9-684a1ea2fc67
slug: warm-anchor-2441
title: 'Bet: delete Help, then audit Start as the second whole-tree candidate'
created_at: '2026-09-07T00:39:39+00:00'
parents:
- zesty-otter-9342
summary: ''
---
## What

Fold the landed Help audit and the gate-verified Help disable, and promote the separate Help delete commit to the head of short. Behind it, queue a bounded dependency audit of `src/Mod/Start` as the second whole-tree candidate and a disable of Start conditional on that audit. Re-rank medium around completing the second removal, then residual GUI-source work, L3 and hide_render. Correct long's metrics and Help placement. No new direction; no charter gap retired.

## Why

Both short units landed. The audit qualified Help with no tracked product importer, no App target and no Help-specific CTest consumer, and wrote the disable and delete boundaries into `docs/HELP-AUDIT.md` [rec: silver-beacon-0723]. The disable (`a04ca822`, ADR-217 in `504b46bc`) is now gate-verified: explicit `-DBUILD_HELP=ON` over both caches collapses to OFF with zero `Mod/Help` rules, release build exit 0, no `Mod/Help` in install or payload, engine suite 2,022 passed, Cadex ctests 4/4, inherited CTest with zero failures outside the baseline by name, packaged gate 26 passed [rec: zesty-otter-9342]. The audit's own rule is that only such a passing disable unblocks the delete, and the delete boundary is already written: remove `src/Mod/Help/`, the parent gate, the option and report line, the Crowdin row and two developer-configuration entries, then repeat the same gates [rec: silver-beacon-0723]. That is one bounded unit and it is the first whole-tree engine removal toward `windy-pebble-4630`; the Measure shim pair was not one [rec: small-tide-8341].

The second removal needs a candidate. Only Start and Test remain outside the payload's retained set. Test carries headless testing obligations: MainCmd depends on TestSources and Test_SRCS installs App tests beside GUI ones [rec: humble-shore-1680]. Start builds an App target and installs Init.py but its product is a GUI start page, so it is the smaller unknown. Audit it, do not assume it; a blocker leaves the conditional disable undispatched, exactly as the Help pair was sequenced [rec: quiet-canyon-3950].

Iterations 28 to 30 cost three units: code and an ADR landed without a record node, the ADR cited a HELP-AUDIT section that did not exist, and the actor then stalled. The fix-forward recorded only what ran [rec: zesty-otter-9342]. That is negative knowledge for every remaining unit: a record node with real impacts in the same unit, and docs that cite only sections that exist.

The loop reports 31 iterations, 5.2 hours elapsed and 9.8 remaining. Three bounded units, one of them a full delete with at most one release build, fit that signal. The catalog is not forgotten: medium keeps L3 immediately behind the second removal and the standing rule that reduction must not indefinitely outrank it [rec: steady-rain-3009]. The frontier is populated, so nothing is invented.

## Method

Read STATE, the charter, the three plan bodies, the Help audit and disable records, `docs/HELP-AUDIT.md`, the PHASE8-AUDIT Start/Test row and the git log for iterations 26 to 31. Mint this single bet parented on zesty-otter-9342 with one impact per plan node; rewrite short, medium and long through optimistic-lock updates preserving negative knowledge and provenance; advance only the plan high-water mark; sync, check and commit the record and plan artifacts. No code, state, charter or existing-record edits and no build.

## Result

Short: Help delete at the audited boundary, then the Start whole-tree audit, then a Start disable conditional on qualification. Medium: complete the second whole-tree removal and honest delta first, then residual GUI-source obligations, L3 and hide_render, with current metrics 56 / 1,638 / 1,797. Long: Help placement and metrics corrected; every direction and charter gap retained.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 655a2b1ca3ebe97bd2f3b1cf488c4a37b27bfb03

## State Impact

- target: plan/young-crane-9546 — fold landed Help audit and gate-verified disable; dispatch Help delete, Start audit and conditional Start disable
- target: plan/strong-birch-7412 — complete the second whole-tree removal before residual GUI work, L3 and hide_render; update metrics
- target: plan/late-valley-7350 — correct Help placement and delta metrics; retain every direction
