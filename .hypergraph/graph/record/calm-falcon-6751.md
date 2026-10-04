---
node_id: ae4f1e77-1636-5d04-a707-8ac0e2ac9235
slug: calm-falcon-6751
title: 'orun2 D2 item 5: the collision view reports which parts touch at rest, to the dashboard and the agent (ADR-508)'
created_at: '2026-10-03T19:00:24+00:00'
parents:
- sweet-mist-9111
summary: ''
---
## What

orun2 D2 item 5, its collision-view slice: the dashboard and the agent both report which parts touch at rest (ADR-508).

- **Engine:** a new `core.inspect` scope value, `contacts` (`CadexInspection._complete_contacts`, `contact_pairs`). It reads each `assembly.mjcf` export's stored t=0 contact evidence (`assembly_data.dynamics.initial_contacts`, measured by `CadexDynamics._initial_contacts`, ADR-087) from the pinned accepted attempt. It groups the contacts by component pair: points, penetrating, deepest signed mm, penetrating pairs first. It carries `pose` and `measures` (collision shapes, not solids), and says why when there is no export or no evidence. No `OP_ARG_SPECS` change.
- **Tool surface:** `contacts` is added to `INSPECT_SCOPES` and to the `inspect` scope/target descriptions (`cli/cadex_cli/tools.py`), and pinned in `test_project_tool_surface.py`. One guidance bullet in `CadexAgentGuidance.md`.
- **Dashboard:** `review_server.initial_contacts` puts a `contacts` block on the accepted model manifest; a borrowed run model gets the accepted one. `#collision-contacts` under the collision toggle shows a head line and one line per pair, with interpenetration in `--bad`.
- **Docs:** ADR-508, DASHBOARD.md §11a, the INTEGRATION.md inspect row, and three SHELL-PARITY rows (`cadex_collision.py`, `collision_view`, Environment) moved to ported with tests.

## Why

The critic's message for iteration 22 asked for two things, in order.

1. **The missing record for iteration 22.** Done as `sweet-mist-9111`, parented to `stormy-grove-7025`, with impact on `twilight-aspen-1541`. Iteration 22's transcript showed its final full CLI run was killed before it reported, and that record says so.
2. **D2 item 5 (Inspect), with the collision view carrying the agent-side t=0 contact report under the tool-surface rule.** Item 5 has four parts: section, exploded, collision, and rollout playback. Each needs its own real-engine browser test, so the four together are more than one unit. This unit is the collision part, the one the critic singled out, done whole: the viewer readout, the agent scope, and a test that they agree.

Still open in item 5: section, exploded, and rollout playback.

## Method

- **Before writing anything, I measured where the evidence lives.** An accepted ot11-quad-1 attempt carries `initial_contacts` on its mjcf output's `assembly_data.dynamics`. It does not appear in `scope=output`, because `assembly_data` is not among the `_OUTPUT_DETAIL_KEYS`.
- **The fixture is a real build.** A slider block plus a post jointed to it, both on a grounded floor.
  - The joints exclude block/floor and block/post from contact.
  - At sink 0 mm, MuJoCo reports 0 contacts, face on face.
  - At 2 mm it reports floor/post as 4 points, each at −2.0 mm, penetrating.
- **The browser test runs against a real engine** (`cli/tests/test_dashboard_inspect.py`).
  - The page names floor · post as interpenetrating 2.0 mm, 4 point(s).
  - The agent's `inspect scope=contacts` through cadexd returns exactly the `/api/model/accepted` pairs.
  - The page's own slider then runs `cadex params` with `sink=0`. The readout goes to `clear`, and the agent's scope returns `[]`.
- **Verification**, with the GPU hidden for the CLI suite:
  - `pixi run test-engine`
  - `pixi run python -m pytest cli/tests`
  - `pixi run build-engine` and `stage-engine`, then the packaged lifecycle gate.

## Result

- **The collision part of D2 item 5 has evidence.** Proof: `test_browser_names_the_parts_touching_at_rest_and_the_agent_reads_the_same`, in headless Chromium against a real engine. The owner note's agent half of `collision_view` (t=0 contacts without a person looking) is in place as `inspect scope=contacts`, and the tool-surface test pins it.
- **Suites:**
  - `pixi run test-engine`: 2592 passed, 56 skipped.
  - `pytest cli/tests` with the GPU hidden: 1335 passed, 1 skipped (the usual `CADEX_REVIEW_HOST` one).
  - After `build-engine` and `stage-engine`, the packaged lifecycle gate passed 24 on the restaged payload. That payload's `CadexInspection.py` contains the new scope.
  - Commit `dafe9fc3`.
- **Iteration 22's code is covered by this full CLI run.** Its own full CLI run had never reported.
- **Concerns and assumptions:**
  - The pair grouping exists twice, about 15 lines each, in the engine and in `review_server.py`. That is because `cli/` may not import the engine. The browser test pins that they agree.
  - The readout covers the accepted model. A run model that borrows the accepted identity reuses it. A run with its own trace says the contacts come from the accepted export only.
  - Pairs are grouped from the 64 contacts the export lists. `pairs_complete` says when that list was cut.
  - It measures MuJoCo collision shapes, not the exact solids, and the value says so.
  - No new dependency. No `OP_ARG_SPECS` change.
- **Open in D2:**
  - Item 5: the section view (an interactive cut in the viewer), the exploded view (reading the engine's `exploded_view` moves), and rollout playback (frames through `setPoses`, not only the first pose).
  - Item 6: STEP/STL export and the concept-sheet download.
- **The tail is 2 unreconciled records** (`sweet-mist-9111` and this one).

Dispatch closed: 1 unit — D2 item 5's collision view: t=0 contacts in the dashboard (#collision-contacts) and to the agent (inspect scope=contacts, ADR-508), agreement browser-tested against a real engine

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun2
- commit: dafe9fc35a4342aa2804b4a85d28d1a299d263c2

## State Impact

- target: twilight-aspen-1541 — item 5 collision view evidenced: #collision-contacts lists the MJCF export's t=0 contacts by pair and inspect scope=contacts gives the agent the same (ADR-508); headless-Chromium test against a real engine shows page and agent agree and the slider clears a 2 mm interpenetration; open: item 5 section, exploded, rollout playback; item 6
