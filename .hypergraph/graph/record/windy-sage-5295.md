---
node_id: e40d8d70-e4b7-503b-8d7c-cd5d8170a202
slug: windy-sage-5295
title: Harness-owned accounts, native login and discovered model selectors (ADR-184)
created_at: '2026-09-05T09:50:43+00:00'
parents:
- curious-sail-8332
- merry-water-7647
summary: ''
---
## What

ADR-184: replace baked-in shell model selectors with installed-harness discovery,
add native sign-in and account display, and preserve per-harness model choices.
The owner requested selecting a harness, logging in, seeing the logged-in account,
and selecting the models that harness offers.

## Why

The settings stored static Claude/Codex model enums and only instructed users to
log in elsewhere. The live Claude initialization menu already differed from those
choices. Account and model selection belong to the chosen CLI rather than a
Cadex-maintained provider catalog.

## Method

Added a pure harness module using Claude stream-JSON control initialization plus
`auth status --json`, Codex app-server `account/read` and paginated `model/list`,
and pi RPC `get_available_models`. Probes send no prompts. Subprocess deadlines,
cleanup, sanitized errors, and harness/path-scoped asynchronous snapshots keep
failure and credential handling out of the UI thread. pi account display uses
only identity/method metadata; API-key identities not reported by pi say so.

The header has a searchable model menu and an account popover; Settings > AI
exposes the same account/login/refresh flow. Native login opens in Terminal and
refreshes after completion, with a manual completion action for a closed terminal.
Tokens are not persisted in Cadex settings. Stable string model IDs replace enum
indices. The harness default omits the model override, and successfully discovered
catalogs flag and block unavailable saved IDs. Late pre-login results are discarded.
Updated VISION's stale Claude-only prohibition to reflect ADR-174/175/184, plus
BLENDER, ROADMAP and the append-only decision log.

## Result

- `python3 shell/tests/python/test_harness.py`: 9 tests passed. Covers all three
  discovery contracts, Codex pagination and hidden models, signed-out/no-auth
  distinction, secret exclusion, process cleanup, timeout/EOF, login quoting,
  and default/explicit models on fresh/resumed commands.
- `bash package/app/build_app.sh gate tests/python/bl_mesh_agent.py`: all tests
  passed on the rebuilt bundle. New UI checks cover selection, per-harness JSON
  persistence, account rendering, obsolete model IDs, old-menu rejection,
  stale discovery results, executable-key isolation and post-login refresh.
- `pixi run build-shell`: exit 0; built local Cadex 0.1.0 build 329. Its stage-only
  engine payload emits the existing relocation-audit diagnostics (248 violations)
  because this local payload resolves libraries from the checkout. This is a local
  build, not release-portability validation. All five changed/new application
  modules were compared byte-for-byte with the installed bundle and match.
- `pixi run gate` after rebuilding: OK, `ok: true`, 372/372 correct picks, slider
  median 0.492 seconds against the 0.650-second bar.
- Live read-only discovery against all three installed harnesses succeeded outside
  the sandbox: five Claude menu entries, seven Codex models, and pi's configured
  provider catalog. No account identities or credentials are recorded here.
- Sandbox-only probes could not see the complete credential state; shell gates
  could not open local sockets or hydrate engine output. Authorized unrestricted
  reruns resolved these environment failures. The first UI regression run also
  caught an offline-account display issue, fixed before the passing final run.
- No real OAuth sign-in or billable model turn was performed. Login launch/refresh
  is covered by scripted contract/UI tests; the user completes native OAuth.
- `git diff --check`: clean. No inherited Blender or engine source changes.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: 9ca1c2272101a3d935f37cde07fccb96d6be8a55

## State Impact

- target: shy-crane-2573 — Shell harness settings now discover account metadata and model menus from installed Claude, Codex and pi CLIs; native Terminal login refreshes account state, searchable menus persist per-harness IDs, and no baked-in shell model catalog remains (ADR-184). Local build and both shell gates passed; real OAuth login was not performed.
