---
node_id: 99dc4b41-a495-557c-a23b-e6089352b78d
slug: soft-journey-2954
title: 'A refusal receipt dates nothing: the F6/F7 gate states present refusal only'
created_at: '2026-09-16T17:01:12+00:00'
parents:
- sage-isle-3511
summary: ''
---
## What

The lower-bound claim is gone from the closing report, and this record
supersedes it wherever `sage-isle-3511` planted it.

`docs/probes/ot7/REPORT.md`, commit `dbb03b59`:

- the gate subsection is retitled **The gate is shut now, and no clock says
  when it opens**, and opens by saying that neither schedule in it bounds the
  refusal in either direction;
- a new first bullet, *What the refusal establishes*, states the receipt's
  whole content: `claude-fable-5` was refused on this account, at the
  organisation level (`overage.disabled_reason: "org_level_disabled"`), **at
  the moment the probe was taken**. It does not date the end of that setting
  and does not put a floor under it — an organisation-level setting can change
  at any time, including before any window resets, as this account did once
  already when the owner refreshed it mid-run (ADR-361);
- the `resets_at` bullet keeps the epoch `1789740000` →
  **2026-09-18T14:00:00Z** with its provenance, and now calls it a scheduled
  reset of a usage window — **not** a lifting of the refusal and **not** the
  earliest the refusal could lift. A probe after it may be refused again; a
  probe before it may not be, which is what the second probe showed reading
  `status: allowed` at 2 % and being refused anyway;
- the arithmetic is preserved verbatim in its numbers — `stop.until`
  2026-09-17T04:25:13Z binding over `stop.after: 48h`, `stop.max_stuck: 25`
  able to end it sooner, the difference **33 h 34 m 47 s** — and re-framed as
  arithmetic between two schedules: the reset will not arrive inside this run,
  which is not the same as the refusal not lifting inside it;
- the conclusion drops "under the current limits and stop rules they will get
  none in this run" and its "expected rather than certain only in the
  direction that makes no difference" hedge. It now says dispatch is
  impossible *while the refusal holds*, that an iteration which probes and
  finds it gone may still dispatch, and that **if** the run ends with the
  refusal in force both designs end unattempted with all eight slots unspent —
  never exhausted;
- the lede and the "what finishing them takes" paragraph match: the latter is
  keyed to an unrefused probe "whenever that is, since no schedule here dates
  it".

Blocked statuses, the eight unspent slots, the void-call accounting and every
number are unchanged. No product code, no prompt, no probe, no slot, no run
lifecycle, no reconcile.

## Why

The critic rejected the previous iteration: the correction in
`sage-isle-3511` swapped a dated opening for a *lower bound*, and the lower
bound is the same unsupported inference one step weaker. A refusal receipt is
a present-tense measurement. `resets_at` belongs to a usage window; the
binding condition belongs to an account setting; nothing ties the second to
the first in either direction, so "cannot lift before 2026-09-18T14:00:00Z"
was never in evidence, and neither was "dispatch before ot7 ends is
impossible". This repo has the counterexample in its own report: the owner
refreshed the account mid-run and F5's `continue-3` went out.

I did what the critic's message asked and nothing else. F10 is the criterion
this serves — the report must claim nothing a record does not carry — and the
instruction after it is to hold. This record is the dispatch's mandatory one.

## Method

Read-only first: `docs/probes/ot7/attempts/f6-window-refusal.json` again for
the two probes (`rejected` / `org_level_disabled`, then `allowed` at 2 % and
refused anyway); `grep` over the record and state graphs and the docs for
every copy of the lower-bound wording, which found the subsection, the report
lede, the one internal anchor, and the three state nodes this record's impacts
target; `grep` over `cli/tests`, `src/Mod/cadex/cadex_tests` and the ot7 runner
for anything pinning the report's headings or the anchor — nothing, so the
retitle is safe.

Then one Python string-replacement edit over four passages of one file, each
asserting its old text matched before writing. Verified with the three suites
that read `docs/probes/ot7`: `cli/tests/test_ot7_runner.py`,
`test_retained_fit.py`, `test_ot7_prompts.py` — **85 passed in 0.69 s**. No
engine or packaged gate run: no engine, protocol or payload file was touched.

