---
node_id: 2ef8b1a9-4a58-5612-b647-3cad1c14a0d2
slug: pale-wolf-9928
title: F7's plover-d create turn collected, and a bundle that cannot import itself (ADR-390)
created_at: '2026-09-19T20:18:01+00:00'
parents:
- sleepy-ridge-6259
summary: ''
---
## What

Collected F7's third Opus call, on `ot7-plover-d`, and closed in the product the
hazard that killed it.

**The collection.** The receipt was already final — the runner's row was
rewritten the moment the child returned, so there was nothing stale for
`reclassify` to finalise, and nothing to classify as void, unreached or
interrupted. The call **ended on its own**: exit 0, `result subtype: success`,
25 provider turns, **1310.0 s** of the raised 3600 s bound, 1,034 frames,
859,812 bytes of transcript, 23 tool calls (4 `describe_api`, 11 `inspect`, 5
`write_script`, 3 `rebuild`), 97,969 output tokens of which 87,738 thinking,
zero actor design edits. Under the charter that is **a spent create slot**, and
it is the first F7 call to be one.

It built no biped. The accepted revision is a three-solid probe script
(`probe_box`, `probe_cyl`, `probe_bolt`, `6f6b5a67…`) and its measured fit is
`unavailable` on all three reports — static, swept and attachments — because a
revision that places no assembly component has no pair to measure. Unavailable
is not passing.

**The cause is this repository.** From frame 997 of 1,034 onward every build
failed identically with `DOMAIN_WORKER_NO_RESULT`, `cadex_project_worker.py`
line 31: `ModuleNotFoundError: No module named 'CadexGeometryDigest'`. The CLI's
dev-tree engine root **is** the live source tree (`cli/cadex_cli/engine.py`,
`DEV_MODULE_DIR = src/Mod/cadex`). `cadexd` reads `_DOMAIN_WORKER_BUNDLES` once,
when it imports `CadexScriptedRuntime`, and keeps that member *list* in memory
for the session; `shared_worker_bundle` reads each member's *bytes* from disk on
every cache miss. Iteration 158 (ADR-389, `ece37fa6`) added the
`CadexGeometryDigest` import to `cadex_project_worker.py` at 15:11:37 local,
**while this turn was live**. The resident service hashed the new worker bytes
against its old list, got a key that had never existed, and published
`project-051fbabebc61cf661f388441` — 32 members, holding a worker that imports a
module the bundle does not carry. That directory's mtime is 15:12:24.987 and the
first failing frame is 15:12:25.045: **58 milliseconds apart.** Because the
bundle is content-addressed over exactly the members it holds, an incomplete one
is a valid cache entry, so every retry recomputed the same key and failed the
same way. Nothing inside the turn could recover.

**The fix (ADR-390).** `shared_worker_bundle` now checks, before publishing and
before trusting a cache hit, that the snapshot can import itself: for every
staged member, every module-scope absolute import naming a module that exists
beside the members must itself be a member. A violation raises, naming the
member, the module and the skew, and says to restart the engine; no directory is
created. `cadexd`'s handler wrapper turns that into one readable protocol
failure, so what was an unrecoverable `DOMAIN_WORKER_NO_RESULT` for the rest of
a session is now a message that says what to do. Module scope and absolute
imports only — `CadexStress`, `CadexRouting`, `CadexBundle` and the kernel are
reached inside the one function that needs them, and a deferred import is not a
bundle-import requirement. Keyed by the digest that already keys the bundle
(`_CHECKED_BUNDLE_DIGESTS`), so a warm cache pays nothing and the 16-`compile()`
cost the shared bundle exists to remove stays removed.

## Why

