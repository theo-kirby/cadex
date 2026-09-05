---
node_id: e5a999bd-63b8-5493-9201-04feafff7da7
slug: simple-bramble-8616
title: Built xscript-owned native Blender mesh recipes
created_at: '2026-09-05T11:20:37+00:00'
parents:
- clear-sand-8062
summary: ''
---
## What

Implemented native Blender geometry recipes as mesh.blender in the authoritative xscript, following the owner's explicit approval to build the proposed system. Added a hybrid enclosure example, a saved local demo, documentation and ADR-185. This is the approved direction change after clear-sand-8062, not a restoration of live-scene authoring.

## Why

The proposal identified native bpy fluency as useful agent capability and the existing recursive CAD/mesh value evaluator as a bridge. One source of truth need not mean one geometry runtime. The owner approved that proposal, including revisiting the eventual Blender-dependency restriction. Exact mounting geometry remains CAD; organic results stay meshes, composed through named inputs and shared dimensions/frames.

## Method

Added the mesh API operation and two independently authored LGPL adapters staged by filename. The FreeCAD worker recursively resolves named mesh inputs, serializes finite geometry and values, and launches a Blender evaluator under macOS sandbox-exec or Linux bubblewrap. The visible shell passes its executable through the child environment; cadexd never imports bpy or either new adapter. The numeric Blender version is explicit, seeds are declared, and canonical topology, source/inputs and executable/evaluator identity join the digest. The existing project transactions, store, revisions and hydration carry the resulting mesh. Blender-derived trees remain refused by BREP conversion and exact routing consumers.

Verified native BMesh, object transforms, evaluated modifiers, units, fresh-process rebuild equality, version/error refusal, file/network sandbox denial and timeout. Tested that cancellation kills a nested worker ignoring SIGTERM and that identity includes winding, recipe and runtime changes. The hybrid protocol test covers CAD-to-Blender inputs, mesh soundness, parameter change/reversal, recipe failure/source rollback, STL export and reopen. Added a shell integration gate covering the real agent-turn undo accounting and hydration using its own runtime discovery. Built with pixi run build-engine and pixi run build-shell, using the required shell toolchain scrubber.

## Result

- Full final source engine suite, with CADEX_BLENDER_EXECUTABLE set: 1969 passed, 47 skipped in 266.56 seconds. The skips are explicitly gated tests; native recipe tests ran.
- Packaged engine lifecycle plus recipe suite, with CADEX_ENGINE_ROOT selecting the staged manifest: 35 passed in 25.24 seconds.
- Final application gate passed with native recipe coverage: one undo push per agent turn, hydrated mesh, geometry following mounting spacing, original digest restored by parameter reversal, and accepted geometry retained on recipe failure. The bundle reports 908 recipe facets and 62 mm width. Ordinary CAD slider latency remained within its existing 0.65-second bar (median 0.542 seconds); picking was 372/372. These are the existing CAD gate measurements, not a claim that native recipe rebuilds meet that slider bar.
- The saved local demo is build/blender-enclosure.blend with its sibling .cadex project and print/skin.stl. Export contains 908 triangles and 45484 bytes. The independently checked enclosure is a closed, sound mesh. The tracked source is examples/blender_enclosure.py. No live wolf project was touched and no wolf-quality improvement is claimed. Background multi-view rendering is unavailable by the existing shell contract; no image was generated.
- Negative results resolved during implementation: the first macOS profile denied Blender startup's root-directory read; allowing that literal directory made startup work without granting user-file reads. The first CAD example incorrectly fused two disconnected rails; declaring a compound fixed it. The first full suite found the expected worker-bundle whitelist change and observed ccx while a concurrent staging run was still pruning the payload; both pass after updating the declared bundle and testing the completed payload. A direct relative-path app launch exposed bpy.app.binary_path being relative; the shell now normalizes it before handing it to cadexd, and the saved-demo run passed through the installed package.
- Native runtime/application validation was on macOS with Blender 5.3.0 Alpha. The Linux bubblewrap path has not been exercised on a Linux host. Windows fails closed. Output is evaluated triangles, not UV/material/animation interchange, a live modifier stack or analytic BREP reconstruction. Arbitrary nondeterministic recipes are not promised reproducible; an accepted-digest mismatch refuses restore.

No protocol op, output kind or inherited Blender file changed. The optional Blender geometry dependency survives a future UI replacement; ordinary engine-only projects still require no Blender. VISION, the agent contract, architecture, scripting, process, shell, CLI, provenance and roadmap docs are updated with ADR-185 and the recipe contract.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: main
- commit: da7787ea063cecb24ea1441db615ea7097390ab8

## State Impact

- target: forest-wind-0342 — mesh.blender adds native Blender recipes through an OS-isolated worker; ordinary mesh artifacts retain the existing protocol and acceptance lifecycle. Source engine suite 1969 passed, packaged suite 35 passed.
- target: idle-lantern-9094 — Script-owned bpy recipes now compose named CAD-derived mesh inputs and JSON dimensions/frames with organic mesh outputs. The hybrid enclosure rebuilds, exports and restores; this does not implement O4 NURBS fitting.
- target: shy-crane-2573 — The shell supplies an absolute Blender runtime path to cadexd, while the live scene still only hydrates accepted output. Native recipe parameter changes, rollback and one undo push pass the application gate.
- target: early-arbor-7123 — Native recipe projects need CADEX_BLENDER_EXECUTABLE when run headlessly; the shell supplies its own binary. macOS verified; Linux bubblewrap path unverified on Linux and Windows refuses. Ordinary engine-only projects need no Blender.
