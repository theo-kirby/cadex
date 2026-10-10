# Docs staleness audit (2026-10-10)

Verified against source: 2026-10-10. Provenance: [Cadex-new] (ADR-628).

*A dated record. It checks every current doc against the source at
`587ffd43`, following ADR-480..ADR-627: the shell's deletion, the
read-only dashboard, no agent of its own, base guidance plus named styles,
and the creature fixes. The rule is AGENTS.md's: code wins over docs. This
pass changed docs only. Code bugs are listed in §3 and were not fixed. When
the owner has settled §4, this file belongs in `docs/history/`.*

## Scope and method

The audit covered `AGENTS.md`, `README.md`, every `docs/*.md` except
`docs/history/` and `docs/probes/`, `training/README.md`,
`training/SETUP.md`, `analysis/README.md`, and the agent guidance:
`CadexAgentGuidance.md`, `CadexAgentStyle.*.md`, `guidance.py` and the output
of `./cadex guidance`.

Checks were made against the source in three ways:
- by grepping and reading the code;
- by running `--help` for every subcommand and every `analysis/` script,
  `./cadex guidance`, `./cadex style --json` and
  `cadex_stress.py --self-check`;
- by dumping `CadexdProtocol.OP_ARG_SPECS`, collecting the test suite, and
  reading the staged payload in the main checkout.

Measured anecdotes from past runs, such as timings and residuals, were not
re-run. They are records.

`docs/DECISIONS.md` is append-only. It was checked only for numbering.

**Counts.** 141 issues were found. 106 are fixed in this branch, including
the seven doc moves. 35 are open, and they reduce to the 11 owner decisions
in §4.
There are also 14 code bugs or stale model-facing strings, which were not
fixed. Every doc that was checked end to end is re-dated 2026-10-10. Two
were only partly checked and keep their old date: `docs/PROVENANCE.md`,
whose catalog source sections §8a–8i rest on outside URLs, and
`docs/MUJOCO.md`, whose historical slices M1–M5 and M9 and §5 hazards were
only skimmed.

## 1. The most significant stale or contradictory items (all fixed)

- **Guidance delivery was misdescribed.** AGENTS.md said the guidance is
  "sent as the server's instructions". In fact `cadex mcp` sends a brief of
  under 2,000 characters that tells the agent to run `cadex guidance`. The
  full text is now about 48,000 characters, not the "about 34,000" that
  CLI.md gave. Several docs also left out the named styles, or named only
  `printed-legged-robot`; `creature` ships too (ADR-626).
- **The dashboard's shape.** DASHBOARD.md, CLI.md and ARCHITECTURE.md said
  the page has two editors and opens as "one 3D viewport". The code has
  three editors, 3D viewport, Status and 2D viewport (ADR-572), and opens
  as 3D plus Status at 0.75/0.25 (`review.js` `DEFAULT_LAYOUT`).
  ARCHITECTURE said no panel shows the evaluation; Status does (ADR-606).
  CLI.md described a "show collision geometry" toggle, a Concept tab and a
  phone column that no longer exist. DASHBOARD §9 cited a test deleted with
  ADR-533.
- **ROADMAP showed removed work as live.** Live mode, live analysis and the
  endless session (ADR-109/110/136) were still checked, although ADR-528
  removed them. `mesh.blender` was not marked retired. The Phase 11 exit
  still required the deleted Blender gate. Phase 15 said O2b was parked;
  it closed with ADR-130. The GPU-run item was "blocked", but it has run
  (ADR-112). The ot5 D-items were open, although STATE.md has them closed.
  ADR-541..627 had no roadmap entry at all.
- **training/SETUP.md said walk continuation "is not automated".**
  `walk --remote --detach` and `--complete` exist (ADR-282). The same
  false sentence is written into every new project's docs by
  `project_docs.py` (§3, item 7).
- **XSCRIPT.md named error codes that do not exist.**
  `SOURCE_POLICY_VIOLATION` is in fact `INVALID_PROGRAM_SOURCE`, and
  `MEMORY_LIMIT_EXCEEDED` is in fact `DOMAIN_MEMORY_LIMIT_EXCEEDED`. The
  doc also said every mutation carries `expected_revision`, but only four
  do. It gave a wrong worker-bundle count (13 instead of 17), a wrong
  `lib.housing` plate default, and an inspect scope list without
  `anatomy`.
