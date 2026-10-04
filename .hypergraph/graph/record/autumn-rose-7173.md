---
node_id: 6f821f71-0f5f-5d0c-a356-875a6f035019
slug: autumn-rose-7173
title: 'orun2 W1/A1: modes.py guidance points settled in CLI_OVERLAY (ADR-521); ledger row ported'
created_at: '2026-10-04T03:14:52+00:00'
parents:
- mellow-fjord-5906
summary: ''
---
## What
The parity ledger's `modes.py` row is ported (ADR-521). The nine guidance points that only the shell's overlay carried (`docs/SHELL-PARITY.md` §4) are each settled. Seven are re-derived in new words in `cli/cadex_cli/agent.py` `CLI_OVERLAY`: determinism, +Z up, output names, primary-to-secondary dimensions, batching builds, a picked-part comment as ground truth, and declaring a harness. One was already covered: the t=0 contact check after `assembly.mjcf`, which `CadexAgentGuidance.md` carries and which is now pinned. One is dropped: copying a hand-fitted terminal row, together with the terminal picker. §4 is now a table with one status per point.

## Why
The critic named this unit as the first of the six remaining ledger rows, in the ledger's own order. It serves W1, where no row may still say "to port", and A1, where there is one guidance source.

Deviation: the critic also asked me to retitle state node `brisk-rock-9862` and regenerate STATE.md before the unit. This dispatch forbids editing anything under `.hypergraph/graph/state/` and editing STATE.md, with no exceptions, so I did not do it. Instead this record's impact on `brisk-rock-9862` asks the next reconcile to retitle it "Projects trained before ADR-469 open with a stale policy named (ADR-520)".

## Method
- Read the §4 list, `CLI_OVERLAY`, `CadexAgentGuidance.md`, `comments.with_comments` (the `on part <name>` form), the `set_params`/`edit_script` field descriptions (a `values` object, a `replacements` array) and the `boards` row schema in `CadexScriptedDomains.py`. Wrote each point fresh against those. Nothing came from the tag; only the ledger's one-line summaries were used.
- I did not confirm which `describe_api` section documents `boards`/`nets`, so the overlay names `describe_api` without naming a section.
- Tests: `cli/tests/test_turn_loop.py::test_the_prompt_carries_the_guidance_that_lived_only_in_the_shell` pins each kept point in the assembled `system_prompt`, and checks that the comment form the overlay describes is the one `with_comments` writes. `src/Mod/cadex/cadex_tests/test_agent_guidance.py::test_the_guidance_checks_the_rest_contacts_after_an_mjcf_export` pins the covered point.
- Updated the ledger row, §4 and the §5 counts (§1: 18 ported, 4 to port), and added ADR-521.

## Result
True now: the `modes.py` row is ported. `pixi run test-engine`: 2607 passed, 56 skipped. `pixi run python -m pytest cli/tests` with the GPU hidden: 1401 passed, 1 skipped (20 min). Both runs were against the existing engine build; no rebuild was needed.

The ledger now lists five rows still to port: `agent.py` (per-turn cost and the text-tool-call warning), `cadex_dimension.py` (viewer overlay), `cadex_print.py` plus the Parameters editor (printable display), and `cadex_roles.py` (role colours). The critic named role colours plus the printable roster next, with a browser test against a real engine. The 5090 leg still needs the owner to load the driver.

Assumptions:
- "+Z is up" is stated alone. The guidance's `right` view looking from +X at the front hints at a forward axis, but I did not add one.
- Face pins stay "owner to confirm".

No new dependency. No engine build is needed: the engine-side change is a test only.

Dispatch closed: 1 unit — modes.py §4 guidance settled in CLI_OVERLAY (ADR-521), ledger row ported with tests; brisk-rock-9862 retitle deferred to reconcile

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: d4d4cfe5be70b2815f9f6ff80407418c75820bc9

## State Impact

- target: shady-clover-5534 — the modes.py parity row is ported (ADR-521, test_turn_loop.py::test_the_prompt_carries_the_guidance_that_lived_only_in_the_shell); five rows still to port: agent.py cost/text-tool-call warning, cadex_dimension.py viewer overlay, cadex_print.py + Parameters printable display, cadex_roles.py role colours
- target: brisk-rock-9862 — retitle to 'Projects trained before ADR-469 open with a stale policy named (ADR-520)' (critic request; the node is working and its title still says cannot be opened)
