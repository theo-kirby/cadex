---
node_id: 8621e01b-317e-5764-a9d8-5979262c9aa3
slug: quiet-wing-7912
title: The contract moves to AGENTS.md; CLAUDE.md becomes a pointer
created_at: '2026-08-09T15:35:35+00:00'
parents:
- even-cliff-3863
summary: AGENTS.md now holds the agent contract verbatim and CLAUDE.md is one line, @AGENTS.md. One contract still, and ADR-137 amended to record the supersession of ADR-005's mechanism.
---
## What

The agent contract moved from `CLAUDE.md` to `AGENTS.md`, and `CLAUDE.md`
became a one-line pointer: `@AGENTS.md`. There is still exactly one contract;
only the name carrying it changed. Logged as an amendment to ADR-137, which
had recorded the opposite decision earlier the same day.

## Why

Follows the doc-drift check, and reverses a call made during the adoption. The
adoption skill's default is to install its onboarding block into `AGENTS.md`; I
declined, because ADR-005 had deleted `AGENTS.md` to stop two agent-instruction
files disagreeing, and I read recreating the file as undoing that.

The author pointed out the third option I had missed: `AGENTS.md` holds the
contract verbatim and `CLAUDE.md` imports it with Claude Code's `@` syntax, so
there is one file to read and one to edit. ADR-005's rationale is satisfied more
completely than before, because the contract is now also legible to agents that
look for `AGENTS.md` by convention.

## Method

- `git mv CLAUDE.md AGENTS.md`, so the file's history follows it.
- `CLAUDE.md` rewritten to the single line `@AGENTS.md`.
- The hypergraph sentinel block's rationale paragraph rewritten — it argued for
  an install target that is no longer the one used.
- Present-tense pointers repointed in `README.md`, `docs/VISION.md`,
  `docs/ROADMAP.md`, `docs/BLENDER.md`, `docs/BLENDER-TREE.md`,
  `docs/FREECAD.md`, `docs/PROVENANCE.md` (18 references) and in
  `docs/DECISIONS.md`'s preamble.
- **`docs/DECISIONS.md`'s ADR bodies were left exactly as written.** ADR-005's
  text says what was decided in 2026-07-24 and rewriting it would falsify the
  log. ADR-137 was amended instead, because it was written hours earlier in this
  same session and had never described a shipped state.

## Result

`CLAUDE.md` is one line; `AGENTS.md` is the contract; ADR-137 records the
supersession explicitly — ADR-005's *mechanism* is superseded and its
*rationale* is not. Adding content to `CLAUDE.md` is now the violation.

The general lesson, which is why this is a record node and not just a commit: I
treated a prior ADR as forbidding a *file name* when what it forbade was a
*second contract*. Reading a decision's rationale rather than its mechanism
would have found the pointer option immediately. When declining a tool's default
on the strength of an old decision, check which of the two the decision actually
binds.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: early-arbor-7123 — new claim: AGENTS.md is the single agent contract and CLAUDE.md only imports it; adding content to CLAUDE.md is the violation
