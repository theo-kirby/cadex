# Frozen design attempts: void, unreached and interrupted calls

Verified against source: 2026-09-19. [Cadex-new]

**Amended for the restart (ADR-355).** The three calls below are **void**,
not attempts: each ended on the provider session limit before any model saw
the prompt, so each spent nothing. Heron, Robin and Plover each still have
their create prompt and all three continuations unspent, and their retries go
to fresh suffixed projects (`ot7-heron-b`, `ot7-robin-b`, `ot7-plover-b`)
with the same frozen prompts, only while the product agent is available.
[`void-calls.json`](void-calls.json) classifies all six pre-restart calls,
these three and the three F4 repair calls, from their retained transcripts
with the runner's own rule. The narrative below is kept as written on
2026-09-14; where it says a receipt "does not authorize another attempt" or
that a refusal is an attempt, the amendment supersedes it.

## F5 arm

At 18:58 America/New_York, iteration 32 dispatched the frozen Heron create
prompt in the fresh external project `cadex-projects/ot7-heron`, using
`runner/run.py heron` with `--model claude-fable-5`. The critic requested this
F5 fallback while the documented 20:20 reset still prevented F4's repair.

The provider refused after **1.917 seconds**: “You've hit your session limit ·
resets 8:20pm (America/New_York)”. This is one provider dispatch, **zero
completed design turns**, zero continuations and zero actor design edits.
The attempt stopped on CLI exit 1. The collector itself exited 0 because it
successfully retained the refusal; that exit does not mean a design passed.

[The portable receipt](heron-refusal.json) carries the frozen prompt digest,
transcript digest, timings and hashes for all retained artifacts. Raw logs,
transcript and the original manifest remain under the external project's
`evidence/` directory. The prompt SHA-256 is
`bcda5af55c50459968d87d4651cf0123e7f996227c6c80895365078860514e37`;
the transcript SHA-256 is
`813e77ee6c0183c17e4a54dec380f83524ae4183ce763f0bfe7aab3ee9c0dedb`.

There is no accepted revision. Static fit, swept fit and catalog inventory
are **unavailable**, not passing: the report's zero pairs and zero failures
describe no measured geometry. The bounded smoke command exited 1 in
0.114 seconds because `script.json` does not exist; no simulation ran.
Compared with ot6's accepted Heron, this attempt produced no design to compare.
F5 remains open with a recorded provider refusal rather than a geometry result.

No retry, continuation, repair, training or design edit followed. The F4 seed
and its single frozen repair slot remain untouched by this unit. Retain this
attempt in final accounting; the collector forbids restarting it or hiding it
behind a fresh project. This receipt does not authorize another arm attempt.

Validation: all eleven retained artifact hashes and sizes matched the manifest;
the committed receipt is below 16 KB; all 33 collector tests passed. No product
code, engine protocol or payload changed, so no build or packaged gate ran.

## F6 balancer

Iteration 33 dispatched the frozen Robin create prompt once in the fresh
external project `cadex-projects/ot7-robin`, using `runner/run.py robin` with
`--model claude-fable-5`, as requested by the critic. The provider refused in
**1.868 seconds**, reporting the same session limit and 20:20
America/New_York reset. The CLI exited 1; the collector exited 0 after
retaining evidence. There was one provider dispatch, **zero completed design
turns**, zero continuations, zero actor design edits and no accepted revision.

[The balancer receipt](robin-refusal.json) retains timings and hashes for all
eleven artifacts and the original manifest. Raw evidence remains in the
external project's `evidence/` directory. The frozen create prompt SHA-256 is
`e20ee7abe5818015182693a2d950b84fc62da67868d2ee42cec748ca2299329b`;
the provider transcript SHA-256 is
`01566753ac81f189b21cc565b300fc00f8d63e4cf63d985989d3663b6b490674`.

Static fit, swept fit and inventory are **unavailable**. Zero measured pairs
and zero reported failures do not establish passing geometry. The smoke
command exited 1 in 0.114 seconds because `script.json` does not exist;
no simulation ran. Compared with ot6's accepted Robin, this attempt has no
design to compare. F6 remains open with refusal evidence, not completion.

No retry or substitute design edit followed. F4's repair dispatch remains
preserved for the documented reset. Both refused design attempts must appear
in the closing report, with unavailable measurements distinguished from passes.

Validation: all eleven artifact hashes and sizes matched the manifest; the
portable receipt is 3,435 bytes; all 33 collector tests passed in 0.35 seconds.
This evidence/documentation unit changed no product code, protocol or payload;
no build or full suite was run.

## F7 biped

