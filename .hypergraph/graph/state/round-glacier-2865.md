---
node_id: f3e93132-d2b9-5934-8fd9-a429a7f84020
slug: round-glacier-2865
title: Inherited-tree reduction, and the unscheduled replacements
created_at: '2026-08-09T15:22:46+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

The standing work of shrinking both inherited trees in place, under the two-commit removal protocol: dependency audit → a **disable commit** → a **delete commit** → a `docs/DECISIONS.md` entry, each step independently verified against the same gates [rec: civic-horizon-2730].

**The delta itself is machine-pinned since ADR-171** [rec: wild-sea-9905]: `docs/inherited-modifications.json` holds the 90 modified inherited files (47 FreeCAD, 43 Blender — one flagged `premodified` because its edit predates the squashed import), `test_licensing_compliance.py` holds that manifest equal to `git diff` against both import commits and requires the per-file §2(a) modification notice on every entry (nine FreeCAD files are ledger-only after formatter fights; FREECAD.md §2b is their notice), and BLENDER-TREE §2a's "eight files stay eight" is test-enforced. An edit to an inherited file now fails the engine suite until it is manifested, noticed and ledgered.

Done: 17 unused FreeCAD workbench trees, the Qt shell and the provider stack, the local bpy modes, and the dead publication paths [rec: civic-horizon-2730] [rec: simple-hollow-8675]. ADR-171 added two removals under the same protocol: the drone demo (~59 MB, seven STLs of unrecorded origin) and the dead PySide/shiboken dylibs the payload prune had always missed [rec: wild-sea-9905].

Outstanding:

- **Phase 8 — delete `src/Gui`** (66 MB, 729 files). `BUILD_GUI=OFF` was its disable commit and it landed long ago; the delete commit has not [rec: kind-ledge-5493] [rec: simple-hollow-8675]. One import makes it more than mechanical: `cadex_assembly_worker.py` reaches GUI-lineage code headlessly for exploded views [rec: kind-ledge-5493].
- **Phase 13b, shell side**: the disable commit is nearly free there because the candidates are already CMake options — Cycles, the VSE, grease pencil, the compositor, `shell/locale/`, most of `shell/tests/files/` [rec: merry-eagle-4093].
- **Phase 13b, engine side**: trees that build but are in no shipped payload, and a staged payload that is ~2.3 GB of which ~2.1 GB is development environment [rec: merry-eagle-4093].

**Phases 11 and 12 — replacing the engine and the shell with our own — are unscheduled by decision, not stalled.** Merging the repositories removed the deadline pressure and turned them into optional internal swaps behind the unchanged protocol; the test-pinned protocol is exactly what keeps them available. **Do not start writing a replacement engine or shell in this tree ahead of its phase** [rec: merry-eagle-4093] [rec: western-badger-3023].

## Negative knowledge

- [scope: writing a replacement engine or shell | confidence: high | evidence: merry-eagle-4093, western-badger-3023] Do not start writing a replacement engine or shell in this tree ahead of its phase. Phases 11 and 12 are unscheduled by decision; what keeps them available is the test-pinned protocol, not partial work in the tree.
- [scope: deleting src/Gui | confidence: high | evidence: kind-ledge-5493] The deletion is not mechanical: cadex_assembly_worker.py imports GUI-lineage code and uses it headlessly for exploded views. That import must be resolved in Phase 8, not deferred to Phase 11.

## Provenance

- civic-horizon-2730 — the two-commit removal protocol and Phase 1
- simple-hollow-8675 — BUILD_GUI=OFF as the disable commit for src/Gui
- kind-ledge-5493 — the outstanding delete commit and the one import that makes it non-mechanical
- merry-eagle-4093 — why Phases 11 and 12 left the critical path, and what 13b covers on both sides
- western-badger-3023 — that the replacements are unscheduled by decision rather than stalled
- wild-sea-9905 — ADR-171: the delta manifest, the notice discipline, and the two removals it logged
