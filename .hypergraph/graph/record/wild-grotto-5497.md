---
node_id: 0e12f475-cc64-55e6-9911-163a0b98c16d
slug: wild-grotto-5497
title: 'Save-As carries a trained policy (ADR-188): verified and recorded'
created_at: '2026-09-06T01:02:36+00:00'
parents:
- small-hawk-3973
summary: ''
---
## What

Save-As now carries a trained policy across (ADR-188), and this node is the record iteration 19 did not leave. `POLICY_SUFFIXES = (".cxpolicy", ".json", ".xml")` joins `ASSET_SUFFIXES` and `LINKED_PART_SUFFIX` in `shell/scripts/startup/mesh_agent/cadex_backend.py`, and `CARRIED_ASSET_SUFFIXES` becomes the union of the three — which is now exactly the engine's `_STORED_ASSET_SUFFIXES` (checked this iteration by reading both: seven suffixes each, the same seven). `_assets_in` still walks the origin's `assets/` flat, skips symlinks, and hands every path to `put_asset`, which stays the store's sole writer and re-validates each one. The gate's `test_save_as_carries_imported_geometry` grew the policy triple (fabricated bytes, because the store validates suffix and the carry is about bytes) and a `notes.txt` negative written straight into the origin's `assets/`.

Files, all in commit `2544d3da` ("ouroboros #19: no record"): `cadex_backend.py`, `shell/tests/python/bl_mesh_agent_cadex.py`, `docs/DECISIONS.md` ADR-188, `docs/ROADMAP.md` (the Save-As-drops-a-policy bullet ticked), `docs/BLENDER.md`, `docs/ARCHITECTURE.md`. This iteration adds no code: it verifies and records.

## Why

Ouroboros run nt1, iteration 20. Target: the goal's priority 1 (file lifecycle, `simple-willow-8989`, status broken), its third done criterion ("Save-As carries `.cxpolicy` forward — the shell suffix list"), and the overseer's directive after iteration 19: report the gate numbers in the record node. Iteration 19 landed the change and the ADR, then hit its session limit while the gate was still running; the iteration log says `recorded: false`, and no record node cites ADR-188. Unrecorded work is invisible to the project, so this unit is the verification the previous one could not finish plus its record — one causal step, taken rather than duplicated.

Assumption stated alone (question policy): the ADR-086 §4 parking of "`_ASSET_SUFFIXES` stays at three members" is respected, not overridden — the engine's mirrored three are untouched and the policy suffixes are a third named tuple in the shell, which is what ADR-138 did for `.cxpart`. The goal's done criterion names the carry, so this is in scope by directive, not by drift. Not taken: the equality guard between the engine's union and the shell's carry list. ADR-188 §4 names it as the obvious next guard and says why it is not in the shell suite (it cannot import the engine); an engine-side test would have to read the GPL shell file's text, which is the boundary AGENTS.md calls one-way and hard, so that stays a doc statement until someone decides otherwise.

## Method

Read iteration 19's commit, its ADR, the iteration log and the overseer verdict. Confirmed no record node cites ADR-188. Read both suffix constants — `CadexScriptedRuntime._STORED_ASSET_SUFFIXES` from the engine and `CARRIED_ASSET_SUFFIXES` from the shell — and compared them. Ran `test_licensing_compliance.py` (the ADR-171 guard that the inherited diff manifest still matches). Ran `pixi run gate` — the full `bl_mesh_agent_cadex.py` suite against the built bundle, add-on from source, engine from the bundle — against the tree as committed, and read the report numbers off it.

## Result

Engine `_STORED_ASSET_SUFFIXES` and shell `CARRIED_ASSET_SUFFIXES`: the same seven suffixes (`.stl .obj .ply .cxpart .cxpolicy .json .xml`). `test_licensing_compliance.py`: 10 passed, 1 skipped — the whole diff is under `mesh_agent/` and `shell/tests/python/`, `docs/BLENDER-TREE.md` §2a still eight files.

`pixi run gate` (the full `bl_mesh_agent_cadex.py` suite against the built bundle): **OK, exit 0, 1142 checks ok, 0 FAIL** — six more checks than the 1136 of the ADR-187 run, all of them ADR-188's. `test_save_as_carries_imported_geometry` passes every new check: the three policy files land in the origin store through `put_asset`; the carry offers exactly the two STLs and the policy triple and never the `notes.txt` written straight into `assets/`; the adoption report names all five ("Carried 5 imported file(s) over from asset-orig.cadex"); the new store holds exactly the five; and the carried `.cxpolicy` is byte-identical. Report numbers unchanged from the previous unit: `model_objects_on_open = 1`, `hydrate_on_open_seconds = 2.08`, `open_seconds = 2.022`, median preview latency 0.007 s.

With this the three done criteria for the file lifecycle are met: hydrate on open (ADR-186), the lockout re-accept box (ADR-187), and the `.cxpolicy` Save-As carry (ADR-188). The state node's reason for staying `broken` was the last of these; the reconcile decides the flip. The unreconciled tail is one node after this one.

Dispatch closed: 1 unit — ADR-188 (Save-As carries `.cxpolicy` with its task bundle and MJCF) verified and recorded: the carry list equals the engine's stored union, gate run reported below; next: the lifecycle audit (run the rehearsal path headlessly and record the lifecycle frontier).

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt1
- commit: 7712860385c0b5e61e66c28e8e65d35f2bb604c8

## State Impact

- target: simple-willow-8989 — The adjacent gap is closed (ADR-188, landed in iteration 19's commit 2544d3da, verified and recorded here): Save-As now carries a trained .cxpolicy with its .json task bundle and .xml MJCF. POLICY_SUFFIXES joins ASSET_SUFFIXES and LINKED_PART_SUFFIX in the shell's CARRIED_ASSET_SUFFIXES, which now equals the engine's _STORED_ASSET_SUFFIXES (the same seven suffixes, compared this iteration); _assets_in still hands every path to put_asset, the store's sole writer. Gate test test_save_as_carries_imported_geometry carries the fabricated policy triple beside two STLs and refuses a notes.txt written into assets/: 1142 checks, 0 FAIL, byte-identical policy in the copy. Negative knowledge to retire: 'Save-As carries assets through the shell's own suffix list, and .cxpolicy has the same gap' -- the list is now the engine's whole union, so the residual rule is only that a future engine suffix must be added to both (no equality test exists; the shell suite cannot import the engine and an engine test may not read the GPL file). All three measured failures and the adjacent gap are fixed (ADR-155, ADR-186, ADR-187, ADR-188); the reason this node stayed broken is gone, and the reconcile decides whether it flips to working.