Iteration 35 dispatched the frozen Plover create prompt once in the fresh
external project `cadex-projects/ot7-plover`, using `runner/run.py plover`
with `--model claude-fable-5`, as requested by the critic. The provider
refused in **3.273 seconds**, reporting the session limit and 20:20
America/New_York reset. The CLI exited 1; the collector exited 0 after
retaining evidence. There was one provider dispatch, **zero completed design
turns**, zero continuations, zero actor design edits and no accepted revision.

[The biped receipt](plover-refusal.json) retains timings and hashes for all
eleven artifacts and the original manifest. Raw evidence remains in the
external project's `evidence/` directory. The frozen create prompt SHA-256 is
`b95f98b77ba7180140d873e3615a24a0802e9645671664c2e7277c465d8457aa`;
the provider transcript SHA-256 is
`b5b359ec0d0f5465cd1e8520701e3d7c17285881823ed028b03e13996434ea59`.

Static fit, swept fit and inventory are **unavailable**. Zero measured pairs
and zero reported failures do not establish passing geometry. The smoke
command exited 1 in 0.114 seconds because `script.json` does not exist;
no simulation ran. ot6 has no product-agent biped baseline: Finch was
actor-authored. This attempt produced no geometry for comparison, and F7
remains open with refusal evidence.

No retry, continuation or substitute design edit followed. The arm and
balancer were not retried, and F4's repair slot remains untouched. All three
refused create attempts must appear in closing-report accounting, with
unavailable measurements distinguished from passes.

Validation: all eleven artifact hashes and sizes matched the manifest;
the portable receipt is below 16 KB; all 33 collector tests passed in
0.36 seconds. This evidence/documentation unit changed no product code,
protocol or payload; no build or full suite was run.

## F7 biped, second and third calls: one dead runner, one dead clock

Verified against source: 2026-09-19.

Neither of the two Opus dispatches that followed the refusal above was a
design result, and neither spent a slot. Both retain their evidence.

**`ot7-plover-b`, iteration 154.** The window probe read `allowed` at 12 %,
the frozen create prompt reached the model, and 18 seconds later the runner
process itself died and took the child with it. Every frame that arrived was
retained frame by frame (ADR-356) — 28 in all, 10 of them from the model —
`turn.stdout.json` is empty, and the receipt read `status: running` because
nothing survived to finalise it. A child that never ended on its own is an
**interruption**: no slot, retry in a fresh letter-suffixed project.

That gap — the runner classified a child *it* killed at the bound and one that
never launched, but had no path for its own death — was closed in iteration
156 (ADR-388), and `run.py reclassify` finalised this receipt: `interrupted`,
`kind: runner_died`, 0 slots spent, `model_messages_before_kill` 10 counted
from the transcript the dead child left, retry `ot7-plover-d`. It could be
ruled because the receipt had been silent for **2769.2 s** against a budget of
2700 s — the 1,800 s bound *this* turn ran under plus the measurement bound
plus a 600 s grace — and nothing touches a receipt while its turn runs. The
stale copy is kept beside it as `attempt.superseded.json`.
[The receipt](plover-b-runner-died.json) carries the digests.

**`ot7-plover-c`, iteration 155.** The probe read `allowed` at 14 % of the
five-hour window, and the same frozen prompt ran on `claude-opus-5` for the
full **1800.0 s** bound: 124 frames, 49 tool calls (4 `describe_api`, 30
`inspect`, 10 `write_script`, 4 `edit_script`, 1 `rebuild`), 1.29 MB of
transcript. The turn was **killed at the bound while repairing its own
measured fit**, so it is an interruption under ADR-356: slot returned, retry
in `ot7-plover-d`, F7 still holding all four slots.

Unlike the refusals above, this call produced measured geometry. The last
revision it built (`15be5515…`, never accepted) is a 30-component biped, 24
components catalogued and 6 printed, and the product measured it: **13 failing
of 435 static pairs** (12 intersections and 1 world-geometry failure) and
**52 failing swept pairs over 4 of 4 joints, coverage complete**. The agent
was reading those numbers back through `inspect scope=clearance` when the
clock ran out. [The receipt](plover-c-interrupted.json) carries the digests.

The measurement that matters for the next dispatch is the bound itself. Every
create turn has cost more the larger its design — Heron 1530.4 s at 120 pairs,
Robin 1676.4 s at 276, Plover 1800.0 s at 435 — so the biped is the first
design whose create turn does not fit in 30 minutes, and a retry at the same
bound has no reason to end differently. `ot7-plover-d` should be dispatched
only after that bound is raised — which iteration 156 did: ADR-388 doubles
`TURN_BOUND_SECONDS` to **3600 s**, and every receipt now records the bound
each of its turns ran under, so the three timings above stay comparable.