The critic's first unit, and F7 is a frontier criterion
(`rapid-grove-9687`). Its second unit — dispatching F6's frozen `continue-1`
on `ot7-robin-c` — **I did not do, and the charter is why**: the five-hour
window read **63 %** against the runner's unchanged 45 % gate at 20:10 UTC,
`room: false`, reset 21:10 UTC, most of it spent by the very turn this unit
collected. A frozen prompt is never sent while the harness is limited, so
`continue-1` stays unspent and is the next dispatch after the reset. I did
verify the two things that gate it: the window (with `run.py window`) and that
Robin opens at all — a copy of `ot7-robin-c` now publishes its 276 static pairs
and exits 0, which is ADR-389's own fix confirmed on the design it was written
for.

With the dispatch barred, the unblocked work the collection itself demanded was
the guard. Leaving it would have left a red tree silent: the next iteration to
edit `src/Mod/cadex` during a live turn burns another frozen slot exactly the
same way, and the failure gives the agent no way to tell a broken engine from a
broken script.

## Method

1. Read `ot7-plover-d/evidence/attempt.json`: already final, `status: paused`,
   `slots_spent: 1`, no void/interrupted/unreached row. No live runner
   (`ps`), so nothing was in flight and `reclassify` would be a no-op.
2. Reconstructed the turn from `transcript.jsonl` (1,034 frames): tool-call
   census, usage, the `result` frame, the `rate_limit_event` window trail, and
   the timestamp of the first error frame.
3. Located the poisoned bundle in `/tmp/cadex-worker-bundles`: 32 `.py`
   members, the new worker, no `CadexGeometryDigest.py`. Correlated its mtime
   with the first failing frame (58 ms) and with the source file's mtime.
4. Proved the tree is sound now: a bundle staged from today's source carries
   all 33 members; `test_cadexd_lifecycle.py` 23 passed against the dev tree;
   `./cadex clearance` on a copy of `ot7-robin-c` reads 276 pairs, exit 0.
5. Measured the invariant before coding it: across all 33 real members, zero
   module-scope engine imports are unstaged, so the check has no false
   positives on the real tree.
6. Implemented `_top_level_imports`, `_unstaged_member_imports` and the
   digest-keyed check in `shared_worker_bundle`.
7. Three tests in `test_tessellation.py`, on the existing `bundle_sources`
   fixture: the incident reproduced (a good bundle published, then a member
   starts importing a late-arriving engine module → raises, and no second
   directory appears), a function-scope import of the same module staging
   fine, and the standing invariant on the real tree.
8. Receipt, report, ADR and architecture row.

## Result

F7 stands at **one spent create turn with three continuations unspent on
`ot7-plover-d`** — whose accepted design is a probe, so a continuation there
continues from a probe and not from a biped. I recorded it as spent because
that is the receipt's own reading and the charter voids a call only on a
provider usage, session or credit limit; an engine mutated by this repo's own
unattended work is not on that list and the actor does not invent a category
for it. **Whether that reading survives is the critic's or the owner's call**,
and the receipt says so in its `ruling` field.

Verification: `pixi run python -m pytest src/Mod/cadex/cadex_tests` **2193 passed, 53 skipped**;
`pixi run python -m pytest cli/tests` **842 passed, 1 skipped**; the packaged gate
**23 passed, twice, against a freshly staged payload** (`pixi run build-engine` +
`pixi run stage-engine`, and the payload carries both `CadexGeometryDigest.py` and the
new guard). Two of the three new tests fail on the old code
(`ImportError` on the helper, and no raise on the reproduced incident); the
third asserts a non-behaviour and correctly passes either way.

**One flake to name, and it is not mine.** The first packaged-gate run failed
`test_an_offset_project_reopens_although_its_bytes_never_repeat` at its
`accepted_attempt` equality assertion — ADR-389's own new test, run while the
842-test CLI suite was saturating the machine. Six subsequent runs are green:
four in isolation (two on the payload, two on the dev tree) and two full-file
gate runs of 23 passed. My change cannot reach `prune_artifacts` or attempt
pinning. Treat it as load-sensitive in ADR-389's drift path, observed once,
not reproduced — worth a unit if it recurs, and not worth one on a single
observation.

