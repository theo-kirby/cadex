---
node_id: acb424c8-3e9e-5419-a1fd-9ff0bcb54a87
slug: salty-wolf-2393
title: A project's own architecture stopped reaching the agent
created_at: '2026-09-09T02:49:58+00:00'
parents:
- clear-shade-1084
summary: ''
---
## What

Two commits. `db3ab38b` lands the detached-training pending receipt (ADR-278)
that the previous iteration finished but was cut off before committing.
`17b14e8e` is this iteration's own unit: a fix for a silent regression in which
a project's own `ARCHITECTURE.md` content stopped reaching the agent's prompt.

Prompt context bounds each project document to 8,000 characters. `ARCHITECTURE.md`
was bounded by keeping its *head* — but its head is the scaffolded guide to the
walk contract, and the project's own paragraphs are appended underneath it. The
guide was 7,717 characters at ADR-276 and 8,191 at ADR-277. From ADR-277
(`66e2dfcd`) on, the head budget was consumed entirely by boilerplate and every
line a project had written about itself was dropped from every visit's prompt.

`ARCHITECTURE.md` is now bounded from **both ends**, half the budget each, with
the omission marker in the middle. Decisions, progress and domain notes keep
their tails as before; the budget is unchanged and nothing on disk changes.

## Why

Charter criterion **Project as codebase** (mission item 2), and behind it the
lifecycle walk: the whole point of scaffolding project docs is that the
revisiting agent reads them. Since ADR-277 it read the guide and nothing else.
Two `test_turn_loop.py` tests were failing at HEAD and had been failing since
that commit, so the tree was not green when this iteration started.

The plan's leading unit was one conditional fresh mixed-joint walk. It was
skipped in one line: a walk dispatched into a broken tree would have run its
design turns without the project's own architecture in the prompt, which is
precisely the context the walk's iterate step depends on. The overseer's
instruction to move to a concrete standing-maintenance defect when the walk is
not runnable is what this took. The walk remains the next unit.

The fix is structural rather than a raised constant, per the question policy's
preference for the reversible, smallest option that cannot silently re-break:
raising `PROMPT_DOC_LIMIT` would have bought one or two more guide paragraphs
and then failed the same way, invisibly.

## Method

Found the failures by running the full CLI gate on the inherited working tree,
then reproduced them at HEAD in a detached worktree with the built engine
symlinked in (the tests skip without an engine, which is why nothing caught
this). Bisected across the last three commits: pass at `2218c90b` (ADR-276),
fail at `66e2dfcd` (ADR-277). Measured the scaffold template at each commit —
7,717 then 8,191, against `PROMPT_DOC_LIMIT` 8,000 — which named the mechanism
exactly.

Added `keep="ends"` to `_bounded`, switched `ARCHITECTURE.md` to it, updated the
scaffold's own self-describing line, `docs/CLI.md`, ADR-279 and the ROADMAP.
The new regression test builds the **real** scaffold rather than a synthetic
string, so a future guide line cannot restore the eviction without failing it;
it was verified to fail with the previous keep mode.

One trap worth naming: flipping the keep mode back and forth with `sed` left a
stale `__pycache__` entry, because `"head"` and `"ends"` are the same length and
the edits landed inside one second — Python's mtime+size invalidation could not
see the change, and a green suite briefly turned red for no source reason.

## Result

Full CLI gate: **288 passed, no failures, no skips** (was 285 passed / 2 failed
before this unit). `bash -n training/remote_train.sh` clean for the carried
commit. No engine, shell or protocol change; the engine suite and `pixi run
gate` are untouched by this diff and were not run.

The regression is closed and the tree is green again. `crisp-reef-5607` and the
project-as-codebase contract are restored to what they were documented to be:
between ADR-277 and here, any claim that the revisiting agent read a project's
own architecture was false.

Still missing before the walk criterion can be ticked: the fresh mixed-joint
walk itself has not been run. That is the next unit, now against a tree whose
agent turns actually carry the project's knowledge.

Dispatch closed: 1 unit — architecture docs bounded from both ends so a growing
guide stops evicting a project's own notes (ADR-279); the carried ADR-278
detached-receipt work committed alongside; CLI gate 288 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 17b14e8e78e31254cdd9f21aa0db29f6fad15629

## State Impact

- target: calm-peak-5247 — ARCHITECTURE.md is bounded from both ends in prompt context (ADR-279); the scaffold guide passing 8,000 characters at ADR-277 had silently evicted every project's own architecture from every visit's prompt since 66e2dfcd. Regression built on the real scaffold.
- target: chilly-union-8972 — cadex train --remote --detach returns a pending run locator in the report and project-local --out/training-receipt.json, verifying and storing no policy and preserving an older policy at the destination (ADR-278). CLI gate 288 passed, no failures, no skips.