- **The packaging doc's manifest example said version `0.0.1`.** Every
  staged payload says `0.0.0`. The doc is now true, and the cause is a code
  bug (§3, item 1).
- **Stale numbers.** These were re-measured: ARCHITECTURE's line, file and
  test counts (2,839 tests collected), PROVENANCE's size table (~220k
  lines), ROADMAP's dynamics-suite count (61) and packaged-gate count (21),
  and the CI status in the packaging doc.

## 2. Issues by doc

`FIXED` means corrected in this branch. `OPEN` means real but not fixed.
`OWNER` means it needs a decision (§4).

### AGENTS.md (re-dated)
- FIXED: guidance delivery (brief vs `cadex guidance`) and styles (line 29).
- OPEN: `build/ctest_baseline_failures.txt`, which AGENTS.md, README,
  ARCHITECTURE, CONTRIBUTING and `pixi.toml` all cite, is untracked and
  absent on this machine. → OWNER.
- OPEN: the Read-this-first table omits CONTRIBUTING.md and PLAN.md.
  PLAN.md is a generated plan view last reconciled 2026-09-09. → OWNER.

### README.md (re-dated; it was 2026-10-03)
- FIXED: "its first page lists every project" is now the viewer home of
  ADR-605.
- FIXED: the guidance is a base plus optional styles.
- FIXED: DESIGN-LANGUAGE.md was missing from the doc list.

### docs/VISION.md (re-dated)
- FIXED: "one guidance text" is now base plus styles.
- FIXED: "no shell diff" is now "no front-end change".

### docs/ARCHITECTURE.md (re-dated)
- FIXED: the styles list now includes `creature`.
- FIXED: the claim that no panel shows evaluation (Status does).
- FIXED: the guidance source names the style file.
- FIXED: added a pointer to CLI.md §4 for the CLI's module map.
- FIXED: added the Noto font files (ADR-568).
- FIXED: re-measured CadexDynamics.py (12,066 lines), cadex_train.py
  (3,224), the test files (159/145/61) and the collected count (2,839).
- OPEN: §2 says worker modules are "copied in rather than imported", yet
  `cadex_library_api`, `CadexCatalog`, `CadexPanels` and `CadexAnatomy` are
  imported by the worker without being in `_DOMAIN_WORKER_BUNDLES`. How
  they reach the sandbox is undocumented, and XSCRIPT.md has the same gap.
  Needs an engine owner's look.
- OPEN: "last full run 1,730 passed (2026-08-09)" is old. §5 has today's
  run.

### docs/IDEAS.md, docs/SHELL-PARITY.md (re-dated)
- FIXED (IDEAS): the per-revision tessellation idea now notes that the CLI
  already keeps per-part models (ADR-546).
- FIXED (SHELL-PARITY): the training-plot row now mentions action std and
  the Status charts (ADR-606).

### docs/CLI.md (re-dated)
All 20 subcommands match the doc. None is missing and none is
undocumented.
- FIXED: `--project` "created if absent" is not true for `review`,
  `budgets`, `style` or `revision`.
- FIXED: the guidance size, now about 48,000 characters.
- FIXED: the walk's train-leg flags now include `--checkpoint-every`,
  `--allow-ungrounded` and the always-on `--stop-on-collapse`.
- FIXED: the collision-geometry toggle is gone.
- FIXED: the list of commands that land a `PROGRESS.md` row was incomplete
  and partly wrong.
- FIXED: the dashboard editors and the default screen.
- FIXED: the Concept tab and phone-column lead.
- FIXED: the shape of `lastPoll()`.
- FIXED: `test_review_history_scale.py` has no browser half any more.
- FIXED: there are six `localStorage` keys, not four.
- FIXED: `error` and `notes` can co-occur, and the per-command envelope
  blocks are now named.
- FIXED: `revision_meshes.py` and `shoves.py` are added to the §4 map.
- FIXED: the styles list.
- RESOLVED (ADR-629): the long dashboard section (about lines 1418–1880) still describes
  page elements that ADR-533 removed. A caveat covers it, but it should be
  trimmed or moved to DASHBOARD.md. → OWNER.
