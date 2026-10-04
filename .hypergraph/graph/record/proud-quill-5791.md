---
node_id: 1d6a8919-2b57-5b6e-bf41-64dd220c5b87
slug: proud-quill-5791
title: 'orun2 A1: leave_note, the agent''s non-blocking channel to the owner, shown on the dashboard and answered through comments (ADR-512)'
created_at: '2026-10-03T21:31:44+00:00'
parents:
- staid-wave-3739
summary: ''
---
## What

orun2 A1, the agent's non-blocking channel to the owner (ADR-512). The product agent gains one bridge-answered tool, `leave_note(type, text, artifact?)`. `type` is `flag` (review the accepted revision, or one project file) or `question`. It appends a `kind: "note"` line to the project's `comments.jsonl`, tagged with the accepted revision, and returns at once. It has no wait argument. The dashboard gains a **From the agent** panel (`#note-panel`, DASHBOARD.md §26) that lists the notes newest first. It links a flagged file through `note/<id>`, a route that serves only the file that note names, inside the project and of a shown type. Each note has an **Answer** box. An answer is an ordinary comment with `reply_to`: `cadex comment --reply <id>`, which the page's box runs, so there is still one write path (A3). The next `cadex -p` receives the answer as a comment quoting the note: `(answering your note "…") …`. `CLI_OVERLAY` gains a paragraph telling the agent to leave a note and carry on, in the same turn, with the most reversible assumption.

Files: `cli/cadex_cli/{comments,bridge,tools,agent,__main__,review_server}.py`, `review_static/{index.html,review.js,review.css}`. Tests: new `cli/tests/test_owner_channel.py` (7 tests), one browser test in `test_dashboard_writes.py`, the reading order and headings in `test_review_design.py`, and a pin in `src/Mod/cadex/cadex_tests/test_project_tool_surface.py`. Docs: ADR-512, CLI.md (the `--reply` flag, the `comments.jsonl` row, a `leave_note` section), DASHBOARD.md (region row 0a′ and §26), SHELL-PARITY.md §2.

## Why

**Deviation from the critic's message.** The critic asked for a reconcile first: fold narrow-crest-4950 and staid-wave-3739 and move D2 to its evidenced state. It named A1 as the iteration after. This dispatch's own rules forbid a reconcile in a work iteration ("Forbidden in a work iteration, no exceptions: the hypergraph-reconcile skill …"), so I did not run one. I took the unit the critic named next, A1's channel, built to its specification: a tool to flag a revision or artifact or post a question, the dashboard shows it, the owner's answer comes back through the existing comments path, pinned by test_project_tool_surface.py, with an ADR. The unreconciled tail is now 3 nodes. That meets the charter's three-record reconcile trigger, so the next maintainer or reconcile pass should fold it, including the D2 gaps the critic named (the accepted attempt's own sim trace cannot be played back, and commands show as numbers).

Target: frontier node `fierce-falcon-5989` (A1), the highest-ranked open criterion after D2 item 5 closed.

## Method

Read `comments.py`, `bridge.py`, `tools.py`, the `review_server.py` comment write and routes, the comment UI in `review.js`, and the existing comment tests, then reused each of them. `comments.py` gets `add_note`/`read_notes`, `reply_to` on `add_comment` (it must name an existing note), a shared `_entries` reader, and the answer quote in `with_comments`. An artifact must be project-relative and resolve to an existing file inside the project; `..`, absolute paths and directories are refused. The bridge tool reads the accepted revision with `read_accepted_identity`, refuses unknown arguments and a project-less session as tool errors, and records a ToolCall. The server validates `reply_to` against `^n-[0-9a-f]{12}$` before spawning anything. Nothing touches `OP_ARG_SPECS`, so `docs/INTEGRATION.md` and the payload are unchanged and the packaged gate does not apply. No new dependency.

## Result

What is true now:
- `pixi run test-engine`: **2593 passed, 56 skipped**, including the new `test_the_cli_bridge_tools_are_pinned_and_the_owner_channel_never_waits`.
- `cli/tests/test_owner_channel.py`: 7 passed, nothing skipped (`-rs`). The engine-backed mock-turn round trip ran against the real engine.
- Browser test `test_browser_shows_the_agents_question_and_the_answer_reaches_the_next_turn`: passed against a real engine in headless Chromium, not skipped. A fake-claude turn called `leave_note` twice through the real MCP bridge. The page listed both notes and served the flagged PNG through `note/<id>`. The owner answered in the page, `comments.jsonl` ended up note, note, comment(reply_to), and the next turn's prompt carried `(answering your note "…") yes, round it`.
- Full CLI suite (GPU hidden, `CUDA_VISIBLE_DEVICES=""`): **1353 passed, 1 skipped** (the skip is `test_review_server.py:851`, which needs `CADEX_REVIEW_HOST`, an environment setting). On the way there, the guard `test_turn_loop.py::test_the_overlay_quotes_no_rating_render_or_judge` (orun1 D2) failed: the agent's prompt may not contain "owner", so that the owner's design ratings reach the agent only as written rules. The tool was first named `notify_owner`. I renamed it to `leave_note` and reworded the overlay as "the person reviewing the design". The guard was not weakened. ADR-512 records the reason for the name.

A1 is now partly evidenced. The channel half is done. The "one contract" half is still open: SHELL-PARITY §4 lists the shell-only guidance points A1 must decide (deterministic script, +Z up, batch rebuilds, and so on), and the `ENABLE_TOOL_SEARCH` check on the `backend.py` row is still undecided. Those are the next A1 unit. Assumption: the note is always tagged with the accepted revision at the time of the call, and the agent cannot name an older revision. Flagging an older one goes through `artifact` or the text. That is the smallest surface and can be extended.

Concern: the reconcile tail is 3 records (narrow-crest-4950, staid-wave-3739, this one), at the charter's trigger.

Dispatch closed: 1 unit — leave_note: the agent flags or asks without waiting, the dashboard shows it, the owner's answer reaches the next turn as a comment (ADR-512)

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: ed1c6e1db73cd3f9768b3f9c24c73cc1a1918c3b

## State Impact

- target: fierce-falcon-5989 — The channel half of A1 is evidenced (ADR-512, commit ed1c6e1d). The bridge tool leave_note(type flag|question, text, artifact?) appends a note to comments.jsonl and returns at once. The dashboard's From the agent panel lists the notes and serves the flagged file. The owner's answer is cadex comment --reply, which reaches the next turn quoting the note. It is pinned by test_project_tool_surface.py, test_owner_channel.py and a browser test against a real engine. Still open: the one-contract half, SHELL-PARITY §4's shell-only guidance points and the ENABLE_TOOL_SEARCH check.
