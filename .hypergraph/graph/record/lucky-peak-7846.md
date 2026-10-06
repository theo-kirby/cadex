---
node_id: f533e3ad-055a-5e54-8ce0-70402ad2c186
slug: lucky-peak-7846
title: 'G1 audited: base plus styles pinned — no project named in any guidance file, MCP brief follows agent.json (ADR-560)'
created_at: '2026-10-06T10:58:06+00:00'
parents:
- glad-basin-7496
summary: ''
---
## What
G1 audited and closed. Commit 7a4205b1 ("ouroboros #10: no record") landed the G1 work (ADR-560) without a record. It was checked against the charter and left unrewritten. Two pins it lacked are added, one project name is cut from `docs/DESIGN-LANGUAGE.md`, and the critic's fix is applied: the pan comment in `review_scene.js` now cites ADR-561, not ADR-560.

## Why
The critic's message: fix the ADR citation first, then audit G1 (`pale-arrow-4660`) against the charter, add any missing pin, and record it with gate output. Done as asked. G2's style folding is the next unit.

## Method
Checked 7a4205b1 against each G1 clause:
- **Base names no robot type as the default.** Already pinned in both suites (`NOT_IN_THE_BASE`, including "look engineered"). The base says *form follows function*.
- **No style text unless chosen.** Already pinned: `cadex guidance --project` with no `agent.json` is the base alone, and so is one holding budgets but no style. No style line appears in the base.
- **No guidance file names a project.** Partly pinned. The tests covered the base `.md`, the style files, the brief and the style text. They did not cover `cli/cadex_cli/guidance.py` or `docs/DESIGN-LANGUAGE.md`, and the doc named `orun1-t1-hexapod` (line 219). **Added** `test_no_guidance_file_names_a_project_and_the_doc_lost_look_engineered`. It checks all four file kinds against a project-directory pattern. Run names such as `ot10` and `orun1` stay allowed, because they are runs, not projects. The test also asserts the doc has no "look(s) engineered". The doc's citation now reads "(orun1, rev `35193b3e`)". The test fails on HEAD's doc (`['orun1-']`) and on the pre-G1 doc.
- **`cadex guidance` / MCP instructions carry base+style or base alone.** `cadex guidance` was pinned. The MCP `initialize` instructions are a ≤2,000-char brief, because Claude Code cuts at 2,048. The brief points the agent at `cadex guidance --project <p>` and names the chosen style. That was pinned only through `brief()` directly, not through the host reading `agent.json`. **Added** `test_the_mcp_server_instructions_follow_the_projects_style`. It drives `McpSession.instructions()` on a project before and after `cadex style`.
- **No new tool.** The tool surface is unchanged (`cadex style` is a CLI command).
- **"Look engineered" gone from DESIGN-LANGUAGE.md.** Confirmed by grep and now pinned.
- ADR-560's Test paragraph names the new pins.

## Result
Gates: `pixi run test-engine` — 2598 passed, 58 skipped (5:39). `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests -q -x` — 1196 passed, 1 skipped (17:00). `cli/tests/test_agent_guidance.py` — 11 passed.

G1's evidence list is complete pending the owner's tick:
- base and style files exist, with a style chosen per project through `agent.json` via `cadex style`;
- `cadex guidance` and the MCP brief follow the chosen style;
- all three charter pins are in tests that fail without the change.

Assumption, owner to revise: the MCP instructions carry the base plus style *by pointer*. The brief names the style and the command that prints base+style. They cannot carry the whole text, because the client's 2,048-character cut would truncate it (ADR-538's brief).

Concern: `docs/DESIGN-LANGUAGE.md` still cites run names (ot10, orun1) as evidence. The charter forbids naming the reference *project*, and none of these is a project, so they stay.

Next: G2. Fold the ledger's lessons into the `printed-legged-robot` style and the base, then do the fresh-session check.

The tail is now 2 records.

Dispatch closed: 1 unit — G1 audited against the charter; project-name and MCP-host pins added; ADR-561 comment fixed

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun4
- commit: ed0ab8f4c1037249a9340ff70d77159fab5fed96

## State Impact

- target: pale-arrow-4660 — G1 evidence complete pending owner tick: base/style files, cadex style + agent.json, cadex guidance and MCP brief follow the chosen style; all three charter pins tested (commits 7a4205b1 + this)
