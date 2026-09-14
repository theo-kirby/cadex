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

**The real collector measured the preserved Heron seed with unchanged script and metadata; no repair ran.** The child exited 0 in 0.164 seconds, collecting 105 unique pairs and 15 inventory components with matching accepted revision across three reports. Static fit has 15 failures: 8 intersections, 6 below-clearance pairs and one world-geometry failure; 91 pairs are clear. Shoulder servo/base overlap is 248.20162986795066 mm³. Both horn/link gaps measure approximately 0.2 mm but do not fail: the seed declares no contact intent and the default minimum is 0.1 mm. Swept coverage is unavailable. Artifact sizes and hashes are retained in `docs/probes/ot7/retained/repair-measurement.json`. This was a published-data read, with no rebuild, new sweep or provider call; the collector repair slot remains unused [rec: long-falcon-7461].

The seeded-repair collector pins seed identity and empty overrides, requires complete unchanged before measurements, consumes one hash-checked frozen fresh-session prompt, and retains before/after reports, transcript hashes and accepted identity even on refusal. Exclusive evidence creation prevents redispatch; there is no continuation or smoke call [rec: blue-sky-2193]. Known-answer fixtures now exercise the real pagination reader and fit summary: later static failures survive, late-page errors prevent partial reports, and later nested joint/pair pages retain collision extrema and first contact. Deliberate truncation mutations fail the new cases. Latest full CLI validation: 706 passed / 1 skipped; focused runner suite: 20 passed. These are synthetic collection checks, not repair evidence [rec: long-spark-1984] [rec: true-wolf-3979].

Reconcile judgement: the baseline and fixtures improve evidence collection but leave F4 open. An eventual zero-failure summary alone cannot prove all three original defects repaired, because the horn gaps lack contact intent. All three units ran before the documented provider reset without a repair dispatch [rec: long-spark-1984] [rec: true-wolf-3979] [rec: long-falcon-7461].

**Two fresh frozen-prompt invocations were refused at the provider session limit: F4 remains open, with zero completed design turns.** The second `claude-fable-5` call used the unchanged prompt without `--resume`, exited 1 after 4.02 seconds and made zero transcript tool calls. No actor design edit occurred. Before/after published reads each report 15 failures: 8 intersections, 6 below-clearance pairs and one world plane. Accepted revision, digest, attempt and script remain unchanged; ordinary restore updates only `latest_candidate` and `updated_at`. The second receipt is `docs/probes/ot7/retained/repair-refusal-iteration19.json` [rec: keen-quill-2265].

The seed is Heron's first accepted ot6 revision `7e9eff5c…`. On the first refused call (4.09 seconds), missing historical artifacts prevented both before-fit reads; product restore recreated artifacts and changed the attempt pointer while preserving accepted revision, digest and script. That restored report had 21 failures. ADR-353 removes six nominal-0.1 mm flags (two bearing gaps and four servo/tab-screw gaps), explaining the later 15 without a design change. The seed still has 248.20162986795 mm³ servo/cheek overlaps; its 0.2 mm child/horn gaps do not fail without contact declarations. Sweep remains unavailable; no smoke or repair success is claimed [rec: lucky-willow-8039] [rec: keen-quill-2265].

The design-agnostic prompt remains frozen at `docs/probes/ot7/prompts/repair.prompt.txt` (sha256 `5d846901…`), with wording test-pinned. Charter criterion: an unassisted session on the first Heron revision resolves all three defects from tools and one frozen continuation prompt, accepting zero failing fit checks, with before/after reports and turn/transcript evidence. Reconcile judgement: retain `open`; refusals do not count as completed repair turns [rec: silent-union-5108] [rec: kind-dusk-1609] [rec: keen-quill-2265].

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