- RESOLVED (ADR-629): much of the dashboard prose duplicates DASHBOARD.md. The HTTP API
  table must stay in CLI.md, because `test_http_api.py` parses it.
- RESOLVED (ADR-629): the dated evidence blocks (the ot4 quill, crank, mix and cart runs,
  and the copy and restart proofs) make up about a third of the doc. Should
  they move to `docs/history/` or `docs/probes/`?

### docs/DASHBOARD.md (re-dated)
The theme question is settled: the code and the doc agree. The page is dark
by default and light or system only on request (`theme.js`). The viewport
and renders always sit on the dark floor.
- FIXED: the Status editor was missing.
- FIXED: the default layout (ADR-572).
- FIXED: action std was missing from the 2D plots.
- FIXED: `--fs-3` is used, not "reserved".
- FIXED: `:root` declares more tokens than the palette.
- FIXED: §9 cited a deleted test and phone assertions the test no longer
  makes.
- FIXED: §15's Videos tab and identity strip are gone; the run video is in
  `api/run/<run>`.
- OPEN: six page ids are absent from the hooks table. This is minor; the
  test only checks that the table is a subset of the page.

### docs/INTEGRATION.md (re-dated)
The op table matches `OP_ARG_SPECS` (15 ops), and the response table matches
`OP_RESPONSE_SPECS`.
- FIXED: only `CLI_TOOL_OPS` (8 ops) is generated from the specs, not the
  agent's "whole tool surface".
- FIXED: the payload `lib/` keeps Qt6 DBus as well.
- FIXED: the non-GUI-Qt paragraph is moved to the payload section.
- FIXED: the guidance section names styles (ADR-560).
- OWNER: `preview_params`, `export_printable` and `resolve_pin` have no
  caller in `cli/`. Their clients were the shell and the dashboard sliders.
- OPEN: rationale prose still mentions "the wiring editor" and "the
  dialog". It is harmless history.
- OPEN: the payload layout tree is duplicated here and in the packaging doc.
  INTEGRATION should keep only the manifest.

### docs/cadex-release-packaging.md (re-dated)
- FIXED: the manifest version is `0.0.0`, with the reason (§3, item 1).
- FIXED: "What ships" now covers `bin/FreeCADCmd`, `bin/python3.11`, `lib/`
  and `share/`.
- FIXED: the CI triggers include `pull_request`.
- FIXED: the CI status is updated. Every run through 2026-10-09 fails at
  "Engine unit suite". §3, item 12 is a likely cause.

### docs/XSCRIPT.md (re-dated)
- FIXED (14): the `CadexScriptStore` line cite; the `expected_revision`
  scope; anatomy `parent_region` is "where present"; nyloc nuts are m3–m8;
  `describe_api section=library_parts` (ADR-619); the `lib.housing` plate
  default; the shell deletion cites ADR-498, not ADR-500; the wiring canvas
  is now `inspect scope="wiring"`; the `anatomy` inspect scope; the
  `INVALID_PROGRAM_SOURCE` code; the kernel-crash text is a message, not a
  correction; the bundle has 17 modules, not 13; the
  `DOMAIN_MEMORY_LIMIT_EXCEEDED` code; the true meaning of `covers nothing`.
- OPEN: the `script.json` field list and the revision-hash field list are
  incomplete. They are not wrong.
- OPEN: "the full `available` list" is capped at 256.
- OPEN: lib's route into the worker (see ARCHITECTURE).

### docs/DESIGN-LANGUAGE.md (re-dated)
- FIXED: style choice per ADR-625. No style is on by default, and the agent
  picks the one its brief names.
- FIXED: a garbled double negative.
- FIXED: §11 now says the creature re-runs happened on 2026-10-09 (record
  `small-brook-2395`) and are not yet rated.
- OWNER: "knee actuator inside the thigh … *owner to confirm*". The style
  file calls it a preference the owner liked.

### docs/ORGANIC.md (re-dated)
- FIXED: the status line. O2b is closed (ADR-130), and so are O1b and the
  October O3b. O4 is parked.
