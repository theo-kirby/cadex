# Translation updater dependency audit

Verified against source: 2026-09-07

[Cadex-new] Offline audit of [FreeCAD-inherited] `src/Tools/updatecrowdin.py`
at `2caba553`, following ADR-232. This is evidence only: no updater import,
credential read, network request, resource write, product edit or build.

## Command and writer inventory

The 663-line script imports PySide6.QtCore, falling back to PySide2.QtCore,
before dispatch. QtCore is used only by `updateTranslatorCpp`. Main eagerly
calls `load_token` even when CROWDIN_TOKEN is present (the default argument
is evaluated); commands require a token, and all paths require
CROWDIN_PROJECT_ID. The token loader checks a home token file before the
environment. None of these paths was executed for this audit.

| Command | Reachable behavior and effects |
|---|---|
| `status` | GET project/language progress, sort and print; threshold 25%, displayed positive-progress languages. |
| `build-status` | GET build list and print. |
| `build` | POST translation build, changing remote state. |
| `download [id]` | Explicit id downloads directly; otherwise list builds, download the sole build, print choices for multiple builds or report none. Writes `<project_identifier>.zip` in cwd. Despite help wording, multiple builds do not select the latest. |
| `update` / `upload` | Recursively glob `../**/*.ts` relative to cwd, remove names containing another stem, map legacy Draft naming, upload via eight-worker pool (serial option exists on the class). Independent of `locations`. Read local sources; POST storage, PUT existing remote file; new-file path calls API helper with default GET plus data, whose server behavior is unverified. |
| `apply` / `install` | GET progress, select strictly above 25%, extract cwd `freecad.zip` into a new temp directory, copy translations using `locations`, then call `updateTranslatorCpp` for each language. Help incorrectly says it runs updatefromcrowdin.py; implementation is inline. |
| `updateTranslator` | Undocumented command; GET/filter progress then call only the deleted-GUI writer. |
| `gather` | Import `updatets`, call main; module is absent in tracked source. An externally supplied Python module remains possible. |
| no/unknown command | Print module help, only after imports and environment checks. |

API helpers resolve project id and file ids; no API pagination or service
behavior was tested. The class's stored token is not what the request helper
uses: it reloads the token. This is an observation, not a repair dispatch.

Local writers, by source lines at the audited commit:

- `updateqrc` (352–408) reads a QRC, skips an existing language, inserts a
  mapped QM entry after the last QM or before closing qresource, rewrites it.
  Missing resource/insertion position exits; not a dry run.
- `updateTranslatorCpp` (411–452) uses QLocale and reads/writes exactly
  `../Gui/Language/Translator.cpp` relative to `__file__`. It scans the
  `d->mapLanguageTopLevelDomain[QT_TR_NOOP(` rows and inserts a language with
  Swedish code mapping. The target is deleted; there is no alternate target.
- `doFile` (455–488) maps names/language, skips a missing source, copies TS
  without creating its destination. Only GENERATE_QM members invoke lrelease
  (five-second timeout), require the QM output, then call updateqrc.
- `doLanguage` (491–508) skips English, loops locations, resolving destination
  paths from cwd, not the script directory. Expected cwd is src/Tools.
- `applyTranslations` (511–532) creates a temp directory, copies/extracts the
  archive, changes cwd and restores it on the normal path, visits existing
  language directories. No finally cleanup/transaction protects partial writes.

## Retained consumers and absent destinations

AST literal inspection, without importing the script, found 27 location rows:

| Entries | Translation directory / QRC on disk |
|---|---|
| App twice | Both present. |
| Base once | Translation directory present; Base.qrc absent. |
| Arch twice; Assembly, draft, Fem, FreeCAD, Inspection, Material, Measure, Mesh, MeshPart, OpenSCAD, Part, PartDesign, CAM, Points, ReverseEngineering, Robot, Sketcher, Spreadsheet, Surface, Test, TechDraw, Tux | Both absent (24 rows). |

The earlier two-complete-row count must not hide Base: **App and Base each
have 39 tracked TS files**, one source and 38 language files. Neither belongs
to GENERATE_QM, so the missing Base QRC does not block doFile's Base copy.
The set contains AddonManager, Arch, Cloud, Draft, Inspection, OpenSCAD, Tux,
Help; the remaining mappings are not an authority on installed capabilities.
App.qrc has 33 QM entries but is not the QRC used by today's App CMake rule.

