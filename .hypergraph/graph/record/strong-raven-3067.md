---
node_id: 5e9240d4-09f2-5aa3-9f18-1c4630e39daa
slug: strong-raven-3067
title: Supported bundle refresh passes design, lifecycle and three gates
created_at: '2026-09-08T01:19:50+00:00'
parents:
- northern-hill-9362
summary: ''
---
## What

Refreshed the stale ordinary local Cadex application through the supported staging, shell build and bundle-install script, then reran the hinged-arm design and complete headless lifecycle against its installed engine. No product source fix or manual module copying was needed.

## Why

Follow the conditional refresh selected by [rec: empty-rain-5162] after [rec: northern-hill-9362] reproduced the missing library_catalog_identity import. Protect charter criteria “The walk exists and is tested headlessly” (crisp-reef-5607) and “The agent can see its work without a screen” (damp-moon-9297), missions 1, 2 and 6. Their prior working evidence remains valid; this unit qualifies the previously failing ordinary bundled deployment path. The reversible assumption is that the existing installed engine in pixi is sufficient for staging when its API matches source; test the resulting bundle rather than rebuild the engine speculatively. No Later criterion promotion or charter edit.

## Method

Read the actor and hypergraph-record skills, STATE, graph contract, parent evidence, VISION, build_app.sh including its toolchain scrub and install implementation, pixi tasks, engine payload staging script, CLI lifecycle docs and training setup. Source and pixi-installed cadex_library_api.py both hash bf469234aa874519bf0715790353ac826f224b91df7910110b9514b651dfb3bc and define library_catalog_identity; both pre-refresh application copies lack it. The existing engine install therefore meets this staging prerequisite without a second build.

Run `pixi run build-shell` (its dependency runs stage-engine), then `bash package/app/build_app.sh install`. The latter is the existing rsync/stamp-discovery install implementation with no build dependency and no application launch; neither pixi run app nor pixi run install-app was invoked. One full shell build invocation, six incremental Ninja steps, build 759, both commands exit 0. Payload MuJoCo 3.10.0 import and GUI-library exclusion checks passed. This is the documented unrelocated, local-only payload, not a portable release.

Set BUNDLE_ROOT to the manifest directory inside the ordinary installed application. Unset CADEX_ENGINE_ROOT, MESH_CADEX_ENGINE, MESH_FREECADCMD, MESH_CADEXD_MODULE and PYTHONPATH for the public commands; use explicit `--engine "$BUNDLE_ROOT"`. Create a fresh scratch project outside the parent checkout so the CLI owns its git repository:

