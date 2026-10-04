# orun2 — closing report

Verified against source: 2026-10-04, at `13c660cf` (the orun2 run branch).
Charter: `.ouroboros/goal.md`, "Cadex is three things — the engine, the
dashboard, the agent". Every number below was measured on sb1x (linux-64,
32 cores). The owner ticks the criteria; this report claims none of them.

## Where each criterion stands

| criterion | where the evidence stands | evidence |
|---|---|---|
| S1 the shell is gone | evidence recorded | `git ls-files shell \| wc -l` = 0; disable commit ADR-495, delete commit ADR-498, live docs ADR-499 |
| R1 the contract | evidence recorded | ADR-500, ADR-501; `AGENTS.md` 215 lines (from 432); the frontier lists live work only |
| D1 clone to dashboard | evidence recorded | the after column below |
| D2 watch and steer | evidence recorded | one browser test per item against a real engine (§4) |
| D3 runs first-class | evidence recorded | ADR-513, ADR-514, ADR-515, ADR-518, ADR-519 |
| A1 one contract, a channel | evidence recorded | `leave_note` (ADR-512), the guidance settled (ADR-521) |
| W1 nothing lost | **open** | walk steps 1–6 and 8 ran; step 7 ran on the CPU, because the 5090's driver was not loaded (`w1/README.md`). The ledger has no "to port" row |
| C1 this report | this file | |

## 1. D1 — before and after

Before: `D1-BEFORE.md`, at `a375745c`. After: `measure_d1.sh` re-run at
`13c660cf` on 2026-10-04, with the same conditions: a `file://` clone,
`CCACHE_DISABLE=1` and a warm pixi cache.

