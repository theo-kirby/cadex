---
node_id: bf438d8d-0f56-5993-b6fc-8aa713282b4a
slug: northern-hill-9362
title: Installed bundled engine refuses the hinged-arm design leg
created_at: '2026-09-08T01:08:38+00:00'
parents:
- empty-rain-5162
summary: ''
---
## What

Attempted the documented hinged-arm design leg against the existing ordinary installed Cadex.app engine, without launching the application. The public command refused at write_script with exit 3: cannot import name 'library_catalog_identity' from 'cadex_library_api', naming the bundled Mod/cadex/cadex_library_api.py. No accepted revision or digest was produced. Stop at this first failed leg as the selected bet requires.

## Why

Execute rank 1 of [rec: empty-rain-5162], protecting the working charter criteria “The walk exists and is tested headlessly” (crisp-reef-5607) and “The agent can see its work without a screen” (damp-moon-9297), missions 1, 2 and 6. This is the previously unqualified ordinary installed engine, not a repeat of clean development-tree walks. Existing lifecycle/review evidence stays working; this experiment establishes a deployment-path limitation, not a new claim that those criteria are unmet. The overseer's reconciliation request is treated as belonging to the separate maintainer: this work dispatch explicitly prohibits reconciliation and state/plan editing. Its requested planner selection already exists as the causal parent. No human question or Later promotion.

## Method

Read STATE.md, graph contract, ouroboros-actor and hypergraph-record skills, VISION, selected bet, historical bundle refusal and CLI engine resolution and walk documentation. Use a fresh scratch project at build/bundled-engine-iteration28/hinged-arm (inside the repository; no existing accepted project is modified). Reproduction command, with BUNDLE_ROOT set to the installed Cadex.app Contents/Resources/cadex manifest directory:

```sh
env -u CADEX_ENGINE_ROOT -u MESH_CADEX_ENGINE -u PYTHONPATH ./cadex script --engine "$BUNDLE_ROOT" --project build/bundled-engine-iteration28/hinged-arm --set examples/lifecycle/hinged-arm/script.py --json
```

The ordinary CLI shim chooses its existing pixi interpreter and adds cli/ to PYTHONPATH. No development module override, external-stage fallback, manual copying or build was used. Manifest schema cadex-engine-v1, version 0.0.0, protocol cadex-cadexd-v1, executable bin/freecadcmd, module_dir Mod/cadex. Path.resolve checks confirm manifest, binary and API module remain inside the installed bundle. SHA256 identities:

- cadex-engine.json: c23a9d1826ca88162605fce7f5e8b1849f50d149b9e16df8422562e8fe10dd1b
- bin/freecadcmd: ef31342ea2803e4cef8ac026ba7dec73753cbd70f0a3b239ef8f7776313c1096
- Mod/cadex/cadex_library_api.py: aebe70a7514a0237d9d06b04c4c6a7d73ebec907400aacab6b1f1ea41b062e4d
- Source src/Mod/cadex/cadex_library_api.py, comparison only: bf469234aa874519bf0715790353ac826f224b91df7910110b9514b651dfb3bc

The source API defines the missing function; textual search finds no such name in installed bundled module sources. The source worker imports it at cadex_project_worker.py:341. The reported failing API import is explicitly bundled, but this experiment does not identify the worker's full import closure or establish that all worker code came from the bundle. Do not call this a self-contained payload qualification. Raw command output stays in ignored build/bundled-engine-iteration28/design.log; this record preserves the outcome without machine paths or payloads.

## Result

Exit 3, ok false, engine source explicit, accepted_revision/digest/revision/session_id empty, outputs and params empty. The CLI scaffolded ARCHITECTURE.md, DECISIONS.md and PROGRESS.md; its envelope honestly says inside an existing git work tree, not initialised, not committed. No project-doc commit success is claimed. No training started, so no training time or memory budget was consumed. MJCF, task, policy witness, rollout, four views, interior section, inventory and named clearance review were not reached. Packaged lifecycle and full CLI gates were not run: the selected bet explicitly ends the unit on refusal. No product source, payload or shell change, build, GUI, remote or GPU execution occurred. This is failed qualification evidence, not a green runtime gate.

The prior historical import failure reproduces today on the installed engine route, with an older API copy demonstrably different from source. Next is the bet's conditional packaging refresh, through the documented packaging path after reading build_app.sh, with at most one full build; if prerequisites need multiple builds or a source fix, return that finding for a new bet. Do not silently substitute a fresh external stage. Bundle qualification still needs successful design, full walk/review and same-engine gates. Existing working charter criteria retain their completed evidence; no charter or ROADMAP box is changed and no removal/direction change requires an ADR. Graph export/check and git diff --check must pass before the single evidence commit. The unreconciled tail becomes two records; maintainer owns reconciliation.
Dispatch closed: 1 unit — reproduced installed bundled-engine design refusal and identified the missing bundled API symbol before training.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 38c98d06ee9fe4f7da01da7a174239f1b0049068

## State Impact

- target: early-arbor-7123 — Current installed bundle public design route reproduces missing library_catalog_identity refusal at exit 3; binary and failing API resolve inside bundle, worker import closure unqualified. Conditional packaging refresh is now evidence-backed.
- target: crisp-reef-5607 — Preserve working lifecycle evidence; ordinary installed bundle qualification stops at design before acceptance, training or review, pending supported packaging refresh and same-engine gates.
