# ARCHITECTURE-REVIEW.md — A Holistic Review of Cadex

Verified against source: 2026-10-10 (tree at `587ffd43`; projects in `~/cadex-projects` read, not modified)

This is a review, not a plan of record. It measures the tree as it stands after the 2026-10-09
creature work (ADR-608..627), diagnoses the panel/shell system, assesses how far the
architecture is from non-creature machines, and ranks what to do. Where it disagrees with
`docs/ARCHITECTURE.md`, the code was checked and wins (§1.8 lists the drift). Nothing here
is authoritative over `docs/VISION.md`; recommendations that would change direction say so
and need an ADR.

## 0. Summary

- **The core is sound.**
  - One script, one sandboxed worker, one digest.
  - One protocol, pinned both ways.
  - One tool surface, 14 tools.

  These have held through 627 ADRs, and they are what make breadth *possible*: a new machine
  class costs ops on existing domains, not a new domain.
- **The accretion is in the layer above the kernel:**
  - **verification**: nine separate fit and clearance paths;
  - **presentation**: six or more render, film and video entry points;
  - **the declared tables**: four copies of one pattern;
  - **the guidance**: 6,012 words in the always-on base.

  Most of it was added one charter criterion at a time, and much of it assumes a legged robot.
- **The panel system fails for an architectural reason, not a tuning one.** `lib.panel`
  runs at script-evaluation time with no kernel. It therefore carries a second, pure-Python
  CSG evaluator (`CadexPanels.sample`), and it can only express a *closed convex sleeve along
  one straight axis*. That shape is the "egg/sausage" the style forbids.
  - None of the nine creature projects of 2026-10-09 kept a `lib.panel`.
  - The one that tried it (castra-heron) removed it twice: "obscured the mechanism, collided
    with moving links", "measured 10.2 mm away from its frame and its screws missed the frame".

  The fix is to move panels into the worker as an *open patch of a closed-then-offset
  envelope*, with seams, openings, mounts and motion clearance (§2.3).
- **Breadth is blocked by four general mechanisms more than by missing SKUs** (§3.3):
  - n-joint couplings (belt→carriage, CoreXY, differential);
  - a slider in a closed loop (every hydraulic linkage);
  - a world beyond a 1 m floor;
  - task metrics that are not gait.

  The catalog gaps (rails, belts, steppers, extrusion, cylinders, spindles) are real, but
  each is a data row once the catalog is data.

## 1. The architecture as a whole

### 1.1 Size and shape

| Area | Files | Lines | Notes |
|---|---|---|---|
| Engine `src/Mod/cadex/*.py` | 55 | 80,255 | plus `CadexGeometryWorker.cpp` (1,032) and 3 guidance `.md` (50 KB) |
| CLI, dashboard, MCP `cli/cadex_cli/*.py` | 37 | 21,186 | plus `review_static/` |
| Engine tests `cadex_tests/` | 159 (145 `test_*`) | 70,739 | 2,216 tests |
| CLI tests `cli/tests/` | 83 (80 `test_*`) | 30,960 | 973 tests |
| `docs/DECISIONS.md` | 1 | 38,593 | 621 ADR headings, numbered to ADR-627 |

The largest modules, from `wc -l` on 2026-10-10:

| Module | Lines |
|---|---|
| `CadexDynamics.py` | 12,066 |
| `cadex_assembly_worker.py` | 8,510 |
| `cadex_assembly_api.py` | 5,138 |
| `cadex_part_worker.py` | 4,713 |
| `CadexScriptedDomainPublication.py` | 4,153 |
| `cadex_part_api.py` | 3,401 |
| `cli/__main__.py` | 3,267 |
| `cli/review_server.py` | 3,176 |
| `CadexScriptedRuntime.py` | 3,003 |
| `CadexStudio.py` | 2,643 |
| `cadex_library_api.py` | 2,624 |

Across the engine and CLI there are 2,722 functions: 169 are over 100 lines, and 54 are over
200. The longest:

| Function | Location | Lines |
|---|---|---|
| `_build` | `cadex_part_worker.py:3560` | 875 |
| `validate_and_solve_assembly` | `cadex_assembly_worker.py:7637` | 874 |
| `build_parser` | `cli/__main__.py:207` | 576 |
| `_command_walk` | `cli/__main__.py:2404` | 539 |
| `build_model` | `CadexDynamics.py:3251` | 461 |
| `run` | `cli/smoke_runner.py:173` | 425 |

Tests outweigh code roughly 1:1, which is healthy. But the engine suite is nearly as large as
the engine, and many tests pin prose and numbers that ADRs then amend. That is part of why
each change costs an ADR plus a test edit.

### 1.2 Layering and boundaries

The intended picture (`docs/ARCHITECTURE.md` §1-2):

- the CLI and the dashboard sit on one side of a *process* boundary;
- the CLI imports nothing from `src/` except `CadexdProtocol`, loaded by path
  (`ARCHITECTURE.md:255-257`);
- `cadexd` stays light;
- the worker does geometry.

What holds:

- **No module-scope import cycles** in the engine or the CLI.
- `CadexDynamics` stays out of `cadexd`'s closure, as `test_engine_purity_guardrails` asserts.
  It is imported only lazily by `cadex_assembly_worker`.
- The protocol is pinned both ways: `OP_ARG_SPECS` and the response goldens.

What has eroded:

- **The CLI loads five engine modules, not one.**
  - `cli/cadex_cli/studio.py:50-58` loads `CadexStudio`, `CadexFitReport`, `CadexPrintables`
    and `CadexAnatomy` by path. They are then used as `STUDIO`, `FIT_REPORT` and `ANATOMY` in
    12 CLI files: `bridge.py` 21 uses, `clearance.py` 21, `render.py` 11, `review_server.py` 12,
    `video.py` 7.
  - The child runners `evaluate_runner.py:103-104` and `checkpoint_runner.py:73-74` do
    `sys.path.insert` and then `import CadexDynamics`.
  - `smoke.py:266` calls a private engine function, `FIT_REPORT._threaded`.

  These are pragmatic: all of them are FreeCAD-free pure Python. But they are a **second,
  unpinned contract** across the boundary ADR-061 drew, and the docs still say there is one.
- **Rendering lives in the engine.** `CadexStudio.py` is a 2,643-line CPU rasteriser under
  `src/` that only the CLI calls. "No UI in the engine" is kept in letter: no Qt, no Coin. But
  presentation code sits in the engine tree, and is staged into its payload, purely so the CLI
  can load it by path.
- **Function-scope hubs.** These modules import most of the engine lazily:

  | Module | Lazy imports | Module-scope imports |
  |---|---|---|
  | `CadexInspection` | 11 | |
  | `CadexScriptedRuntime` | 12 | 3 |
  | `cadexd` | 12 | 1 |
  | `cadex_project_worker` | 11 | 5 |

  Four lazy cycles exist:
  - the six `cadex_*_api` modules, through `cadex_domain_api`;
  - assembly worker ↔ domain worker ↔ mesh worker;
  - `CadexPanels` ↔ `cadex_library_api`;
  - `CadexScriptedRuntime` ↔ `CadexWarmWorker`.

  The closure test guards what is *loaded*, but the true dependency graph is denser than the
  module-scope graph suggests.
- **The worker bundle is hand-listed.** `_DOMAIN_WORKER_BUNDLES["project"]`
  (`CadexScriptedRuntime.py:44-129`) names **29 files**. `ARCHITECTURE.md:121-123` says "five
  … and seventeen more". Every new pure module must be added by filename, which is the
  mechanism that made `CadexPanels`, `CadexAnatomy` and the rest cheap to add and easy to
  forget.

### 1.3 The xscript model and the library

**The model is the project's best idea, and it scales.**

