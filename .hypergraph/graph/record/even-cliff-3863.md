---
node_id: 23b6ea26-9c7c-5192-85f8-b2cc3bd31644
slug: even-cliff-3863
title: The engine suite count in the docs was stale by 54%
created_at: '2026-08-09T15:27:26+00:00'
parents:
- western-badger-3023
summary: CLAUDE.md and ARCHITECTURE.md said 1,105 passed / 12 skipped; the suite reports 1,698 passed / 22 skipped. Measured, corrected, and dated.
---
## What

Ran the engine suite to check a doc claim the adoption interview had left open,
and found it stale by 54 %. `CLAUDE.md` and `docs/ARCHITECTURE.md` both stated
**1,105 passed / 12 skipped**; the suite actually reports **1,698 passed, 22
skipped**. Both documents were corrected in the same pass, and
`ARCHITECTURE.md`'s `Verified against source:` date moved from 2026-08-04 to
2026-08-09.

## Why

Follows the current-state assessment. Asked what in the docs is now false, the
author declined to name anything and asked for it to be checked instead. This is
the check, and it found one — which also means the assessment node's "no
contradiction found in this pass" is now qualified rather than wrong: that pass
was doc-level, and this one measured.

## Method

`pixi run test-engine` (headless, no build, pixi environment), plus a file count
under `src/Mod/cadex/cadex_tests/`. Cross-read against the running suite-count
line in `docs/DECISIONS.md`, which tracks the number ADR by ADR: 1105 at M8's
close (2026-07-31) → 1109 → 1112 → 1153 → 1333 → 1509 → 1532 → 1565 → 1588 →
1698 (ADR-136, 2026-08-07).

## Result

- Measured: **1,698 passed, 22 skipped in 116.84 s**, exit 0.
- File counts were stale too: 97 Python files of which 84 are collected test
  modules (documented as 77 / 64), and 45 `test_dynamics_*.py` files
  (documented as 38).
- **The ADR log was never wrong.** ADR-136 records 1698/22 correctly. What
  drifted is the two *summary* documents that restate a number the ADRs keep
  updating — which is the failure mode a `Verified against source:` date is
  supposed to expose, and did: `ARCHITECTURE.md` carried its own 2026-07-31
  qualifier honestly, while `CLAUDE.md`'s figure carried no date at all and read
  as current.
- Corrected: `CLAUDE.md` command table, `docs/ARCHITECTURE.md` §3 Tests, and
  that document's verification date.

The generalisable point, which is why this is recorded rather than just fixed: a
restated number in a summary doc has no owner, and the ADR that moves it has no
reason to know it was restated. Prefer pointing at the command; where a figure
is restated, date it.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 41e6aa6ceeed3078210e02c1f94d85bd715fbb9d

## State Impact

- target: forest-wind-0342 — new claim: the engine suite is 1,698 passed / 22 skipped, measured 2026-08-09, replacing the 1,105/12 figure
- target: early-arbor-7123 — new negative knowledge: figures restated in summary docs drift silently; the ADR log is the live source