`src/App/CMakeLists.txt:355` globs both App and Base language TS files,
compiles QMs, generates `App_translation.qrc`, embeds resources into FreeCADApp.
`cMake/FreeCAD_Helpers/SetupQt.cmake` keeps LinguistTools outside BUILD_GUI
and implements those helpers. `Application.cpp:2901` installs the Qt
translation bridge. `TranslationQtBridge.cpp` loads QTranslator files and
translates via QCoreApplication; `src/Base/Translate.cpp` exposes translator
installation. These are retained headless consumers, not deleted GUI debt.
Their continued presence is statically established; this audit does not
claim a runtime translation test or current Crowdin source availability.

## Entry points and search limits

Tracked-tree `git grep` for updatecrowdin and updateTranslatorCpp finds no
caller outside the script; remaining updater mentions are audit/docs and the
inherited manifest. The script's shebang, command examples and direct Python
imports are maintenance entry points even without tracked callers. The
XDG metainfo translation link points to Crowdin, not a script invocation.
The Tools attributes still name the missing updatets.py as export-ignore.
Neither updatets.py nor updatefromcrowdin.py is tracked.

CMake/pixi/package reference searches show other Tools scripts but no updater
build/install rule. Local release build.ninja, cmake_install.cmake and
install_manifest.txt also contain no updatecrowdin occurrence. This proves
only absence in those tracked rules and existing generated outputs: external
CI, developer aliases, cron jobs, imports and alternate checkouts are unknown.
No external maintenance system was queried. No claim that the tool is unused
or absent from every possible source archive follows.

Reproduce the static inventory with `ast.parse` + `ast.literal_eval` of the
locations assignment, resolving paths against `src/Tools`; enumerate TS with
`git ls-files '*.ts'`. Search references with `git grep -n -i updatecrowdin`
and `git grep -n updateTranslatorCpp`; inspect the dispatch and writer bodies,
App CMake, SetupQt and TranslationQtBridge at the paths above. Do not execute
the updater to inspect its help: startup reads credentials.

## One qualified boundary; later bet required

Qualify only the **deleted GUI translator writer**: updateTranslatorCpp,
its apply/install tail, the updateTranslator command, and the exclusive
PySide QtCore import. The helper has exactly two internal call sites and no
tracked external consumer. Its sole output target disappeared with src/Gui.
No App/Base resource, translation API or build rule consumes that output.

Compatibility cost: direct maintenance calls or imports expecting GUI language
registration cease to work, including external users with a restored GUI tree.
Apply/install retains TS installation but loses that GUI-registration side
effect. Existing missing destination/cwd/archive problems are not solved;
retiring this tail cannot certify the full network workflow. Other commands,
locations, duplicate entries, QRC helpers and gather remain outside this
boundary. No whole-tool, App resource, Qt library or shell removal qualifies.

The evidence-only disposition below hands this boundary to the maintainer and
planner. A later planner bet is required before implementation. If selected,
use two commits:

1. Disable the GUI-writing call paths, retaining the helper/source dependency
   until the separate delete stage. Give updateTranslator an explicit retired
   diagnostic without requesting language progress; retain apply/install's
   non-GUI behavior. Pin both paths with isolated stubs that cannot read real
   credentials, touch repository resources or use the network.
2. Only after verified disable evidence, delete the unreachable helper and
   its exclusive PySide import (and any temporary disable-only scaffolding
   explicitly named in the later bet). Preserve a clear retired-command
   outcome rather than silently performing an unrelated operation.

Each future removal unit needs its ADR/ROADMAP/record; the existing inherited
manifest entry and modification notice must remain accurate, checked against
committed HEAD. Record changed inserted/deleted line totals separately from
file count: this boundary removes no whole inherited file.

