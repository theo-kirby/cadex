# orun2 — closing report

Verified against source: 2026-10-04, at `37733eec` (the orun2 run branch).
The D1 and D2 numbers were measured at `13c660cf`; no later commit touches
the build, the setup route or the slider path.
ADR-531 and ADR-532 (the payload's LLVM, then OpenCV/PCL/Node/Perl prunes)
landed after; §3 and defect 6 carry them. W1's GPU leg (defect 5) was measured at `50442820`. The done claim (§7)
was re-checked at `3d0c6faa`, the reconcile that folded the last records.
Charter: `.ouroboros/goal.md`, "Cadex is three things — the engine, the
dashboard, the agent". Every number below was measured on sb1x (linux-64,
32 cores). The owner ticks the criteria; this report claims none of them.

## Where each criterion stands

| criterion | where the evidence stands | evidence | records |
|---|---|---|---|
| S1 the shell is gone | evidence recorded | `git ls-files shell \| wc -l` = 0 (re-run at `37733eec`); disable commit ADR-495, delete commit ADR-498, live docs ADR-499 | `lucky-haven-1081`, `clear-heron-4371`, `crimson-union-6659`, `calm-quartz-1493`, `mellow-pine-4848` |
| R1 the contract | evidence recorded | ADR-500, ADR-501; `AGENTS.md` 215 lines (from 432); the frontier lists live work only | `smooth-cedar-5324`, `careful-rain-8917`, `even-clover-8953`, `light-path-5130`, `crimson-stone-9344` |
| D1 clone to dashboard | evidence recorded | the after column below | `old-arrow-4088`, `mild-grove-9448` |
| D2 watch and steer | evidence recorded | one browser test per item against a real engine (§4) | `morning-peak-8268`, `placid-bell-2440`, `noble-glade-0483`, `stormy-grove-7025`, `sweet-mist-9111`, `calm-falcon-6751`, `narrow-crest-4950`, `staid-wave-3739`, `polished-lodge-7956` |
| D3 runs first-class | evidence recorded | ADR-513, ADR-514, ADR-515, ADR-518, ADR-519 | `mellow-otter-0798`, `polished-reef-4161`, `lean-star-6139`, `quiet-ivy-3898`, `amber-moon-9415` |
| A1 one contract, a channel | evidence recorded | `leave_note` (ADR-512), the guidance settled (ADR-521) | `proud-quill-5791`, `autumn-rose-7173` |
| W1 nothing lost | evidence recorded | walk steps 1–8 ran and were seen in the dashboard; step 7 trained on the 5090 (300 it × 1024 envs, 331 s) and `evaluate` passed 10 of 10 seeds (defect 5, cleared). The ledger has no "to port" row | `red-loom-2239`, `icy-tooth-7719`, `dusty-bramble-8099`, `mellow-fjord-5906`, `neat-grove-1406`, `solemn-birch-8260` |
| C1 this report | this file; done claimed for critic review (§7) | §1–§6 below | `clear-current-6218`, `lively-beacon-5538`, `clever-sky-3211`, `hidden-glacier-9870`, `rough-bell-4055` |

