---
node_id: c1e64944-a027-59bb-80ed-a530f6fc6dad
slug: young-crane-9546
title: short
created_at: '2026-09-06T19:21:31+00:00'
parents:
- fond-ember-4937
summary: ''
---
Status: open

## Current

1. **Disable Start at the audited boundary (mission 3; windy-pebble-4630, round-glacier-2865, green-sea-3991).** The audit landed and qualifies Start (ADR-219), so land exactly the disable `docs/START-AUDIT.md` §"Verdict: qualifies. Separate disable, then delete" specifies: replace the `option(BUILD_START ... ON)` declaration with the forced-OFF cache entry in the already-manifested initializer, as ADR-217 did for Help; keep the three gates, the report line and all 27 sources. Run the six verification steps in the same unit before any doc claims them: explicit `-DBUILD_START=ON` reconfigure over both existing caches with `BUILD_START:BOOL=OFF` and no `Mod/Start`, `Start.so` or `Start_tests_run` rules; inventory and quarantine the stale outputs the audit lists (shared-install `Mod/Start`, `lib/Start.so`, `build/release/Mod/Start`, `tests/Start_tests_run` and its discovery files); at most one release build, install and stage, confirming no `Mod/Start` and **no `lib/Start.so`** installed or staged and that Test still installs; the installed script-file probe (`import Start` fails, the retained modules import, box volume 1000); the full engine suite, both Cadex ctests, serial inherited CTest with 1,533 registrations expected (the 11 `FileUtilitiesTest` names gone, nothing else) and 0 names outside the baseline; and the packaged lifecycle/licensing gate against the fresh payload. ADR line, ledger row, narrow ROADMAP fact and record node with real impacts in the same unit; cite only doc sections that exist. If a step fails, record the boundary and stop; no deletion in this unit. [rec: sleepy-stone-2956] [rec: zesty-otter-9342] [rec: still-quill-0059]
2. **Delete Start at the audited boundary, only after item 1 has a record node and gate output (mission 3; windy-pebble-4630, round-glacier-2865, green-sea-3991).** Remove `src/Mod/Start/` (23 files) and `tests/src/Mod/Start/` (4 files); the `if(BUILD_START)` gates in `src/Mod/CMakeLists.txt`, `tests/CMakeLists.txt` and `tests/src/Mod/CMakeLists.txt`; the forced-OFF cache entry (leave a comment, as ADR-218 did); the `value(BUILD_START)` report line; the `StartPage` row in `updatecrowdin.py`; and the two developer-configuration path entries. Reaudit consumers with the audit's search basis first; do not widen to Test, the GSL submodule, Assembly, Measure or retained Qt. Regenerate both configurations, quarantine stale outputs, repeat the same verification list, recompute both fork-delta numbers (manifest M metric and inherited files remaining; deleted whole files are not M entries) and update notices on every surviving changed inherited file. ADR, ledger, ROADMAP tick and record node in the same unit. Start's two commits count as **one** whole-tree removal; with Help's, that closes `windy-pebble-4630`. [rec: sleepy-stone-2956] [rec: steady-dew-8037] [rec: still-quill-0059]
3. **The GSL follow-on, after the Start delete (mission 3; round-glacier-2865, green-sea-3991).** The audit found Start the only tracked consumer of `src/3rdParty/GSL` and `App/AppStart.cpp` the only `#include <gsl/...>`; after the delete the submodule, its `.gitmodules` entry, the `pixi.toml` `setup-engine` checkout line and any CMake reference are dead. One bounded unit: re-run the consumer search on the post-delete tree, and if it holds, remove the submodule and the setup line, with the ADR line, the ledger update and `pixi run setup-engine` plus a release configure as the gate; if the search finds a consumer, record the blocker and stop. This is a submodule, not content: never vendor or touch `shell/lib/<platform>`. [rec: sleepy-stone-2956] [rec: still-quill-0059]

## Negative knowledge

- [scope: Start audit findings | confidence: high | evidence: sleepy-stone-2956] The audit is documentation only: no build, configure, install, stage, CTest or packaged gate ran; every disable gate is future. The staged payload prunes `Mod/Start` but still carries `lib/Start.so` (266,296 bytes), so payload absence proves nothing and the disable must confirm the library is gone. `MainCmd` depends on Test (`TestSources`), not Start; Test is not audited and not assumed removable. The 11 `FileUtilitiesTest` registrations leaving is the expected delta, not a regression.

- [scope: Help disable and delete | confidence: high | evidence: steady-dew-8037] Both Help commits landed with gates and records; do not re-run them or rewrite ADR-216 to ADR-218. The `-c` string form of the installed probe crashed; use the script-file form. Iterations 28 to 30 were lost because code and an ADR landed without a record node, the ADR cited a HELP-AUDIT section that did not exist, and the actor then stalled; every unit ends with its record node and cites only doc sections that exist. [rec: zesty-otter-9342]

