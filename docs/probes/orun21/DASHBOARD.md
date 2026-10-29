# D2: where the dashboard shows an empty, stale or wrong state

Verified against source: 2026-10-29 (`9c451756` plus ADR-851).

D2 lists every case found where the dashboard shows an empty, stale or wrong
state, ranked by how often the owner meets it times how wrong it is. Each
entry gives its cause at file:line and a one-line fix. The cheap ones are fixed
under ADR-851; the rest are listed with their fixes. Line numbers are as of
ADR-851.

The sources are D1's watch (`D1-WATCH.md`, "Found while watching"), the
open claims `autumn-hawk-8597` and `spare-willow-9655`, the charter's list,
and a sweep of every project under `~/cadex-projects` (386 projects). The
sweep compared what each home-page card reads with what that project's page
reads (`ReviewProject.review()["stage"]`), using a probe script kept outside
the tree.

## Fixed (ADR-851)

| # | What the owner saw | Cause | Fix | Proof |
|---|---|---|---|---|
| 1 | **A hand-started run's checkpoints had no rollout.** The checkpoint picker stayed hidden for every bare `cadex_train.py` run, including all three D1 runs (`d1w-cad`: "the run has no train directory"). | `review_server.py:698` `_checkpoint_dir` read only `runs/<run>/train/`, and only `cadex train`'s engine watcher (`checkpoints.py`) wrote traces. A bare trainer left `seed0/policy.000050.cxpolicy` with nothing to play. | The trainer rolls each numbered checkpoint out from the witness rollout it has already run (`cadex_train.py:4744`, written at `:5613` as `<out>.<tag>.rollout-trace.json`). The server falls back to the trainer's progress directory. A checkpoint with no trace there is counted in `reason` and never shown as pending (`review_server.py:792`). | `runs/d2-ckpt` (leon V concept, 40 it, `--checkpoint-every 10`): 3 ready items, playback 301 frames over 6 s, its policy linked; [d2-checkpoints.png](d2-checkpoints.png). Pinned in `test_http_api.py`; with the fallback removed the pin fails. |
| 2 | **`look`, films and the CAD overlay said "missing tessellation" after `export --rebuild`** (`autumn-hawk-8597`). | `__main__.py:1433` (export), `:1744` (link) and `:1894` (train) sent `rebuild` with no `display`, but the attempt still became the accepted pin. | Each of them now sends `{"display": STANDARD_DISPLAY}`, as accepts do. | Lab biped copy `d2-biped`, `cadex export --rebuild` (51 s): the pinned attempt `1793263771643-e16b46647d87` has `display` in its request and 55 tessellations. `accepted_model` draws 55 of 55 parts. Before: attempt `1793259117431-0b699131c55a`, no display key (`odd-river-0066`). |
| 3 | **A home-page card read a different run from the project page.** leon V's card said `t0 · idle` while its page said `k1-e1 · failed`; cadex-quad's said `p0-trot · idle` against `p0-gallop · failed`. | `review_server.py:3724` `_newest_run_dir` stamped a directory with no `run.json` by its own mtime. A judge's output directory (`runs/t0`, `runs/p1-cut`) therefore beat real runs. A bare trainer's run was stamped by `seed0/` creation, not by its telemetry. `default_run` (`:2703`) could also open such an `empty` directory. | Stamp a run by `run.json`, then `review.json`, then its trainer's `progress.json`, and skip directories that have none of them (`_run_written`, `:3709`). `default_run` never opens an `empty` one. The card's cache key stats the progress file it read. | Sweep of `~/cadex-projects`: card and page agreed on 380 of 386 projects before and 382 of 386 after. Both projects that showed a failed run as idle now agree. The 4 that still differ are row 7. |
| 4 | **The stage chip said `idle` while the agent worked.** Only an accepted revision counted as designing, so a `look`, an `inspect` or a refused script showed nothing. | `review_server.py:2925`: `designing` required `accepted_at` inside the window. | `designing` also holds when the newest logged call (ADR-836) was made in the last 10 min. Its line reads `the agent's <tool> call`. A call that trained or evaluated does not count (`_agent_worked_at`, `:2800`). | Stage and card read the same activity log, and the CLI suite passes. |
| 5 | **A `cadex evaluate` started from a shell was not `evaluating`** until its directory appeared. Most of the call is the build, before that directory exists. | `review_server.py:2781` `_evaluate_in_flight` matched only the MCP tool name `evaluate`, not the logged `cadex evaluate`. | Match both names. | leon V's lab log holds `cadex evaluate … outcome: running` lines, and this change reads them. |
| 6 | **The episode-length chart read 81,920 on leon V** (`D1-WATCH.md`) and 2,156 on `d1w-con`'s 1,000-step episode. | `cadex_train.py:4521`: `unroll × envs / max(endings, 1)`. A time-out is not an ending, so a batch with no endings read the whole batch. | Cap it at the horizon, as `episode_collapse` (`:2976`) already does. | `d2-ckpt`'s curve peaks at 1000.0, against 2,155.8 for `d1w-con` before (the same task). |