- FIXED: `describe_cad_api` is now `describe_api`.
- FIXED: the `part.mate` signature.
- FIXED: a broken §4 table.
- OPEN: the standing benchmark `~/arch/woof.cadex` does not exist on this
  machine. → OWNER.
- OWNER: "O3b" names two things: the October panels (ADR-610..612) and the
  August "wolf rebuilt on cages" (ADR-129). ROADMAP carries both.

### docs/ROADMAP.md (re-dated)
- FIXED: Phase 17 is in the intro.
- FIXED: the Phase 9 exit note and the 10b shell-side items are closed by
  deletion.
- FIXED: Phase 11 STEP, where export today is `cadex export`.
- FIXED: the Phase 11 exit gate.
- FIXED: the live-mode items are marked removed (ADR-528).
- FIXED: the 14b GPU run is ticked.
- FIXED: `mesh.blender` is retired.
- FIXED: the verification counts.
- FIXED: the "Later" items whose subject is gone (`--model`, `walk
  --prompt`, the GUI-attached walk, the `DECISION:` lines and others).
- FIXED: the status line for the live project review.
- FIXED: five entries for ADR-541..627.
- FIXED: the Phase 17 catalog additions.
- FIXED: the Phase 15 header (O2b closed).
- FIXED: the links to the audits moved to history.
- OPEN: "12 skips is the expected count" for MJX was not re-measured.
- OPEN: the Phase 13b payload "no GUI" `lib/` gap was not re-verified.
- RESOLVED (ADR-629): about 900 lines of pre-ADR-538 run logs ("Later", "Live headless
  project review") belong in history.
- RESOLVED (ADR-629): the opening dependency diagram still draws the Blender shell, "our
  shell" and Qt.

### docs/MUJOCO.md (partly checked; date kept)
- FIXED: M8 and M9 now say "the shell bakes" and "the shell's Training panel
  polls" in the past tense.
- FIXED: three `./cadex -p` mentions are marked removed (ADR-538).
- FIXED: §7 gains a paragraph mapping its steps to today's commands
  (`smoke`, `train`/`walk` with `--remote --detach/--complete`, the
  `train_*` tools, `--checkpoint-every`, and `evaluate`).
- OPEN: no section covers `assembly.success`, motion predicates (ADR-587)
  or ADR-597. They live in XSCRIPT, CLI and training.
- RESOLVED (ADR-629, M0–M9 only; §7c stays): should M0–M9 and §7c's history move to `docs/history/`?

### training/README.md, training/SETUP.md (re-dated)
- FIXED: `action_std_curve` in progress.json.
- FIXED: `curve` is also charted by Status.
- FIXED: the detached walk is automated (see §1).
- FIXED: the trainer's stderr line has four numbers (`sigma`).

### docs/STRUCTURAL.md, analysis/README.md (re-dated)
- FIXED: two stale VISION.md line cites.
- FIXED: `params.specs` is the right field, not `param_specs`.
- FIXED: four drifted line cites.
- FIXED: a CLI.md cite.
- FIXED: "Nothing computes stress" now notes that `part.stress` exists
  (§6.2).
- FIXED: the shell's Save-As is in the past tense.
- FIXED: "Four things worth knowing" is followed by five.
- OPEN: the README's GPL list is a subset of what the test bans (pygmsh,
  fenitop and platypus are missing).
- OPEN: §8.5, whether a headless caller can read the safety factor, is
  unconfirmed.

### docs/FREECAD.md (re-dated)
The `src/Mod` list and every count against
`docs/inherited-modifications.json` match.
- FIXED: Show's rationale. Its only importer is the Part
  AttachmentEditor.
- FIXED: "four areas" is now four of five domains.
- FIXED: `src/Build`, `Doc`, `Ext`, `MacAppBundle` and `XDGData` are
  ledgered.
- FIXED: `updatecrowdin.py` gets a bullet.
- FIXED: §5 is re-dated.
- FIXED: the links to the audits moved to history.
- OPEN: these are removal candidates under the removal protocol: the dead
  `BUILD_JTREADER` gate (`src/Mod/JtReader` does not exist),
  `src/3rdParty/3Dconnexion` and `OpenGL`, the `BUILD_VR` and
  `BUILD_DESIGNER_PLUGIN` options, `src/XDGData` (nothing builds it), and
  Show. → OWNER.

