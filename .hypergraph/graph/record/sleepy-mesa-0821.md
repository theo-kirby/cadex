---
node_id: 18d4f36d-7012-5509-985a-6c43442bc89a
slug: sleepy-mesa-0821
title: 'Bet: the provider block was one model, not the account'
created_at: '2026-09-08T23:36:05+00:00'
parents:
- dry-rain-0489
summary: ''
---
## What

Re-rank the short rung on a measured correction: **the provider is not out of
credits — one model is.** `dry-rain-0489` recorded the live walk as refused
because `claude` said "You're out of usage credits", and parked the charter's
leading item on that. Probed this pass: the bare `claude -p` and `claude usage`
still refuse, and `claude -p --model claude-opus-5`, `--model claude-sonnet-5`
and `--model claude-haiku-4-5-20251001` each answered `OK`. The refusal is
scoped to the walk's default model, `DEFAULT_MODEL = "claude-fable-5"`
(`cli/cadex_cli/agent.py:45`), which `default_model()` returns whenever
`$CADEX_MODEL` is unset.

So the rung leads, again and exclusively, with **one uninterrupted
`walk --prompt … --resume` on `ot4-quill` run under a model this login can
use.** Beneath it, the defect that caused the refusal to look terminal: the
walk never consults the model the project itself recorded. Third, the section
eye's own named miss on the swing arm.

## Why

Charter mission 2 and the criterion **"The walk exists and is tested
headlessly"** (`crisp-reef-5607`). Two facts decide this pass.

**First, the block is false.** `humble-star-3313` closed the exclusive live
iterate — a real turn read `ot4-quill`'s `PROGRESS.md`, disputed the project's
own ADR-005, wrote project ADR-007, and drove the clearance eye 1 → 0 — but its
design and measurement legs ran in two pieces after a kill. The overseer then
named the single uninterrupted invocation, and `dry-rain-0489` attempted it and
was refused. That refusal is real and was reported honestly by the walk
(`runs/uninterrupted-44`, leg `design`, exit 1, the provider's sentence verbatim
in `walk.legs[0].error`), but its stated cause does not survive a probe. The
rung's own negative knowledge already carried the shape of this, from
`open-hollow-2140`: "on this login `claude-opus-5` answers and the constant
`claude-fable-5` does not." That entry was read as historical. It was current.
One environment variable stands between this run and the charter's leading
item, so the exclusivity is restated rather than lifted.

**Second, the refusal exposed a real product defect, and it is the one new
direction this pass takes.** `ot4-quill/agent.json` recorded
`model: claude-opus-5` from the last turn that worked. The walk ignored it,
ran `claude-fable-5`, was refused — and then *overwrote* the record:
`git diff agent.json` in the project shows `claude-opus-5` → `claude-fable-5`
with the session id unchanged, because `write_agent_state`
(`session.py:87`) is called on any result carrying a session id and compares
`(session_id, model)` as one identity. A turn that never ran replaced the
project's memory of the model that did. That is the project-as-codebase
contract failing in the direction it exists to prevent, and the fix is the
resolution order the project already has the data for: `--model`, then
`$CADEX_MODEL`, then **`agent.json`'s own model**, then `DEFAULT_MODEL`. It is
a narrowing of ADR-247, not a reversal: that ADR's reason for persisting on
failure is that "a refused turn can create a resumable conversation", which is
about the session locator; the session id here was unchanged, so nothing about
resumability argues for regressing the model.

**Third, the eyes' own named gap.** `dry-rain-0489` measured the derived
section live on two more rigs and declared the honest half in its State Impact:
swing-arm `-9.2 mm` cuts 6 of 10 and **`cmp_swing_arm`, the moving part the rig
exists to look at, is still `empty`**. The cause is in the source, not in the
numbers: `offset_candidates` ranks by `coverage(offset)`, which counts objects
whose *bounds* the plane strictly crosses, and `derived_section` returns the
first candidate whose overall `status == 'ok'` — where `ok` means *any* object
cut. Both halves are indifferent to which objects come back. Ranking the eight
candidates by objects actually cut is the same measurement the caller already
performs, read one step earlier.

`--detach` through the CLI's walk drops off short to medium: it polishes a limb
whose remaining honest gap this run forbids, and it must not sit above two units
that move criteria.

## Method

1. Probed the provider directly rather than trusting the recorded conclusion:
   `claude usage` and bare `claude -p` refuse; three named models answer.
2. Read the resolution path in source: `agent.py:45,53,59`,
   `__main__.py:158,409` — no reader consults `agent.json`.
3. Read the overwrite in source and in the project: `session.py:87` compares
   `(session_id, model)`; `git -C ot4-quill diff agent.json` shows the model
   line moved and the session id unchanged.
4. Read `section.py:86-131` and `derived_section` for the ranking and the
   accept test.
5. Rewrote `young-crane-9546`'s `## Current` to three units in that order,
   restated the exclusivity on unit 1 with its new trigger, and added the
   probe correction as the leading negative-knowledge entry so no later pass
   re-parks on the credit premise.
6. Rewrote `strong-birch-7412`'s items 1 and 2 to match, and took `--detach`
   onto its tail.

## Result

The short rung reads: (1) the uninterrupted live walk under a working model,
exclusive; (2) the walk resolves its model from the project's own record and a
failed turn stops regressing it; (3) the derived section chooses by what it
cuts. One new direction, unit 2, serving mission 2. No gap retired, none marked
done, no status change proposed on any state node — `crisp-reef-5607` stays
open on the run, not on credits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 9ea5af8486f9025058d644705a48d78318e69999

## State Impact

- target: plan/young-crane-9546 — re-rank to the uninterrupted live walk under a working model (exclusive), the project-recorded model resolution, and the section chosen by what it cuts; --detach demoted
- target: plan/strong-birch-7412 — restate the last-leg item as not provider-blocked, narrow the eyes item to the swing-arm coverage miss, and take --detach onto the tail