Fixed earlier, listed for completeness: **the Go1 played with no body drawn**
(Playground keeps every geom in group 3). `write_view` now draws every visible
geom when nothing else is drawn (`cadex_train.py:5475`, ADR-839).

## Listed, not fixed

Ranked by how often the owner meets it times how wrong it is.

| # | What the owner sees | Cause | One-line fix |
|---|---|---|---|
| 7 | When two runs overlap, the card and the page can name different finished runs (4 of 386: `leon-v-runlab`, `ot4-quill`, two `ot5-wren` copies). | The card orders runs by last write (`review_server.py:3724`). The page orders them by launch (`review_record.py:1022`, `recorded_at`). | Order the card by `recorded_at`/`started_at` read from the newest few records, memoised per file identity. |
| 8 | The Runs table and the source menu list judge-output directories as `empty` runs. leon V has 23 of them among 35 entries. | `review_record.py:1008` `list_runs` deliberately lists every directory under `runs/`. | List only directories with a record or telemetry, and add one line counting the others. |
| 9 | After a page has shown a failed or stopped run, it stays `failed` or `stopped` through later agent work until something is accepted. | `review_server.py:2916–2924` gates both states on `accepted_at` alone. | Gate them on the later of `accepted_at` and `_agent_worked_at`. |
| 10 | Picking leon V's CAD-derived run is slow to draw: 37 s to a headless shot against 17 s for its concept (`D1-WATCH.md`). | `run_model` → `_cad_on_bodies` (`review_server.py:1657`) costs 0.8–1.5 s per call and is not memoised. The page then fetches all 101 part meshes (17 MB of display). The rest is SwiftShader in the headless shot. | Memoise `_cad_on_bodies` by (export sha, model sha), and reuse accepted meshes the page already holds. |
| 11 | A run cut from an older revision shows primitives only (`spare-willow-9655`). | `_cad_on_bodies` (`review_server.py:1657`) matches only the current accepted attempt's MJCF export. | Match the run's `cad_sha256` against each retained revision's export (the ADR-546 store). |
| 12 | A design that walked off its rest bounds leaves the viewport empty at later playback times unless Follow is on (`D1-WATCH.md`). | `fit()` (`review_scene.js:721`) frames the rest-pose bounds. | Frame the union of the rollout's placed bounds when a rollout loads. |
| 13 | A trainer-written trace (the closing view, and checkpoints since ADR-851) gives the Activations editor no motor data. | `write_view` (`cadex_train.py:5493`) writes placements only: no `joint_positions` and no `actuator_efforts`. | Write each frame's actuated `qpos` and `actuator_force` in channel order. |
| 14 | A run kept outside the project, or reached through a symlink out of it, is `unreadable` or absent. This includes leon IV/V's runs in their own repositories. | `review_record.py:869`: containment refuses an escaping run directory. This is by design, since the dashboard reads only its own project. | None in the server: train with `--out` under the project's `runs/`. |

## Method

- **Sweep:** for every project, `project_card(root)["stage"]` and
  `ReviewProject(root).review()["stage"]` were compared on `run` and `state`.
  Before used a scratch worktree of `9c451756`; after used this tree.
  Read-only on every project.
- **Bare run:** the leon V concept task as in D1
  (`runs/d1w-con/outputs/leon4_joystick-task.json`), 4096 envs × 40
  iterations, `--checkpoint-every 10 --view-seconds 6`, under
  `systemd-run --user --scope -p MemoryMax=30G` (103 s, rc 0). It was read back
  with `checkpoint_rollouts` and `checkpoint_playback`, and shot with
  `d1_shot.py --timeline --seek 2`.
- **Rebuild:** `cadex export --rebuild --format brep` on `d2-biped`, an rsync
  of the lab biped without `runs/`, under `ulimit -v 16000000`.
- **Suites:** `pixi run test-engine` and
  `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests`, plus
  `training/` from `~/cadex-train-venv` on the CPU. The results are in ADR-851.