### docs/PROVENANCE.md (partly checked; date kept)
- FIXED: §1's size table is re-measured, with its scopes stated.
- FIXED: the links to the audits moved to history.
- OPEN: the section order is broken. There are two "§8b" headings, §9 sits
  mid-document, 8c–8g follow it, and 8f and 8g are `###`. XSCRIPT's
  "PROVENANCE §8b" cite is ambiguous as a result. Tests pin only the Noto
  and OFL strings, so a renumber is safe.
- OPEN: §2's list of modules "not on the keep-list" mixes four deleted
  modules with Test, which exists.

### The one-off audits at the top of `docs/` (ADR-628)
- FIXED (moved to `docs/history/`): FIFTH-SERVO-AUDIT, HELP-AUDIT,
  HORN-PIGTAIL-AUDIT, START-AUDIT, SURVIVING-DIFF-AUDIT, TEST-TK-AUDIT and
  TRANSLATION-UPDATER-AUDIT. Each was a dated record of finished work.
- Kept in `docs/`:
  - `PHASE8-AUDIT.md`: the `BUILD_GUI=ON` CMake error points at it. →
    OWNER.
  - `HEADLESS-BIPED-REVIEW.md`: two tests and a probe report read it by
    path.
  - `L3-COVERAGE.md`: the evidence for the open Phase 17 L3 item. Its
    banner was re-checked on 2026-10-04 and still holds.

### Agent guidance and `cadex guidance` (no edits needed)
`./cadex guidance` runs with no unfilled placeholder.
`cadex guidance --project P` appends the chosen style, and
`cadex style --json` lists `creature` and `printed-legged-robot`. Every
name in the text was checked and exists:
- every tool (8 `CLI_TOOL_OPS` and 6 bridge tools);
- every inspect scope and `look` view;
- every CLI command and flag;
- every catalog SKU and figure (the QDD tiers, the battery, the horn);
- every `lib.*`, `assembly.*` and `success` name.

- OPEN (minor): the header comment of `CadexAgentStyle.creature.md` says
  "the base tells an agent to choose it". In fact the overlay in
  `guidance.py` does. The comment does not reach the model.

### docs/DECISIONS.md (numbering only)
- OPEN: ADR-111 and ADR-258 are vacant but not recorded in the header.
  ADR-260 is used twice, and its second use follows ADR-259. The log is
  append-only, so this is noted in ADR-628 and not renumbered.

## 3. Code bugs and stale code strings (not fixed)

1. `package/engine/build_engine_payload.sh:38` reads `PACKAGE_VERSION` with a
   `sed` pattern that never matches `CMakeLists.txt:66`, so every payload is
   named and stamped `0.0.0`. Meanwhile `version.json` says 0.0.1 and
   `VERSION` says 0.1.0.
2. `cMake/FreeCAD_Helpers/InitializeFreeCADBuildOptions.cmake:10` (an
   inherited zone): the `BUILD_GUI=ON` error says "the application is the
   shell".
3. `src/Mod/cadex/cadex_tests/test_panels.py::test_panels_and_housings_build_valid_single_solids_on_the_kernel`
   does not skip without a built engine (`FREECADCMD` is None, so the test
   raises `FileNotFoundError`). `pixi run test-engine` therefore fails on a
   bare checkout, against AGENTS.md's "no build needed".
4. `cli/cadex_cli/__main__.py`: the `export --blueprints` help says "the
   shell renders them". `draw_blueprint` draws them (ADR-516).
5. `cli/cadex_cli/__main__.py:1066-1069` and `session.py:142` say
   `agent.json` sits "beside the conversation" and holds `session_id` and
   `model`. Since ADR-538 it holds budgets and the style.
6. `cli/cadex_cli/__main__.py:1105,1141`: `style` and `revision` help says
   `--project` is "created if absent", but both refuse a missing directory.
7. `cli/cadex_cli/project_docs.py:125`: every new project's scaffold says
   "Detached walk continuation is not automated". It is (`walk --complete`,
   ADR-282).
8. `analysis/search.py:166` tells the user to run "one `./cadex -p` turn",
   which ADR-538 removed.
9. `training/cadex_train.py`: the `--progress` help names the shell's
   Training panel, and a comment near line 3098 names a deleted
   `cadex_training.py`.
