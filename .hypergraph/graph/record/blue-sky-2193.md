---
node_id: 1e62376e-7d57-5578-880a-62e372402445
slug: blue-sky-2193
title: 'F4: collect one frozen repair from the preserved Heron seed'
created_at: '2026-09-14T22:14:20+00:00'
parents:
- narrow-valley-3317
summary: ''
---
## What

Extended the bounded ot7 evidence runner with the F4 seeded-repair mode,
known-answer fixtures, usage instructions and an ADR-354 extension. It reads
the preserved first Heron seed and collects one frozen fresh-session repair
call with before/after fit reports, transcript hashes and accepted identity.

## Why

Advances F4 (`polished-forest-0215`). The critic explicitly requested the
seeded runner fixture if the documented provider reset was still ahead. At
unit start it was 2026-09-14 22:02 UTC, 18:02 America/New_York, before the
recorded 20:20 local reset. I took that fallback without another provider
invocation or retained audit. No deviation from the critic's requested unit.

## Method

The repair mode verifies script/revision against the first refusal receipt,
pins the preserved accepted digest and empty override tables, and requires
the working revision to match. It writes only evidence. Exclusive creation of
`evidence/f4-repair` prevents redispatch even after an interrupted invocation.
Before a provider call, it reads the complete published clearance via the
existing restore=False collector and checks that script and full metadata
remain unchanged. Failed or missing before measurements stop before dispatch.
The one repair.prompt.txt slot is hash-checked and durably consumed before
launch. It uses a fresh session with no resume, the existing automatic-nudge
block and 30-minute bound. After measurements and identity are retained even
on a provider refusal. F4 has no extra continuation or smoke call.

Known-answer fixtures supply seven failures before and zero after, preserve
seed bytes, assert the single frozen prompt, reject altered script/revision/
digest/parameters, refuse repeat dispatch, and stop on failed/missing/mutating
before reads. A separate child fixture verifies no --resume and exact frozen
text. The real preserved seed passed a read-only identity validation; no
evidence directory or provider call was created there.

## Result

Validation: full CLI suite exited 0, **702 passed / 1 skipped in 529.70 s**.
The final focused runner suite passed **17 tests**, including the extra changed
repair-prompt parameterization added after full-suite collection began; it
also exercises the final early seed-manifest save. Runner --help and
`git diff --check` passed. Full log:
`cadex-projects/ot7-runner-validation/evidence/iteration25/cli-tests.log`,
SHA-256 `fcdd79c121c4f9ca197be50e29259fffbfc158728045fd9dd3b02b5df81d968b`.
No engine, protocol or payload source changed, so no engine suite, full build
or packaged gate was rerun. No new dependency, design edit, provider call,
charter edit or dashboard change.

F4 remains open: these are collector fixtures, not a real before/after repair
result. The preserved seed is ready for the documented post-reset command in
the runner README. All prior refusals remain evidence; the single frozen
prompt and its meaning are unchanged. Assumption: the recorded reset remains
the earliest appropriate retry time. This node brings the pending record count
to three; the next dispatch owes reconcile under the charter, but this dispatch
explicitly forbids reconcile and does not write state or generated views.
Dispatch closed: 1 unit — bounded F4 seeded-repair evidence collector.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 33d1974de9a9a04c772bbdf7347e11bdf55ebb60

## State Impact

- target: polished-forest-0215 — F4 now has a tested seeded-repair collector preserving seed identity, frozen fresh prompting and before/after evidence; provider reset was still ahead, so no repair ran and F4 remains open.
