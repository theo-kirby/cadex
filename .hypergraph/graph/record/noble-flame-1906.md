---
node_id: 9209e07f-4e58-5747-9dad-028fb06fab75
slug: noble-flame-1906
title: The swept row's motion flag is pinned against its contract (ADR-374)
created_at: '2026-09-16T20:51:05+00:00'
parents:
- wild-eagle-4128
summary: ''
---
## What

A headless regression guard that holds the published sweep's `relative_motion`
field against the protocol document that is its contract, plus the one-clause
doc edit that makes the contract checkable about that key alone.

`src/Mod/cadex/cadex_tests/test_joint_fit_sweep.py` gains
`test_the_protocol_document_carries_the_swept_row_motion_flag`. It reads the
swept pair row's constant keys out of `_sweep_joint` with `ast` — the row's
shape is one dict literal — and holds them against the
`### Published joint sweeps` section of `docs/INTEGRATION.md`:

1. `_sweep_joint` publishes `relative_motion` on every pair row;
2. the section names that key;
3. a sentence *naming that key* says it is **absent** on a revision accepted
   before ADR-374 — the legacy-absence rule the CLI's reader implements by
   counting an unflagged row as moving.

`docs/INTEGRATION.md`'s sentence read "The key is **absent** on a revision
accepted before ADR-374"; it now reads "The `relative_motion` key is
**absent** …", so check 3 is about that key rather than about any absence
word anywhere in a section that also documents ADR-367's and ADR-371's
legacy behaviours. `docs/DECISIONS.md`'s ADR-374 entry carries a dated line
saying the sentence is now pinned and how.

Commit `07b4beed`.

## Why

The critic asked for exactly this: one focused regression guard for the
published sweep's `relative_motion` field and its documented legacy-absence
behaviour, demonstrated red by removing the contract documentation, bounded
to the demonstrated F9 documentation gap and introducing no schema
framework. It advances F9 (nothing regressed) on the ot7 frontier
(`mild-ledge-7157`); F6 and F7 stay untouched with every slot unspent, and
no product-agent call was dispatched.

The gap was real and had already bitten once. The flag has two behaviour
guards — the real-kernel fixture in `test_joint_fit_sweep.py` and the CLI
roll-up test in `cli/tests/test_clearance.py` — and had none for the
contract sentence, which is why that sentence landed in a follow-up commit
(`60f298bc`) rather than with the behaviour (`65cbe3ca`). Both behaviour
guards for the engine half also skip without a built `FreeCADCmd`; this one
runs on a bare checkout.

## Method

- Read `_sweep_joint` (`cadex_assembly_worker.py:5675,5755,5768`), the CLI
  reader (`cli/cadex_cli/clearance.py:201`), and the existing contract tests
  that parse `docs/INTEGRATION.md` (`test_response_schemas.py`,
  `test_engine_purity_guardrails.py`) — the guard follows their shape.
- Derived the row keys with `ast` rather than by running a sweep, so the
  guard needs no kernel and a rename is visible where it is decided.
- Demonstrated red three ways, restoring between each:
  - deleting the whole ADR-374 block from the section → check 2 fails,
    naming the keys the section still documents;
  - deleting only its absence sentence → check 3 fails, printing the
    sentences that do name the key;
  - renaming `relative_motion` to `moves` in the worker → check 1 fails,
    naming the change as a protocol change and the two files that move with
    it.
- `pixi run test-engine`: **2149 passed, 53 skipped in 274.6 s** (2148 before
  this unit). No CLI source changed, so `cli/tests` was not re-run; no op,
  argument spec, response shape, threshold, acceptance behaviour or payload
  changed, so the packaged gate has nothing new to see and was not re-run
  (the previous unit rebuilt and restaged a payload for the behaviour this
  guards, 20 passed).

## Result

The `relative_motion` contract can no longer be dropped silently: renaming
the field, un-naming it in `docs/INTEGRATION.md`, or deleting the sentence
that documents its absence on an older revision each fail a headless engine
test with a message saying what to write and where.

Assumption recorded: the guard requires the absence sentence to *name* the
key, which is a wording constraint on one sentence of
`docs/INTEGRATION.md`. That is deliberate — the section documents three
different legacy behaviours (ADR-367's unavailable sweep, ADR-371's
`skipped` row, ADR-374's missing flag) and a check that matched any absence
phrasing anywhere in it passed with the ADR-374 sentence deleted. The
failure message states the requirement, so a future editor is told rather
than left guessing.

Not done, and deliberately: no equivalent guard for `docs/CLI.md`'s
consumer-side sentence, and no generalisation to the other published row
keys — the section describes most of them in prose rather than as backticked
keys, and pinning those would be the schema framework the critic ruled out.

Unreconciled tail is now two nodes. F6 and F7 remain blocked on provider
capacity with every create and continuation slot unspent; nothing in this
unit spent one.

Dispatch closed: 1 unit — `relative_motion` and its legacy-absence rule are
pinned to `docs/INTEGRATION.md` by a headless guard, demonstrated red three
ways.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 07b4beed17ed9c983137518a4c665065f653bcc2

## State Impact

- target: forest-wind-0342 — a headless ast-plus-document guard pins that _sweep_joint publishes relative_motion and that docs/INTEGRATION.md names it and documents its absence on a pre-ADR-374 revision; both behaviour guards for the flag skip without a kernel, this one does not