10. `src/Mod/cadex/CadexFitReport.py:1201`: the model-facing `covers
    nothing` detail says "inside its box", but the code tests a box grown by
    5 mm and excludes world geometry.
11. `cli/tests/test_review_history_scale.py`: the module docstring and the
    unused helpers (`OBSERVE`, `_idle_poll_additions`) describe a browser
    half that no test runs.
12. CI (`.github/workflows/cadex-app.yml`) fails at "Engine unit suite" on
    every run through 2026-10-09. The log was not readable. Item 3 is a
    plausible cause, since CI's unit job has no built engine.
13. `src/Mod/CMakeLists.txt:10-12`: the dead `BUILD_JTREADER` gate.
14. The header comment of `CadexAgentStyle.creature.md` (see §2).

## 4. Decisions the owner needs to make

1. **Payload version.** Which file names the payload: `VERSION` (ADR-166
   says it is the source of truth), `version.json` or CMake? Then fix
   §3, item 1.
2. **Client-less protocol ops.** Should `preview_params`,
   `export_printable` and `resolve_pin` be subtracted? That needs an ADR,
   an `OP_ARG_SPECS` change and test changes.
3. **`build/ctest_baseline_failures.txt`.** Five files cite it, but it is
   untracked and absent. Regenerate it, commit a baseline, or drop the
   instruction.
4. **`PHASE8-AUDIT.md` to history.** This needs the inherited-zone CMake
   message (§3, item 2) changed first.
5. **History moves inside the large docs.** RESOLVED (2026-10-10,
   ADR-629): the owner approved the move.
   - CLI.md's dated evidence blocks and its stale dashboard prose went to
     `docs/history/CLI-EVIDENCE.md`, with a pointer to DASHBOARD.md for
     the page (3,651 → 3,159 lines);
   - ROADMAP's finished "Later" items, the ot5 run log and the dependency
     diagram went to `docs/history/ROADMAP-RUNS.md` (3,014 → 2,248);
   - MUJOCO.md's M0–M9 went to `docs/history/MUJOCO-SLICES.md`
     (3,420 → 1,796). §7c stays, because code cites its rows.
6. **O3b name collision.** Rename either the October panels or the August
   cages benchmark, in ORGANIC.md and ROADMAP.md.
7. **The knee actuator inside the thigh.** It is marked "owner to confirm".
   Is it a confirmed rule, or a preference?
8. **`~/arch/woof.cadex`.** Give the benchmark's real location, or mark it
   gone.
9. **PLAN.md.** This generated plan view was last reconciled on
   2026-09-09. Regenerate it, list it in AGENTS.md, or delete it.
10. **Removal candidates** under `docs/FREECAD.md` §3: Show, XDGData,
    MacAppBundle, the 3rdParty GUI residue, `BUILD_VR`,
    `BUILD_DESIGNER_PLUGIN` and the JtReader gate.
11. **MUJOCO.md success-spec section.** Should the dynamics vertical cover
    `assembly.success` and motion predicates itself, or keep pointing at
    XSCRIPT?

## 5. Tests

All runs were CPU-only (`CUDA_VISIBLE_DEVICES="" JAX_PLATFORMS=cpu`), in
this worktree, with no engine build (the worktree has no `build/`).

- `pixi run test-engine`: 2,595 passed, 243 skipped, 1 failed. The one
  failure is §3, item 3. It is environmental (no engine build in the
  worktree), and it fails the same way on the untouched baseline. Pointed at
  the main checkout's staged payload, it fails differently ("No module named
  'freecad'"), so the test is not payload-aware either.
- `pixi run python -m pytest cli/tests`: 1,148 passed, 112 skipped, 0
  failed. The engine-needing half skips without a build, as AGENTS.md
  warns.
- Pinned doc tests: these were run after the edits and are green:
  - `test_project_docs.py`
  - `test_http_api.py`
  - `test_review_design.py`
  - `test_dashboard_read_only.py`
  - `test_evaluate.py::test_the_report_block_is_documented`
  - both `test_agent_guidance.py` files
  - `test_licensing_compliance.py`
  - `test_response_schemas.py`
  - the INTEGRATION op-table test
