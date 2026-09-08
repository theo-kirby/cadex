---
node_id: 3ff8c8cd-fdcb-5c3d-a8f1-e05e6df6d61c
slug: early-gate-3510
title: Bound catalog dependency paths and cold-report identity limits
created_at: '2026-09-08T04:22:48+00:00'
parents:
- brave-pebble-4147
summary: ''
---
## What

Execute the bounded catalog dependency experiment selected in brave-pebble-4147 and scoped in snowy-cove-0032. Three fresh scratch projects pass real-kernel acceptance. Existing serialized definitions separate direct, transformed-fuse and cut-tool dependencies; a discarded catalog value has zero reachable paths. The surviving pan-tilt's two fused servo definitions can be matched using a newly evaluated run-local identity map, but cannot be labeled from its cold accepted report alone. Stop at that identity boundary; no diagnostic implementation follows.

## Why

Advances missions 2 and 6 and charter criterion **The agent can see its work without a screen** (`damp-moon-9297`) by bounding its fused-hardware blind spot. This is the selected first short unit, not a new direction. Assumption: syntactic dependency matches are useful research evidence, but neither provenance of an individual generator invocation, surviving material, purchases nor missing hardware. Preserve shipped placed-instance counts and placement guidance.

The overseer's reconciliation request is already reflected in the checkpoint and planner bet. This actor dispatch explicitly forbids reconciliation; no state, plan or charter edits occur. At completion the clock reads 2026-09-08 04:21 UTC, still before the 06:30 UTC provider eligibility gate. No provider request, quota probe, wait, training, GUI, remote action or paid fallback.

## Method

Read STATE, graph contract, VISION, actor and record skills, the causal bet and discovery/repair/guidance records; inspect the existing library identity map, project execution, part operation definitions and lifecycle client. Tree clean on arrival. All scratch scripts/projects/logs remain outside the checkout. Identify engine explicitly: `build/engine/cadex-engine-0.0.0-macos-arm64`, manifest `module_dir=Mod/cadex`, `freecadcmd=bin/freecadcmd`. Both declarative probes import that payload's modules, and the real NDJSON client uses `CADEX_ENGINE_ROOT` pointing to that payload. Assert CadexScriptedRuntime.py SHA256 `602164e85c399ad203517eb269ec81bca549dc07b72d303659c1cffffe1dc6df` before probing. Do not rebuild or requalify the already-qualified repair. The installed application is not used.

Local reproduction drivers/logs are `/tmp/cadex-44-discovery.py`, `/tmp/cadex-44-discovery.log`, `/tmp/cadex-44-isolated.py`, `/tmp/cadex-44-isolated.log`; each final `pixi run python <driver>` exits 0. They are uncommitted local evidence, not durable artifacts. The measured sources and procedure below permit reconstruction without them.

For declarative execution use the payload's `cadex_project_worker._staged_globals(CadexScriptedRuntime._project_api_contracts(), {}, {})`, then `_execute_project_source(source=source, document_name='Probe', document_objects=[], inputs={}, globals_by_name=globals, max_operations=400000, max_seconds=60)`. Copy `library_catalog_identity()` immediately after each evaluation. This is payload construction, not geometry execution. Canonicalize definitions with `json.dumps(d, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)`, exactly the current library's join key.

Walk each selected assembly source output's definition from `$`. At each node, record a matching canonical definition before descending. Traverse only these explicitly measured shape-input edges: fuse `arguments[0]` list as `fuse.input`; transform `arguments[0]` as `transform.source`; cut `arguments[0]` as `cut.base` and `arguments[1]` list as `cut.tool`. Append list indices to paths. Unknown operations have unknown roles and are not traversed by this bounded probe; zero reported hits there is not proof of no dependencies. Do not infer Python variable names or deduplicate distinct paths into occurrence counts.

The combined real-kernel source is:

```python
servo = lib.servo("mg90s")
unused = lib.bolt("M3", 12)
block = part.box(50, 50, 50, origin=[-25,-25,-25])
moved = part.transform(servo.body, translation=[2,0,0])
fused = part.fuse([block, moved])
cut = part.cut(block, [moved])
a = assembly.component(servo.body, grounded=True, label="first")
b = assembly.component(servo.body, placement=[100,0,0], grounded=True, label="second")
f = assembly.component(fused, placement=[200,0,0], grounded=True)
c = assembly.component(cut, placement=[300,0,0], grounded=True)
asm = assembly.assembly([a,b,f,c], [])
result = {"servo":servo.body,"fused":fused,"cut":cut,"first":a,
          "second":b,"fused_component":f,"cut_component":c,
          "assembly":asm,"solve":assembly.solve(asm)}
```

Drive the existing test_cadexd_lifecycle `_spawn_cadexd` client through `open_project` on a fresh temporary directory, `write_script` with source above and empty expected_revision, then `inspect scope=inventory`. Read `script.json` and its `accepted_attempt.staging/result.json`, and assert accepted-definition paths equal declarative-definition paths. Stop the client in finally. Source outputs are the four components' named sources, not recursively re-counted copies in the assembly definition.