Required future checks: isolated command regressions for retained dispatch,
App/Base copy and Swedish mapping, denied GUI writer, synthetic archive/QRC
behavior as affected; full engine pytest; at most one `pixi run build-release`
per unit, plus inherited CTest comparison against the recorded baseline.
Check retained App/Base TS hashes and generated QM/QRC resources and exercise
installed FreeCAD.Qt translator load/translate/remove on a known translation.
No shell gate is needed without shell changes. If staging/payload is touched,
run the packaged lifecycle gate against that stage; otherwise distinguish an
existing-stage baseline from fresh payload proof. Network success is never
inferred from stub tests. No live service exercise is authorized here.

## Audit validation

Documentation-only unit: `pixi run python -m pytest -q
src/Mod/cadex/cadex_tests/test_licensing_compliance.py`: **10 passed, 1 skipped**
(0.22 s); the packaged-license test skipped because CADEX_ENGINE_ROOT was
not set. `git diff --check` passed. Hypergraph export/check passed with zero
violations and warnings. No engine build, full engine suite, packaged
lifecycle, shell gate or translation runtime probe was run. Code, translation
resources, inherited manifest and fork measurements remain unchanged.

## Evidence-only disposition and role handoff (2026-09-07)

Short rank 2 accepts exactly the boundary qualified above. This disposition
is not an implementation dispatch. The sole future inherited source edit is
`src/Tools/updatecrowdin.py`: its `updateTranslatorCpp` definition (411–452
at the audited revision), apply/install tail (642–644), updateTranslator
branch (646–655), and exclusive PySide6/PySide2 import block (88–91).
`src/Gui/Language/Translator.cpp` is an absent output, not a file to restore
or delete. No whole-file saving is claimed.

The later bet must name two separately gated commits:

- **Disable:** remove the apply/install GUI-writing tail and replace the
  updateTranslator branch with an explicit retired-command diagnostic, with
  no language-progress request. Keep the helper and PySide import until the
  delete commit. Preserve existing startup credential/project checks; moving
  them or repairing unrelated commands is outside this boundary. Isolated
  tests must stub imports, credentials and service calls before dispatch.
- **Delete:** after the disable commit's evidence passes, remove only the
  unreachable helper and exclusive PySide import. Retain the retired-command
  diagnostic. No temporary production scaffolding is proposed for removal.
  Direct external imports of the helper cease to work at this stage; external
  use is unknown, including users who restore a GUI tree. The first stage
  already retires GUI registration through the two CLI paths.

Supporting files for that later bet: add isolated regression coverage in
`src/Mod/cadex/cadex_tests/test_translation_updater.py`; update this audit,
`docs/DECISIONS.md`, `docs/ROADMAP.md` and `docs/FREECAD.md`, plus one record
per unit. Verify `docs/inherited-modifications.json` and the updater's existing
modification notice; change them only if accuracy requires it. No other
inherited source, build rule or shell file belongs to the proposed pair.

Retain `applyTranslations`, `doLanguage`, `doFile`, `updateqrc`, all locations
and mappings, and every other command. In particular, preserve App/Base's
39 TS files each, TS installation and Swedish filename mapping, App's
compilation of both translation families, generated QM/QRC resources,
`Application.cpp` bridge installation, `TranslationQtBridge.cpp`,
`src/Base/Translate.cpp` and `SetupQt.cmake` LinguistTools behavior. Losing
GUI registration is the compatibility cost; it does not justify removing
Qt, App/Base resources or fixing gather or absent translation destinations.

For **each** future stage, run isolated regressions for the retired command
and retained dispatch/copy/mapping/archive/QRC behavior, full engine pytest,
licensing checks against committed HEAD, one release build at most, and
inherited CTest against its recorded baseline. Check unchanged App/Base TS
hashes, generated QM/QRC resources, and installed FreeCAD.Qt
load/translate/remove using a known translation. If payload/staging changes,
run the packaged lifecycle gate against the new stage. Report skipped gates
and existing-stage limits explicitly; stub success proves no network workflow.
No live Crowdin execution or shell gate is part of this boundary.

**Next owners:** the overseer reports three unreconciled records; the supplied
snapshot lists two. This work adds one more, so the reconciliation threshold
is reached under either count. The maintainer must fold the actual tail first;
the planner must then write the later bounded disable bet with these files,
retained behavior, compatibility cost and gates. Actors must not implement
from this disposition alone, reconcile, or edit state/plan. Qualification is
complete; implementation and the separate delete dispatch remain pending.
