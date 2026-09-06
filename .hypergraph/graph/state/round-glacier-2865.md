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

- **Phase 8 — delete `src/Gui`** (66 MB, 729 files). `BUILD_GUI=OFF` was its disable commit and it landed long ago; the delete commit has not [rec: kind-ledge-5493] [rec: simple-hollow-8675]. **The delete is mechanical again** (ADR-197, 2026-09-06) [rec: first-moss-9524]: `cadex_assembly_worker.py` no longer imports `CommandCreateView` — the worker computes FreeCAD's exploded-view rule itself, equal to the native readback to 1e-12 and pinned under a real kernel. The audit also changed the premise: `src/Mod/Assembly/CMakeLists.txt` installs `CommandCreateView.py` outside its `if(BUILD_GUI)` blocks, so deleting `src/Gui` never would have removed it; the real objection was the engine's authoring path leaning on a `Command*` module for forty lines of arithmetic. The publisher still imports the module to build the native document object, which is what a published view *is*, and deleting `src/Gui` does not touch that.
- **Phase 13b, shell side**: Cycles completed both halves of the removal protocol. ADR-196 now records the disable build (732 steps) and gate (1,142 ok), then the delete build (build 497, six steps) and gate (1,142 ok) [rec: rich-key-5043] [rec: ancient-crest-4588]. The cached configure proves the OFF configuration, but a fresh configure has not verified the changed option default [rec: ancient-crest-4588]. The second removal, locale, has its verified disable half: `WITH_INTERNATIONAL=OFF`, 77 MB of bundled locale data pruned, build 499 (737 steps) and gate (1,142 ok, `ok:true`), ADR-198. Its source delete, option default OFF and configure-flag removal remain unevidenced by this tail [rec: ancient-crest-4588]. Reconcile judgement: the directive ticks two shell removals as shipped, but gives no locale-delete evidence; retain the narrower recorded boundary rather than infer that delete landed [rec: empty-wolf-3962].
- **Phase 13b, engine side**: trees that build but are in no shipped payload, and a staged payload that is ~2.3 GB of which ~2.1 GB is development environment [rec: merry-eagle-4093].

**Phases 11 and 12 — replacing the engine and the shell with our own — are unscheduled by decision, not stalled.** Merging the repositories removed the deadline pressure and turned them into optional internal swaps behind the unchanged protocol; the test-pinned protocol is exactly what keeps them available. **Do not start writing a replacement engine or shell in this tree ahead of its phase** [rec: merry-eagle-4093] [rec: western-badger-3023].

## Negative knowledge

- [scope: writing a replacement engine or shell | confidence: high | evidence: merry-eagle-4093, western-badger-3023] Do not start writing a replacement engine or shell in this tree ahead of its phase. Phases 11 and 12 are unscheduled by decision; what keeps them available is the test-pinned protocol, not partial work in the tree.
- [scope: deleting src/Gui | confidence: high | evidence: kind-ledge-5493, first-moss-9524] Retired 2026-09-06. The line was "the deletion is not mechanical: cadex_assembly_worker.py imports GUI-lineage code"; ADR-197 removed that import, and the audit found the premise was off anyway — the module installs regardless of BUILD_GUI. What survives as the lesson: the engine's authoring path should not lean on a `Command*` module, whichever tree it lives in.
- [scope: a removal landed under quota pressure | confidence: high | evidence: pale-river-6583] A disable commit can reach git with a session-limit banner for a message, no record node and no DECISIONS entry, and then be invisible to both graphs and the log. Check `docs/DECISIONS.md` numbering against the ADRs the docs cite before the next removal; the reconcile pass caught this one by grepping for the ADR number, not by reading the commit log.

## Provenance

- civic-horizon-2730 — the two-commit removal protocol and Phase 1
- simple-hollow-8675 — BUILD_GUI=OFF as the disable commit for src/Gui
- kind-ledge-5493 — the outstanding delete commit and the one import that makes it non-mechanical
- merry-eagle-4093 — why Phases 11 and 12 left the critical path, and what 13b covers on both sides
- western-badger-3023 — that the replacements are unscheduled by decision rather than stalled
- wild-sea-9905 — ADR-171: the delta manifest, the notice discipline, and the two removals it logged
- first-moss-9524 — ADR-197: the worker computes exploded views itself, the `CommandCreateView` import gone from the authoring path, Phase 8's non-mechanical item resolved, and the missing ADR-196 entry noted
- pale-river-6583 — the Cycles disable commit (70591c1e) found in git with no record node; ADR-196 unlogged; the delete commit and the log entry owed

- rich-key-5043 — ADR-196 and verified Cycles disable build and gate
- ancient-crest-4588 — Cycles delete evidence and verified locale disable; fresh-configure limitation
- empty-wolf-3962 — charter completion claim distinguished from the narrower removal evidence
