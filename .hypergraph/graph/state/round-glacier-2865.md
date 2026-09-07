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

**The delta is machine-pinned since ADR-171:** the manifest must match inherited modifications against both imports and carry modification notices; BLENDER-TREE §2a's eight-file boundary is test-enforced [rec: wild-sea-9905]. The nt2 audit baseline was 91 modified inherited files (47 FreeCAD, 44 Blender, including one premodified entry) [rec: wise-isle-1725]. After deletion the manifest has 56 FreeCAD files (40 src, 16 build/tests) and 44 Blender files. FreeCAD modified-file line totals fall from 1,804/1,907 inserted/deleted to 1,633/1,796 after the Measure shim disable/delete and sit at 1,638/1,797 after the Help disable, while modified-file count rises from 47 to 56; Blender stays 1,046/129 and 44. Deleted upstream volume is separate; the broad fork-delta criterion remains open [rec: terse-ridge-1619] [rec: humble-shore-1680] [rec: placid-harvest-8845] [rec: small-tide-8341] [rec: zesty-otter-9342].

Done: 17 unused FreeCAD workbench trees, the Qt shell and the provider stack, the local bpy modes, and the dead publication paths [rec: civic-horizon-2730] [rec: simple-hollow-8675]. ADR-171 added two removals under the same protocol: the drone demo (~59 MB, seven STLs of unrecorded origin) and the dead PySide/shiboken dylibs the payload prune had always missed [rec: wild-sea-9905].

Outstanding:

- **Phase 8 — directory deletion complete; broader GUI-source exit open (ADR-214/215).** Separate metatype/disable prerequisites were followed by deletion of thirteen GUI directories and three retired sources, totaling 3,734 files / 137,376,129 bytes. Release build, both cadex ctests, unchanged inherited baseline/inventory and fresh install/stage are evidenced; 2,021 engine tests pass with 52 skips and the expected precommit HEAD mismatch. The subsequent 26-test packaged lifecycle/licensing pass resolves that mismatch using the same local stage-only payload [rec: terse-ridge-1619] [rec: humble-shore-1680]. Preserve `App/MetaTypes.h`, retained Qt and Assembly `CommandCreateView`, `JointObject`, `Preferences`, `UtilsAssembly`: they serve headless publication/solving. Material GUI scripts and MeshPart InitGui still install; Start/Test retain build/install consumers despite payload absence, and Help's are now disabled (see below). Main's unused GUI resource template and four inactive GUI-launcher branches sit beside a required Windows CLI launcher; other mixed helpers/resources need separate audits [rec: humble-shore-1680].
- **Measure GUI shim removal complete (ADR-215).** The shared target/copy/install list was disabled in a separate verified commit before deleting `Measure/MassPropertiesGui.py` (one file, 22 lines, 1,477 bytes). Measure App's view-provider identity, four other Measure scripts and four required Assembly modules remain. Both configurations, each unit's release build, install and completed stage pass; the deletion's engine suite reports 2,022 passed / 52 skipped and fresh packaged lifecycle/licensing reports 26 passed. Inherited CTest retains 162 failures with no new names against the 164-failure baseline, identical 1,544 registrations and unchanged skips/disabled tests. The installed native probe creates `Measure::Result` headlessly; no stale shim or bytecode remains in release/install/stage [rec: placid-harvest-8845] [rec: small-tide-8341]. Reconcile judgement: the completed shim sequence supersedes the audit's proposed next boundary, but proves neither two whole engine-tree removals nor the broader GUI-source exit. The local 2.4 GB stage has external rpaths and is not a relocated distribution; arbitrary dynamic/external imports and Windows behavior remain unproved [rec: humble-shore-1680] [rec: small-tide-8341].
- **Phase 13b, shell side**: Cycles completed both halves of the removal protocol. ADR-196 now records the disable build (732 steps) and gate (1,142 ok), then the delete build (build 497, six steps) and gate (1,142 ok) [rec: rich-key-5043] [rec: ancient-crest-4588]. The cached configure proves the OFF configuration, but a fresh configure has not verified the changed option default [rec: ancient-crest-4588]. The second removal, locale, has its verified disable half: `WITH_INTERNATIONAL=OFF`, 77 MB of bundled locale data pruned, build 499 (737 steps) and gate (1,142 ok, `ok:true`), ADR-198. Its source delete, option default OFF and configure-flag removal remain unevidenced by this tail [rec: ancient-crest-4588]. Reconcile judgement: the directive ticks two shell removals as shipped, but gives no locale-delete evidence; retain the narrower recorded boundary rather than infer that delete landed [rec: empty-wolf-3962].
- **Help whole-tree disable landed (ADR-216, ADR-217); delete owed.** The audit (`docs/HELP-AUDIT.md`) qualified `src/Mod/Help` for a separate disable: 85 tracked files / 802,267 bytes, no App target, no `Init.py`, no Help CTest consumer, no tracked product importer; `BUILD_HELP` was ON in both caches independently of `BUILD_GUI=OFF`, four sources copied/installed it unconditionally, and the shared install carried a stale `Help_rc.py` plus two bytecode files. The Crowdin translation updater is an external source-resource writer that must lose its Help row at deletion, with two developer-configuration references to clean [rec: silver-beacon-0723]. The disable (`a04ca822`) landed without a record node and with gates it claimed but had not run; the follow-up ran them and corrected ADR-217, the ROADMAP line and HELP-AUDIT §"Disable landed": explicit `-DBUILD_HELP=ON` collapses to OFF in both caches, 0 `Mod/Help` Ninja rules, release build 690 steps, no `Mod/Help` in install or payload, `import Help` fails in the installed `FreeCADCmd` while nine retained modules import, engine suite 2,022 / 52 skipped, inherited CTest 162 of 1,537 with no names outside the baseline (two baseline names are ADR-214-deleted binaries), packaged gate 26 passed. The stale copies and bytecode were already absent when the gate unit began; which unrecorded unit removed them is unknown. Fresh-cache configure and non-macOS remain unrun. Retained Qt, required Assembly publishers, Measure App and attribution are untouched [rec: zesty-otter-9342]. Reconcile judgement: this is real whole-tree disable evidence and unblocks the delete as a separate unit; no engine-tree removal is complete until the delete lands, and Start (App target) and Test (MainCmd dependency) are not qualified as a second candidate [rec: silver-beacon-0723] [rec: zesty-otter-9342].
- **Phase 13b, engine side**: trees that build but are in no shipped payload, and a staged payload that is ~2.3 GB of which ~2.1 GB is development environment [rec: merry-eagle-4093].