Repeat in separate fresh projects for cut-only and discarded-only cases. Both use suffix `c=assembly.component(x,grounded=True); a=assembly.assembly([c],[]); result={"source":x,"component":c,"assembly":a,"solve":assembly.solve(a)}` (separate Python lines). Cut-only prefix: `s=lib.servo("mg90s"); b=part.box(50,50,50,origin=[-25,-25,-25]); x=part.cut(b,[part.transform(s.body,translation=[2,0,0])])`. Discarded-only prefix: `s=lib.servo("mg90s"); x=part.box(1,2,3)`. Require successful acceptance, one component, empty placed catalog counts, and respectively one and zero dependency matches.

Inspect the unchanged scratch project `cadex-nt3-i35-pantilt` under `/tmp`: resolve its accepted report through script.json, and evaluate its unchanged script declaratively with stored param_values, without loading policy assets or building geometry. Join that fresh evaluation's identity map to the historical accepted solid definitions. Independently attempt the same traversal with only whole-output catalog stamps from the cold report. Hash the accepted report before and after; require equality. No accepted project is reaccepted or edited.

Two negative controls: (1) two temporary LibraryPart wrappers named probe/alpha and probe/beta over the same box definition leave only beta in the existing map, demonstrating overwrite, not disambiguation; classify true identity as unknown. (2) compare `s=lib.servo("mg90s"); result={"servo":s.body}` with the same source plus an unused identical servo call: maps and output definitions are equal, so the unused occurrence adds no path but occurrence provenance is unrecoverable. A fabricated unknown operation is not assigned an input role.

Initial scratch-driver errors were corrected before the final probes: Python's platform temp root did not contain the historical project (use its actual `/tmp` location); the first combined source omitted required solver_diagnostics (add assembly.solve). The latter correctly returned DOMAIN_CANDIDATE_FAILED with “An Assembly program must return exactly one assembly and one solver_diagnostics output.” These were probe mistakes, not product defects. Its stderr also contained the known `No module named 'freecad'` startup diagnostic; no new gate failure is inferred from it.

## Result

All three final scratch acceptances and both final driver commands exit 0. No product source, behavior, protocol, registry, metadata or test changes; no full build, zone suite or packaged qualification is claimed. This read-only experiment's verification is its assertions against accepted real-kernel artifacts plus graph export/check and diff check before commit.

| Source output | Definition path | Syntactic role | Definition match |
| --- | --- | --- | --- |
| combined servo | `$` | direct source reused by first and second components | servo/mg90s |
| combined fused | `$.arguments[0][1].arguments[0]` | fuse.input → transform.source | servo/mg90s |
| combined cut | `$.arguments[1][0].arguments[0]` | cut.tool → transform.source | servo/mg90s |
| isolated cut-only source | `$.arguments[1][0].arguments[0]` | cut.tool → transform.source | servo/mg90s |
| isolated discarded source | no paths | unused servo does not reach output | none |
| pan-tilt base_solid | `$.arguments[0][2]` | fuse.input | servo/mg90s, fresh-map join only |
| pan-tilt yoke_solid | `$.arguments[0][4]` | fuse.input | servo/mg90s, fresh-map join only |
| pan-tilt head_solid | no matches | custom geometry | unknown catalog identity |

Combined inventory remains **4 components, servo/mg90s: 2 placed instances**, with fused and cut listed as uncatalogued sources. The unused M3 bolt has zero matches across all three combined source definitions. Isolated cut-only and discarded-only inventory each remains **1 component, 0 placed catalog counts**. These observations demonstrate why dependency paths must not be added to placed counts. One body feeding both a component and a cutter remains one direct source used by two placements, plus distinct boolean paths.

Pan-tilt retains 14 historical outputs and zero catalog stamps; accepted report SHA256 remains `03b65bbf9ef821a753a62a9dc13359889ef79810d21c67da9c58fb6faa618c9d`. Its cold identity map is empty, so both labels above are unavailable from that report alone. Re-evaluation supplies definition matches, not historical evaluation provenance; no claim of fresh pan-tilt kernel acceptance. Registry overwrite and identical discarded-call controls prohibit inferring occurrence identity, even when definitions match exactly. Unknown roles and ambiguous provenance remain unknown. Traversal never tests material survival.

The advantage over shipped placement guidance is narrow: with evaluation-time knowledge, a reviewer can point to the named fused output and exact boolean input containing a catalog-shaped definition. It cannot make the cold accepted inventory complete, establish purchases or certify that hardware survives the fuse. The cold identity/ambiguity stop conditions are reached. No parser, persisted identity table, new field or automatic reaccept is authorized; any implementation needs a later bet. Fresh agent compliance with placement guidance remains unmeasured.

Next: replan on this result, retaining the pending two-servo rehearsal for controller scheduling at provider eligibility. Do not dispatch an actor merely to repeat the unchanged pre-reset blocker. Existing reconciled lifecycle and review criteria remain working; this evidence closes no additional charter checkbox. What remains for this narrower review limitation is a separately justified identity contract and implementation if the planner chooses one; nothing in this unit authorizes that work. Two unreconciled records now remain; the maintainer owns reconciliation.

Dispatch closed: 1 unit — bound catalog dependency paths with real-kernel controls and stop at cold identity and occurrence ambiguity.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 3a548eaacf4afbd4f3e06372e2ff363ebef1c1ca

## State Impact

- target: damp-moon-9297 — Real-kernel scratch controls separate direct, fused, cut-tool and discarded dependencies without changing placed counts; pan-tilt labels require fresh evaluation identity, and equal definitions lose occurrence provenance. No diagnostic implementation authorized.
