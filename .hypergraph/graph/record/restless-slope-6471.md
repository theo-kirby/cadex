---
node_id: 2318e0b0-ace5-5439-83d5-b3a9b2585f95
slug: restless-slope-6471
title: Absent provenance is unknown, not printed (ADR-382)
created_at: '2026-09-17T00:28:28+00:00'
parents:
- still-rock-6891
summary: ''
---
## What

The system prompt no longer reads a silence as a pass. ADR-381's clause told
the agent that a name absent from `derived_catalog_sources` is "an ordinary
printed part"; the overlay now calls an absent name **provenance unknown**,
says why (the producer follows a definition's base operand only, so a catalog
body fused into a printed solid as a *second* operand is a purchase it cannot
name), keeps the one absence that is conclusive (a body used only as a cutter
is a clearance tool, not a purchase), and tells the agent to read the script
that built an unlisted name before calling it printed. `docs/CLI.md` says the
same beside the `derived_catalog_sources` description, ADR-381 clause 3 carries
the withdrawal, and ADR-382 records the correction. One new CLI test,
`test_the_prompt_reads_absent_provenance_as_unknown_not_printed`, is red on the
old overlay. Commit `c179781a`.

## Why

This is exactly the fix the critic's message named, and it is the in-flight
unit the owner's 2026-09-17 charter directive says to finish before waiting:
"only fixes directly required by its critic review and its required
verification". Nothing else was started — no tooling, no checker, no probe of
the organisation-level refusal that blocks F6 and F7.

The defect matters because it is the same failure ADR-362 and ADR-381 were each
written to remove, reintroduced one clause later. ot7's F5 closed with one
failing count, *catalog hardware for every purchased part*, because the agent
could not see that its drilled servos had lost catalog identity. ADR-381 gave
it the names; the clause then told it that everything *not* named is fine,
which the producer cannot support and which ADR-381's own "what it does not
claim" paragraph contradicts in the same entry.

It advances **F1** only in the sense that the reply's advisory block tells the
truth about its own bounds; it claims no criterion tick. The frontier criteria
F6 and F7 remain blocked on product-agent access, and F4/F5 stay exhausted with
their slots and measurements untouched.

## Method

1. Read the producer's bound at its source: `_stamp_catalog_identity` follows
   `arguments[0]` down, and `test_a_fuse_reads_the_first_operand_of_its_one_list_argument`
   (`src/Mod/cadex/cadex_tests/test_inventory_scope.py:405`) asserts the second
   operand is *deliberately* unnamed.
2. Rewrote the clause in `CLI_OVERLAY` (`cli/cadex_cli/agent.py`), keeping the
   purchased-part repair instruction and the cutter case, and replacing the
   false half with the bound and what to do about it.
3. Added the prompt regression in `cli/tests/test_turn_loop.py`, beside the
   existing catalog-identity prompt test, whose docstring cites the engine
   fixture that makes the bound real — the fixture is engine-side and cannot
   import the CLI overlay, so the assertion lives with the prompt it pins and
   names the fixture rather than duplicating it.
4. Corrected `docs/CLI.md`'s `derived_catalog_sources` paragraph, which had let
   the cutter case stand as the only reason a name is absent.
5. Appended ADR-382 and marked ADR-381 clause 3 withdrawn in place.

Verification: the new test fails on the pre-change overlay (checked by stashing
`agent.py`); `pixi run python -m pytest cli/tests` — **831 passed, 1 skipped**.
No engine, protocol or payload code was touched, so no engine suite and no
packaged gate were run, and none was required.

## Result

The agent's advisory catalog block now states its own blind spot instead of
covering it. Detection is unchanged and stays bounded: the producer, the
`inventory` scope value, the reply block, `cadex inventory`'s document and
every ADR-381 test are untouched, and ADR-243's boundary stands where ADR-381
left it. No `ot7-*` design was edited and no frozen prompt was spent.

For the next iteration:

- The owner's directive (`.ouroboros/goal.md`, dated 2026-09-17, modified in
  the working tree and **not** committed by this unit — unattended roles do not
  edit or commit that file) makes the **next dispatch the reconcile pass**:
  fold `terse-chart-0277` into its four targets to replace the rejected ADR-379
  claims, fold this record and `still-rock-6891`, regenerate the views, export
  and check. The critic asked for the same. Reconcile is forbidden in a work
  iteration, which is why it was not done here.
- The directive also asks that the owner directive itself be recorded once,
  causally parented, with the charter change in the same handoff. That belongs
  to that reconcile dispatch, not to this unit.
- After that: **wait**. The directive bars filling the wait with more tooling,
  test, documentation or bookkeeping units, and bars re-probing the unchanged
  organisation-level refusal of `claude-fable-5`. F6 and F7 resume only on
  concrete evidence of restored product-agent access; every slot stays unspent.

Dispatch closed: 1 unit — the prompt calls an absent `derived_catalog_sources`
name provenance unknown rather than a printed part (ADR-382), pinned by a
regression that is red on the old overlay, with `cli/tests` green.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: c179781a30e8487d2ddcdfbd218be427d0220c33

## State Impact

- target: chilly-union-8972 — the CLI overlay's catalog-identity clause now calls a name absent from derived_catalog_sources provenance unknown, with the base-operand bound and the cutter exception stated (ADR-382, withdrawing ADR-381 clause 3's printed-part reading); docs/CLI.md matches and a prompt regression pins it
