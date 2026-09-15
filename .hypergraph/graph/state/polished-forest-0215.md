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

**F4 has one call that reached the model, and it produced no repair: the frozen prompt on `ot7-heron-repair-b` was killed at the runner's 30-minute bound with no submit call, the seed unchanged at 15 failures [rec: rare-birch-0755].** The three earlier calls are void, not attempts [rec: narrow-wave-7452].

**The measured attempt [rec: rare-birch-0755].** With Claude available (a one-word probe answered in 5.4 s; the probe is not a frozen prompt and spent no slot), the repair prompt (`5d846901…`) was dispatched once through the runner's `repair` mode on `ot7-heron-repair-b`, a copy of the seed with `evidence/`, `agent.json` and the CLI lock excluded and passed by `validate_seed` (script `3339a178…`, accepted revision `7e9eff5c…`, empty overrides). The guarded before-read reproduced the retained baseline exactly: 105 pairs, 15 failures, both horn/link gaps at 0.2 mm, the 248.2 mm³ servo/cheek overlap, the collision plane on `comp_base`. The model made **17 tool calls, all reads** — clearance summary and pairs, script, `describe_api`, the assembly and library API, the script source, the exports — reading the measured fit first, which is the F1 behaviour the run built. It never called submit and emitted no text: after the fifteenth read it produced one message of 64,000 output tokens, 63,999 of them thinking, ending on the provider's output cap (`stop_reason: max_tokens`) with no text and no tool call, then two more reads, and was generating again when the runner killed the process group at 1,800.0 s. Usage over 16 API messages: 82,904 output tokens, 746,388 cache-read and 94,540 cache-write input tokens. After the call: script, accepted revision and the 15-failure fit byte-for-byte unchanged, attachment assessment `fail` before and after, zero design turns, zero actor edits, zero continuations. The receipt is `docs/probes/ot7/retained/repair-timeout-b.json` (11,180 bytes); the runner's `transcript.jsonl` was never written because the kill came first, so the provider stream was recovered unmodified from the Claude Code session store (698,175 bytes, digest in the receipt, thinking blocks redacted by the harness) and the receipt names it as recovered, not as the runner's capture.

**Slot accounting is an owner ruling, not decided [rec: rare-birch-0755].** The call is not void: `void_reason` returned null, no limit appears anywhere. Under the runner's documented rule the turn is `interrupted` with `slot_consumed: true`, `slots_spent: 1`. The charter voids only provider limits and counts "a turn that reached the model and ended on its own"; a runner-bound kill is neither. The actor did not re-dispatch on `ot7-heron-repair-c` because a retry spends provider budget irreversibly while the slot ruling is reversible. If the owner or critic rules the timeout a non-turn, the same frozen prompt goes to `ot7-heron-repair-c`, a fresh seed copy, only while Claude is available. **Two collector defects are named and not fixed**: `CapturedTurn.run` writes `transcript.jsonl` only after the turn returns, so a kill loses the stream (write frames as they arrive); and the CLI passes no thinking or output bound to Claude, so one silent thinking burst can eat 16.5 of 30 minutes. A per-message bound or a longer turn bound must be decided before the next design turn. Reconcile judgement: fold as F4's first attempt under the runner's rule; retain `open`.

**The three pre-restart calls are void [rec: narrow-wave-7452] [rec: keen-wing-6569].** Three frozen-prompt invocations of the repair collector on the preserved Heron seed were refused at the provider session limit (4.09 s, 4.02 s and 4.171 s), zero tool calls, no actor edit [rec: lucky-willow-8039] [rec: keen-quill-2265] [rec: blue-slope-0916]. The runner now classifies them void by code from their retained transcripts (`docs/probes/ot7/attempts/void-calls.json`): no slot spent, listed apart from the design's attempts, retry named as `ot7-heron-repair-b` [rec: narrow-wave-7452]. The iteration-39 receipt `docs/probes/ot7/retained/repair-refusal-iteration39.json` still holds before/after fit and both horn-contact assessments [rec: blue-slope-0916]. After the measured attempt the repair slot is consumed under the runner's rule and the three continuations remain unspent.

**The frozen repair collector.** Before/after `repair-assessment.json` receipts retain accepted identity and require static fit plus measured contact at `comp_horn_shoulder/comp_upper_arm` and `comp_horn_elbow/comp_forearm` (distance within 0.001 mm, common volume within 0.000001 mm³); fixtures catch the otherwise unflagged 0.2 mm gaps [rec: western-fox-7010]. The collector pins seed identity and empty overrides, requires complete unchanged before measurements, consumes one hash-checked frozen fresh-session prompt without `--resume`, retains before/after reports and transcript hashes even on refusal, and refuses an existing evidence directory, which is why a retry needs a fresh seed copy [rec: blue-sky-2193] [rec: blue-slope-0916]. Known-answer fixtures exercise the real pagination reader and fit summary [rec: long-spark-1984] [rec: true-wolf-3979]. A void repair leaves the seed untouched and points at a fresh seed copy [rec: narrow-wave-7452].

**The seed's measured baseline.** Heron's first accepted ot6 revision `7e9eff5c…`: 105 unique pairs, 15 inventory components; 91 pairs clear; shoulder servo/base overlap 248.20162986795066 mm³; both horn/link gaps about 0.2 mm, not failing because the seed declares no contact intent; swept coverage unavailable [rec: long-falcon-7461]. ADR-353 removed six nominal-0.1 mm flags, explaining an earlier 21-failure restored report becoming 15 without a design change [rec: lucky-willow-8039] [rec: keen-quill-2265].

The design-agnostic prompt is frozen at `docs/probes/ot7/prompts/repair.prompt.txt` (sha256 `5d846901…`), wording test-pinned [rec: silent-union-5108]. Charter criterion: an unassisted session on the first Heron revision resolves all three defects from tools and one frozen continuation prompt, accepting zero failing fit checks, with before/after reports and turn/transcript evidence [rec: kind-dusk-1609] [rec: keen-wing-6569].

## Negative knowledge

- [scope: the F4 repair prompt on `ot7-heron-repair-b` under the CLI's unbounded thinking and the runner's 30-minute turn bound | confidence: medium | evidence: rare-birch-0755] The model reads the measured fit but then thinks to the output cap without submitting; the turn ends on the runner's clock, not the model's.

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
- narrow-wave-7452 — the three F4 calls classified void by the runner's code; retry named `ot7-heron-repair-b` on a fresh seed copy
- rare-birch-0755 — the repair prompt reached the model on `ot7-heron-repair-b`: 17 reads, a 64k thinking burst, no submit, killed at 30 minutes; seed unchanged; slot ruling left to the owner
