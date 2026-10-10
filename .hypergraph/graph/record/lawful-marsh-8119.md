---
node_id: dfa2fdee-5ca2-560f-90ff-6e26cd805f89
slug: lawful-marsh-8119
title: 'Unused inherited trees and options removed: Show, XDGData, MacAppBundle, 3Dconnexion/OpenGL, VR, designer plugin, JtReader gate (ADR-629)'
created_at: '2026-10-10T12:48:03+00:00'
parents:
- solemn-ivy-5988
- steady-dew-8037
summary: ''
---
## What
Removed the unused inherited FreeCAD trees and options the docs audit listed (DOCS-AUDIT.md §4 item 10), after the owner approved: `src/Mod/Show`, `src/XDGData`, `src/MacAppBundle`, `src/3rdParty/3Dconnexion` and `src/3rdParty/OpenGL`, the `BUILD_VR` option (with `cMake/FindRift.cmake`), the `BUILD_DESIGNER_PLUGIN` option (with its macro and `src/Tools/plugins/widget`), the dead `BUILD_JTREADER` gate, `FREECAD_CREATE_MAC_APP` and the 3Dconnexion options. Two commits under the removal protocol: disable `c911a5d8`, delete `e3b8ecd3`; ADR-629.

## Why
The engine builds with BUILD_GUI=OFF and src/Gui is deleted (ADR-214), so these trees and options served only the GUI or a desktop app bundle. Nothing was kept, because the dependency audit found no used dependant:
- Show's importers were Part's GUI-only TaskAttachmentEditor.py, inside its own try/except ImportError fallback, and one inherited Test case (`Document.py` testContainerChainGroupInPart) that tested Show's ContainerChain.
- XDGData had no CMake reference.
- MacAppBundle's only other consumer was a QuickLook signing block.
- 3Dconnexion and OpenGL were built by no CMake file.
- VR and the designer plugin fed only src/Gui and a Qt Designer plugin.
- src/Mod/JtReader does not exist.

## Method
- Audit: grep over CMake, src/, tests/, pixi.toml, package/, tools/, cli/tests and cadex_tests.
- Disable: forced-OFF cache entries (the ADR-217 pattern). Also: dropped `add_subdirectory(MacAppBundle)`, dropped Show from the payload keep_mods, removed the Show test case (Document.py is now manifested and noticed, 57 entries; CRLF preserved by a byte-level edit, because tools/apply_modification_notices.py rewrote the whole file to LF), and removed the rattler 3Dconnexion driver install.
- Delete: `git rm` of 88 files / 30,586 lines; then the options, gates, report lines, Qt Designer component, presets, the QuickLook signing block, the dead weak-link allowance, dev-config entries and the THIRD_PARTY_LICENSES rows (13 trees to 11).
- Gates were run in the worktree, CPU-only (`CUDA_VISIBLE_DEVICES=`), against a baseline built from unmodified 091e962a. `build/ctest_baseline_failures.txt` does not exist, so the comparison is to that baseline run.

## Result
- Baseline (091e962a):
  - release build: 2,120 steps, exit 0;
  - CTest -j16: 1,526 run, 1 failed (ImporterTest.TestOBJ);
  - `FreeCADCmd -t Document`: 121 run, 1 failure (testColorList);
  - test-engine: 2,777 passed / 62 skipped;
  - cli/tests: 1,259 passed / 1 skipped.
- Disable:
  - Configure, and an explicit `-D...=ON` reconfigure, left every option OFF/None, with no Show or widget rule in build.ninja.
  - The stale build/release/Mod/Show was moved out. Build exit 0.
  - CTest: the same single failure.
  - Document: 120 run, the same failure.
  - FreeCADCmd probe: `PROBE-OK imports=10 show=ABSENT volume=6.0`.
  - Licensing, guardrail and build-option tests: 21 passed / 3 skipped.
- Delete:
  - `cmake -U` of the dropped entries, then build exit 0.
  - A fresh-cache configure into an empty directory exits 0, with no removed option in its cache or report.
  - CTest: 1,526 run, the same single failure, no new names.
  - Document and the probe: as above.
  - test-engine 2,777 / 62 and cli/tests 1,259 / 1: identical to the baseline.
  - install-release and stage-engine exit 0; no Show in the installed Mod/ or the payload Mod/.
  - Packaged gate (CADEX_ENGINE_ROOT=payload, lifecycle + licensing): 36 passed.
  - Committed-HEAD licensing, guardrail, build-option and project-docs tests: 50 passed / 3 skipped.
- Not run: macOS or Windows builds. The MacAppBundle, QuickLook-signing and 3Dconnexion-driver removals are unexercised on Apple.
- The negative lesson: apply_modification_notices.py --write normalises a CRLF file's line endings and turns a 1-line notice into a whole-file diff. Insert the notice by hand on mixed-EOL files.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: worktree-agent-a17fa6c2bdafdb934
- commit: e3b8ecd3b8894b912e1acf2435a34c59e3182c71

## State Impact

- target: round-glacier-2865 — ADR-629 (disable c911a5d8, delete e3b8ecd3): src/Mod/Show, src/XDGData, src/MacAppBundle, src/3rdParty/3Dconnexion and OpenGL, src/Tools/plugins, BUILD_VR/FindRift, BUILD_DESIGNER_PLUGIN, the dead BUILD_JTREADER gate, FREECAD_CREATE_MAC_APP and the 3Dconnexion options are deleted (88 files / 30,586 lines); nothing kept. FreeCAD manifest now 57 files (Document.py added: the Show test case removed). Gates: CTest 1,526 run with the baseline's single failure (ImporterTest.TestOBJ), test-engine 2,777/62 and cli 1,259/1 identical to baseline, packaged gate 36 passed, fresh-cache configure clean; macOS/Windows not exercised. Negative knowledge: tools/apply_modification_notices.py --write rewrites a CRLF/mixed-EOL file to LF (whole-file diff); insert the notice by hand there.
- target: early-arbor-7123 — DOCS-AUDIT.md §4 item 10 (removal candidates) resolved by ADR-629; FREECAD.md, THIRD_PARTY_LICENSES.md (eleven 3rdParty trees), ARCHITECTURE.md, INTEGRATION.md and cadex-release-packaging.md updated
