---
node_id: 2866ed1f-aa57-5850-a497-064d1cba20dd
slug: mellow-fjord-5906
title: 'orun2 W1: shell parity ledger audited row by row; every cited test passes; six rows still to port'
created_at: '2026-10-04T02:38:07+00:00'
parents:
- dusty-bramble-8099
summary: ''
---
## What
Audited `docs/SHELL-PARITY.md` row by row (commit `07746b65`): checked coverage against the tag `v1-blender-shell`, checked that every cited test exists and passes, fixed stale rows, and added §5 with the counts.

## Why
The critic's named unit (W1): every "ported" row must name a test that exists and passes; every mesh_agent module, all 23 tools and all seven editors need a non-blank row; record the counts. Done as asked.

## Method
- `git ls-tree v1-blender-shell shell/scripts/startup/mesh_agent/` has 47 entries; a script matched each to a §1 row: 47/47, no blank cell. The tools in the tag's `tools.py` match §2's 23 rows; `shell/source/blender/editors/space_cadex_*` has 7 dirs, matching §3's 7 rows.
- Extracted every `test_*.py[::name]` the ledger cites (11 files, 8 named functions) and checked each exists. Ran them: `CUDA_VISIBLE_DEVICES="" pixi run python -m pytest` on the 9 cli files gave **77 passed, 0 skipped** against the built engine. The 2 engine files gave **23 passed**.
- Checked the open rows against source: the slider's min/max come from the spec (`test_browser_moves_a_slider_and_sees_the_rebuilt_model` asserts both). ADR-504 streams the transcript live and stores none. `ClaudeTurn._command` enumerates the tools in `--allowedTools`. W1 step 1's real turn used `inspect`/`look`/`edit_script`/`set_params`/`rebuild` without `ENABLE_TOOL_SEARCH` (`docs/probes/orun2/w1/README.md`). The §4 guidance points do not appear in `CadexAgentGuidance.md` or `CLI_OVERLAY` (grep).

## Result
- **Moved to ported, with tests:** `model.py` and `model_api.py` (ADR-503), `history.py` (live transcript, ADR-504; the store stays dropped), and `ui.py`.
- **Settled:** `backend.py`'s ENABLE_TOOL_SEARCH check, as not needed.
- **Owner-confirmed drops (owner notes):** `cadex_live.py`, the Live editor and `demo/`.
- **"Drop (proposed)" made final:** dropped (ADR-498) in `cadex_backend.py`.
- **Split:** `cadex_dimension.py` is now "ported on sheets (ADR-516), viewer overlay to port".
- **Exact test names:** the Chat and Parameters editors now cite theirs.

No ported row lacks a passing test.

Counts (a row with a split status counts under each part):

| section | rows | ported | covered | dropped | to port | owner to confirm |
|---|---|---|---|---|---|---|
| §1 | 47 | 17 | 15 | 24 | 5 | 2 |
| §2 | 23 | 6 | 17 | 2 | 0 | 0 |
| §3 | 7 | 5 | 2 | 5 | 1 | 0 |

**W1 is not claimable yet. Six rows still say "to port":**
- `agent.py`: per-turn cost and the text-tool-call warning (A1);
- `cadex_dimension.py`: the viewer overlay;
- `cadex_print.py` and the Parameters editor: printable-part display (charter A1 port list);
- `cadex_roles.py`: appearance-role display (charter A1 port list);
- `modes.py`: the §4 guidance points, none yet in the guidance (A1).

These are the next W1/A1 units. My suggested order:
1. the §4 guidance re-derivation into `CadexAgentGuidance.md`;
2. role colours plus the printable roster in the viewer;
3. per-turn cost.

The two face-level "owner to confirm" rows stay open for the owner.

Docs-only change. `test_project_docs.py` passed (40). The full suites were not re-run, because no code changed.

The unreconciled tail is now 3 records, so the critic's reconcile is due next; it folds brisk-rock-9862.

Dispatch closed: 1 unit — shell parity ledger audited: 77/77 rows present (47 modules, 23 tools, 7 editors), all cited tests pass, 6 rows still to port named

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: 07746b657c8f44173e633de5f2e3102e8bfe9f87

## State Impact

- target: shady-clover-5534 — parity ledger audited (07746b65): 47/47 modules, 23/23 tools, 7/7 editors rowed, none blank; every cited test exists and passes (77 cli real-engine + 23 engine, 0 skipped); six rows still 'to port' (agent.py cost/warning, dimension viewer overlay, print roster + Parameters ticks, roles, modes.py §4 guidance) block the W1 claim