- There are five domains: `part` has 60 ops, `assembly` 27 and `lib` 25.
- Values are lazy recipes (`DomainValue`), and the worker evaluates them once.
- Topology is named by selectors (ADR-029), not indices.

**The structural tension is `lib`.** `lib.*` runs at **script time**, composing recipes with
no kernel (`cadex_library_api.py`, "FreeCAD-free"). That suits the generators that are pure
functions of catalog rows: bolts, bearings, a QDD envelope, gears. It does not suit anything
that depends on *other geometry*. Panels, bays, clearance-driven bosses and routing all need
geometry, and the codebase has three answers to the problem:

1. **Re-derive the geometry in Python.**
   - `CadexPanels.sample`, a ~330-line CSG evaluator (`CadexPanels.py:359-690`).
   - The ring fit, which duplicates `CadexCage`.
   - The kernel-neutral modules `CadexRouting`, `CadexBundle`, `CadexSolder` and
     `CadexTerminals`, where it is justified because they are algorithms over inputs, not
     re-implementations of OCCT.
2. **Make it a worker op**: `part.cable`, `part.mate`, `part.offset`, `part.stress`.
3. **Declare a table and let the worker resolve it**: `mounts`, `boards`, `nets`, `cage`.

The third answer is the right one for anything placement-dependent, because the worker
publishes exact frames that the script references by name. `lib.panel` chose the first answer
(ADR-610, "Rejected: measuring the contents in the worker, which would leave the screws'
positions unknown to the script"). The third answer removes that objection. A rule worth
writing down:

> **`lib.*` may compose catalog rows; anything that needs another part's geometry is a worker
> op that publishes named frames.**

**Declared tables: four copies of one pattern.** `CadexNets`, `CadexBoards`, `CadexMounts`
and `CadexCage`, with `CadexTerminals` beside them, each implement:

- an error class and a `_MARKER`;
- `canonical_*rows`: 66 / 72 / 76 / 63 lines;
- `declared_*`;
- `prune_*`, each citing ADR-039 in near-identical docstrings;
- `effective_*`;
- a `*Collector` with an `_called` guard: 131 / 208 / 115 / 83 lines;
- a `*Values` mapping;
- a staged stub;
- for Boards and Mounts, `row_from_world`: 56 / 58 lines.

That is 1,549 lines across five modules, about 1,280 of them the same structure. "A stored row
list replaces the declaration" is implemented four different ways:

- `CadexNets.py:315`: the whole list;
- `CadexCage.py:368`: per cage;
- `CadexMounts.py:399`: the whole list;
- `CadexBoards.py:514`: the whole list plus a derived selector.

The override plumbing is threaded by hand: `*_values` appears 58 times in
`CadexScriptedRuntime` and 37 times in `cadex_project_worker`, and the four collectors are
wired one by one at `cadex_project_worker.py:825-840`. These tables were built for the deleted
shell's editors: ring-drag, the wiring editor, the board editor (`docs/SHELL-PARITY.md`). With
the dashboard read-only (ADR-537), **stored overrides have no writer except `set_params`**,
and the "prune drift" rule exists for edits nobody can now make. A shared `DeclaredTable` base
would remove an estimated 700-900 lines. Dropping stored overrides entirely would remove more,
but it is a direction change (ADR).

**Small algebra, redefined everywhere.**

| Helper | Files that define it |
|---|---|
| `_unit` | 8 |
| `_cross` | 7 |
| `_finite` | 6 |
| `_dot` | 4 |
| `_sha256` | 9 CLI files |

`CadexPanels.py:86-233` carries its own matrix inverse, `_rotation_between` and `axis_angle`.
`CadexDynamics.py:368-676` carries frames and quaternions. `CadexCage` and `CadexMounts` borrow
`CadexBoards`' private helpers (`CadexCage.py:54-62`). One `CadexVec.py`, FreeCAD-free and
staged, removes several hundred lines and a class of sign-convention bugs.

**The catalog is code.** `CadexCatalog.py` is 1,559 lines of Python dicts. Every family has
meant a table, a generator in `cadex_library_api.py`, a `describe_api` entry and an ADR. Five
of the 25 generators have **never been used** in any of the 320 projects:

- `lib.spur_gear`;
- `lib.rack`;
- `lib.rack_and_pinion`;
- `lib.linear_actuator`;
- `lib.bldc`.

`lib.qdd` has 94 uses, `lib.bearing` 88 and `lib.housing` 34. §3.3 proposes the catalog as data.

### 1.4 The tool surface and guidance

**Tools.** There are 14 (`tool_definitions`, `tools.py:584`):

- 8 engine ops (`CLI_TOOL_OPS`, `tools.py:50`);
- 6 bridge tools: `look`, `draw_blueprint`, `train_start`, `train_status`, `train_stop`,
  `evaluate`.

`inspect` has 14 scopes (`tools.py:509`). The surface is small and principled, and it should
stay that way. New capability belongs in xscript ops and `inspect` scopes, not in new tools.

**Guidance.** `guidance.OVERLAY` (`guidance.py:97-333`) wraps `CadexAgentGuidance.md`, and a
style is appended (`guidance.py:335`). The base is **6,012 words in 90 lines**. Its longest
paragraphs explain *how to read the reply's verification blocks*:

| Paragraph | Words | Line |
|---|---|---|
| HOLD EVERY PART | 613 | `:43` |
| MOTION FIT | 528 | `:30` |
| FIT IS MEASURED | 409 | `:28` |
| CATALOG IDENTITY | 252 | `:29` |

That is about 1,800 words teaching the agent the shape of JSON blocks that the blocks could
explain themselves (each already carries `source` and `note` strings, e.g.
`CadexFitReport.SHELL_NOTE`).

The base also holds domain-specific rules:

- "A MACHINE IN AN ANIMAL'S FORM MOVES LIKE ONE" (`:36`);
- the QDD and servo tier choice (`:64-65`);
- target speed and stride (`:80-81`).

The owner's own rule (memory, 2026-10-03) is "domain-neutral base plus optional styles". The
base has drifted towards legged robots, and there are only two styles, both legged or
creature: `CadexAgentStyle.creature.md` and `CadexAgentStyle.printed-legged-robot.md`.

### 1.5 The verification stack

This is the subsystem with the most duplication, and it is also the most valuable. There are
nine paths that measure interference or clearance:

| # | Path | Where | Judged by |
|---|---|---|---|
| 1 | Static exact-solid pairs | `cadex_assembly_worker._measure_clearance :6216`, `_check_fit :7240` | `CadexFitReport.pair_status :91`, `fit_summary :1240` |
| 2 | Joint sweeps, tree and loop | `_sweep_joint :6622`, `_sweep_loop_joint :6908`, `_measure_joint_sweeps :7044`, `CadexDynamics.loop_sweep :4098` | `sweep_summary :191` (314 lines) |
| 3 | Shell gaps | `_measure_shell_gaps :7424` | `shell_summary :1083` |
| 4 | Mounting, "held", attachments | from pair rows | `mounting_summary :790`, `attachment_summary :536` |
| 5 | Clearance along a simulation trace | `_clearance_over_trace :3228`, `_declared_clearance :3176` | |
| 6 | MuJoCo contacts | `CadexDynamics.collision_geoms :1309`, `_measure_reset_clearance :8513`, `contact_offsets :11767`; `CadexInspection.contact_pairs :1081`; `review_server.collision_proxies :669` | |
| 7 | Smoke penetration in stock MuJoCo | `cli/smoke_runner.py` | |
| 8 | Exact BREP re-measurement in a separate FreeCAD child | `cli/smoke_geometry.py`; `smoke.thread_allowances :241` re-reads the engine's thread rule | |
| 9 | Bounds agreement | `clearance.bounds_agreement :179` | |

Plus the anatomy block (graph only) and the image proxies (`CadexStudio.PROXY_BARS :201`).

The common shape underneath all nine is *pairs × poses → distance and common volume*, with
the poses coming from:

- the rest pose;
- a joint sample;
- a closed-loop re-solve;
- a simulation frame;
- an MJCF reload.

**One pose-set × pair-set measurement service**, with the five pose sources as inputs and
`CadexFitReport` as the only judge, would collapse paths 1, 2, 3, 5 and 8, and make panels'
motion clearance (§2) free. Today's checks are also uniformly *advisory*: `shells`,
`mounting`, `anatomy` and `sweep` are counted among no failure. Agents treat advisory as
optional, and the cfix runs left panels and mounting "to come".

### 1.6 Dynamics and MuJoCo

`CadexDynamics.py` is 12,066 lines with 177 top-level functions. `docs/ARCHITECTURE.md:219`
says 10,824. The section markers are natural module seams:

| Lines | Section | Size |
|---|---|---|
| `:128-676` | units, frames, quaternions | ~550 |
| `:677-1662` | inertia, collision | ~985 |
| `:1663-2229` | joint table, forest | ~565 |
| `:2230-3998` | model build | ~1,770 |
| `:3999-5953` | closed-loop motion (ADR-621) | ~1,955 |
| `:5954-10492` | tasks: identity, actions, reward, bundle, episode | **~4,540** |
| `:10493-11373` | policy | ~880 |
| `:11374-` | rollout | ~690 |

The task half is legged in its vocabulary:

- `evaluation_rig(feet=...)` and `hip_height_mm` (`:9342-9514`);
- "Name the components that are feet" (`:6107`);
- `CadexEvaluation.METRICS` (`:94`), with 12 of 31 metrics in a feet-based `gait` family;
- tuning constants `STANCE_MM`, `STEP_ADVANCE_HIP_HEIGHTS` and `REST_TILT`
  (`CadexEvaluation.py:59-81`).

The CLI has a **second gait reading**, `walk.gait_from_trace` (`walk.py:899`), separate from
`CadexEvaluation.gait` (`:395`). `smoke_runner.py` re-implements termination and tilt
(`_quat_tilt_degrees :167`).

The translator's general gaps, which matter for §3:

- a slider loop closure is refused (`:1836`);
- `rack_pinion` is refused (`:2381`);
- couplings are two-joint linear only (`:2358`, `:2506`);
- actuators are joint-transmission with gear 1 only (`:3500-3530`);
- there are no tendons;
- the world is a floor.

### 1.7 Creature- and robot-specific assumptions in general machinery

Word counts with tests excluded: `leg` 226, `servo` 130, `shove` 109, `anatomy` 89, `foot` 83,
`gait` 69, `feet` 69. The ones that shape behaviour:

1. **`assembly.anatomy` and `CadexAnatomy`** (ADR-613/614) are a creature concept in the
   general assembly API. `SUGGESTED_REGIONS` is spine, neck, jaw, tail, legs and wings
   (`CadexAnatomy.py:43-47`). The `inspect` tool calls it "the creature's MOVING ANATOMY"
   (`tools.py:472`, `:526`). The useful general fact underneath it is *which declared
   subassemblies have actuated DOF, and which rigid appendages protrude*. That is a "regions"
   or "subsystems" declaration, which a tractor (steering, hitch, PTO) needs too.
2. **Held-by families are hard-coded.** `CadexFitReport.py:639` has
   `DRIVE_FAMILIES = {"servo","gearmotor","bldc","qdd"}` and
   `OUTPUT_FAMILIES = {"servo_horn","wheel"}`. A pulley on a stepper or a spindle's collet is
   "held by nothing" until the code is edited.
3. **Stance is assumed.** The fit notes assume "a leg reaching below its stance" and "a foot
   on the floor" (`CadexFitReport.py:146-152`, `:1279-1280`). The smoke support check
   requires the base to "still hold the attitude" (`smoke_runner.py:20-26`).
4. **The key-numbers sheet always counts "servos"** (`CadexStudio.py:1214`, `:1641-1683`).
5. **The API tutorial is legged.** Examples use `m['leg']`, `hip_l` and
   `cage({'torso': ...})` (`CadexScriptedRuntime.py:2899-2919`).
6. **`appearance` conflates tone and role** (§2.2, item 8).

None of these is wrong for a legged robot, and most are a constant or a rename away from
general. Together, they mean a non-legged machine meets a stream of irrelevant or misleading
blocks: gait metrics, "servos: 0", anatomy `undeclared`, stance notes.

### 1.8 Dead code and doc drift

**Likely dead.** Grep each name as a quoted string before deleting it, because the sandbox
dispatches some names by string.

- **`CadexProject.py` (914 lines).** No engine or CLI module imports it. The string
  `"CadexProject"` that does appear is a workbench name (`cadexd.py:295`,
  `CadexScriptedDomains.py:347`). Only three `cadex_tests/*_integration.py` scripts import it.
  Its `CadexConversationStore` (conversations, from the deleted shell's chat panel) has no
  callers.
- `cadex_domain_worker._assembly_worker_validation` (`:969`, 113 lines) and
  `_build_isolated_sketch` (`:599`).
- `CadexTools.normalize_tool_failure` (`:112`, 90 lines) and
  `ToolSpec.supports_edit_mode` (`:303`).
- `CadexScriptedPublication`: `retarget_references` (`:533`), `model_publications` (`:136`),
  `group_implementation` (`:382`), `delete_implementation` (`:432`) and three smaller ones.
- `CadexReferenceContracts`: six functions, among them `scripted_model_dependencies`
  (`:234`), `capture_native_part_carriers` (`:626`) and `validate_native_part_refresh`
  (`:745`).
- `CadexModelingSurface.infer_engine_from_names` (`:235`) and
  `CadexScriptedOwnership.delete_owned_model_objects` (`:63`).
- **Unused library generators:** the five listed in §1.3.

In total there are 38 names with no reference outside their definition, and 10 more
referenced only by tests.

**Doc drift in `docs/ARCHITECTURE.md`:**

| Line | It says | Measured |
|---|---|---|
| `:219` | `CadexDynamics.py` is 10,824 lines | 12,066 |
| `:410` | `training/cadex_train.py` is 2,993 lines | 3,224 |
| `:431` | 146 test files | 159 (145 `test_*`) |
| `:121-123` | the project bundle is 5 + 17 modules | 29 |
| `:255-257` | the CLI imports only `CadexdProtocol` from the engine | 5 modules (§1.2) |
| `:439-445` | 2,634 collected, 1,730 passed | dated 2026-08-09, unverified here |

The CLI's runners (`smoke`, `film`, `video`, `evaluate`, `walk`, `loop`) are barely mentioned.

### 1.9 Presentation and lifecycle duplication (CLI)

**Render, film and video.** All run over one rasteriser (`CadexStudio`):

- `render.py`;
- `video.py`, with two styles: CPU studio, and headless Chromium through `browser.py` and
  `review_server`;
- `film.py`, which reuses `video`'s private `_studio_frames`, `encode`, `_posed` and `_rows`;
- `shoves.py`, on `film._Stage`;
- `section.py`;
- the `look` and `draw_blueprint` bridge tools;
- the three.js viewer.

**Lifecycle runners:**

- `walk.py`, 1,132 lines, plus `_command_walk`, 539 lines;
- `loop.py`, 891 lines;
- `smoke.py`, `smoke_runner.py` and `smoke_geometry.py`;
- `evaluate.py` and `evaluate_runner.py`;
- `checkpoints.py` and `checkpoint_runner.py`.

`checkpoint_runner.py:43-57` and `evaluate_runner.py:86-100` are identical copies.
`cadex walk` is "kept as one scripted single pass and is not the ot11 loop" (ADR-464). It is a
candidate for removal now that any agent drives the lifecycle through MCP (ADR-538).

## 2. The panel/shell system, in depth

### 2.1 How it works today

Four pieces, landed together on 2026-10-09 (ADR-610..612, ADR-626):

| Piece | Where | Lines | What it does |
|---|---|---|---|
| `lib.panel` | `cadex_library_api.py:2482` → `CadexPanels.build_panel` (`CadexPanels.py:1329`) | ~1,280 of `CadexPanels.py` | Wraps a closed superellipse sleeve, lofted along one axis, round everything in `over` *plus the frame*; splits it; plans screw bosses |
| `lib.housing` | `cadex_library_api.py:2525` → `CadexPanels.build_housing` (`:1557`) | ~210 | A drum (QDD) or tub (servo) grown from the catalog envelope, screwed through the drive's own holes |
| `fit.shells` | `cadex_assembly_worker.py:7424` (`_measure_shell_gaps`) + `CadexFitReport.shell_summary` (`CadexFitReport.py:1083`) | ~100 + ~180 | For every component with `appearance="shell"`: median inner-face gap, `2V/A` wall estimate, held-by-screws |
| creature style rule | `CadexAgentStyle.creature.md:21` and base `CadexAgentGuidance.md:50` | prose | "PANELS WRAP THE MECHANISM … grown from what it covers (`lib.panel(over=[...])`)" |

The `lib.panel` pipeline (`CadexPanels.py`):

1. **A second geometry kernel.** `sample()` (`:359-690`, about 330 lines) re-evaluates part
   *recipes* in pure Python: primitives into surface points, transforms, booleans, and lofts,
   with a point-membership test where the tree permits one. It has to exist because `lib.*`
   runs at script-evaluation time and has no OCCT. ADR-610 says so: "Rejected: measuring the
   contents in the worker, which would leave the screws' positions unknown to the script."
   Imported, meshed, offset and swept parts are refused, or return `_unknown` membership
   (`:338`). Partial spheres, partial cylinders and wedges also have no membership test.
2. **Stations along one axis.** `plan_panel` (`:875`) stands 3-40 stations every `step` mm
   (default 12). Each station takes the points within ±half a step and fits *the tightest
   convex superellipse* about the window's box centre (`fit_ring`, `:720`). The centres are
   then smoothed, and the half-axes become a slope-limited envelope of at most 0.15 mm per mm
   (`MAX_SKIN_SLOPE`, `:77`). `exponent=None` picks one exponent from 2-6 for the whole panel.
3. **A closed sleeve.** `build_panel` lofts an outer and an inner B-spline ring per station and
   cuts the inner from the outer. The result is a **360° tube, open at both ends**
   (`:1385-1397`), cut into pieces by axial `seams` and at most one axis-parallel parting
   plane (`split="top_bottom"|"left_right"`, `_SPLITS` `:809`).
4. **Bosses.** `_plan_bosses` (`:1006`) and `_boss_option` (`:1111`) search 8 angles × 7
   lateral offsets × stations for a radial line that reaches the frame without crossing other
   parts. Each boss is a cylinder from the frame's surface up to the skin. The screw is a
   stocked `lib.bolt`, and the frame gets tap-drill pilots in `.holes`.

### 2.2 Why it produces poor results

**Evidence from real outputs.** These are the nine creature projects of 2026-10-09: `cfix-*`
(Opus, after ADR-608..627 landed) and `castra-*` (Codex/Astra). All chose the creature style
(`agent.json`).

| Project | `lib.panel` in the final `script.py` | in any `script_history/` revision | `lib.housing` | How the "panels" were made |
|---|---|---|---|---|
| cfix-deinonychus-a | 0 | 0 of 4 | 10 | none; the DECISIONS.md "Structural links are `mechanism`; `shell` is kept for panels", but no panels |
| cfix-deinonychus-b | 0 | 0 of 6 | 1 | "shell" put on torso, thigh, shin, tarsus, neck, skull, tail links (`script.py:271-457`) |
| cfix-heron-a | 0 | 0 of 6 | 1 | "Torso and head panels (`lib.panel`, shell)" still listed under *to do* (DECISIONS.md:110) |
| cfix-heron-b | 0 | 0 of 7 | 9 | "Shell check: the jaw, the feet and the neck_2 links are flagged … No torso panels or tail yet" |
| cfix-leopard-a | 0 | 0 of 7 | 10 | none |
| cfix-leopard-b | 0 | 0 of 3 | 0 | 87-line script, unfinished |
| castra-deinonychus | 0 | 0 of 4 | 1 | none |
| **castra-heron** | 0 | **3 of 9** | 1 | **tried `lib.panel` and removed it** (below) |
| castra-leopard | 0 | 0 of 3 | 1 | none |

None of the nine shipped a single `lib.panel`. The one project that tried it, castra-heron,
removed it twice, and recorded why in its project ADR-006:

> "The large generated torso sleeve obscured the mechanism, collided with moving links and
> lacked a physical mounting seat. It was removed. … The generated compact panel still measured
> 10.2 mm away from its frame and its screws missed the frame. It was replaced by an explicit
> rounded lid derived from the catalog Pi envelope … two M2 x 8 screws into integral 5.6 mm
> diameter posts."

Its history revision `0006` shows the call:
`lib.panel(over=[controller.body], axis=(1,0,0), up=(0,0,1), span=(-82,-12), exponent=4,
split="top_bottom", split_at=H+110, mount_to=…)`. The hand-made replacement is a rounded box
less a rounded box, two posts and two screws. That is what a designer would draw, and the
library could not produce it.

**Root causes, in order of weight:**

1. **The wrong primitive: a sleeve, not a panel.** A real shipping robot's cover is an *open
   patch* of surface: a top cover, a side cover, a belly pan. It follows the frame and the
   masses under it, ends in a return flange or lip, and screws into the frame's edge. Examples
   are Spot's and ANYmal's body covers, a Unitree's top shell, and the panels on a Meca500.
   `lib.panel` makes a *tube round everything*, including the frame (`build_panel`, `:1352`:
   "The frame is covered too, whether or not over= names it"). Splitting the tube top and bottom
   gives two half-tubes, still wrapped round the frame's sides, and still a sausage. The style
   names that very defect: "an egg, a dome, a sausage or a cone".
2. **Convexity per station is a hull, and the hull is the egg.** Each ring is a convex
   superellipse fitted to the whole section (`fit_ring`), and the slope limit can only *grow*
   rings (`_fit_rings`, `:847-872`). So the skin is a smoothed convex hull swept along one
   axis. ADR-610's own Consequences measure it: "one panel over a tall narrow part on a wide
   deck stands off the deck's sides by the step (p90 9.6-10.5 mm)". castra-heron measured 10.2
   mm. A cover over two masses with a valley between them must dip into the valley, and a
   convex ring cannot.
3. **One straight axis.** Stations stand along one straight `axis`. A creature torso pitched
   at an angle, a curved neck, an excavator's house, a mower deck: none of these sweeps along
   one line. Real panels are shaped by a *surface* intent, not an axis.
4. **No motion awareness.** The panel is fitted to the rest pose only. castra-heron's sleeve
   "collided with moving links". The engine already has the exact-solid joint sweep (ADR-349,
   ADR-621). The panel never consults it, and `fit.shells` does not either.
5. **No openings.** A cover over a body with four hip drives needs holes where the legs leave,
   where cables exit, and where the sensor looks out. The tube has none, so the agent must cut
   them by hand, in recipe space, against a skin whose numbers it cannot see.
6. **Bosses that miss.** Boss lines are radial within a station plane, aimed at one of 8 fixed
   angles (`_BOSS_ANGLES`, `:817`). The frame surface comes from *sampled points* whenever the
   frame has no membership test (`exact_frame: false`). That covers any frame built from lofts,
   offsets or fillets, which is most good-looking frames. Hence "its screws missed the frame".
7. **A Python CSG kernel shadows OCCT.** `sample()` is a second geometry evaluator that must
   track every op the real worker supports, and refuses the rest. That is the "two of
   anything" VISION.md forbids. It also duplicates the frame and vector algebra found in six
   other modules (§1.4).
8. **The check confuses colour with role.** `appearance="shell"` is a palette tone (ADR-413,
   `cadex_assembly_api.py:1301`) *and* the trigger for `fit.shells`
   (`cadex_assembly_worker.py:7441`). Agents painted structural links "shell" to get the light
   tone (cfix-deinonychus-b, cfix-heron-b). The check then judged thighs and jaws as panels and
   flagged them, which taught the agent nothing about panels.
9. **The check measures the wrong things.** "What it covers" is *whatever's box comes within 5
   mm of the shell's box* (`_SHELL_ENVELOPE_MM`, `:7383`), not what the agent said it covers.
   The verdict is a *median* gap under 6 mm (`SHELL_FLOATING_GAP_MM`, `CadexFitReport.py:1064`).
   A sleeve hugging a deck's top face passes, even while it stands 10 mm off the sides. Nothing
   measures:
   - **coverage**: does it hide what it was meant to hide;
   - **exposure**: does it hide an actuator the style says must show;
   - motion clearance;
   - minimum wall;
   - bed fit;
   - seam quality;
   - **form**: the enclosed-volume ratio that separates a wrap from an egg.

   The check is also advisory and counted in no failure.
10. **Cost and ordering.** In the cfix runs, panels were always the *last* step ("to come"),
    and the sessions ran out of budget on fit and sweep failures first (cfix-heron-a
    DECISIONS.md:108: "roughly 200 screw components" slowing the sweep). The panel tool makes
    a panel cost one more fit-failing iteration, so agents defer it until it never happens.

`lib.housing` is the part that *works*: 34 uses across `~/cadex-projects`, and 10 per creature in
cfix-deinonychus-a and cfix-leopard-a. It works for the same reason the panel fails. It is
grown from an **exact, declared envelope** (the catalog's `segments`, its mounting PCD and its
holes; `_qdd_housing`, `:1571`), not from a guessed hull, and it is screwed through holes the
catalog knows exist.

### 2.3 What a proper design is

**Principle.** A panel is a *thin, open, bounded patch of a smooth offset surface* of the
mechanism it covers. It is bounded by authored seams, thickened inward, given lips and bosses
that land on features the frame declares, and checked against motion. Every step that needs
geometry runs **in the worker on exact BREP**. The script states *intent*, and the screws are
placed through the existing mount and mate mechanism (ADR-126) from frames the worker
publishes. That answers ADR-610's one objection, that the script could not know the screws'
positions.

#### The geometric core: closing, then offset

The intent "gently curved, form-fitting" has a precise meaning. Let `C` be the union of the
covered solids. To make the union safe against motion, use the union of their joint-swept
volumes over the declared ranges, which the sweep machinery can already produce. Then the
envelope is:

```
E(C; r, c) = offset( closing(C, r), c )      closing = dilate by r, then erode by r
```

Here `c` is the clearance, and `r` is a *rolling-ball radius*, the one knob that matters:

- `r = 0` shrink-wraps;
- `r = ∞` is the convex hull: the egg;
- `r ≈ 15-40 mm` bridges the gaps between parts and fills valleys narrower than `2r`, yet still
  dips between masses further apart.

`r` is also a *physical* parameter: the curvature the panel's material and print process can
take. The convex-ring rule in today's code amounts to `r = ∞` within each station.

Implementation is in the worker, on the existing stack:

1. **Default: a signed distance field.** Voxelise the swept union at about 1 mm. `CadexStress`
   already voxelises with scanline parity (`CadexStress.voxelise`, `CadexStress.py:209`). Compute the distance
   transform (scipy is already used under `CadexDynamics`/`CadexStress`), take the
   iso-surface `d = r` to dilate, re-distance, and take `d = r - c`. Then fit a B-spline
   surface, or go through `part.shape_from_mesh` (ADR-043) for prototyping. It is robust on any
   input, imported meshes included, which `sample()` refuses.
2. **Exact path.** `BRepOffsetAPI_MakeOffsetShape` with arc joins, run on a simplified union.
   It is already behind `part.offset` (`cadex_part_api.py:3032`). Use it for simple contents
   where it does not fail.
3. Both publish the envelope as an ordinary `shell` output with a digest. This is the same
   class of thing as `part.offset`'s measured-geometry digest (ADR-389).

#### Proposed API: three ops plus a check, replacing `lib.panel`

```python
# 1. The envelope: what panels are cut from. Worker op on part.
env = part.envelope(
    over=[pack, board, hip_l.body, hip_r.body],   # exact solids, lib parts, meshes
    frame=deck,                 # what the panels bolt to; NOT wrapped unless listed
    clearance=1.5,              # c, mm, min gap to contents
    radius=25.0,                # r, the rolling-ball radius: hug (small) .. hull (inf)
    motion=asm_draft,           # optional: an assembly whose limited joints' swept
                                #   volumes are added to `over` (reuses ADR-349/621 sweep)
    resolution=1.0)             # SDF voxel, mm

# 2. Panels: open patches of the envelope, bounded by seams, with real edges.
skin = part.panel(
    env,
    region=part.region(side=(0, 0, 1), within=part.box(...)),
        # which part of the envelope: faces whose normal is within 75 deg of `side`,
        # optionally clipped by a solid; or `region=["top", "left"]` from a named
        # split of the envelope by seam set
    seams=[part.seam(plane=((0, 0, 0), (1, 0, 0)), gap=0.4, joint="lap"),
           part.seam(curve=sk.wire("parting"), gap=0.6, joint="butt")],
        # seams as planes or as sketched curves projected on the envelope (part.project);
        # joint = butt | lap (stepped overlap lip) | tongue
    thickness=2.0,              # thicken inward (BRepOffsetAPI_MakeThickSolid)
    edge=part.edge_style(return_flange=4.0, radius=1.0),   # a lip that stiffens and seats
    openings=[part.opening(around=hip_l, clearance=2.0, motion=True),   # swept, not rest
              part.opening(cone=(cam.origin, cam.axis, 40.0))],          # a sensor's view
    draft=1.0,                  # deg, for moulded panels; 0 for printed
    max_piece=(250, 250, 250))  # the print bed: refuse or auto-seam a piece that won't fit

# 3. Attachment: features declared on the frame, met by features grown from the panel.
seat = mounts(deck, [mount("p0", origin=(...), axis=(0, 0, 1), fastener="m2"), ...])
held = part.panel_mounts(
    skin, to=seat,              # land on the frame's declared mounts (ADR-126 tables)...
    # ...or auto: kind="boss" | "standoff" | "tab" | "snap", screw="m2", pitch=60.0,
    #   max_unsupported_span=120.0  (exact ray-cast to the frame's BREP, not samples)
)
# held.parts       the panel pieces with bosses/standoffs fused and holes cut
# held.mounts      a published mounts(...) table: one frame per fastener, in the
#                  worker's exact numbers, so the script places screws by
#                  part.mate(lib.bolt("m2", 8).body, held.mounts["0_top"]["b0"], ...)
#                  or by the one-liner held.screws(lib)
# held.frame_holes the tap-drill/insert pilots for the frame: deck = part.cut(deck, held.frame_holes)
```

On the assembly side, separate role from tone:

```python
assembly.component(skin_top, role="panel", covers=[pack, board], appearance="shell")
#                            ^ structural role: what fit.panels judges
#                                                 ^ unchanged: colour only
```

`role=` gets a small closed set: `panel`, `frame`, `link`, `housing`, `hardware`. With it,
"what this panel covers" is *declared*, not inferred from bounding boxes, and painting a thigh
light no longer makes it a panel.

**`lib.housing` stays** and becomes a special case: `part.envelope` of a drive's catalog
envelope with `radius=∞` about its axis, which is a drum. Its screw logic is already right.
**`lib.panel` and `CadexPanels.sample()` go.** That is about 1,300 lines out of
`CadexPanels.py`, with the ring fit `fit_ring`/`ring_points_2d` left to `CadexCage`, its first
owner.

#### Verification: `fit.panels` replaces `fit.shells`

| Measure | Definition | Fails when |
|---|---|---|
| `gap` p10/p50/p90/max | inner face → *declared* `covers=` (exact, as `gap_statistics` today) | p90 > `clearance + radius/2` (floating) or min < `clearance` |
| `coverage` | share of the declared covered parts' exterior that is hidden, rendered from 26 directions (`CadexStudio.design_proxies`, `CadexStudio.py:979`, already computes a per-pixel owner buffer) | below the declared intent, e.g. `< 0.7` for a "cover" |
| `exposes` | for each `lib.qdd`/`lib.servo` (the creature style: "the actuator is the joint, and it shows"), share of its housing hidden by panels | a drive more than 50 % buried |
| `egg_ratio` | panel-enclosed volume / covered parts' volume | > ~2.5 (the cosmetic shell; measured on the cbase eggs to fix the bar) |
| `motion` | panel vs every non-welded part across the joint sweep (ADR-349 machinery) | any contact in range |
| `wall` | min/max thickness by inward ray sampling (not `2V/A`) | min < 1.2 or max > 4 mm printed |
| `held` | fasteners into a non-panel part per piece, and max unsupported span between them | < 2 fasteners, or span > declared |
| `printable` | piece fits the bed (`CadexStudio.BED_MM` = 256³ mm, `CadexStudio.py:2072`), overhang share | does not fit, or overhangs with no seam to flip it |
| `seams` | gap uniformity along each seam; piece count | gap varies > 0.3 mm |

Make it **count**. A `role="panel"` with `floating`, `motion` or `unmounted` is a fit failure,
like any interference. An advisory block is the reason nine agents could leave panels "to come".

#### How the agent should express intent

The guidance becomes three sentences in the base, not a creature rule:

> Panels are cut from `part.envelope` of what they cover, at the radius the form wants (small
> hugs, large smooths). Each is a region with seams you choose where it must come apart for
> access, mounted to declared frame seats. Declare `role="panel", covers=[...]` and fix what
> `fit.panels` names.

Styles then set *defaults*:

- creature: `radius` 20-40, lap seams, openings at every drive;
- printed-legged-robot "panelled hard surface": `radius` small plus `part.chamfer` on the
  envelope edges, butt seams;
- an industrial enclosure: `radius = 0` box envelope with a sheet-metal flange (§3).

The same three ops serve a mower deck shroud, a 3D printer's skirts and an excavator's cab.

#### Staging (each step shippable)

1. **P0, now, no new kernel code.**
   - Add `role=`/`covers=` and judge on the declaration.
   - Make `fit.shells` measure p90 and motion, using the existing sweep.
   - Stop wrapping the frame by default.
   - Add `side=` to `lib.panel` so it can emit an open patch: keep the ring fit, but drop the
     rings' far half.

   This removes the sausage today.
2. **P1.** Add `part.envelope` (SDF closing+offset) and `part.panel(region, seams, thickness)`
   in `cadex_part_worker`, with the boss ray-cast moved onto the exact frame BREP. The worker
   publishes `mounts` for the screws. Delete `CadexPanels.sample` and `plan_panel`.
3. **P2.**
   - Lap and tongue seam joints, return flanges, `openings` from swept volumes.
   - `coverage`, `exposes` and `egg_ratio` in `fit.panels`, the bars calibrated on the cbase,
     cfix and castra renders the owner already rated.

## 3. Breadth: what non-creature machines need

### 3.1 What exists today

**Catalog** (`CadexCatalog.py`, `catalog_families()` at `:1441`): 14 families in 20 tables.

| Family | Rows | Notes |
|---|---|---|
| Fasteners: `METRIC_THREADS :95`, `SOCKET_HEAD_SCREWS :169`, `COUNTERSUNK_SCREWS :185`, `HEX_NUTS :199`, `NYLOC_NUTS :217`, `FLAT_WASHERS :229`, `HEAT_SET_INSERTS :252` | 49 | M1.6-M8 |
| `BALL_BEARINGS :270` | 15 | |
| `SERVOS :317`, `MICRO_HORNS :546` | 8 | |
| `BOARDS :587` | 9 | |
| `QDD_ACTUATORS :1124` | 4 | its notes say "hips and knees … necks, heads, jaws, tails" (`:1497`) |
| `BATTERIES :816` | 1 | |
| `WHEELS :851` | 1 | |
| `FOOT_PADS :913` | 1 | |
| `GEARMOTORS :1041` | 1 | |
| `BLDC_MOTORS :1078` | 1 | |
| `LINEAR_ACTUATORS :1257` | 1 | |
| `JOINTS :1289` | 1 | |
| gear standard | 0 | coefficients only, no SKUs |

**Library** (`cadex_library_api.py`, `LibraryAPI` at `:1138`): 25 `lib.*` generators.

- 11 general hardware generators.
- 5 drives.
- Wheel, spur gear, rack, rack-and-pinion, rod end.
- Panel, housing, catalog.

Usage across the 320 projects in `~/cadex-projects`:

| Generator | Uses |
|---|---|
| `lib.qdd` | 94 |
| `lib.bearing` | 88 |
| `lib.housing` | 34 |
| `lib.wheel` | 18 |
| `lib.spur_gear`, `lib.rack`, `lib.rack_and_pinion`, `lib.linear_actuator`, `lib.bldc` | **0** |

**Joints** (`_JOINT_TYPES`, `cadex_assembly_api.py:53`): 13 FreeCAD-native kinds, including
`screw`, `gears`, `belt` and `rack_pinion`. In dynamics (`JOINT_TABLE`,
`CadexDynamics.py:1675`) they become:

- **Tree joints:** weld, hinge, slide, ball, and cylinder (as slide plus hinge).
- **Loop closures:** revolute, ball and fixed only. A **slider that closes a loop is refused**
  (`CadexDynamics.py:1836`: "a sliding closure needs a tendon … belongs to a later slice").
- **Couplings** (`_coupling_records`, `:2358`): `gears`, `belt` and `screw` become linear
  `equality/joint` rows. **`rack_pinion` is refused** (`:2381`, `:2398`). `gears` and `belt`
  must be revolute to revolute (`:2506`).
- **Actuators** (`_ACTUATOR_KINDS`, `cadex_assembly_api.py:668`): `motor`, `position`,
  `velocity`, all joint-transmission with gear 1.
- **Joint stiffness** exists (`stiffness_n_per_mm`, `cadex_assembly_api.py:2390`), so a sprung
  suspension slider is expressible.

**Tasks and evaluation** (`CadexEvaluation.METRICS`, `CadexEvaluation.py:94`): 31 metrics.

| Group | Count | Basis |
|---|---|---|
| episode | 2 | |
| posture | 8 | |
| gait | **12** | feet-based |
| reach | 4 | |
| motion (turns, laps, distance about a centre) | 5 | |

Goal kinds are `value`, `speed`, `point` and `phase`. The tuning constants are legged
(`STANCE_MM`, `STEP_ADVANCE_HIP_HEIGHTS`, `REST_TILT`, `:59-81`).

**Non-creature projects that exist:**

- **`excavator-mini` / `orun5-excavator`** (about 485 lines each). Four `sts3215` servos where
  the cylinders would be. The sprockets, idlers and tracks are **welded**, and the track is two
  collision boxes. Its DECISIONS.md: "Track belts cannot be simulated as belts … tracks hold
  still".
- **`ball-plate`.**
- **`strandbeest`.**
- **`ot4-cart`, `ot4-carriage`, `ot4-quill`, `ot4-crank`.** Single-axis rigs.
- **Robin.** A two-wheeled balancer.

**No project uses a `gears`, `belt`, `screw` or `rack_pinion` joint.**

### 3.2 Machine by machine: what blocks it

| Machine | Needs | Cadex today | Blocking gap |
|---|---|---|---|
| **3D printer** (Cartesian, CoreXY, bed-slinger) | extrusion frame; linear rails or rods with carriages; GT2 belts and pulleys; NEMA17; leadscrew Z; hot-end and nozzle; bed; enclosure panels | `slider` joints; `screw` coupling (leadscrew Z); nothing else | **No belt → carriage coupling in dynamics** (rack_pinion refused). No CoreXY's two-motor coupled mapping (needs a 3-joint linear equality). **No catalog rows** for extrusion, rails, GT2, NEMA, or an E3D-class hot-end. No *workspace* or *path* verification (is the nozzle's reachable box the bed?). No path-following task. |
| **CNC router or mill** | rigid gantry; ball screws; profile rails; spindle; workpiece | `screw` coupling; `slider` | Catalog: ball screws, HGR/MGN rails, ER-collet spindles. **Stiffness verification of a frame** (`part.stress` is per-part, not an assembly). Spindle as a tool body with a cutting envelope. Tool-path coverage metric. |
| **Lawn mower** (robot) | chassis; two drive wheels plus casters; blade disc on a motor; deck shroud; bumper and lift sensors | wheels (1 SKU), N20 gearmotor (1), generic contact | Wheel catalog (1 row), tyres, casters (none). **No terrain** beyond the 1 m floor (ADR-604). **No area-coverage metric**, no odometry, no boundary-wire or GNSS sensor. The blade is a hazard envelope with nothing to check it (guard clearance). The deck shroud is a *panel* (§2). |
| **Tractor** | Ackermann steering linkage; differential; rigid or pivoting axle; 3-point hitch (a linkage driven by hydraulics); PTO | revolute closures (the steering four-bar is fine) | **Differential**: a 3-joint coupling, none. **Hydraulic cylinder**: a slider in a loop, refused. **Ackermann geometry check**: none. Large-scale catalog: none (every SKU is under 1 kg). |
| **Excavator** (full, not the servo stand-in) | boom, stick and bucket each driven by a cylinder in a 4-bar; slew; tracks | revolute loops (ADR-593..621) | **Slider loop closure** (`CadexDynamics.py:1836`): the cylinder is exactly that. Tracks: no model. Cylinder catalog: none (only Actuonix L12). |
| **Tracked vehicle** | sprockets, idlers, road wheels, track | welded stand-in | A track model: in MuJoCo, either a chain of capsules with hinge links or a "virtual" track with tangential contact velocity. No `lib.track`. |
| **End effectors** | grippers; spindles; blades; nozzles; vacuum cups | `lib.joint`, generic | No tool frame or TCP declaration on a component; no tool-pose metric or orientation goal; no gripper library (parallel-jaw rack, 4-bar). |
| **Sheet-metal and extrusion frames** | bent sheet (k-factor, flat pattern); 2020/2040/4040 profiles with T-slot and brackets | `part.thicken`, boxes | No `part.sheet` or bend op, no flat pattern (`export_printable` has no DXF equivalent). No extrusion profile. The **frame-as-a-lattice** idea is absent: every design is hand-composed solids. |
| **Enclosures** | box or tub plus lid, gasketed seams, bosses, vents that are real, cable glands | `lib.panel` (a sleeve) | §2: `part.envelope` with `radius=0`, plus sheet-metal flanges, plus `panel_mounts`. |

### 3.3 Architectural (not catalog) gaps

These matter more than SKUs, because each blocks a whole class.

1. **Coupling generality in dynamics.** One mechanism, `equality/joint` with a
   polynomial over *n* joints, would cover:
   - `rack_pinion`, and a belt driving a carriage (revolute to slider, ratio r);
   - CoreXY (x = (a+b)/2, y = (a-b)/2);
   - a differential (ω_c = (ω_l+ω_r)/2);
   - a cable or tendon.

   MuJoCo's `equality/joint` only couples two joints, so the n-joint form needs a
   `fixed` tendon. That is one tendon type, and it also closes the slider loop.
2. **Linear actuator in a loop.** Make a slider closure a MuJoCo tendon (or a `connect`
   equality at both cylinder ends, with the cylinder as a slide joint inside a free pair). This
   unblocks every hydraulic and pneumatic linkage, excavator to 3-point hitch. Add the actuator
   kind `cylinder`: a force limit from bore × pressure, and a velocity limit from flow.
3. **The world.** Today the world is a 1 m floor (ADR-604). It needs a terrain declaration
   (heightfield, slopes, grass friction), workpieces, and fixtures. Mowers, tractors, CNC
   workpieces and printer beds all need it.
4. **Task vocabulary beyond locomotion.** `CadexEvaluation` is 12 gait metrics, plus posture,
   reach and motion. Machines need:
   - path following (tool tip error along a declared path);
   - area coverage (fraction of a region swept by a tool footprint);
   - odometry and heading;
   - throughput (cycle time);
   - accuracy and repeatability under disturbance.

   These are generic once a **tool frame** (`assembly.tool(component, origin, axis)`) exists.
5. **Kinematic verification for machines.**
   - Workspace (the reachable box of a TCP over joint limits; does it cover the bed?).
   - Ackermann error over steering range.
   - Backlash and stiffness of a gantry (a frame-level `part.stress`, or a compliance estimate
     from a MuJoCo static solve).
   - Belt tension and alignment (pulley coplanarity).
6. **Scale.** Every catalog SKU and default is hobby-scale: M1.6-M8, 1 battery, a 0.5-5 kg
   design. Fit thresholds in mm suit a 300 mm robot. A tractor or a 2 m excavator needs scale-aware
   thresholds: fit tolerances relative to part size, and screws past M8.
7. **Catalog as data, not code.** `CadexCatalog.py` is 1,559 lines of Python dicts, and each
   new family has meant a table, a generator in `cadex_library_api.py`, a describe_api entry
   and an ADR. Breadth needs families added as *data*:
   - a row schema per family (rails, belts, pulleys, steppers, extrusions, cylinders, spindles);
   - one generic generator per *interface type* (bolt pattern, shaft, rail, belt pitch);
   - provenance per row.

   That would make 50 SKUs a data PR, not 50 code paths.

## 4. Recommendations, ranked by impact over effort

**Effort scale:**
- **S** is a day or less;
- **M** is a few days;
- **L** is a week or more.

**Impact** is judged against the owner's two stated wants: panels that are "there", and
breadth. "Remove" items are listed with the lines they free.

| # | Recommendation | Impact | Effort | Adds / removes |
|---|---|---|---|---|
| 1 | **Panel P0.** Add `role=`/`covers=` on `assembly.component`, separate from `appearance`. `fit.shells` judges declared covers, on p90 and on motion (reuse the sweep). `lib.panel` stops wrapping the frame by default and gains `side=` for an open patch. A floating, colliding or unmounted panel becomes a fit failure. | High: removes the sausage and the "thigh painted shell" confusion now | S-M | Adds about 150 lines. Removes the bounding-box "covers" inference. |
| 2 | **Panel P1.** Add `part.envelope(over, clearance, radius, motion)` (closing + offset, SDF in the worker) and `part.panel(env, region, seams, thickness, openings)`. Boss ray-casts run on exact frame BREP and publish a `mounts` table for the screws. | **Highest**: the owner's first ask | L | **Removes `CadexPanels.sample` and `plan_panel` (about 1,300 lines)**, the second CSG kernel |
| 3 | **Dynamics: n-joint couplings and slider loop closure via fixed tendons.** Covers `rack_pinion` (belt→carriage), CoreXY, the differential, and a hydraulic cylinder in a linkage. Add the actuator kind `cylinder` (force from bore × pressure). | High: unblocks printers, CNC, excavator, tractor hitch | M | Adds about 400 lines. Removes two refusals (`CadexDynamics.py:1836`, `:2381`). |
| 4 | **Catalog as data.** A row schema per family in JSON, one generic generator per *interface*: bolt pattern, shaft, rail, belt pitch, profile. Then land the motion families as rows: MGN rails and carriages, GT2 belts and pulleys, T8 leadscrews and SFU ball screws, NEMA17/23, 2020/2040 profiles and brackets, small hydraulic and pneumatic cylinders, ER spindles, casters, tyres, springs, couplers. | High for breadth | M-L | Each SKU becomes a data PR. **Converts about 1,000 lines of dict-code to data.** Delete the 5 never-used generators or fold them in. |
| 5 | **Make the base guidance domain-neutral and short.** Move animal, gait and servo-tier text into styles. Move "how to read block X" into each block's own `note`/`source`. Add styles for **gantry machine**, **vehicle** and **enclosure/industrial**. | High: every non-creature brief reads this first | S-M | **Cuts the base from 6,012 words to about 2,500.** Adds 3 short styles. |
| 6 | **Rename anatomy to regions.** `assembly.region(name, components, reason=)` with no creature vocabulary in the engine (the creature style supplies the suggested names). Make `DRIVE_FAMILIES` and `OUTPUT_FAMILIES` catalog attributes, not code constants (`CadexFitReport.py:639`). Drop stance and "servos" assumptions from notes and sheets. | Medium-high: a tractor gets "steering, hitch, PTO" checked the same way | S | Rename plus about 50 lines changed. Removes constants. |
| 7 | **One pose × pair measurement service.** Inputs are the rest pose, joint samples, loop re-solves, trace frames and MJCF reload. Output is one table of distance and common volume, judged only by `CadexFitReport`. Smoke's separate BREP child (`smoke_geometry.py`) and thread re-reading go. | Medium-high: fewer disagreeing verdicts, motion clearance for panels for free | L | **Removes an estimated 1,000-1,500 lines** across the assembly worker, smoke and clearance |
| 8 | **Machine task vocabulary.** `assembly.tool(component, origin, axis)` declares a TCP. Add goal and success kinds `path` (tip follows a polyline, with error), `coverage` (a footprint sweeps a region), `heading`/`odometry`, and `cycle_time`. Add a terrain and workpiece declaration on the world (heightfield, friction patches, a fixture). Move `gait` behind a `legged` rig so it is one family among several. | High for mowers, CNC, printers | M-L | Adds about 600 lines. Removes the walk.py second gait reading (`walk.py:899`). |
| 9 | **Shared small modules.** `CadexVec.py` for frames, quaternions, `_unit`, `_cross` and `_finite`. One `DeclaredTable` base for nets, boards, mounts and cage. The runners share `_sha256` and plan-loading. | Medium: less code, fewer sign bugs | M | **Removes an estimated 1,000-1,300 lines** (700-900 tables, 300 or more algebra, about 100 runner copies) |
| 10 | **Delete the dead and the shell-era.** `CadexProject.py` (914 lines, after confirming no string dispatch). The unreferenced `CadexScriptedPublication`, `CadexReferenceContracts`, `CadexTools` and `cadex_domain_worker` functions (§1.8). Consider retiring `cadex walk` (ADR-464 already demoted it), and the stored-override and prune machinery of the declared tables, which had the deleted shell's editors as their only writer (needs an ADR). | Medium | S (deletes) / M (walk, overrides) | **Removes 1,500-3,000 lines** |
| 11 | **Name the second contract.** The engine modules the CLI loads by path (`CadexStudio`, `CadexFitReport`, `CadexPrintables`, `CadexAnatomy`, `CadexDynamics` in runners) are listed in one place, pinned by a test, and documented in `docs/INTEGRATION.md`. Alternatively, move `CadexStudio` to `cli/`, since only the CLI calls it. Fix the `ARCHITECTURE.md` drift (§1.8). | Medium: honesty of the boundary | S | Docs plus one test. Possibly moves 2,643 lines out of `src/`. |
| 12 | **Split `CadexDynamics.py` at its seams** (§1.6): `CadexDynamicsModel`, `CadexLoops`, `CadexTasks`, `CadexPolicy`. The purity test keeps the closure. | Medium: the 12k-line file is where breadth work (rec. 3, 8) lands | M | Moves code, no net lines. Exposes the task half's legged assumptions. |
| 13 | **Frame-level structure and sheet metal.** `part.sheet(profile, thickness, bends=[...])` with a flat-pattern export, and `lib.extrusion("2020", length)` with T-slot and bracket mounts. `part.stress` over a welded subassembly, not just a part. | Medium-high for CNC, printers, tractors | L | Adds |
| 14 | **Scale-aware thresholds.** Fit, shell and clearance bars relative to part size, and fasteners past M8, so a 2 m machine is judged like a 0.3 m one. | Medium | S-M | Changes constants |

**The order to do them in:**

1. **1, 5, 6 and 10** are small, and make the next creature run and the first non-creature
   run better immediately.
2. **2 and 3** are the two big unlocks.
3. **4 and 8** turn the unlocks into machines.
4. **7, 9, 11 and 12** pay the accumulated debt down. They are best done before the breadth
   work lands in the same files.

### What to remove, collected

| Item | Lines | Condition |
|---|---|---|
| `CadexPanels.sample` and `plan_panel` | ~1,300 | after rec. 2 |
| Duplicated declared-table skeleton | 700-900 | rec. 9 |
| Stored-override and prune machinery | | with an ADR |
| Duplicated vector algebra in 7-8 modules | ~300 | |
| `CadexProject.py` | 914 | |
| ~38 unreferenced functions | ~600 | |
| Five never-used `lib` generators | | or keep them, as rows of the data catalog |
| Second gait reading `walk.gait_from_trace`; smoke's re-implemented tilt and termination | | |
| `smoke_geometry.py`'s separate exact re-measurement | | after rec. 7 |
| `cadex walk` | 1,132 + 539 | ADR |
| Creature and gait prose in the base guidance | ~3,500 words | to styles or blocks |

Removal is likely to outweigh addition by 2-3× over the whole programme: **about 6,000-8,000
lines removed against about 2,500 added**.

## 5. Method

**Measurements.**
- Line counts: `wc -l` at `587ffd43`.
- Import graph: an AST walk of `src/Mod/cadex/*.py` and `cli/cadex_cli/*.py`, module scope
  and function scope counted separately.
- Duplication: AST spans of the named functions and classes.
- Dead code: name-token search across `src`, `cli`, `docs`, `training` and `tools`, minus
  string-dispatched `_op_*`.
- Word counts: tests excluded.

**Projects.** The nine creature projects of 2026-10-09 (`cfix-*`, `castra-*`) were read:
`script.py`, `script_history/`, `DECISIONS.md`, `PROGRESS.md` and `agent.json`. The 320
`~/cadex-projects/*/script.py` files were grepped for library usage. Nothing in them was
modified.

**Not run.** No tests were run; this review changes no code.
