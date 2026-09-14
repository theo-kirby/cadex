# Frozen design attempts: provider refusals

Verified against source: 2026-09-14. [Cadex-new]

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
