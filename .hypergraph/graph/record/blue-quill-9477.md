---
node_id: 2919a79f-4b82-5b44-a699-638c04ccb034
slug: blue-quill-9477
title: 'Correct the reproduction notes: explicit interpreter, not discovery'
created_at: '2026-09-08T17:39:29+00:00'
parents:
- western-gate-9567
summary: ''
---
## What

Closed both of the critic's must-fixes on iteration 20 (`western-gate-9567`,
commit `f152798a`) in one fix-forward commit, `00c8f8ec`:

1. The absolute machine path `/home/theo/cadex-train-venv/bin/python` is gone
   from the `western-gate-9567` record node, replaced by
   `--trainer-python "$TRAINER_PYTHON"` plus a portable description ("this
   machine's trainer venv interpreter, the home-directory `cadex-train-venv`,
   the last entry in the CLI's discovery order"). A grep for `/home/theo` over
   the whole branch diff (`git diff main...HEAD`) now returns nothing.
2. Both `examples/lifecycle/*/PROGRESS.md` reproduction sections said the
   trainer venv was "discovered without `--trainer-python`". That was false for
   the two measured walks, which passed the interpreter explicitly; only the
   third carriage walk exercised the discovery order. All three places that
   describe the run — both `PROGRESS.md` sections and the README's reproduction
   table — now state which walk evidences the flagless command, and ADR-257
   carries a same-day correction paragraph saying what the first revision got
   wrong.

## Why

The overseer's message made these two the must-fix for this iteration, ahead of
anything on the plan. Both are honesty defects in evidence the charter's
criteria rest on, which is the one class of defect that compounds: the
`swift-dusk-2951` and `crisp-reef-5607` state nodes will be reconciled from
`western-gate-9567`, so an overstated claim about which command form ran would
enter the state graph as fact. Criterion advanced: **The walk holds on a second
mechanism** (`swift-dusk-2951`) and **The walk exists and is tested headlessly**
(`crisp-reef-5607`) — not by new evidence but by making the existing evidence
say only what was measured.

Machine paths in a record node are worse than untidy: they are the artifact a
reader on a different machine copies and fails on, which is exactly the defect
iteration 20 had just fixed in the README. Fixing the note while leaving the
same path in the record would have been the same mistake one file over.

Judgement call written here rather than asked: the correction is stated in
place (the sections a reader actually reads) *and* appended to ADR-257, rather
than rewriting ADR-257's decision paragraph. The ADR log is a narrative record;
a correction that erases what was first claimed teaches nothing.

## Method

Edited four files: the record node's `## Method` paragraph, both `PROGRESS.md`
reproduction paragraphs, the README's reproduction paragraph and its third-walk
sentence, and a `**Correction, same day.**` paragraph appended to ADR-257 in
`docs/DECISIONS.md`. Verified with `git diff --check` (exit 0) and by grepping
the added lines of the full branch diff for `/home/theo` (no hits).

No test was run and none was implicated: the diff is markdown only. The three
`cli/tests` that reference `examples/lifecycle` read `script.py` and nothing
else, and `script.py` is untouched, so the previous commit's measured run
(`JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests` → 227 passed, 0
skipped, 201.50 s) still describes this tree. Saying that plainly is more
honest than re-running 200 s of tests to decorate a documentation fix.

## Result

Both must-fixes are closed in commit `00c8f8ec` (5 files, +38/−17). The
measured numbers in both examples are unchanged and were never in question: the
same interpreter binary ran whether it was named on the command line or
resolved by the discovery order, so the correction is about what the evidence
claims to have exercised, not about what it measured.

What the corrected record now says, and what it no longer says: the hinged-arm
and linear-carriage rows on this machine were produced with the trainer
interpreter configured explicitly; the flagless command block the README
documents is evidenced by exactly one walk, the third carriage run, which
returned the same `total_reward` −24159.195371510654 in 13.19 s. Before this
commit a reader could have taken all three walks as evidence for the flagless
form.

**Still missing before either criterion ticks:** nothing new was measured here,
so nothing moved on the frontier. `swift-dusk-2951` and `crisp-reef-5607` still
carry two unreconciled records (`sleepy-hollow-9498`, `western-gate-9567`) plus
this one; the maintainer pass the overseer called for is due and is not a work
iteration's to run. After it, the planner's short-rung unit 1 — the `motion`
travel block in `review.json` with its two regressions — is the next unit, and
is the first thing this run has that changes CLI code rather than prose.

Dispatch closed: 1 unit — both critic must-fixes closed in commit 00c8f8ec: the absolute machine path is out of the western-gate-9567 record and out of the whole branch diff, and both PROGRESS.md sections, the README and ADR-257 now distinguish the two explicitly configured measurements from the single walk that verified interpreter discovery.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 00c8f8ec9c4f6e819f732590ce5dd57eb3f3898a

## State Impact

- target: swift-dusk-2951 — the second-mechanism reproduction evidence is corrected: both measured example walks passed the trainer interpreter explicitly, and only the third carriage walk exercised the CLI's discovery order; the numbers are unaffected
- target: crisp-reef-5607 — the documented flagless walk command is evidenced by one verifying walk rather than three, said so in the README, both PROGRESS.md files and ADR-257