## Result

The report's account of the F6/F7 gate is now exactly as strong as its
receipts: a refusal measured at a moment, an account-level setting with no
dated end, a window reset scheduled for 2026-09-18T14:00:00Z that says
nothing about that setting, and a run configured to stop 33 h 34 m 47 s
earlier. F6 and F7 are blocked with all eight create and continuation slots
unspent; if the run ends with the refusal in force they end **unattempted,
never exhausted**, and no verdict or record may read that as "no authorised
experiment remaining".

`sage-isle-3511`'s State Impact is **superseded on all three targets**: its
"earliest the refusal could lift" / "bounds the refusal from below" reading is
withdrawn, and `first-snow-5587`'s "so F6 and F7 cannot be dispatched from
inside ot7" with it. Everything else those impacts carried stands.

For the next iteration: the charter's hold still applies — a design turn may
be dispatched only after an unrefused `run.py window --model claude-fable-5`,
and no schedule says when that becomes possible, so the only honest posture is
to probe cheaply when a unit is otherwise idle and work unblocked tooling,
tests or reconcile otherwise. The record tail is three deep and two of the
three nodes are this gate's corrections; a reconcile pass is the natural next
unit if the critic wants one. No new dependency, no code change, no open
concern beyond the block itself.

Dispatch closed: 1 unit — the closing report's gate subsection drops the lower-bound claim and now states present refusal only, with the deadline arithmetic, the blocked statuses and the eight unspent slots preserved.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: dbb03b59ef8b2b9a2df6da398d725f581af2a59e

## State Impact

- target: first-snow-5587 — Supersedes sage-isle-3511 on this target. REPORT.md's gate subsection (commit dbb03b59) is retitled 'The gate is shut now, and no clock says when it opens' and no longer bounds the refusal from below: the f6-window-refusal.json receipt establishes only that claude-fable-5 was refused on this account at the organisation level (overage.disabled_reason 'org_level_disabled') at the moment the probe was taken, and an account setting can change at any time, including before any window resets (ADR-361). WITHDRAWN: 'the earliest the refusal could lift', 'bounds the refusal from below', and 'so F6 and F7 cannot be dispatched from inside ot7'. PRESERVED: every number and its provenance — stop.until 2026-09-17T04:25:13Z binding over stop.after 48h, stop.max_stuck 25 able to end it sooner, the rejected window's resets_at 1789740000 = 2026-09-18T14:00:00Z, the 33 h 34 m 47 s difference — now stated as arithmetic between two schedules rather than a prediction about the refusal; F6 and F7 blocked with all eight slots unspent; unattempted-not-exhausted if the run ends with the refusal in force; no done claim. The three ot7 suites read 85 passed; no test pins the report's headings and the one internal anchor moved in the same edit.
- target: narrow-dune-9454 — Supersedes sage-isle-3511 on this target. The 2026-09-18T14:00:00Z epoch is a scheduled reset of the seven_day_overage_included window and is neither proof the org-level claude-fable-5 refusal lifts nor a floor under it; the receipt is present-tense evidence only, and the second probe reading status 'allowed' at 2 % and being refused anyway is the same lesson. WITHDRAWN: 'the earliest the block could lift' and 'F6 cannot be dispatched from inside ot7'. F6 stays blocked with all four create/continuation slots unspent and resumes on an unrefused run.py window probe, whenever that occurs — an iteration that probes and finds the refusal gone may dispatch inside this run. If the run ends with the refusal in force F6 ends unattempted, never exhausted. The stop arithmetic and its provenance are unchanged.
- target: rapid-grove-9687 — Supersedes sage-isle-3511 on this target, with the same correction behind F6: the 2026-09-18T14:00:00Z epoch is a scheduled window reset that bounds the org-level Fable refusal in neither direction, and the refusal receipt establishes present refusal only. WITHDRAWN: the 'earliest the refusal could lift' reading and any claim that dispatch before ot7's stop is impossible. F7 stays blocked behind F6 with all four slots unspent, its frozen plover.create.prompt.txt (b95f98b7…) and three continuations available; unattempted rather than exhausted if the run ends with the refusal in force.