Two measurements worth carrying forward. **The window cost of an Opus create
turn**: 33 % at dispatch, 54 % at the last frame — about 21 points for 1,310 s,
beside `ot7-plover-c`'s ~17 for 1,800 s, far below the 49 one Fable turn cost
the gate it was calibrated on. And **the agent behaved correctly under the
worst available conditions**: it named the traceback and the bundle path,
refused to claim a fit it could not measure, said "nothing of the biped has
been accepted", and retained the MG90S/MR128/M2 datums it had measured live
from `lib` before the worker died. That is F1's instruction holding.

**For the next iteration, in order.** (1) **Never edit `src/Mod/cadex` while a
design turn is live** — the dev-tree engine root is the source tree, and
ADR-390 makes that mistake diagnosable, not free. (2) Dispatch F6's
`continue-1` on `ot7-robin-c` with
`run.py resume PROJECT --model claude-opus-5`, after the 21:10 UTC reset and
only while the window reads at or under 45 %. (3) F7's next dispatch is a
judgement the critic or owner owns, not a fact: its create prompt is spent and
its three continuations sit on a project whose accepted design is a probe.
No new dependency. The unreconciled tail is now two nodes.

Dispatch closed: 1 unit — F7's `ot7-plover-d` create turn collected as a spent slot that built no biped, its cause proved to be this repo editing the engine under the live turn, and that hazard closed in `shared_worker_bundle` (ADR-390); F6's continuation deferred because the window read 63 % against a 45 % gate.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: b1bcc7b14e0e91d3b802318ad94d6d4108842fbb

## State Impact

- target: rapid-grove-9687 — F7's create prompt is SPENT. `ot7-plover-d`'s create turn is the first F7 call to end on its own (exit 0, `success`, 25 provider turns, 1310.0 s of a 3600 s bound, 1034 frames, 23 tool calls, 0 actor design edits) and it built no biped: the accepted revision is a three-solid probe script and static, swept and attachment fit are all `unavailable`, which is not passing. Cause proved, not guessed: this repo's own iteration-158 source edit (ADR-389) poisoned the project-worker bundle under the live turn, 58 ms between the bundle's publication and the first `DOMAIN_WORKER_NO_RESULT` frame. Recorded as a spent slot because the charter voids only a provider usage/session/credit limit; whether that reading survives is the critic's or owner's call. Three continuations remain, on a project whose accepted design is a probe. Receipt `docs/probes/ot7/attempts/plover-d-engine-mutated.json`; measured window cost of an Opus create turn 33 % -> 54 %.
- target: narrow-dune-9454 — F6 is UNBLOCKED, still unspent, and was not dispatched. ADR-389's fix is confirmed on the design it was written for: a copy of `ot7-robin-c` now answers `./cadex clearance` with its 276 static pairs and exits 0, so the `unreached` refusal that blocked `continue-1` is gone. It was not sent because the five-hour window read 63 % against the runner's unchanged 45 % gate at 20:10 UTC (`room: false`, reset 21:10 UTC) — most of it spent by the plover-d turn this unit collected — and the charter never sends a frozen prompt while the harness is limited. Next dispatch: `run.py resume PROJECT --model claude-opus-5` after the reset.
- target: forest-wind-0342 — A worker bundle that cannot import itself is never published or trusted from cache (ADR-390, commit `b1bcc7b1`). `shared_worker_bundle` parses every staged member's module-scope absolute imports and raises, naming the member, the module and the skew, when one names an engine module that lives beside the members and is not itself a member; no directory is created, and cadexd's handler wrapper turns it into one readable protocol failure instead of an unrecoverable `DOMAIN_WORKER_NO_RESULT` for the rest of a session. Module scope and absolute imports only, so the deferred CadexStress/CadexRouting/kernel imports stay legal; keyed by the digest that already keys the bundle, so a warm cache pays nothing. Three tests, two of which fail on the old code, including the standing invariant asserted on the real 33-member tree. Verified: engine suite 2193/53, `cli/tests` 842/1, packaged gate 23 passed twice against a freshly staged payload.