**Phases 11 and 12 — replacing the engine and the shell with our own — are unscheduled by decision, not stalled.** Merging the repositories removed the deadline pressure and turned them into optional internal swaps behind the unchanged protocol; the test-pinned protocol is exactly what keeps them available. **Do not start writing a replacement engine or shell in this tree ahead of its phase** [rec: merry-eagle-4093] [rec: western-badger-3023].

## Negative knowledge

- [scope: writing a replacement engine or shell | confidence: high | evidence: merry-eagle-4093, western-badger-3023] Do not start writing a replacement engine or shell in this tree ahead of its phase. Phases 11 and 12 are unscheduled by decision; what keeps them available is the test-pinned protocol, not partial work in the tree.
- [scope: deleting src/Gui | confidence: high | evidence: kind-ledge-5493, first-moss-9524] Retired 2026-09-06. The line was "the deletion is not mechanical: cadex_assembly_worker.py imports GUI-lineage code"; ADR-197 removed that import, and the audit found the premise was off anyway — the module installs regardless of BUILD_GUI. What survives as the lesson: the engine's authoring path should not lean on a `Command*` module, whichever tree it lives in.
- [scope: a removal landed under quota pressure | confidence: high | evidence: pale-river-6583] A disable commit can reach git with a session-limit banner for a message, no record node and no DECISIONS entry, and then be invisible to both graphs and the log. Check `docs/DECISIONS.md` numbering against the ADRs the docs cite before the next removal; the reconcile pass caught this one by grepping for the ADR number, not by reading the commit log.

- [scope: a removal commit landing ahead of its gates | confidence: high | evidence: zesty-otter-9342] The Help disable reached git with an ADR citing a HELP-AUDIT section that did not exist and gates that had not run, across three iterations without a record node. Run the gates before the ADR claims them; a later unit had to rewrite three docs to say only what ran.
- [scope: Phase 8 boundary audited at d031bde0 | confidence: high | evidence: wise-isle-1725] Preserve the active Material metatype contract and retained headless Assembly publisher modules; mixed GUI-lineage Python outside the thirteen directory trees is not blanket-removable. Earlier worker-import removal does not prove whole-tree deletion readiness.

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
- wise-isle-1725 — ADR-213: corrected boundary/counts, active metatype dependency and retained Assembly publisher narrow earlier mechanical-deletion claim
- sharp-pond-0087 — metatype prerequisite, release dependency cleanup and baseline ctest evidence; nineteen inherited edits
- fair-cabin-5280 — complete disable and unchanged baseline failures/inventory; retained Qt/source and outstanding deletion

- terse-ridge-1619 — ADR-214: verified directory deletion, fresh install/stage and scoped delta measurements
- humble-shore-1680 — ADR-215: 26 packaged tests resolve HEAD verification; residual consumers and narrow Measure boundary

- placid-harvest-8845 — ADR-215: separately verified Measure shim copy/install disable; retained consumers and unchanged inherited failures
- small-tide-8341 — ADR-215: verified shim deletion, native Measure probe, fresh packaged gates and scoped delta totals; broader gaps remain open
- silver-beacon-0723 — ADR-216: Help audited and qualified for a separate whole-tree disable; consumers, stale artifacts and the external translation writer inventoried
- zesty-otter-9342 — ADR-217 gates run after the fact: Help disable verified across build/install/stage/suites/packaged gate; delete unblocked; docs corrected