```sh
./cadex script --engine "$BUNDLE_ROOT" --project "$PROJECT" --set examples/lifecycle/hinged-arm/script.py --json
JAX_PLATFORMS=cpu ./cadex walk --engine "$BUNDLE_ROOT" --project "$PROJECT" --out "$PROJECT/runs/baseline" --trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Wrap the walk in the existing process-tree monitor: sample RSS every 0.25 seconds, terminate above 2.9 GB or 850 seconds, with a five-second kill fallback. CLI gate uses the same whole-process-tree guard and CPU selection, bounding its training children too. The normal CLI shim adds cli/ to its own Python path; no development engine override or external-stage fallback is used.

Installed and built bundle identities match: manifest c23a9d1826ca88162605fce7f5e8b1849f50d149b9e16df8422562e8fe10dd1b; binary ef31342ea2803e4cef8ac026ba7dec73753cbd70f0a3b239ef8f7776313c1096; API bf469234aa874519bf0715790353ac826f224b91df7910110b9514b651dfb3bc; project worker 20544c5135fffb8829be634a1db4a1f7e9a7e3a39570743c9c372ac2239fa571; runtime 6c36853b7a8eb8b5b8659af5eb501f84eb16d93f0ed7a6fd851b99d8fcb8e824. All 56 top-level engine Python modules match between built and installed bundles. Existing development-prefix dynamic linking remains a documented limitation; no hermetic import-closure claim.

## Result

Design exits 0 and accepts de0dae7f91cb701274254132f3855ae23b2e3d40085165c946233fad4e847cc6. Complete walk exits 0: train, declare and rollout all succeed. Monitor: 16.0437 seconds, 1,054,588,928 bytes peak tree RSS, no cutoff. Training is CPU, one iteration, four environments, seed zero; reported training wall 1.19378 seconds, reward/step -0.3801981508731842, 4,609 parameters and witness error 1.3841167412209642e-09. Rollout total reward -27.109384220927513; accepted revision baf546fb9afbef313fc0b606d4eba3267506b87ee39f71b1ca3caa1fadfcc9c9 and digest 72d31498aff258780d0da14a77c62fe628e4af31430f616d3b9ef8864305e10e. These are toy execution measurements, not learned-control quality.

Visually inspected all four embedded PNGs from the generated SVGs: blue plate and orange projecting arm, consistent front/right/top/isometric placements. Reviewed the XZ section at Y=3.125 mm: both objects have closed contours, base spans X=0..60/Z=0..6 and swing X=12..92/Z=6..14. Inventory has two components and zero catalog IDs, explicitly uncatalogued. Clearance names base/swing as below the 0.1 mm minimum, distance 0 and common volume 0; one checked pair, zero unknown. This is initial solved pose, not swept clearance, and the section is tessellation rather than BREP.

The scratch project has five commits and a clean status. ARCHITECTURE.md, DECISIONS.md, PROGRESS.md, inventory, clearance, review JSON, all four views and section files equal project HEAD bytes. PROGRESS carries train, verify/rollout and clearance numbers. Its SHA256 is acab2956f6c6de898696f8564ee8e8197e050bb39f0c64c7705f9e5e65df90ea; review JSON is c25d854856ee22fb63c2780f4d968e100b1ef901cda66f48f1cdf2f53037f3fb. Scratch runtime assets stay outside this repository's commit; raw build, install, design, walk and gate logs remain in ignored build/bundled-engine-iteration29. This record preserves compact evidence without machine paths, checkpoints or rollout payloads.

Sequential verification, no exclusions: `CADEX_ENGINE_ROOT="$BUNDLE_ROOT" pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py -q -ra` passes 15 in 13.63 seconds; full `cli/tests -q -ra` against the same installed root passes 195 in 200.54 seconds, no skips. CLI monitor records 201.0795 seconds, 1,163,886,592 bytes peak RSS and no cutoff. The test suite includes fake/unit cases as well as real-engine/training cases; its protocol fixture deliberately loads source, so this is not a claim that every test exercised the installed payload. No remote dispatch occurred; remote contract tests use local fakes.

`pixi run gate` with engine overrides unset exits 0 against the ordinary built bundle, not the installed pathname (the documented wrapper fixes that location). Its matching engine modules/binary are recorded above. CADEX-BLENDER-GATE reports ok=true, engine_from_bundle=true, model_objects_on_open=1, restore.matches_accepted=true, slider median 0.523 seconds below 0.65, assembly render pixels [0,1024,1024], restored-source pixels [1024,0,0], and picking 372/372. The application ran only with --background; no interactive GUI or GUI-attached lifecycle walk was launched. No engine source suite or inherited CTest was rerun because no source changed; the requested packaged lifecycle, full CLI and shell gates all ran and passed.

Next: this clean supported refresh exhausts the selected stale-packaging direction. No further repair or replay is justified by this result. Existing working lifecycle/review criteria retain their qualification; nothing remains for this bundled-engine maintenance unit before those evidence claims can stand. Human-owned charter boxes remain untouched. GUI-attached mode remains documented-only, remote mode scripted-only, portable release unqualified. No source behavior, removal or direction change occurred, so no new ADR or ROADMAP feature checkbox is warranted. Graph export/check and diff whitespace validation are the final evidence-commit gates. Tail becomes three unreconciled records; the separate maintainer owns reconciliation, not this work iteration.
Dispatch closed: 1 unit — supported bundle refresh resolves design refusal and passes the complete CPU walk plus packaged lifecycle, CLI and background shell gates.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: cbd22c361bfa9dcad142cb3b41d8fc4c2f095afc

## State Impact

- target: early-arbor-7123 — Stale installed API resolved through stage-engine, one shell build and supported bundle install; complete ordinary installed-engine walk and same-root packaged/CLI gates pass, matching built-bundle background shell gate passes. Local-only deployment remains nonportable.
- target: crisp-reef-5607 — Preserve working criterion; previously failing installed bundle now accepts fresh hinged-arm design and full CPU walk in 16.04 seconds at 1.055 GB peak RSS, no source fix.
- target: damp-moon-9297 — Installed bundled walk now evidences four views, interior XZ section, inventory and named base/swing clearance pair with committed project bytes; initial-pose and tessellation limits retained.