| | before | after |
|---|---|---|
| Tracked files | 25,633 | **6,267** (−75.6%) |
| … under `shell/` | 19,446 | 0 |
| Tracked blob bytes at HEAD | 436,436,320 | **143,893,448** |
| Git-LFS objects / LFS rules | 6,716 / 111 lines | **0 / 0** |
| Submodules | 4 `shell/lib/*` + OndselSolver | OndselSolver only |
| Fresh-clone working tree | 453,179,173 B | **160,920,788 B** |
| Fresh-clone `.git` | 269,075,679 B | 268,622,513 B. History still carries the shell; nothing was rewritten |
| Python LOC, all tracked | 873,875 | **332,171** |
| … `shell/` | 549,304 | 0 |
| … `cli/` | 46,392 | 53,695 (the dashboard's write paths, runs, notes, blueprints) |
| … `src/Mod/cadex/` | 139,983 | 140,348 |
| … `package/` | 3,439 | 3,161 |
| … `src/`, `tools/`, `docs/`, `analysis/`, `training/` | 216,785 / 17,605 / 16,292 / 6,986 / 3,219 | 217,150 / 17,605 / 16,551 / 6,986 / 3,219 |
| JS LOC, all tracked | 2,531 | **3,754** (`review_static/` 1,804 → 3,453; the shell's 426 gone) |
| C/C++ outside `src/Mod/cadex` | — | unchanged: no diff since `a375745c` |
| Setup steps (linux) | 4, not documented as one sequence; the documented route was macOS-only and needed git-lfs and Xcode | **4, documented in README**: `git clone`, `pixi run setup-engine`, `pixi run build-engine`, `pixi run app` — pixi only |
| What the last step serves | `cadex review`: one project | `cadex app`: a projects directory, its runs and CLI turns |
| C++ compiles in `build-engine` | 1,185 | 1,185 |
| Clone → first page `HTTP 200` | 114 s | **117 s** (first page 1,680 B, the projects index) |
| `.pixi` environment | 5,649,462,867 B | 5,649,469,569 B |
| `build/release` | 226,308,245 B | 226,195,014 B |
| Staged engine payload | 3,258,061,207 B | 3,260,333,775 B |

The wall time did not move, and it was not expected to: the shell was never
part of the linux build. 1,185 compiles before and after; the 3 s
difference is noise. A browser probe ran on the same machine during part of
the after build. What changed is that the 4 steps are the documented route
and need nothing but pixi. The installed footprint did not shrink either:
the pixi environment still carries the GUI-era dependencies. That audit
was deferred by the owner to the next run.

## 2. The parity ledger

`docs/SHELL-PARITY.md` has one row for each of the 47 `mesh_agent`
entries, the 23 agent tools and the seven Cadex editors. No row is blank,
and no row says "to port". A split row counts under each status it carries.

| section | rows | ported | already covered | dropped | owner to confirm |
|---|---|---|---|---|---|
| §1 modules | 47 | 20 | 15 | 25 | 2 |
| §2 tools | 23 | 6 | 17 | 2 | 0 |
| §3 editors | 7 | 5 | 2 | 5 | 0 |

The ledger's §5 audit reran every test a row cites, with the GPU hidden and
none skipped. Four ports came after the audit: roles and printables
(ADR-522), the guidance (ADR-521), turn cost (ADR-523) and the viewer's
dimensions (ADR-524). The two "owner to confirm" rows are face-level pins
and the face-ID channel. Part picking, which A1 asks for, is ported.

## 3. Removals, each with its ADR

| removed | ADR |
|---|---|
| Everything that built, gated or read `shell/` (the disable commit) | ADR-495 |
| `mesh.blender`: the op, runner, worker, adapters, `examples/blender_enclosure.py`, its tests and `docs/BLENDER-RECIPES.md`; `OP_ARG_SPECS` and `docs/INTEGRATION.md` in the same commit | ADR-496 |
| The Codex and pi harnesses | ADR-497 |
| `shell/` itself: 19,446 files, the LFS rules and pointers, the four `shell/lib` submodules, and the one GPL file outside it. The repository carries no GPL code | ADR-498 |
| Every live doc's description of the shell, held by a test | ADR-499 |
| The Rust shell (ROADMAP Phase 12) and VISION's "Blender-class UX" pillar | ADR-500 |
| `docs/REVIEW-DESIGN.md`, renamed to `docs/DASHBOARD.md` | ADR-501 |
| Every ledger row marked dropped: cage ring-drag, the wiring editor UI, the blueprint editor, playback baking, chrome, the Blender transcript store, the live policy session, the demo biped | ADR-498, by the ledger's reasons and the owner notes |

## 4. D2 — slider latency

On a warm one-box plate, with a real engine in headless Chromium,
re-measured at `13c660cf` (`test_browser_moves_a_slider_and_sees_the_rebuilt_model`, n = 5):

| path | p50 | p95 |
|---|---|---|
| Slider release → model drawn (dashboard) | **554 ms** | **583 ms** |
| `cadex params` child alone | 0.53 s | 0.54 s |
| ADR-503's own measurement (n = 20, 2026-10-03) | 548 ms | 556 ms |

The raw-NDJSON bar beside it (`cadexd_latency_integration.py`, same commit,
10 drags) gives these medians: `set_params` 0.381 s, and 0.432 s with a
draft display, both within the 0.65 s bar. The dashboard spends about
120 ms more than the raw engine. That is the cost of a fresh `cadex params`
process per move: the price of A3's single write path.

The other D2 items each have a browser test against a real engine:
- turn: `test_browser_starts_a_turn_and_watches_it_land`;
- image: `…attaches_an_image_to_a_turn…`;
- comment: `…comments_on_a_picked_part…`;
- revisions: `…accepts_rejects_and_restores_a_revision`;
- collision: `…names_the_parts_touching_at_rest…`;
- exploded and section views: `…explodes_the_engine_stages_and_cuts_a_section`;
- rollout: `…plays_a_real_rollout…`;
- export: `…exports_step_and_stl_and_downloads_the_concept_sheet`.

## 5. Screenshots

`report_shots.py` took these from `cadex app` over the projects directory, on
`orun2-w1-quad` (a copy of `ot11-quad-1`). It is read-only. What it measured is
in `report-shots.json`. Every image is on the dark floor, under 300 KB.

- `dashboard-index.png`: the projects index.
- `dashboard-concept.png`: the tab a project opens on, the concept sheet of
  the accepted design.
- `dashboard-model.png`: the Model tab after **Fit**, framing the robot
  (defect 1, fixed).
- `dashboard-evaluation.png`: evaluations and the predicate table.
- `w1/w1-*.png`: the W1 walk, one per step.

## 6. Remaining defects

Each was re-checked on 2026-10-04 while the screenshots were taken.

1. **The robot as a speck: fixed (ADR-525).** The viewer's bounds had run
   from −600 to +600 mm because `c_floor`, the task's 1.2 m floor, counted
   toward what Fit frames, and `modelPixels()` boxed the floor slab. The
   engine already names that slab world geometry in the fit block; the
   model manifest now carries it as `world: true`, and the viewer leaves
   world parts out of Fit's bounds and out of the coverage check while
   still drawing them. Re-taken: Fit frames 178 × 151 × 123 mm (the robot
   alone), and the robot covers 20.3% of the canvas, its box well inside
   the frame (`report-shots.json`). `test_dashboard_fit.py` pins it
   against a real engine.
2. **Debug colours: fixed.** The page paints by appearance role. Its parts
   line reads "colours by role: accent #FF6A1A, mechanism #2A2C31, shell
   #ECE8DF", and the model is white and orange in the shot (ADR-522).
3. **A CLI turn's transcript and its `look` images: fixed (ADR-526).**
   The index listed a terminal turn, but the page's transcript was hidden
   and showed 0 `look` images: the transcript was the dashboard's own
   in-memory copy of a child it had started. `cadex -p` now keeps each turn
   under the project's self-ignoring `turns/<id>/` (record, transcript,
   one PNG per `look`), the CLI stays the only writer (A3), and the page
   reads the newest stored turn. `test_turn_store.py` pins it against a
   real engine in headless Chromium: a turn run through the CLI's `main()`,
   not from the page, shows its transcript, status and both decoded `look`
   images, and the project's repository tracks none of it.
4. **The raw-NDJSON bar's preview lane: fixed (ADR-527).** Its median
   was 0.763 s against a 0.10 s bar, so the script's `ok` was false.
   Profiling one warm preview put 0.72 s of 0.77 s in static-fit
   clearance, which the preview threw away. A preview now skips fit, as it
   already skipped traces and exports. The median is now 0.043 s, the
   first preview 0.28 s, `ok` is true, and the bar is unchanged.
   `test_preview_skips_fit.py` pins it.
5. **W1 step 7 ran on the CPU.** The kernel had no `nvidia` module, so
   the 5090 leg is waiting on the owner. This is a lifecycle check, not a
   gait.
6. **The installed footprint is unchanged** (§1): the pixi GUI-era
   dependency audit is deferred to the next run.