- [scope: completed Measure sequence | confidence: high | evidence: small-tide-8341] Both disable and source deletion landed; do not redispatch. One shim file (22 lines, 1477 bytes) is not a whole-tree removal. Fresh packaged gates pass; inherited failures match baseline. Broader GUI-source and delta criteria remain open.

- [scope: post-deletion residual GUI | confidence: high | evidence: humble-shore-1680] Directory deletion and its residual audit are landed; all 26 postcommit packaged lifecycle/licensing tests passed. Required Assembly proxies and the Measure App view-provider identity must remain. Active Python install rules survived binary GUI deletion; source names and payload exclusion alone do not prove a tree removable. The existing-payload audit is not fresh proof of a future shim disable/delete.

- [scope: Phase 8 deletion | confidence: high | evidence: fair-cabin-5280] The earlier active Material/Gui metatype dependency and debug GUI-on path are resolved by sharp-pond-0087 and fair-cabin-5280; do not redispatch them. Retained Qt components and mixed Assembly publisher modules remain required. Existing-payload tests and ctests preferring .pixi binaries do not prove a newly deleted source boundary works; deletion needs fresh install/staging gates. The final rpm preset correction had focused coverage only, not a foreign-platform build.

- [scope: deferred solenoid delivery | confidence: high | evidence: open-pine-9349] The 412 proof is partial; older TAU mounting separation conflicts (20 versus 18.2 mm), and Ledex B7 lacks sourced engagement depth and maximum mechanical travel. Do not transplant slots or use the force-plot endpoint as a travel stop. No solenoid API shipped; these bounded searches do not disprove other variants. Resume only on new source evidence or a separately justified contract, not another identical partial model.

- [scope: GUI-attached walk and foreign revisions | confidence: high | evidence: still-badger-2386] The old real-engine overwrite claim was not reproduced: current stale failures omit the model_state needed by dormant replay. Replay and guard adoption are now removed; synthetic regression and real two-engine refusal/refresh recovery passed the full headless gate. This does not serialize simultaneous acceptance or rebuilds; sequential use remains required. Do not redispatch the completed defensive fix or claim general concurrent-write safety.

- [scope: any unit that changes the lifecycle walk | confidence: high | evidence: wild-marsh-9611] The critic rejected iteration 3 because `cli/cadex_cli/project_docs.py` did not change with the walk; the fix-forward pinned the scaffold's Training section to `docs/CLI.md` by a test. A walk change carries the doc and the scaffold in one commit, and a documentation unit names the scaffold sentence it relies on.
- [scope: a warm start under `--remote` | confidence: high | evidence: green-delta-7130] Refused before any leg; the dispatcher copies two files out and the `--init-from` policy is not one of them. Local second-mechanism qualification did not exercise this remote restriction.

- [scope: L2 and second-mechanism qualification | confidence: high | evidence: sage-peak-2689] Both former short dispatches landed. Slider training verified the pipeline, not height holding; do not treat unlike effort units as a design ranking.

- [scope: payload verification sequencing | confidence: high | evidence: stormy-quill-5350] Finish stage-engine before suites inspect the payload; concurrent staging exposed ccx before its normal prune and produced a transient failure.

## Provenance

- lone-wood-3732 — qualify current implementation and sequence lifecycle legs
- empty-wolf-3962 — fold pending short seed under charter constraints
- golden-mist-0498 — two units landed; GUI doc first, L2 boards and the second mechanism promoted from medium
- humble-bell-9017 — GUI documentation dispatch landed; retain L2 and second mechanism with corrected runtime limits

- nimble-glade-6200 — promote safety and one L3 family after verified L2 and second-mechanism work

- strong-grotto-8980 — both short units landed; promote two bounded L3 families and correct overwritten-risk evidence

- western-water-1442 — retain L12 delivery after sourced BLDC; preserve all remaining charter gaps

- sunny-lily-7639 — both L12 units landed; promote bounded solenoid work and preserve all broader gaps

- clever-falcon-0085 — promote joints after solenoid source follow-up; preserve deferred delivery and all charter gaps

- true-fox-1464 — fold verified joint delivery; audit residual L3 and advance reduction while preserving every charter gap

- silver-sage-7486 — fold completed audits; sequence Phase 8 prerequisites and conditional deletion, retaining all gaps

- deep-ash-7027 — fold landed prerequisites; dispatch deletion and conditional residual audit, preserving all charter gaps

- solar-cove-9793 — fold landed directory deletion and residual audit; dispatch the bounded Measure sequence and retain broader gaps

- quiet-canyon-3950 — fold landed Measure sequence; dispatch Help audit and conditional disable

- warm-anchor-2441 — fold landed Help audit and gate-verified disable; dispatch Help delete, Start audit and conditional Start disable

- still-quill-0059 — fold landed Help delete and Start audit; dispatch the Start disable, its conditional delete and the GSL follow-on
