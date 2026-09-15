---
node_id: fa126afd-6bd8-51d7-896f-0c1aaa676854
slug: polished-forest-0215
title: F4. The agent repairs from measurements alone
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: open

## Current

**F4 remains open with zero completed design turns, and every slot is unspent.** Three frozen-prompt invocations of the repair collector on the preserved Heron seed were refused at the provider session limit (4.09 s, 4.02 s and 4.171 s), each with zero transcript tool calls and no actor design edit [rec: lucky-willow-8039] [rec: keen-quill-2265] [rec: blue-slope-0916]. The third run's receipt is `docs/probes/ot7/retained/repair-refusal-iteration39.json` (5,286 bytes, with before/after fit, both horn-contact assessments, timings and artifact digests); before and after each report 15 failures (8 intersections, 6 below-clearance pairs, one world plane) and both 0.2 mm attachment gaps unchanged [rec: blue-slope-0916]. The record that folded that run counted the collector slot as consumed [rec: blue-slope-0916]; the operator's ot7 restart amendment (ADR-355) rules otherwise: **a call that ends on a provider usage or session limit is void, consumes no create, continuation or repair slot, and is not a design result.** The repair prompt and all three continuations are therefore unspent, and the retry sends the same frozen prompt to a fresh copy of the seed with a letter suffix (`ot7-heron-repair-b`), only while the Claude harness is available [rec: keen-wing-6569]. Reconcile judgement: the refusals stay in the accounting as void calls, listed apart from the design's attempts; retain `open`.

**The frozen repair collector assesses both original horn attachments independently of the static fit summary.** Before/after `repair-assessment.json` receipts retain accepted identity and require static fit plus measured contact at `comp_horn_shoulder/comp_upper_arm` and `comp_horn_elbow/comp_forearm` (distance within 0.001 mm, common volume within 0.000001 mm³). Fixtures catch the otherwise unflagged 0.2 mm gaps; missing, renamed, duplicate, errored, nonfinite or stale attachment evidence stays unknown [rec: western-fox-7010]. The collector pins seed identity and empty overrides, requires complete unchanged before measurements, consumes one hash-checked frozen fresh-session prompt without `--resume`, and retains before/after reports, transcript hashes and accepted identity even on refusal; exclusive evidence creation prevents redispatch into the same evidence directory, which is why a retry needs a fresh seed copy [rec: blue-sky-2193] [rec: blue-slope-0916]. Known-answer fixtures exercise the real pagination reader and fit summary; deliberate truncation mutations fail them [rec: long-spark-1984] [rec: true-wolf-3979]. The collector does not yet recognise a usage-limit exit as void: that is the restart's first tooling item [rec: keen-wing-6569].

**The seed's measured baseline.** The seed is Heron's first accepted ot6 revision `7e9eff5c…`. The collector read it with unchanged script and metadata in 0.164 s: 105 unique pairs, 15 inventory components, matching accepted revision across three reports; 91 pairs clear; shoulder servo/base overlap 248.20162986795066 mm³; both horn/link gaps about 0.2 mm, not failing because the seed declares no contact intent and the default minimum is 0.1 mm; swept coverage unavailable [rec: long-falcon-7461]. The first refused call found missing historical artifacts; product restore recreated them and changed the attempt pointer while preserving accepted revision, digest and script, and that restored report had 21 failures. ADR-353 removed six nominal-0.1 mm flags, explaining the later 15 without a design change [rec: lucky-willow-8039] [rec: keen-quill-2265].

The design-agnostic prompt is frozen at `docs/probes/ot7/prompts/repair.prompt.txt` (sha256 `5d846901…`), wording test-pinned [rec: silent-union-5108] [rec: blue-slope-0916]. Charter criterion: an unassisted session on the first Heron revision resolves all three defects from tools and one frozen continuation prompt, accepting zero failing fit checks, with before/after reports and turn/transcript evidence [rec: kind-dusk-1609] [rec: keen-wing-6569].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f4-agent-repairs-from-measurements`
- silent-union-5108 — ADR-345 prompt freeze recovered with digest pins; no design or repair evidence
- lucky-willow-8039 — one frozen invocation refused, zero completed design turns; restored seed identity and 21-failure report retained
- keen-quill-2265 — second refusal, zero completed turns, 15 before/after failures and unchanged accepted identity
- blue-sky-2193 — seeded-repair collector and fixtures preserve identity and frozen prompting; no provider invocation or real repair
- long-spark-1984 — static pagination and late-page-error fixtures; mutation detects lost failures
- true-wolf-3979 — nested sweep pagination fixture and mutation; CLI 706 passed / 1 skipped
- long-falcon-7461 — real unchanged-seed baseline and retained artifacts; 15 failures, unflagged horn gaps and unavailable sweep
- western-fox-7010 — before/after geometry assessment requires static fit and both original horn contacts; fixtures verified, no real repair
- blue-slope-0916 — third refusal at the session limit in 4.171 s; receipt retained, 15 failures and both 0.2 mm gaps unchanged
- keen-wing-6569 — the ot7 restart directive (ADR-355): usage-limit calls are void and consume no slot; the repair prompt is unspent