The owner-note units each have their own record: the blueprint composer
(ADR-516, `sweet-arrow-0695`) and the project budgets (ADR-517,
`curious-flint-4836`). The long-term subtractions after the W1 claim are in
§3 (`icy-bramble-4392`, `royal-quill-2455`, `gentle-hawk-3921`).

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
and need nothing but pixi. The installed footprint did not shrink in this
table either: the pixi environment still carries the GUI-era dependencies,
and that audit was deferred by the owner to the next run. After this table
was measured, the staged payload lost LLVM and clang (ADR-531), then
OpenCV, PCL, Node and Perl (ADR-532, defect 6): 2,213,397,834 B.

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
| The live policy session: `live_open`/`live_step`/`live_close` from `OP_ARG_SPECS`, their goldens and handlers | ADR-528 |
| The studio renderer's child-process entry, which only the shell spawned | ADR-529 |
| The engine's FreeCAD preference-group fallback for its sandbox budgets, which nothing writes now | ADR-530 |
| LLVM and clang from the staged payload: 669,587,257 B that no ELF in it links | ADR-531 |
| OpenCV, PCL, Node and Perl from the staged payload: 375,045,987 B that no ELF or module in it uses | ADR-532 |
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
5. **W1 step 7 ran on the CPU: cleared.** The owner loaded driver
   580.178.04 on 2026-10-04; `nvidia-smi` sees the RTX 5090 and
   `~/cadex-train-venv` reports `jax.default_backend() == "gpu"`. The leg
   ran again without `JAX_PLATFORMS=cpu`: `cadex walk --iterations 300
   --envs 1024 --seed 1001` exited 0 in 517.5 s, with receipt `device: gpu`,
   331.1 s of training, reward/step 0.950, and a rollout upright over all
   501 frames. `cadex evaluate` then passed **10 of 10 seeds**. Both are on
   the dashboard (`w1/w1-7-training.png`, `w1/w1-8-evaluate.png`).
6. **The installed footprint shrank by two slices; the pixi environment
   did not.** The staged payload no longer carries LLVM and clang (ADR-531)
   or OpenCV, PCL, Node and Perl (ADR-532), none of which any ELF or module
   in it uses: 3,258,031,078 B → 2,588,443,821 B → **2,213,397,834 B** on
   the same tree (−32.1% in all), with the packaged gate green. Still
   copied: the compiler's `lib/gcc` and nine libraries ADR-532 orphaned.
   The `.pixi` environment (5.65 GB) is unchanged; its GUI-era dependency
   audit is deferred by the owner to the next run.
7. **The short plan bet still names a shell client.** `young-crane-9546`
   (rank 1, rollout-pose clearance) says an op change moves "the shell
   client" in the same PR. R1's frontier clean-up (`light-path-5130`)
   declared its replacement by the orun2 ladder, but the plan impact is
   still pending: `hypergraph check` reports it as `I5`, 5 pending
   impacts awaiting reconcile. It is planner-owned text, not a live doc,
   a frontier node or a criterion, so it does not hold S1 or R1; the next
   reconcile folds it.

## 7. The done claim

**Done is claimed, for the critic's review.** The reconcile at `3d0c6faa`
folded the last records (`rough-bell-4055`, `snowy-beacon-2710`,
`empty-heron-1077`); the unreconciled tail is empty and `hypergraph check`
exits 0 (0 violations, 6 warnings). Re-checked there, against each
criterion's folded state node:

- **S1** (`sunny-clover-3750`): `git ls-files shell | wc -l` = 0. Outside
  ADRs, `docs/history/` and the graph, the files that still name `shell/`,
  `mesh_agent` or `.blend` are the guardrails that forbid them coming back
  (`test_project_docs.py`, `test_licensing_compliance.py`), the licensing
  manifest and its tool saying the Blender half left, the parity ledger,
  and `docs/ROADMAP.md`'s Phase 6, which R1 marks historical.
- **R1** (`eager-sea-3906`): `AGENTS.md` is 215 lines (432 before); the
  frontier is four live nodes, none a stale run criterion.
- **D1, D2, D3, A1** (`sweet-bloom-8352`, `twilight-aspen-1541`,
  `swift-nest-0229`, `fierce-falcon-5989`): working, each with the records
  in the table above; nothing after their evidence touched them.
- **W1** (`shady-clover-5534`): working, steps 1–8 seen in the dashboard,
  step 7 on the 5090 and `evaluate` 10 of 10.
- **C1** (`wild-ocean-3878`): this file, §1–§6.

Remaining defects: 6 (the `.pixi` environment, deferred by the owner) and
7 (the plan's leftover wording, for the reconcile). Neither holds a
criterion. The owner ticks the boxes, and none is ticked here.
