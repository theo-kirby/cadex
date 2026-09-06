---
node_id: 3738c538-6cb7-5843-a0e3-0954faaa6792
slug: small-hawk-3973
title: The lockout re-accept box (ADR-187)
created_at: '2026-09-05T22:31:39+00:00'
parents:
- twilight-isle-0370
summary: ''
---
## What

A project locked out by a restore failure now has a button back in (ADR-187). The chat panel draws a **Re-accept Stored Script** box when `cadex_backend.locked_out_project(scene)` is true — read off the `open_failure_code` ADR-186 cached on the per-root `_State`, so a panel draw opens nothing — and the parameters panel's alert row offers the same operator in place of Rebuild Model while the lockout stands. The operator, `MESH_AGENT_OT_reaccept_script` → `cadex_backend.reaccept_stored_script`, is the manual recovery ROADMAP recorded (`open_project restore=false`, then `write_script`) as one button: `ensure_open(unrestored_ok=True)` and then the engine's own stored source back through `write_script`.

Three smaller changes underneath it: the synchronous `ensure_open` now caches the failure code too (ADR-186 cached it from the pump only), `_open_unrestored` keeps it, and the accept of a `write_script` clears it with the restore warning; and the blocking `write_script` now runs through `begin_write_script`, so the tool path and the button path share one meaning of an accepted rewrite (it used to take its own `_lifecycle` route with `unrestored_ok=False` and no accept hook).

Files: `shell/scripts/startup/mesh_agent/cadex_backend.py` (`locked_out_project`, `reaccept_stored_script`, `write_script` over `begin_write_script`, the code cached on both open paths), `shell/scripts/startup/mesh_agent/ui.py` (the operator, the chat box, the alert row swap, registration), `shell/tests/python/bl_mesh_agent_cadex.py` (`test_a_locked_out_project_is_reaccepted_from_the_chat` and its workdir), `docs/DECISIONS.md` ADR-187, `docs/ROADMAP.md` (the lockout bullet becomes a ticked landed item), `docs/BLENDER.md`, `docs/ARCHITECTURE.md`.

## Why

Ouroboros run nt1, iteration 3. Target: the goal's priority 1 (file lifecycle, `simple-willow-8989`, status broken), its second done criterion ("a project locked out by a digest-moving change shows the re-accept box in the chat panel ... and `write_script` recovers it from the UI"), and the overseer's directive to take it next. Until this landed every digest-moving engine change shipped with a manual recovery [rec: western-badger-3023].

Assumptions taken alone (question policy: the reversible option, said out loud): the button sends the **engine's** stored source, not the `.blend`'s mirror — for the engine-moved case they are the same script, and a script edited outside Mesh is accepted **as edited**, which the operator's description says; reverting a hand edit is what a backup of the `.cadex` directory is for and the failure report still says so. The alert-row swap in the parameters panel is included because Rebuild Model refuses there, correctly, and the user was otherwise back at the alert row with nothing else to press. Not taken: a digest diff in the box, and a route that re-accepts from the mirror (that is `adopt_script`, for a different failure).

## Method

Read the state node, ROADMAP's lockout bullet, `ensure_open`/`_open_unrestored`/`begin_write_script`/`write_script`, the orphan box and `adopt_script` operator, the parameters panel alert row, and the four existing restore-failure gate tests. Wrote the backend pair beside `orphaned_project`, unified the blocking `write_script` onto `begin_write_script`, added the operator and the two panel hooks. Wrote the gate test to reproduce an engine move faithfully: the accepted digest in `script.json` is overwritten with the script untouched, the file is reopened through `load_post`'s queued open, and the operator is driven from the locked-out state through `bpy.ops` (poll first). Ran `pixi run gate` twice and the licensing test.

## Result

`pixi run gate` (the full `bl_mesh_agent_cadex.py` suite against the built bundle, engine from the bundle, add-on from source), second run: **OK, exit 0, 1136 checks ok, 0 FAIL**. The new test's 24 checks all pass: the queued open refuses the moved digest as a restore failure; the code is cached; `locked_out_project` is true and `orphaned_project` false; the parameters panel has a failure to draw; Rebuild Model returns `{'CANCELLED'}` and the digest stays moved; Re-accept Stored Script returns `{'FINISHED'}`; the code, the unrestored warning and the panel failure are cleared; the accepted digest is the true one again; the plate is back in the viewport; `get_script` no longer says "WITHOUT restoring"; one child per project; a fresh restoring open passes with `matches_accepted: true`; and the operator refuses a saved empty project. Gate report numbers unchanged from the previous unit: `model_objects_on_open = 1`, `hydrate_on_open_seconds = 2.061`, `open_seconds = 2.035`, slider latency within the bar.

The first gate run failed one check (1135 ok, 1 FAIL): the negative case ran `reaccept_stored_script` on a File > New scene, and the unsaved scene's temporary root — keyed by scene name, surviving across files — still held the previous test's model, so it was found and rewritten. A test-isolation fault, not a product one, and the same trap the ADR-186 `bpy.data.filepath` guard exists for; the check now uses a saved empty file. Recorded here because the trap is worth knowing.

`test_licensing_compliance.py`: 10 passed, 1 skipped — the whole diff is under `mesh_agent/` and `shell/tests/python/`, `docs/BLENDER-TREE.md` §2a untouched. The done criterion for the lockout is met; the `.cxpolicy` Save-As suffix is the last open item on the file-lifecycle node. The unreconciled tail is 1 node after this one.

Dispatch closed: 1 unit — the lockout re-accept box landed (ADR-187): drawn off the cached failure code, wired to write_script, gate test drives the operator from the locked-out state; next: the `.cxpolicy` Save-As suffix.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 3e83e255d69048ede2726d5beba0b98404fc05b3

## State Impact

- target: simple-willow-8989 — The second of the two open failures is fixed (ADR-187): a project whose restore pass fails at open shows a Re-accept Stored Script box in the chat panel, drawn off open_failure_code (now cached by both the hydrate-on-open pump and the synchronous ensure_open, kept by the unrestored reopen, cleared by an accepted write_script), and the parameters panel's alert row offers the same operator in place of Rebuild Model. reaccept_stored_script = ensure_open(unrestored_ok=True) then the engine's stored source through write_script; a hand edit is accepted as edited, by design. The blocking write_script now runs through begin_write_script (one accept path). Gate test test_a_locked_out_project_is_reaccepted_from_the_chat moves the accepted digest with the script untouched and drives the operator from the locked-out state: 1136 checks, 0 FAIL. Negative knowledge to retire: 'Rebuild Model cannot recover a lockout and no button reaches the remedy' -- Rebuild Model still refuses (correctly), but the button now exists; every digest-moving change no longer ships with a manual recovery. New negative knowledge (scope: gate tests on an unsaved scene, confidence high, evidence this node): an unsaved scene's temporary root is keyed by scene name and survives File > New, so a negative check against a fresh empty scene can find an earlier test's model there; use a saved empty file. Still open on this node: the .cxpolicy Save-As suffix.
