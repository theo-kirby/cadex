# Frozen-design evidence runner

Verified against source: 2026-09-19. [Cadex-new]

An explicit `resume PROJECT --model MODEL` switches subsequent calls to that
model (ADR-384). The receipt records the transition and each turn's model;
previous turns and prompt allowances are preserved. Without `--model`, resume
keeps the receipt's model. This permits the owner-authorized Opus continuation
of Robin after its Fable create turn without replaying that turn.

This is the F4–F7 evidence collector (ADR-354), amended for the ot7 restart
(ADR-355). **Every product-agent call ot7 dispatched before the restart was
void**: all six ended on the provider's session limit in two to four seconds,
no model saw a prompt, and none spent a create, continuation or repair slot.
The runner now recognises that outcome itself; see [Void calls](#void-calls-adr-355)
below and the [classified receipt](../attempts/void-calls.json). Nothing is
exhausted. Every design still has its create or repair prompt and all three
continuations unspent, and the retry is the same frozen prompt in a fresh
letter-suffixed project, dispatched only while the product agent's harness is
available. Earlier wording in this file and in the receipts that called a slot
"consumed" after a refusal is superseded by that amendment and is kept as
history, not deleted.

Run one design, in a new external project, using the existing pixi environment:

```bash
pixi run python docs/probes/ot7/runner/run.py heron \
  "$PROJECTS/ot7-heron" --model claude-fable-5
```

`PROJECTS` must name the operator's external `cadex-projects` directory.
Use `robin` or `plover` for the other frozen designs. The runner checks all
four prompt digests against the freeze before creating the project. The create
prompt and the three continuations are the complete schedule. Each slot is
persisted before dispatch. Existing projects are refused, including interrupted
ones: this command does not reset a consumed budget. `resume` (below,
ADR-357) continues a project whose every turn ended on its own, and
`--turns N` bounds how many prompts one invocation dispatches.

Each design change is made by the ordinary product-agent turn. The collector
uses the CLI's turn-factory seam to write the provider stream to
`transcript.jsonl` **frame by frame as it arrives** (ADR-356), so a call
killed at the runner's bound keeps every frame it had produced, and to
suppress the CLI's automatic no-tool follow-up, whose text is outside the
frozen schedule. A blocked follow-up stops the attempt. The ordinary
stale-session recovery may retry the same frozen text; both streams are
appended in order. No script, parameter or accepted-state writer exists in
this runner.

Under `evidence/`, `attempt.json` records the design, model, prompt digests,
continuation counts, elapsed time and process status. Each `turn-N/` retains:

- A verbatim frozen prompt and the provider `transcript.jsonl`, with digests.
- The CLI JSON envelope and stderr, including errors and printed claims.
- `clearance.json`: all published static pairs and the raw swept report,
  including missing or incomplete coverage and per-joint timings.
- `fit.json`: the product's static verdict, failure count and every failing
  pair, read independently from the accepted measurements after the turn.
  Since ADR-366 it also carries the `sweep` half the turn's own build reply
  carried — coverage, per-joint extrema and every pair overlapping through a
  range — and the attempt row summarises it as `swept_fit` beside
  `static_fit`. A receipt measured before ADR-366 has neither.
- `inventory.json`: the accepted catalog inventory.

Artifact paths in each row are relative to its `turn-N/` directory; smoke
artifact paths are relative to `evidence/smoke/`. Every listed file carries its
byte size and SHA-256. The manifest is project-local, and may exceed the 16 KB
limit for committed receipts. Publish only a compact receipt citing it.

The runner uses all three continuations even if an earlier static report
passes: a static pass says nothing about missing swept coverage. It adds no
second swept checker and claims no design passes. The final report author must
assess the retained swept extrema against intent and account for missing
coverage. Provider errors, timeouts and launch failures stop further prompts;
an ordinary rejected design (CLI exit 3) can receive the next frozen
continuation. Three outcomes end an attempt early and mean different things:
a provider error the call returned on its own (a nonzero exit with a stream,
such as an authentication failure) is a **failed** turn that keeps its
consumed slot; a usage limit is **void** (ADR-355, below); and a call the
runner cut off at its bound, or whose child never launched, is
**interrupted** (decision #44, ADR-356, below) and returns its slot. Missing
transcript or measurement files mean unavailable evidence, never zero
failures. The runner must not be restarted against another project to hide
a failed attempt.

Each model call has a 30-minute process bound (`TURN_BOUND_SECONDS`, written
into the receipt); each measurement read has a five-minute bound. Timeout
kills the child process group, and a call killed there is an interruption,
not a spent slot (ADR-356). One final one-second
holding smoke is attempted even for failing designs, with a 240-second internal
budget and a 300-second process bound. Its full receipts and logs stay in
`evidence/smoke/`. A process exit of zero alone is not a passing smoke: read the
receipt's verdict. No policy is trained. The collector does not change engine,
CLI, protocol, acceptance or dashboard behavior.

`cli/tests/test_ot7_runner.py` exercises a permanently failing design through
all four slots, refuses a restart before any fifth dispatch, checks that a
failed turn stops with its slot spent, rejects changed prompts, blocks the
automatic follow-up, checks evidence hashes and kills a timed-out child. Its
interruption fixtures pin a runner-bound kill on a create, on a continuation
after two completed turns, and on the repair, each returning only its own
slot and naming the retry project; frame-by-frame capture that keeps every
frame received before a kill; and that a limit seen before the kill is void,
not interrupted. These are runner fixtures, not F5–F7 design results.

## Void calls (ADR-355)

A product-agent call that ends on a provider usage, session or credit limit
is **void**: it spends no slot, it is not a design result, and its evidence
directory stays as a receipt. The runner classifies every turn after the
child exits, from three things it already retains, and reads them in this
order:

- the provider stream in `transcript.jsonl`: a `rate_limit_event` frame with
  status `rejected`, a synthetic assistant frame tagged `error: rate_limit`,
  or an error result frame with HTTP status 429 or limit text;
- the CLI envelope `turn.stdout.json`: its `error` field, which is empty on
  an ordinary turn;
- `turn.stderr.txt`, only when no envelope was written.

A limit that lands after the model has already spoken is still void: the
turn did not end on its own. The row records `cut_off_mid_turn` and how many
model messages preceded the limit. The classification does not depend on the
child's exit code.

On a void call the row's status is `void`, `slot_consumed` is false,
`continuations_used` stays at the count before the call, the measurement is
still read and hashed, no smoke runs, and nothing further is dispatched from
that project: the receipt's status is `void` and its `retry` names the fresh
project the same frozen prompt goes to next (`ot7-heron` → `ot7-heron-b`,
`ot7-heron-repair` → `ot7-heron-repair-b`). The receipt also carries
`slots_spent` and `void_calls`. The runner still refuses an existing project,
so the retry is never a resume: a design whose continuation went void is
retried from its create prompt in the fresh project, and the completed turns
before the void stay in the earlier project's receipt as that attempt's
evidence. Dispatch the retry only while the product agent's harness is
available; the runner cannot see the window, so that rule is the operator's.

`run.py --classify TRANSCRIPT [ENVELOPE] [STDERR]` applies the same rule to a
retained call without dispatching anything; siblings named `turn.stdout.json`
and `turn.stderr.txt` are found automatically. The six pre-restart calls,
classified that way, are in [`attempts/void-calls.json`](../attempts/void-calls.json):
the two hand-copied F4 transcripts carry only the synthetic assistant frame
and the envelope text, the other four carry all three stream frames, and none
was cut off mid-turn. The fixtures in `cli/tests/test_ot7_runner.py` pin a
void create, a void mid-turn continuation with exit code 0, a void repair that
leaves the seed untouched, both transcript shapes and the text-only shapes, a
near-limit warning that is *not* void, an unrelated provider error that is
still `interrupted`, a synthetic `authentication_failed` frame that spends
its slot (a `<synthetic>` model name alone is never limit evidence), the
retry naming, and the six-call receipt.

## Unreached calls (ADR-386)

A third way a frozen prompt fails to be sent, and the only one that is local:
the CLI refused before a provider session existed, so the child wrote no
provider stream at all. F6's first continuation on `ot7-robin-c` is the
case — `open_project`'s restore pass refused in six seconds because the
accepted design does not rebuild byte-identically
([`DIGEST-DRIFT.md`](../DIGEST-DRIFT.md)) — and before this rule it fell
through to "a provider error the call returned on its own" and spent a slot
the model never saw.

A turn is `unreached` when its child exited nonzero for neither of the other
two reasons, `transcript.jsonl` holds no frames, and `turn.stdout.json` carries
an error with an empty `session_id`. Both halves are required, so a synthetic
`authentication_failed` frame (a stream) stays failed, a crash after the model
spoke stays failed, and a call with no envelope stays failed.

What follows differs from a void or interrupted call: nothing is consumed and
**no fresh project is named**. The row is `unreached` with `slot_consumed`
false, `unreached_calls` counts it apart from the other two, the measurement is
still read and hashed, no smoke runs, and the receipt's status is `paused` with
a `blocked` block naming the refusal. `remaining()` skips unreached rows
entirely, so the same prompt is still next in the same project; `resume`
re-sends it into a `turn-N-retry-M` directory, leaving the refusal's evidence
where it is. `run.py --classify` reports `unreached` beside `void` and
`interruption`.

`run.py reclassify PROJECT` corrects a receipt written before this rule by
re-reading each retained turn's own stream and envelope. It can only demote a
row the evidence proves never reached the model, and it keeps the superseded
receipt as `attempt.superseded*.json` beside the corrected one. Applied to
`ot7-robin-c` it returned that design to one completed create turn with three
continuations unspent; the committed receipt is
[`attempts/robin-c-unreached.json`](../attempts/robin-c-unreached.json).

## Interrupted calls (decision #44, ADR-356)

A call the runner killed at its 30-minute bound did not end on its own, so
under the charter it is not a turn. The critic ruled this for the iteration
44 call (decision #44): an **interrupted execution**, zero frozen-prompt
slots consumed, recorded apart from provider-limit void calls. The runner
applies that rule itself, after the void check: a turn whose child exited
`timeout` or `launch_failed` carries an `interruption` block (`kind`,
`bound_seconds`, `elapsed_seconds`, `model_messages_before_kill`), its row is
`interrupted` with `slot_consumed` false and `continuations_used` unchanged,
the receipt's `interrupted_calls` counts it apart from `void_calls` and
`slots_spent`, the measurement is still read and hashed, no smoke runs, and
the receipt's `retry` names the fresh project the same frozen prompt goes to
next, exactly as for a void call. A limit that landed before the kill is
void, not interrupted. `run.py --classify` reports `interruption` too, from
the exit code in the sibling `attempt.json`.

The bound stays at 30 minutes. What changed beside the accounting is the
turn itself: since ADR-356 the CLI launches every turn at an explicit effort
level (`high`, or `$CADEX_EFFORT`) and passes the harness its documented
per-message output cap (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`, 32,000 by default,
or `$CADEX_MAX_OUTPUT_TOKENS`), which caps thinking and text together. On
Fable models the harness documents that its fixed `MAX_THINKING_TOKENS`
budget has no effect, so this is the only hard per-message bound available;
the effort level is the documented soft control. Neither touches a frozen
prompt.

## Seeded repair (F4)

Iteration 25 added `repair` while the documented reset was still ahead
(18:02 New York time; ADR-354). No provider call was made in that unit.
After the reset, collect the frozen repair call on the preserved seed:

```bash
pixi run python docs/probes/ot7/runner/run.py repair \
  "$PROJECTS/ot7-heron-repair" --model claude-fable-5
```

This mode requires an existing seed. It checks the script hash and first
accepted revision against the original refusal receipt, the preserved accepted
digest, working revision, and empty parameter/board/cage/mount/net overrides.
It neither copies nor writes a design. It exclusively creates
`evidence/f4-repair/`; an existing directory refuses redispatch, including an
interrupted call. A void repair call (ADR-355) leaves that directory as its
receipt and is retried on a fresh copy of the seed, `ot7-heron-repair-b`; an
interrupted one (ADR-356) likewise, on the next copy, `ot7-heron-repair-c`.
Earlier void calls remain in their original evidence directories and are
listed in the final accounting apart from the design's attempts.

The runner first reads all accepted clearance pages with `restore=False`,
retaining `before/clearance.json`, `before/fit.json` and their hashes. A failed
read, missing report or changed script/metadata stops before any provider call.
It then dispatches only `repair.prompt.txt`, without `--resume`, under the same
30-minute bound and automatic-follow-up guard as design attempts. It records
the repair slot as spent only when the call ends on its own, the provider
stream, elapsed time, after-fit report and before/after accepted metadata and
script hashes. The before artifacts are
relative to `before/`, and turn artifacts to `turn-0/`, within `f4-repair/`.
A refusal still retains after measurements. No smoke is run for F4; the three
frozen continuations follow through `resume`, one per invocation (ADR-357,
below). Missing evidence never means passing fit, and CLI exit status
alone does not establish a completed design turn or a successful repair.

Known-answer fixtures preserve a seed through collection, supply seven before
failures and zero after failures, verify the sole frozen prompt and fresh
session, reject changed seed identity, and stop on missing/failed/mutating
before reads. They prove collection behavior only; F4's actual repair remains
open until a product-agent turn supplies the measurements.

Iteration 27 additionally exercises `child_measure` through the real paginated
inspect reader and product fit summary. A known-answer fixture places an
overlap and missed contact on a later page, plus a world-plane failure, and
requires all three findings and their exact numbers in `fit.json`. It checks
that nested swept extrema, first-contact angle, incomplete coverage and runtime
survive unchanged in `clearance.json`, along with catalog inventory. An error
on the later page must raise without writing a partial fit report. The session
must use `restore=False` and issue only inspect requests. These are synthetic
collector tests, not measurements of Heron or an F4 repair result. The provider
reset was still ahead at 18:17 New York time; no provider call was made.

Iteration 28 adds a nested-pagination fixture: the swept joint array has two
pages, and the joint on its later page has a two-page pair array. Only the last
pair page carries the worst overlap (12 mm³) and first contact (30 degrees).
The real collector must preserve both joint rows, both pair rows, their exact
extrema and timings in `clearance.json`. This is synthetic collection evidence,
not a design result. At 18:29 New York time the reset remained ahead, so this
unit made no provider call.

## Real preserved-seed measurement (iteration 29)

The real `--child-measure` process now has an integration receipt:
[`repair-measurement.json`](../retained/repair-measurement.json). It read
`ot7-heron-repair` with `restore=False`, exited zero in 0.164 seconds, and
preserved both the script identity and the complete metadata bytes. The
project-local files are under `evidence/iteration29-measurement/`; the receipt
lists every artifact's size and SHA-256. Assertions verified those hashes,
105 distinct pairs, 15 inventory components, and the same accepted revision
in the clearance, fit and inventory reports.

The measured baseline has **15 failing entries**: eight intersecting pairs,
six below-clearance pairs, and one world-geometry failure on `comp_base`.
The shoulder servo overlaps its base by 248.20162986795066 mm³. The shoulder
horn is 0.19999999999999732 mm from the upper arm; the elbow horn is
0.19999999999993 mm from the forearm. These gaps are present in the collected
measurements but do not fail the default 0.1 mm clearance rule: this old seed
declares no contact intent. A zero-failure summary alone therefore cannot
establish that the repair resolved those disconnected attachments.

Swept coverage is explicitly unavailable on this accepted revision. This read
does not rebuild geometry, measure new poses, or prove real swept pagination.
It establishes integration with the retained published measurements. At
18:40 America/New_York the documented 20:20 provider reset was still ahead;
no provider call or design edit occurred, and `evidence/f4-repair/` remains
unconsumed. After reset, use the repair command above and compare its guarded
before-read with this retained baseline; dispatch only the frozen repair
prompt. F4 remains open, and earlier refusals remain part of its accounting.

## Repair geometry assessment (iteration 31)

The repair collector now writes and hashes `repair-assessment.json` alongside
both the before and after measurements. It recomputes the product static fit
from `clearance.json` and additionally requires contact for the original
`comp_horn_shoulder` / `comp_upper_arm` and `comp_horn_elbow` / `comp_forearm`
pairs, regardless of their declared intent. Contact uses the product's
0.001 mm distance tolerance and 0.000001 mm³ overlap tolerance. The report
retains each distance, common volume and reason. This is evidence assessment;
it does not add contact declarations to the design or alter the prompt.

A passing geometry assessment requires passing static fit and both attachments.
Missing, duplicate, renamed or replaced pairs, failed measurement reads,
unavailable reports, missing world-geometry evidence, or a revision differing
from the accepted metadata cannot pass. Those attachments are **unknown**;
any known failure still makes the overall result fail. Renamed or redesigned
attachments need separate evidence connecting them to the original function;
the collector does not guess that mapping. A pass assesses the static geometry
only, not whether the provider completed a repair, nor swept fit.

Fixtures cover a zero-failure summary with both original 0.2 mm gaps, actual
contact, world geometry, 248.2 mm³ servo overlap, missing evidence, and failed
reads. The collected assessment and its digest are pinned in the repair-run
fixture. At 18:45 New York time the documented reset was still ahead; this
unit made no provider call and left the seed and frozen prompts untouched.
F4 still needs its real frozen repair turn and before/after evidence.

## The fresh-copy repair dispatch (iteration 44)

The first repair call that reached a model ran on `ot7-heron-repair-b`, a
copy of the seed without its `evidence/`, `agent.json` or CLI lock, made by
the operator role and validated by `validate_seed` before dispatch. The
outcome is in [`repair-timeout-b.json`](../retained/repair-timeout-b.json):
the turn was killed at the 30-minute bound with no submission, the after-read
matched the before-read exactly, and the runner of that day reported
`interrupted` with the slot consumed. **Decision #44 (the critic, iteration
44) ruled otherwise: an interrupted execution, zero frozen-prompt slots
consumed, recorded apart from void calls.** The receipt keeps its
`slot_consumed: true`, `slots_spent: 1` and `continuations_used: 1` as the
collector's historical output under the superseded rule, with a `ruling`
field saying so; the design's repair prompt and all three continuations are
unspent, and the retry is `ot7-heron-repair-c`. Two collector limits showed
up in that call, and iteration 46 fixed both:

- **A killed turn lost the stream.** `CapturedTurn` wrote `transcript.jsonl`
  only after the turn returned, so the kill left no transcript and an empty
  envelope; the provider stream was recovered from the harness's own session
  store, and the receipt names it as recovered, with its digest. The
  collector now writes each frame as it arrives, and a fixture kills a fake
  provider mid-stream and finds every frame it had sent.
- **The turn had a wall-clock bound but the model had no per-message bound.**
  One message of 63,999 thinking tokens took 16.5 minutes of the 30. The CLI
  now pins the effort level and passes the harness's documented per-message
  output cap (ADR-356, above).

## The void call on c and the completed turn on d (iteration 48)

Both ran under the collector as amended above. `ot7-heron-repair-c` was
dispatched into a window the first `rate_limit_event` frame showed at 95 %,
and the session limit cut it off after six reads: the runner classified it
void, spent no slot, kept the whole stream, and named `ot7-heron-repair-d`.
That copy, dispatched after the reset, is the first repair call to end on
its own: a completed turn of 1,461.9 s (the receipt's `status: exhausted`,
`slots_spent: 1` and `continuations_used: 1` are the collector's output under
the superseded one-slot repair rule, ADR-357 below), after-read static fit
0 of 120 failing,
sweep complete, attachment assessment still failing on both horn-to-link
pairs. The receipts are
[`repair-void-c.json`](../retained/repair-void-c.json) and
[`repair-completed-d.json`](../retained/repair-completed-d.json). Two
operator lessons the runner cannot enforce: an answering probe says nothing
about the window, so read the first `rate_limit_event` frame instead; and
one completed repair turn moved the five-hour window from 8 % to 57 %, so a
create-plus-three-continuations schedule for F5–F7 will not fit in one
window alongside the actor.

## Resuming after a completed turn (iteration 49, ADR-357)

The collector of iteration 48 carried the repair prompt as F4's whole
schedule and wrote `status: exhausted` after the one turn on
`ot7-heron-repair-d`. The amended charter (ADR-355) says otherwise: a design
is exhausted only after "its create or repair prompt and all three
continuations have reached the model", so the repair prompt is F4's first
prompt, not a continuation, and three continuations remain. The critic of
iteration 48 ruled the same. Three things changed, none of them a prompt byte
(`frozen()` still verifies every digest against the manifest):

- **The schedule.** `frozen('repair')` is `repair.prompt.txt` followed by
  `continue-1`, `continue-2` and `continue-3`, the same three as every
  design. The first prompt of any schedule counts no continuation, so a
  completed repair row now reads `continuations_used: 0`.
- **One turn per window.** A completed turn uses about half a five-hour
  window, so `run.py repair` dispatches the repair prompt alone and pauses
  (`status: paused`, with a `remaining` block naming the next prompt), and
  `run.py resume PROJECT` dispatches exactly the next continuation, with
  `--resume` into the agent's own session, without replaying anything that
  came before. `--turns N` sets how many prompts either command dispatches;
  a design attempt still dispatches all four by default. `run.py remaining
  PROJECT` only reads the schedule. The smoke runs when a design attempt
  exhausts or fails, whichever invocation gets there.
- **What `resume` refuses.** A project closed by a void, interrupted or
  failed call (those retry on a fresh copy, as before); an exhausted one; a
  project with no attempt; and a project whose script or metadata differ
  from the snapshot the last turn took (`accepted_after`, now on every row),
  because the actor never edits a design. A receipt written under the old
  rule, `exhausted` with fewer than four completed rows, resumes and gains a
  `ruling` field saying so; its historical `continuations_used` value is
  kept as written, and the schedule is read from the rows.

On `ot7-heron-repair-d`, `remaining` reads: 1 completed, 0 continuations
used, 3 unspent, next `continue-1.prompt.txt`, not closed. Fixtures in
`cli/tests/test_ot7_runner.py` pin a repair that pauses with three
continuations and resumes through all three without replaying the repair
prompt, the legacy `exhausted` receipt resuming with its ruling, the three
refusals, a create paused per window and resumed to its smoke, and that a
continuation child passes `--resume`. The continuations are dispatched only
while the product agent is available, which a `rate_limit_event` frame
decides, not the fact that a probe answered: at 74 % of the window a turn
of the observed size does not fit. Iteration 51 resumed `continue-1` on that project two
minutes after the reset, at 8 %; the turn completed on its own in 738.5 s,
took the window to 63 %, and the runner paused with `continue-2` next
([receipt](../retained/repair-continue-1-d.json)).

## Reading the window before every prompt (iteration 52, ADR-358)

Until iteration 51 the dispatch decision was the operator's: read the first
`rate_limit_event` frame of a one-word turn, compare it with what one
completed turn costs, and only then run the collector. The void call on
`ot7-heron-repair-c` is what that costs when it is skipped: an answering probe
was taken as room, the window stood at 95 %, and the model was cut off after
six reads. The runner now does the reading itself, and keeps it:

- **A probe before every frozen prompt.** `dispatch()` runs a one-word
  `claude -p` turn with no project, no MCP server and no tools (so it is not
  a product-agent call and spends no slot), parses the first
  `rate_limit_event` frame (`unifiedWindows.five_hour.utilization`, or the
  older flat `utilization` on a `five_hour` frame), and appends the reading to
  the receipt's `window_readings` with the prompt it was read for, the bound,
  the time and whether the prompt was sent. The probe's stream is kept under
  `evidence/window/`. A dispatched row carries its reading as `window`, so a
  receipt says at what utilization each turn started.
- **No room, nothing sent.** Room is a frame the provider allowed, read at or
  under `--window-bound` (default 45 %, from the two measured turns: 8 → 57 %
  and 8 → 63 %). Above it, a rejected frame, no frame, or no `claude` binary,
  the runner writes `status: paused` with a `deferred` block naming the prompt
  and the reset time, and stops before the slot is persisted or the turn
  directory exists, so `resume` picks the same prompt up after the reset. A
  whole-schedule design dispatch therefore pauses by itself at the first
  prompt that no longer fits. `run.py window` only reads and prints the
  reading.
- **Fixtures read nothing.** The function default (`window_bound=None`)
  skips the probe so the provider-faking fixtures stay hermetic; the command
  line always passes a bound.

Fixtures in `cli/tests/test_ot7_runner.py` pin the real probe frame of
2026-09-15 15:45 UTC (84 %, no room) against 8 % (room), the parse of both
frame shapes, a create deferred on each no-room shape and resumed from its
create prompt after the reset, a schedule that pauses mid-way when the window
fills, a repair that measures the seed and sends nothing, and that the
default reads no window. On the live account at 15:49 UTC `run.py window`
read 93 % (`allowed_warning`, reset 20:20 UTC): no room, nothing dispatched,
`continue-2` still next on `ot7-heron-repair-d`.

The gate's first live dispatch was `continue-2` on `ot7-heron-repair-d` at
20:23 UTC, three minutes after the reset: the probe read 6 % (`allowed`) and
the prompt was sent; the receipt's row carries that reading and
`window_readings` holds it with the time and the bound. The turn completed in
128.7 s and the runner paused with `continue-3` next
([receipt](../retained/repair-continue-2-d.json)).

Its second was `continue-3` on the same project at 20:34 UTC, in the same
window: the probe read 44 %, one point under the bound, and dispatched. The
turn completed in 104.9 s, reading only, and moved the window from 46 % to
48 %; the runner wrote `status: exhausted` with `slots_spent: 4` and
`next_prompt: null`, so `resume` on this project now refuses with
"exhausted" ([receipt](../retained/repair-continue-3-d.json)).

## The first create call, interrupted (iteration 55)

`run.py heron … --turns 1` on the fresh project `ot7-heron-b` is the first
design-attempt dispatch under the gate: probe 13 %, dispatched at 21:28 UTC,
killed at the 30-minute bound with no design written
([receipt](../retained/heron-interrupted-b.json)). The runner classified it
`interrupted`, spent no slot and named `ot7-heron-c`; the receipt's
`interruption_analysis` has the timeline. Two collector facts the call
exposed, neither of them a runner defect:

- **`describe_api` did not fit the harness's tool-result cap.** Its
  163,200-character reply was refused and written to a file the product
  agent has no tool to read (`Grep`, `Read`, `Bash` and `Agent` are disabled
  in that session), so the agent paged the contract through 44
  `inspect scope=api` reads instead, in 3 min 35 s. Fixed in iteration 56
  (ADR-359, below): the bridge's view keeps every signature and the first
  paragraph of each description, under a 90,000-character budget a
  live-engine test holds.
- **The 32,000-token output cap does not bound a turn's thinking.** Three
  consecutive thinking-only messages each hit the cap and were auto-resumed
  by the harness ("Output token limit hit. Resume directly…"), 24 minutes in
  all; the cap converts one long thought into several. The effort level is
  the documented soft control (`CADEX_EFFORT`, ADR-356), and a lower one is
  the reversible change to try before the retry; that is a recorded decision,
  not a prompt change.

## Effort for the retry, and the contract that fits (iteration 56, ADR-359)

Two reversible tooling changes before `ot7-heron-c`, neither touching a
frozen prompt byte or a design:

- **Every turn of an attempt is launched at `medium` effort.** The CLI's
  own default stays `high` (ADR-356); the collector passes
  `--child-turn --effort <level>` to each child, which sets `CADEX_EFFORT`
  before the CLI starts, and records the effective settings in the receipt
  (`settings`: `effort`, `max_output_tokens`, `turn_bound_seconds`) and on
  every row. `run.py <design> --effort LEVEL` overrides it for a new
  attempt; `resume` reuses what the receipt records, so an attempt cannot
  change level between its turns. A receipt written before this field
  existed resumes at `high`, which is what its turns ran at. The 32,000-token
  output cap and the 30-minute bound are unchanged. The reason is the
  iteration 55 timeline: at `high`, a create turn spent 24 of its 30 minutes
  in three thinking-only messages that each hit the cap, and the effort
  level is the documented soft control on that.
- **`describe_api` now fits under the bridge's budget, and measured on
  `ot7-heron-c` (iteration 57, below) it still does not fit the harness.**
  The bridge trims each export's description to its first paragraph and
  says where the rest is (`docs/CLI.md`); the 82,523-character reply was
  refused, and the agent paged the contract in 2 min 40 s instead of 3 min
  51 s.

Dispatch, after the 02:20 UTC reset and only when `run.py window` reads
room:

```bash
pixi run python docs/probes/ot7/runner/run.py heron \
  "$PROJECTS/ot7-heron-c" --model claude-fable-5 --turns 1
```

Fixtures in `cli/tests/test_ot7_runner.py` pin the recorded setting on the
receipt and every row, the flag on the child command, the resume reusing
the receipt's level, the legacy receipt at `high`, and the child setting
`CADEX_EFFORT` before the CLI starts.

## The create turn that completed (iteration 57)

```bash
pixi run python docs/probes/ot7/runner/run.py heron \
  "$PROJECTS/ot7-heron-c" --model claude-fable-5 --turns 1
```

Dispatched at 02:22:53 UTC with the probe at 5 %, at `medium`. The turn
ended on its own in 1,530.4 s: 123 model messages, 35 thinking blocks, no
output-cap hit, 82 tool calls, three accepted design revisions, the last
`512c157c…` with static fit 7 of 120 failing, the sweep unavailable (no
`sweep_step_degrees` declared), and the slot spent. The receipt is
`retained/heron-create-c.json`; the assessment is REPORT.md's iteration 57
section. The window read 64 % afterwards, so the schedule's next prompt
waits for the 07:20 UTC reset:

```bash
pixi run python docs/probes/ot7/runner/run.py resume "$PROJECTS/ot7-heron-c"
```

Two facts the turn measured about the tooling, neither a change this
iteration made:

- **`describe_api` at 82,523 characters is still refused** by the harness
  ("exceeds maximum allowed tokens"), and the largest tool result it
  accepted in the turn was 20,717 characters. The cap is somewhere between
  those two numbers; ADR-359's 90,000-character budget does not reach it,
  and a further cut is a separate recorded decision — made in iteration
  60 as ADR-360, below. The agent recovered by
  paging `inspect scope=api`, as in iteration 55, in less time.
- **`medium` fits the bound.** One thinking message of about 30,000
  estimated tokens ended on its own; iteration 55's three cap-limited
  messages did not recur.

## The first continuation completed (iteration 59)

```bash
pixi run python docs/probes/ot7/runner/run.py resume "$PROJECTS/ot7-heron-c"
```

Dispatched at 07:22:36 UTC, two minutes after the reset, with the probe at
5 %, into the create turn's own session at the receipt's `medium`. The turn
ended on its own in 610.6 s: 41 model messages, 18 thinking blocks, no
output-cap hit, 19 tool calls (13 `inspect`, ten of them the clearance
scope, and 6 `edit_script`, two accepted). The first continuation slot is
spent; two remain, and the runner paused with `continue-2` next. The
receipt is `retained/heron-continue-1-c.json`; the assessment is
REPORT.md's iteration 59 section. Five minutes passed between the dispatch
and the first stream frame, which is the end of the first message; the
first read came one second later.

The measured result: static fit **1 of 120 failing**, the bench's world
geometry row, with zero intersections and zero below-clearance pairs; the
sweep **complete on both joints at 5°** with 0 mm³ on every pair; the
inventory unchanged, servos and horns still uncatalogued. The smoke was run
by the actor after the turn with the runner's own command into
`evidence/turn-1/smoke`, as the runner does at exhaustion, and passed. The
window read 35 % at the last stream frame and 38 % after the measurement,
under the 45 % bound, so `continue-2` is dispatchable before the 12:20 UTC
reset.

## The second continuation completed (iteration 66)

```bash
pixi run python docs/probes/ot7/runner/run.py resume "$PROJECTS/ot7-heron-c"
```

Dispatched at 12:22:51 UTC, three minutes after the reset, with the probe
at 7 %, into the same session at the receipt's `medium`. The turn ended on
its own in 482.4 s: 36 model messages, 12 thinking blocks, no output-cap
hit, 19 tool calls (13 `inspect`, eleven of them the clearance scope, 4
`edit_script` with two accepted, 1 `write_script` rejected, 1 `rebuild`).
The second continuation slot is spent; one remains, and the runner paused
with `continue-3` next. The receipt is `retained/heron-continue-2-c.json`;
the assessment is REPORT.md's iteration 66 section. One minute passed
between the dispatch and the first stream frame.

The measured result: the bench deleted from the model in two accepted
revisions, static fit **0 of 105 failing** with `world_geometry` empty; the
sweep **complete on both joints at 5°** with 0 mm³ on every pair; the
inventory still listing both servos and both horns as uncatalogued. The
smoke was run by the actor after the turn with the runner's own command
into `evidence/turn-2/smoke` and passed. The window read 50 % at the last
stream frame and 56 % after the measurement, over the 45 % bound, so
`continue-3` waits for the 17:20 UTC reset. The stream's `rate_limit_event`
frames also carried the seven-day window at 90–94 % as `allowed_warning`;
the runner's bound reads only the five-hour figure.

## The last continuation completed, and F5 exhausted (iteration 72)

```bash
pixi run python docs/probes/ot7/runner/run.py resume "$PROJECTS/ot7-heron-c"
```

Dispatched at 13:51:42 UTC with the probe at 7 %, at `medium`, into the
same session; the first dispatch after the owner refreshed the account
(ADR-361), which moved the five-hour reset from 17:20 to 18:50 UTC and
left the seven-day window at 0 %. The turn ended on its own in 142.9 s:
12 model messages, 5 thinking blocks, no output-cap hit, 6 tool calls
(5 `inspect`, all the clearance scope, 1 `rebuild`), no edit. The third
continuation slot is spent and the runner wrote `status: exhausted`,
`slots_spent: 4`, `next_prompt: null`, then ran its own smoke into
`evidence/smoke` (exit 0, 14.6 s, verdict pass). `resume` on this project
now refuses with "exhausted". The receipt is
`retained/heron-continue-3-c.json`; the assessment is REPORT.md's iteration
72 section.

The measured result: the design byte-identical to the end of continue-2,
re-accepted at the same revision and digest; static fit **0 of 105
failing**, `world_geometry` empty; the sweep **complete on both joints at
5°** with 0 mm³ on every pair; the inventory still listing both servos and
both horns as uncatalogued while the closing message calls all twelve
purchased parts catalog parts. F5 is exhausted with that result: every
count of its bar met except catalog hardware for every purchased part. The
window read 38 % at the last stream frame and 41 % after the measurement,
so the next design turn, F6's create on `ot7-robin-b`, waits for the 18:50
UTC reset.

## The window closed, and describe_api paged (iteration 60, ADR-360)

No design turn. The probe read 52 % at 07:40 UTC, above the 45 % bound
(reset 12:20 UTC), so `continue-2` was not dispatched: `ot7-heron-c` still
has two continuations unspent and `continue-2` next through `resume`. The
window rose from 38 % because the actor's own iterations spend it.

The tooling unit the limited window permitted is ADR-360, the cut this
README's iteration 57 section said was a separate decision. `describe_api`
now reaches the model as an **index** (every export by name, no
signature) and, with the bridge's own `section=<domain>` or
`section=library` argument, one **section** at a time (notes, every
signature, first-paragraph descriptions, the whole catalog for the
library). The budget is the measurement the two ot7-heron-c transcripts
give — every accepted result at most 21,742 characters, 82,523 refused —
so `API_VIEW_CHAR_BUDGET` is 21,500 and a live-engine test holds every
page under it: the index at 13,239 characters and the largest section,
assembly, at 20,502 on 2026-09-16. The engine op, the protocol and the
frozen prompts are untouched; the CLI's system prompt now says to read
the index and then the section of every domain used. Whether every page
is accepted is what `continue-2`'s transcript measures next: under this
budget no page exceeds a size the harness has accepted.

## The probe's own refusal is the reading (iteration 77, ADR-364)

No design turn. F6's create on `ot7-robin-b` was blocked, and the gate that
blocked it was reading the wrong number.

At 14:29 UTC the probe on `claude-fable-5` came back **refused in 2.369 s**
with the five-hour window at **1 %**. The binding limit was not the five-hour
one at all: `seven_day` stood at 51 % and `seven_day_overage_included` at
100 %, with `overageDisabledReason: org_level_disabled`, and the provider's
own words were "You've reached your Fable limit. Switch to another model."
The receipt is [`f6-window-refusal.json`](../attempts/f6-window-refusal.json).

The gate returned no room, but only by accident. It reads two things — the
frame's top-level `status` and `unifiedWindows.five_hour` — and on that probe
`status` happened to carry the *overage* rejection. Nothing made that so, and
**it did not repeat**: the next probe, on the same account twenty minutes
later, returned `status: allowed`, `rateLimitType: five_hour`, five-hour at
**2 %** — and was refused just the same, in 2.069 s, with the same Fable
message. The pre-ADR-364 gate reads that frame as room and sends the prompt.
Both probes are in the receipt.

The fixture in `cli/tests/test_ot7_runner.py` runs that frame against the old
gate, and the old code dispatches Robin's create prompt **and all three
continuations** into a model the provider will not run.

**Corrected in iteration 78.** That fixture's design calls are the suite's
ordinary mocked-successful ones, so the four spent slots it ends with are the
fixtures answering — not the provider, and not a measured loss. This file and
ADR-364 first wrote them up as the cost of the old gate; they are not.
ADR-355 is underneath it, and a refused design call is void. Measured against
the same Fable frames — `test_a_room_reading_before_a_refused_model_costs_one_void_dispatch`,
where the probe reads ordinary room and every design call is refused — the old
gate costs **one** dispatch, its receipt and a burned project name: the attempt
goes void on turn 0, `slots_spent` stays 0, and the retry moves to
`ot7-robin-c` with all four frozen slots intact. The gate below is the earlier
of two guards, not the only one. It still earns its place — it spends no
provider call, keeps the frozen prompt in the project the report names, and
turns a refusal into a pause instead of a chain of suffixed retry projects.

So the probe is now read as what it is — a real model call on the product
agent's model:

- **A refused probe is no room, whatever the window says.** Its stream is
  classified by `void_reason`, the same ADR-355 rule a design call's stream
  gets, and `window_has_room` returns false on any refusal before it looks at
  a number. The five-hour percentage is a forecast of what a turn will cost;
  the probe's own outcome is a measurement of whether one can start.
- **The reading names which window is full and which limit refused.** Every
  `unifiedWindows` entry is kept as a percentage, beside `rate_limit_type`
  and the refusal. A receipt saying `five_hour 1 %, no room` is unreadable;
  `seven_day_overage_included 100 %, org_level_disabled` is a reason.
- **On a refused probe, the frame that rejected is the reading** (ADR-369).
  A stream carries several `rate_limit_event` frames and their order is the
  provider's: at 14:29 UTC on 2026-09-16 the rejected frame came first, and
  at 17:02 UTC the same account put an allowed five-hour frame in front of
  it. Reading the first frame alone reported `five_hour, allowed, resets
  19:20Z` on a call the seven-day overage window refused, and dropped the
  100 % that was the reason. The chosen frame is authoritative for every
  window it names and the others fill in the names it omits, so the full
  window that refused reaches the receipt either way. `resets_at` is the
  reset of the window `rate_limit_type` names, and on a refusal
  `resets_at_is` says so in words — it is the schedule of a usage window and
  dates nothing about the account or organisation setting that refused, in
  either direction.
- **A probe that answered is never a refusal.** An organisation with overage
  disabled emits a rejected `seven_day_overage_included` frame beside an
  ordinary allowed window; on a call that reached the model and returned its
  own answer that means "no overage is available", not "no room". Reading it
  as a refusal would strand every remaining frozen prompt, so the classifier
  runs only on a probe that did not answer.

The bound, the probe text, the one-probe-per-prompt schedule and the pause
behaviour are unchanged, and an ordinary allowed probe still passes the gate.

**F6's four slots are unspent and no `ot7-robin-b` exists.** The product
agent's model stays `claude-fable-5`: ADR-363 moved the Ouroboros roles to
`claude-opus-5` and deliberately left the experiment's model alone, so F6 and
F7 remain comparable with F5, which ran on Fable. Until that account's Fable
capacity returns, F6 cannot be dispatched by any reading of the five-hour
window, and the charter's answer is the unblocked tooling unit — this one.

## The stray frame in front (iteration 106, ADR-376)

No design turn: the 21:37 UTC probe was refused outright again
(`seven_day_overage_included` 100 %, `org_level_disabled`, five-hour 11 %),
which the ADR-364 rule above reads as no room. The unit is the other half of
ADR-369, found by reading the gate that will decide F6's dispatch when
capacity returns.

ADR-369 fixed the refused direction — read the frame that rejected, not
whichever arrived first, because frame order is the provider's and this
account produced both orders twenty minutes apart. The **answered** direction
kept reading `infos[0]`. That is the same stray rejected
`seven_day_overage_included` frame ADR-364 named and deliberately excluded
from `refused`, so that an organisation with overage disabled could not have
its gate closed for good — and it was still the frame supplying `status`
whenever the provider sent it first.

Reproduced with one answered probe, five-hour at 8 %, two `rate_limit_event`
frames and nothing else changed:

| frame order | `refused` | `status` | five-hour | gate |
|---|---|---|---:|---|
| allowed, rejected | none | `allowed` | 8 % | dispatch |
| rejected, allowed | none | `rejected` | 8 % | **defer** |

Same account, same answer, same numbers. The deferral is not a delay of one
probe: it repeats for as long as overage stays disabled, so it withholds F6's
and F7's eight frozen prompts from a model that would have answered, under a
`deferred` block citing an overage window's reset as the reason.

**The reading's frame is now the frame that bound the call, in both
directions**: the one that rejected on a refused probe, the one that allowed
on an answered one. A probe with no frame of the kind it needs falls back to
the first, which is conservative both ways — an answered probe carrying only
rejected frames still reads `rejected` and still does not dispatch. Window
merging is unchanged, so a window at 100 % that is simply unavailable is still
named in the receipt by the frame that named it.

`test_an_answered_probe_reads_the_frame_that_allowed_it_whatever_the_order`
sends both orders and requires one reading;
`test_a_stray_rejected_frame_in_front_still_dispatches_the_frozen_prompt`
pins the schedule-level cost — the old reading pauses Robin's create with four
unspent slots, the new one dispatches all four. Both are red on the old code.
The two existing stray-frame tests keep the allowed frame in front, passed
throughout, and never covered the order that fails.

F6's and F7's eight slots remain unspent; no `ot7-robin-b` exists.

## Fable restored: the interrupted b and the completed create on c (iteration 148, ADR-383)

The owner restored Fable access on 2026-09-17 and authorized the remaining
experiments (ADR-383, commit `bcfa6914`); the launch-time availability check
is `retained/fable-restart-availability.json` (14:45:54 UTC, `READY`,
five-hour 0 %).

**`ot7-robin-b` is an interrupted execution, not a spent slot.** At
14:54:01 UTC — fifty seconds after the restart's `ouroboros run` began and
two minutes before the loop's first actor iteration — a runner outside the
loop dispatched Robin's create prompt on `ot7-robin-b`. The model answered
(9 messages, 6 tool calls, every `rate_limit_event` allowed at 7–11 %), and
16.3 s in the stream stops: no result frame, an empty envelope, and the
runner died with its child before classifying anything, leaving
`attempt.json` at `running`/`started` with no exit code. `--classify` on the
retained transcript returns `void: null` (no limit anywhere in the stream)
and `interruption: null` (the rule reads an exit code a dead collector never
wrote). The charter's own rule decides it — only a turn that ended on its
own counts (ADR-355), and a call cut off by its collector is an interruption
(decision #44, ADR-356) — so zero slots are spent, the project's receipt
stays as the dead runner wrote it, and the committed ruling is
[`retained/robin-interrupted-b.json`](../retained/robin-interrupted-b.json).
The only accepted script it left is the product agent's own datasheet probe;
no design was written and no actor edited anything.

**The retry completed.** `run.py robin … --turns 1` on the fresh
`ot7-robin-c` at 14:58:53 UTC: probe 24 % allowed (the ADR-364/376 gate
passing on a real allowed frame), dispatched at `medium`. The turn ended on
its own in 1,676.4 s — result frame `success`, 35 API turns, 62 model
messages, 19 thinking blocks, no output-cap hit, 33 tool calls (4
`describe_api`, 6 `write_script`, 19 `inspect`, 4 `edit_script`) — and the
create slot is spent: `status: paused`, `slots_spent: 1`, three
continuations unspent, `continue-1` next through `resume`. The measured
result on accepted revision `192db5b9…`: static fit **0 of 276 failing**
(zero intersections, zero below-clearance, `world_geometry` empty,
attachments touching); the sweep **incomplete on both wheel joints**,
because neither `joint_wheel_l_axle` nor `joint_wheel_r_axle` declares
limits, so no range exists to sweep; the inventory carrying catalog rows for
every purchased part (2× `gearmotor/pololu-2367`, 1× `board/pi-zero-2-w`,
8× `heat_insert/m2-standard`, 8× `bolt/m2x4-socket`) with only the five
modelled printed parts uncatalogued. The stream's last frame read the
five-hour window at 74 %, so `continue-1` waits for the 19:40 UTC reset.
The assessment is REPORT.md's iteration 148 section.
