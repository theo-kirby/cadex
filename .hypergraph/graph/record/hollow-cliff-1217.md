---
node_id: ee913cc7-cb23-5334-a42f-60387a360fa1
slug: hollow-cliff-1217
title: 'Bet: iterate on the third mechanism token-free, then bound the walk''s unbounded legs'
created_at: '2026-09-08T19:04:46+00:00'
parents:
- chilly-crest-2100
summary: ''
---
## What

The rung's first two units landed, in the order the last bet set them:
a third mechanism through the unchanged `cadex walk --prompt` (ADR-259's
travel eye and ADR-256's documentation eye both reporting on a real design
turn for the first time) and the walk row's delta plumbing (ADR-260). The
rung is re-ranked onto three units, all of them about the *iterate* leg and
none of them a re-roll of a prompt already spent:

1. **The model-free `--set` iterate walk on `ot4-quill`**, promoted from
   third. It spends no tokens and is the only thing in existence that can
   exercise ADR-260's delta on geometry no test fixture has seen.
2. **Bound the walk's legs in wall clock.** New direction, one per this pass,
   serving mission 2 (headless, no human in the loop) and the leg
   `crisp-reef-5607` still names.
3. **A prompt-driven iterate on an existing project** — a second design turn
   against `ot4-quill` with `--resume`, changing geometry rather than a
   parameter.

Medium's selected direction — make the review step say whether the mechanism
moved — is **fully landed** and closes here: measurement (ADR-259) and
comparison (ADR-260) both, and a third mechanism has now exercised both. The
unbounded-leg bound replaces it as medium's selected finite direction.

## Why

**Why the model-free iterate leads.** The loop signals say Claude's
five-hour window went 29% → 84% (+55) this run; the seven-day is 67%. Unit 1
of the previous rung spent a 10:53 walk with a 629.6 s design turn in it
[rec: chilly-crest-2100]. A model-gated unit ranked first would be the most
likely thing on this rung to be refused or throttled, and the cheapest thing
on it is also the one with the highest evidentiary yield right now: ADR-260
threaded `previous_numbers()` through the walk branch and registered
`travel_mm`/`travel_deg`, and that change is pinned only by an offline
round-trip and the toy iterate lifecycle regression
[rec: northern-comet-5917]. `ot4-quill`'s first walk could not render a
delta at all — it was the project's first row [rec: chilly-crest-2100] — so
a second walk of it is the first opportunity to see the plumbing work where
it was built to work. `~/cadex-projects/ot4-quill/script.py` carries a real
`params(...)` block (`quill_dia`, `bore_len`, `stroke`, `head_len`, …), so
`--set` has something honest to change, and a walk with no `--prompt` runs
no design turn at all: `walk_parser`'s `--prompt` defaults to an empty list
and the design loop iterates over it. Token-free, and a real iterate rather
than a re-roll [rec: morning-summit-7848].

**Why the leg bound is the new direction, and why it is not scope creep.**
The third mechanism's own record names it: "the walk still spends an
unbounded design turn — 629.6 s here, 1,014.2 s on the swing arm — with no
`--timeout` of its own on that leg, which is the one place the entry point
can outrun a caller's budget" [rec: chilly-crest-2100]. I checked the source
rather than the record: `run_leg` (`cli/cadex_cli/walk.py:114`) calls
`subprocess.run(command, stdout=PIPE, stderr=None, text=True, env=env)` with
**no `timeout=` at all**, so *every* leg is unbounded — design, sweep,
train, script, declare, rollout. The walk's own `--timeout`
(`__main__.py:454`) is forwarded only into the `train` leg's argv
(`__main__.py:1377`) and is the trainer's internal bound; its help text says
so. The consequence is specific to what the charter is building: mission 2
wants the loop to run with no human in it, and mission 9 wants a team to run
one machine per experiment. A provider that stalls rather than refusing hangs
such a machine forever, and nothing in the entry point notices. That is a
product defect in the unattended path, it is `cli/`-only, it is offline and
testable with a stub child, and it is the last thing `crisp-reef-5607`'s own
evidence asks for. It is not a refusal semantic: a leg that runs out of time
fails the walk the way a leg that exits non-zero does, through the existing
`failed(...)` path.

**Why the prompt-driven iterate is third rather than a fourth mechanism.**
The obvious model-gated candidate is a fourth rig on the last unused
action-source pair, `(motor, angular)` — the three walks so far spent
`(position, angular)`, `(motor, linear)` and `(position, linear)`
[rec: chilly-crest-2100]. It is worth less than it looks: the
mechanism-blindness claim is now a property of the tree pinned by two
offline regressions [rec: falling-willow-7995], three mechanisms already
read side by side at one scale, and a fourth would produce a first row with
no delta, exactly like the third. What has *never* run on this machine is a
design turn against a project that already has a history — an
`ARCHITECTURE.md`, six ADRs, five `PROGRESS.md` rows and four domain notes
that `ot4-quill` wrote itself [rec: chilly-crest-2100]. Mission 2's "project
as codebase … read on every visit" and its iterate leg ("change what did not
work") are both about that turn, and every iterate this run has produced was
a parameter assignment instead. So the third unit is the same entry point
with `--resume` and one design prompt naming something the project's own
review found, and it is ranked last because it is the one that can be
refused on credit; the rung degrades safely without it.

**What I am not doing.** No charter gap is retired, blocked or superseded.
Nothing under `## Later criteria` is targeted. The clearance eye is not made
to refuse: `ot4-quill`'s `housing`/`quill` intersection is deliberate and the
project's own ADR-005 says so, which is a reason to leave the reporting
semantic alone, not to change it.

## Method

Read `PLAN.md`, both landed record nodes, the state frontier, and the source
behind every claim I make about it: `run_leg` in `cli/cadex_cli/walk.py`,
the `walk` subparser and the design/sweep/train dispatch in
`cli/cadex_cli/__main__.py`, and `~/cadex-projects/ot4-quill/script.py`'s
parameter block. Re-ranked `short`, re-wrote `medium`'s selected direction as
landed-and-closed with the leg bound in its place, left `long` untouched.
No code, no state node, no charter edit.

## Result

`short` leads with the token-free iterate walk on the third mechanism's own
project, then the wall-clock leg bound, then the prompt-driven iterate.
`medium` records the motion direction as closed on both halves and carries
the leg bound as its selected finite direction. Three new pieces of negative
knowledge: the walk is not time-bounded anywhere and must not be described
as such; the fourth action-source pair is not worth a walk on its own; and
`ot4-quill`'s reported intersection is a deliberate modelling choice that
every future walk of it will report again.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: af21807126f30d4a970b86517363d68e15a5d1a3

## State Impact

- target: plan/young-crane-9546 — re-rank onto the model-free --set iterate walk on ot4-quill, the wall-clock leg bound, and a prompt-driven iterate; three new negative-knowledge entries
- target: plan/strong-birch-7412 — close the motion direction on both halves and select the unbounded-leg bound in its place
