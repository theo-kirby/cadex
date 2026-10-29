# orun21 M0: where a design-to-policy iteration's time goes

Verified against source: 2026-10-29. Frozen run evidence; read it, never cite
it as current.

M0 in two halves: **the log pass** over the last three Ouroboros runs (§1),
then fresh timings on this checkout (§2–§6): the trainer's closing view, cold
and warm builds of leon V and the biped, each model tier's steps/s, both
suites, and the route's cheap legs. §7 ranks the sinks and names S1's three;
§8 is S1's cuts and §9 re-times the two representative iterations after them.
Everything timed ran on the lab copies in `~/cadex-projects/orun21-lab/`
(32 CPUs, 60 GB, one RTX 5090).

## 1. The log pass

`m0_logs.py` (this directory) reads every role session's stream-json
transcript in a run's `.ouroboros/runs/<run>/transcripts/` and splits its wall
time into model time, foreground tool time by kind, and idle time spent waiting
for a background task of that kind to finish (a session that ends its turn and
is woken by a task notification). Kinds are regexes on the command text; a
`until … sleep` loop is counted as waiting on whatever it polls. "model" is an
upper bound: it is every gap between a tool result and the next assistant
event, so API latency and any idle gap with no finished task to blame land in
it.

    python3 docs/probes/orun21/m0_logs.py .ouroboros/runs/orun20 \
      ~/cadex-projects/leon-iv/.ouroboros/runs/l4r1 ~/cadex-projects/leon-v/.ouroboros/runs/l5r1

| run/role | sessions | wall h | model | build | train | judge | test | memory | other |
|---|---|---|---|---|---|---|---|---|---|
| orun20/actor | 7 | 4.85 | 0.99 (20%) | **2.97 (61%)** | 0.11 (2%) | 0.00 | 0.15 (3%) | 0.00 | 0.64 (13%) |
| orun20/critic | 6 | 0.01 | 0.01 | | | | | | |
| orun20/scribe | 6 | 0.34 | 0.10 (30%) | | | | | 0.24 (70%) | |
| l4r1/actor | 30 | 9.26 | 2.66 (29%) | 1.22 (13%) | **3.30 (36%)** | 1.40 (15%) | 0.23 (2%) | 0.00 | 0.52 (6%) |
| l4r1/critic | 29 | 0.09 | 0.08 | | | | | | |
| l4r1/scribe | 29 | 0.57 | 0.50 (88%) | | | | | 0.06 (11%) | |
| l5r1/actor | 22 | 8.01 | **2.37 (30%)** | **2.29 (29%)** | **2.23 (28%)** | 0.43 (5%) | 0.15 (2%) | 0.00 | 0.53 (7%) |
| l5r1/critic | 21 | 0.06 | 0.05 | | | | | | |
| l5r1/scribe | 21 | 0.42 | 0.36 (86%) | | | | | 0.06 (13%) | |
| **all three** | | **23.6** | **7.1 (30%)** | **6.5 (27%)** | **5.7 (24%)** | 1.8 (8%) | 0.5 (2%) | 0.4 (2%) | 1.7 (7%) |

orun20 was design only (leon I in four styles); l4r1 and l5r1 were design and
training (leon IV, leon V). Sessions include one retried actor attempt in l4r1.

Per iteration, from each run's `loop.log` (role end stamps):

| run | wall h | iterations | actor median (mean) | critic median | scribe median |
|---|---|---|---|---|---|
| orun20 | 5.29 | 6 | 46.3 min (48.4) | 0.2 min | 3.0 min |
| l4r1 | 10.43 | 29 | 18.1 min (18.9) | 0.3 min | 1.1 min |
| l5r1 | 8.59 | 21 | 11.6 min (22.3) | 0.2 min | 1.2 min |

What the logs say:

- **The actor is the iteration.** Critic and scribe together are 4–7% of a
  run's wall time. The scribe's largest share is model time; orun20's scribe
  spent 70% of its 0.34 h in `governor`/`ouroboros mem` calls (14 min over
  six folds and records), the edge-scaling cost noted when the graph moved to
  Flywheel. In l4r1 and l5r1 memory is 11–13% of the scribe, about 4 min a run.
- **Builds, training and the model are a third each** on the training runs.
  On the design-only run builds are 61%. Judging is 5–15%, tests 2–3%.
- **Waiting on usage cost nothing in these three runs.** No `rate_limit_event`
  was `rejected`; l5r1 ran 346 events at `allowed_warning`, none blocking, and
  no `loop.log` shows a usage wait or retry for capacity.
- **Model time is turn count.** l5r1's actor took 1,114 turns for 2.37 h of
  model time, 7.7 s a turn; l4r1 1,416 turns, 6.8 s; orun20 471 turns, 7.6 s.

### What an actor reads

From the `usage` of each session's first and last assistant message (input +
cache creation + cache read), and the text of every tool result (chars/4):

| run | context at turn 1, median | at the last turn, median | text tool output per session | images read |
|---|---|---|---|---|
| orun20 | 56.7 k tokens | 136.7 k | 26 k tokens | 25 |
| l4r1 | 46.9 k | 121.3 k | 25 k | 30 |
| l5r1 | 47.5 k | 134.3 k | 28 k | 14 |

Of the ~47 k at turn 1, the files this repo controls are small, by chars/4:
`AGENTS.md` 3.5 k, `.ouroboros/goal.md` 4.7 k, the auto-memory index
`MEMORY.md` 2.1 k, and the orient block (frontier, architecture head, tail)
roughly 6–8 k. The rest is the harness's own system prompt and tool schemas.
Every turn re-reads the whole context from cache: l5r1's actor read 126.9 M
cached tokens over 1,114 turns, about 114 k a turn. A token cut at the top of
the prompt saves on every turn, but the context doubles within a session from
tool output and the actor's own work, so the prompt is not the main reader.

## 2. Timed: the closing view, alone

GO1-BASELINE.md found the end of a run 24 s slower than in orun18. ADR-835's
closing view is the suspect: after the last iteration the trainer JIT-compiles
and runs a `--view-seconds` (default 10 s, 500 steps) deterministic rollout of
the witness batch (`view_rollout`, `training/cadex_train.py:4343`, called from
`train` at :4550). Timed on its own with `m0_view_screen.sh`: run1's Go1
command at 100 iterations (8192 envs, unroll 20, 16.4 M steps), no
checkpoints, seed 1, `--view-seconds 10` against `0`, twice each, alternating,
alone on the 5090 under `systemd-run --user --scope -p MemoryMax=30G`.
Seconds from launch (`orun21-lab/go1/m0-view/v*/train.log`, each line
stamped by the script):

| run | first iteration | iteration 99 | policy written | end to end | last iteration → written |
|---|---|---|---|---|---|
| view 10, a | 52.4 | 72.7 | 123.4 | 123.9 | **50.7** |
| view 0, a | 51.2 | 71.4 | 97.4 | 97.9 | **26.0** |
| view 10, b | 52.6 | 72.8 | 124.1 | 124.6 | **51.3** |
| view 0, b | 52.6 | 72.8 | 98.8 | 99.3 | **26.0** |

- **The closing view costs 25.0–25.3 s**, a fixed cost whatever the run's
  length. It is the 24 s seen on run1. On a Playground-sized run (372 s) it
  is 7%; on this screen it is 20% of the wall time.
- **The rest of the end costs 26 s too**, with no view and no checkpoint.
  It is not split yet: what runs there is the final `snapshot` (with the
  witness rollout's own compile and the policy pack) and the witness check
  before the policy is written, but how the 26 s divides between them is
  unmeasured.
- **Training proper is 20 s of a 124 s screen (16%).** Compile before the
  first iteration is 51–53 s, the end 51 s. A screen of minutes is mostly
  fixed cost, and the fixed cost is the same on a 200-M-step run.
- The view was written (`v10-*/view/trace.json`) and the reward curves agree
  (0.0184 / 0.0185 / 0.0182 / 0.0183 per step at iteration 99), so the
  `--view-seconds 0` runs are the same training.

## 3. Timed: builds, cold and warm

`m0_build.sh PROJECT NAME [reaccept]` copies a lab project to
`orun21-lab/m0-build/NAME`, deletes its part and fit caches, and runs
`cadex export --format brep` on the accepted script twice: **cold** (no
caches) and **warm** (the caches the cold pass left, same script). Each
FreeCADCmd under `ulimit -v 16000000`, one build at a time, on the engine as
built at `a612af90` (`pixi run build-engine`: 8.0 s, nothing to compile).
Wall times are from `m0-build/times.txt`; the split is the moment the CLI
printed `· rebuild` (`m0-<pass>.err`'s mtime), so "open" is
`open_project` and "command" is export's own rebuild.

| project | pass | open (restore) | command (rebuild) | total |
|---|---|---|---|---|
| biped (`orun9-biped`) | re-accept, `script --set` its own `script.py` | — | — | 47.7 s |
| biped | cold | 20.0 s | 46.4 s | **66.5 s** |
| biped | warm | 20.3 s | 35.8 s | **56.1 s** |
| leon V (`4d67e21`, 102 MJCF bodies) | cold | 446.8 s | 1432.6 s | **1879.5 s** |
| leon V | warm | **432.3 s** | 661.3 s | **1093.6 s** |

- **Every engine open re-runs the script.** `open_project` runs a restore
  pass that rebuilds the accepted script to re-prove its digest
  (`src/Mod/cadex/cadexd.py:567`, `restore` defaults to true). On leon V it
  costs 432–447 s and **does not get faster with warm caches**; then
  `export` rebuilds again. A warm export of an unchanged leon V is 40% restore.
  Every engine-opening `cadex` command pays it once per call; an MCP session
  pays it once per engine open.
- **A warm rebuild of an unchanged leon V still takes 661 s**, half the cold
  1,433 s. The part cache (ADR-782) does not make an unchanged rebuild cheap
  on this project; PERFORMANCE-AUDIT.md's 108–158 s were one-part edits on
  the deinonychus, not measured here.
- **The biped no longer opens on this engine as stored.** Its stored digest
  (from 2026-10-17) does not reproduce: `export` refuses with "The restore
  pass digest does not match the accepted digest". Re-accepting its own
  `script.py` (`cadex script --set`) lands the same revision id `605e9bc8…`
  in 31–48 s with a new digest, after which it builds. Any project accepted
  on an older engine needs this step before the route can use it.
- During leon V's cold rebuild the engine suite ran once (19:02–19:07) on
  CPUs 0–15; the worker was pinned to CPUs 20–23 (`taskset -cp`).

From the logs, the same commands in the three runs
(`m0_build_calls.py`, every `cadex` command an actor ran, background ones from
launch to end): l5r1 ran 8 background `cadex script` builds, 69.7 min, median
360 s, max 1,299 s; l4r1 5, 55.5 min, median 412 s, max 1,490 s; orun20 2
(13.9 min) plus 25 foreground (13.1 min). `cadex hero` was 21–31 min a run
(median 387–485 s).

## 4. Timed: steps/s of each model tier

`m0_tiers.sh` runs leon V's `tools/train_bench.py` (the lab copy; P1 ports it)
on each model: MJX, zero policy from `qpos0`, 100 control steps of 20 ms,
alone on the 5090, under `systemd-run --user --scope -p MemoryMax=30G`
(`orun21-lab/m0-tiers/<name>.json`).

| model | sha256 | bodies | timestep, solver iter / ls, integrator | MJX contacts / rows | compile at 8192 | env steps/s, 2048 envs | **env steps/s, 8192 envs** | vs Go1 |
|---|---|---|---|---|---|---|---|---|
| Go1 (Playground's, the reference) | `1d03aaeb` | 18 | 4 ms, 1 / 5, Euler | 4 / 40 | 10.1 s | 741 k | **1,498 k** | 1 |
| leon V concept (D1) | `0959b4a3` | 23 | 2.5 ms, 1 / 5, Euler | 18 / 102 | 15.7 s | 306 k | **524 k** | 0.35 |
| leon V training model | `b09ec284` | 25 | 2 ms, 2 / 3, Euler | 18 / 68 | 20.5 s | 174 k | **302 k** | 0.20 |
| leon V engine MJCF (the judge) | `41a4e7e0` | 102 | 2 ms, 100 / 50, implicitfast | 218 / 910 | 116.7 s | 14.6 k | **9.4 k** | 0.006 |
| biped engine MJCF | `2b9c8268` | 56 | 2 ms, 100 / 50, implicitfast | 12 / 54 | 18.7 s | 59 k | **181 k** | 0.12 |

Every model stayed finite. The Go1's `upright` is false: its `qpos0` is not
its stand (the bench does not use the Menagerie keyframe), so it falls during
the bench; its number is the physics rate, not a standing rate. The leon V
training model matches leon V's own record (302.6 k, `docs/training-model.md`).

P1 re-ran every row with the port, `training/cadex_train_bench.py`, which
starts from keyframe 0 with its controls (ADR-842,
`orun21-lab/p1-bench/`): each rate within 0.5% of the table, and every model
now stands through the bench, the Go1 included. Added there: the biped's
training model (`b1e12e2d`, implicitfast 2 / 3), **651 k** at 8192 envs,
3.6× its engine MJCF.

What the trainer reaches with PPO on top (`progress.json` `wall_time_s`,
including compile and the run's end; 8192 envs × 20 steps an iteration):

| run | model | env steps | trainer wall | env steps/s |
|---|---|---|---|---|
| Go1 `run1` (this checkout) | Go1 | 206.4 M | 324.7 s | **636 k** |
| leon V `concept-d1/seed0` | concept D1 | 599.6 M | 1,804.6 s | **332 k** |
| leon V `t1zero/seed0` | training model | 206.4 M | 730.5 s | **283 k** |
| biped `b1-b1` | its engine MJCF | 49.2 M | 666.4 s | **74 k** |

- **The engine MJCF of a large creature is not a training model**: 9.4 k
  steps/s is 32× slower than the training model cut from it and 160× slower
  than the Go1. 200 M steps on it would take over 6 hours of physics alone.
  The biped's engine MJCF trains because it is small (12 contacts).
- **The training model is physics-bound**: 283 k in the trainer against 302 k
  bare. The Go1 is not: 636 k against 1,498 k, so on fast models PPO and the
  fixed cost (§2) are the rest.
- The leon V runs used the trainer in `~/leon-iv-tooling` at the time; only
  the Go1 row is this checkout's trainer.

## 5. Timed: the suites

On an idle machine, one run each, after `pixi run build-engine`:

| suite | result | wall | AGENTS.md says |
|---|---|---|---|
| `pixi run test-engine` | 157 passed, 3 skipped | **130.3 s** (137.1 s under the build, pinned to CPUs 0–15) | ~34 s (2026-10-16) |
| `CUDA_VISIBLE_DEVICES= pixi run python -m pytest cli/tests` | 53 passed | **38.6 s** | ~38 s |

The engine suite's twelve slowest tests are all `test_cadexd_lifecycle.py`
through a real `cadexd` (93 s between them, the end-to-end test 18.1 s); the
growth from the documented 34 s is not traced here. The quality bar runs both
at every accepted commit that touches code: about 170 s a commit.

## 6. Timed: the route's cheap legs

On leon V's lab copy, CPU only:

| leg | command | wall |
|---|---|---|
| spec → concept MJCF | `training/cadex_concept.py concept/leon-v-d1.json` | 0.12 s |
| engine MJCF → training model | leon V `tools/training_model.py --frozen <41a4e7e0>` | 0.13 s (byte-identical `b09ec284`) |
| fidelity and standing | leon V `tools/training_fidelity.py` | 0.94 s (worst gated 1.88 mm, stands, pass) |

The derived tiers cost nothing to make. What costs is the CAD build that feeds
the training model, and training.

**A representative iteration at the start**, composed from the legs above
(the judge was not timed fresh; §1 puts judging at 5–15% of actor time):

| route | legs | wall, before judging |
|---|---|---|
| concept (spec change → policy) | concept 0.1 s; train 206 M steps at 332 k/s ≈ 620 s (D1 trained 600 M: 1,805 s) | **~10 min** (30 min at D1's budget) |
| CAD (script change → policy on the training model) | build ≥ 1,094 s (unchanged script, warm: 432 s restore + 661 s rebuild); derive + fidelity 1 s; train 206 M at 283 k/s = 730 s | **≥ 30 min**, 60% of it the build |

## 7. The sinks, ranked

By time saved per unit of work, from §1–§6.

| rank | sink | evidence | size | cut | S1 |
|---|---|---|---|---|---|
| 1 | **the restore pass on every engine open** | §3: 432–447 s on leon V, warm or cold; 20 s on the biped; every `cadex` command pays it, then rebuilds | ~7 min per engine-opening command on a large creature, 40% of a warm export | skip the restore when the command rebuilds anyway, or serve it from the pinned attempt or the part cache; `open_project` already takes `restore` (`cadexd.py:567`) | **yes** |
| 2 | **trainer fixed cost per run** | §2: compile 52 s + end 51 s (closing view 25 s, the other 26 s unsplit) | ~100 s on every run; 83% of a 100-iteration screen, 27% of a Playground-sized Go1 run (372 s) | JAX persistent compilation cache; compile the view with the final snapshot or reuse its rollout; split and cut the end's 26 s | **yes** |
| 3 | **a warm rebuild that the caches do not make cheap** | §3: unchanged leon V rebuilds in 661 s warm (1,433 s cold) | ~11 min per build on a large creature | profile the warm rebuild (which parts and fit passes re-run), then serve the unchanged ones from the caches | **yes** |
| 4 | training on slow models | §4: leon V training model 302 k vs Go1 1,498 k; engine MJCF 9.4 k | 730 s per 206 M steps on leon V vs 325 s on the Go1 | P1's route keeps training off the engine MJCF; the training model's 2 ms 2 / 3 is fidelity-bound (`docs/training-model.md`), so faster settings must re-pass fidelity | P1 |
| 5 | the engine suite | §5: 130 s against the 34 s documented | ~95 s a commit | trace the lifecycle tests' growth; drop or merge what costs more than it protects (ADR-725) | next |
| 6 | model turns | §1: 30% of actor time, 7–8 s a turn | 7.1 h of 23.6 | fewer turns per unit: one-command tools (P1), judges that answer in one call | P1, G2 |
| 7 | judging | §1: 5–15% | 1.8 h of 23.6 | one generic judge (P1, G2) | P1, G2 |
| 8 | memory writes | §1: 14 min of orun20's scribe | small | not ours (Flywheel) | no |
| — | waiting on usage | §1: none | 0 | — | — |

**S1 takes ranks 1, 2 and 3.** Ranks 1 and 3 are the CAD route's build: on
leon V together they are the whole 1,094 s of a warm export. Rank 2 is on
every training run, on every robot. Rank 4 is P1's work; rank 5 is next if
S1 finishes early.

## 8. S1's cuts, before and after

Each on the same input, re-timed after the cut.

**Rank 1, the restore pass: export reads the retained attempt (ADR-848).**
`cadex export` no longer opens the engine: it copies the attempt the store
retained under the accepted pin, after checking its result carries the
accepted digest. Timed with `m0-build/s1/export_time.sh` on `m0-build/leonv`
(leon V `4d67e21`, warm caches), one after the other, `times.txt` there:

| export of leon V, warm | open (restore) | command | total |
|---|---|---|---|
| before (`e69cab16`, `--format brep`) | 439 s | 1,405 s rebuild | **1,844.5 s** |
| after, `--format brep` | — | copy | **1.2 s** |
| after, `--format step,stl` | — | FreeCADCmd conversion of 101 BREPs | **24.5 s** |

The after run's 102 files are byte-identical to the before run's; same
revision `67b2a28c`, same digest. The biped (`m0-build/biped`): 0.2 s, 57
files byte-identical to M0's warm rebuild export (56.1 s). The 1,405 s
rebuild is 2.1× M0's 661 s on the same copy: the before run re-accepted the
same revision under a new digest (`70542856` → `78a948c6`), so leon V's
build is not byte-reproducible run to run and every rebuilding export
re-accepted it. `--rebuild` keeps that road; the restore still runs on
every other restoring command (`params`, `render`, `section`, `inventory`,
`link`, `asset`, `train`).

**Rank 2, the trainer's fixed cost per run (ADR-849).** The run's end compiled
the same witness-batch rollout twice (witness and closing view, ~25 s each);
now once. jax's persistent compilation cache keeps every compile between runs.
The M0 view screen's command (`go1/s1-fixed/screen.sh`, `--view-seconds 10`),
seconds from launch:

| run | iteration 0 | iteration 99 | end | total |
|---|---|---|---|---|
| before (`258e1536`) | 53.3 | 73.6 | 51.0 | **125.1** |
| after, empty cache | 54.1 | 74.4 | 27.1 | **102.0** |
| after, same command, warm cache | 19.5 | 39.4 | 8.6 | **48.5** |
| after, warm, `--learning-rate 1e-4` | 45.0 | 65.5 | 8.7 | **74.2** |
| after, warm, `--learning-rate 1e-4 --seed 2` | 52.4 | 73.2 | 26.9 | **100.6** |

The end's cut holds on every run. The cache hits only on the same program:
the learning rate is a constant in the compiled update and the seed reaches the
rollout through the drawn pools, so a hyperparameter screen still compiles its
update. The 19.5 s left before iteration 0 on a full hit is imports, the
environment's build and loading the cached programs; not split.

**Rank 3, the warm rebuild: the part cache was wiped by every other pass
(ADR-850).** The restore attempt and the build attempt of one export each
spent 260–270 CPU-s on `chest_frame` and 180–190 on `skull_frame`
(`progress.json` in each attempt): every part missed, twice. ADR-782's
fingerprint hashed the request's `document_objects`, which the restore pass
sends empty and a build sends full (317 objects on leon V), so each pass
deleted the other's folder. Now the fingerprint leaves them out.
`m0-build/s1/rebuild_time.sh` runs `cadex export --format brep --rebuild` on
`m0-build/leonv` (leon V `4d67e21`, revision `67b2a28c`) and keeps both
attempts' ledgers (`ledgers-<label>.txt`, `times.txt`):

| export --rebuild of leon V, warm | restore attempt | build attempt | total |
|---|---|---|---|
| M0 warm (`a612af90`) | 432.3 s | 661.3 s | **1,093.6 s** |
| before (`82498a40`) | 435.8 s | 607.2 s | **1,055.7 s** |
| after | 21.0 s | 195.5 s | **226.3 s** |
| after, again | 21.8 s | 198.5 s | **230.1 s** |

The before run's build attempt started after the fix was in the dev tree the
CLI runs, so it missed for a changed engine rather than for the restore's
folder; it is the cold-once that any engine edit costs, and it wrote the folder
(`61aabbfe…`) both later passes hit. All three runs give digest `78850ab3…`
and the same 102 files byte for byte, so leon V's rebuild is reproducible
again once its parts are kept (the before run itself re-accepted under a new
digest, as ADR-848's did). What the warm build still spends: ~157 CPU-s before
the swept fit, led by panel checks (`c_pnl_shin_r` 9.7 s, `c_pnl_withers`
8.1 s) and the script (5.9 s), then the swept fit; not split further.

## 9. The representative iterations, re-timed after S1

`s1_iteration.sh` (this directory) runs both iterations one stage at a time on
a lab copy of leon V at the P1 trot revision (`479e53ce`, export `41a4e7e0`),
and times each stage (`orun21-lab/s1-iter/times.txt`). The engine is the dev
tree at `eaa9fa5f` (ADR-848–850 in), and the trainer is this checkout's. Both
routes train at P1's budget (8192 envs × 300 iterations × 20 steps, 49.2 M
env steps, seed 0) and judge the best checkpoint with `cadex evaluate` on the
project's export: 10 frozen seeds, 6 predicates.

**Warm-up, not counted.** The copy's part cache was written under the
pre-ADR-850 fingerprint, so `cadex export --rebuild` first warmed it:
**1,442.4 s** (restore 446 s cold, then the build 997 s). The build hit the
part cache but re-ran every static fit (`c_chest_frame / c_pnl_neck_collar`
85 CPU-s, …), so the copied fit cache did not serve either. This is the
cold-once cost that any engine edit to a fingerprint carries.

**Concept route.** The spec change is real: the frozen spec's chest raised
8.51 → 10.72 kg, so the concept weighs the CAD's 33.31 kg (ADR-843 found E2
7.1% light).

| stage | command | wall |
|---|---|---|
| spec → concept | `cadex_concept.py leon-v-frozen.json --set trunk.0.boxes.0.mass=10.72` | 0.1 s |
| relay | `cadex_relay.py` the export's trot task onto it | 0.1 s |
| train | `cadex_train.py`, 300 iterations (progress `wall_time_s` 260.6, launch to end 289.5) | 290.4 s |
| judge | `cadex evaluate`, best (257): measure 30.6 s, **10/10**; film failed (below) | 36.2 s |
| **total** | | **326.8 s** (5.4 min), without the film |

**CAD route.** The edit is one script parameter, `panel_gap` 3.0 → 3.5 mm,
accepted with `cadex script --set`.

| stage | command | wall |
|---|---|---|
| edit + accept (the build) | `cadex script --set script.py` (one attempt, 1,408 s request to result) | **1,421.2 s** |
| export | `cadex export --format brep` (copies the accepted attempt) | 1.1 s |
| compare | `cadex_cad_vs_concept.py` concept against the new export | 0.1 s |
| cut + fidelity | `cadex_training_model.py cut --project` (ok, cut `e5233cc9`) | 0.9 s |
| relay | onto the cut | 0.1 s |
| train | 300 iterations with `--cad-model` (`wall_time_s` 326.0, launch to end 362.5) | 363.4 s |
| judge | `cadex evaluate`, best (275) on export `b5bb6356`: measure 30.5 s, film sheets 23.3 s, video 188.9 s; **10/10** (speed ratio 1.05, rated 0.82–0.84) | 244.6 s |
| **total** | | **2,031.4 s** (33.9 min) |

**Against the start.** M0 had no end-to-end iteration; §6 composed one at a
206 M-step budget and before judging. The rows below are logged wall times at
P1's 49.2 M-step budget on the pre-S1 code (`e69cab16`, ADR-847's runs in
`orun21-lab/p1-leonv/`, export from §8's before run). No number from the
before column is reused as new.

| stage | before (pre-S1, logged) | after (§9) | what moved it |
|---|---|---|---|
| concept: spec + relay | 0.1 s (§6; relay not timed) | 0.2 s | — |
| concept: train | 337.2 s (E2, launch to end) | 290.4 s | ADR-849, one witness/view rollout |
| judge, measure | 32.8 s | 30.5–30.6 s | — |
| judge, film | 215.3 s | 212.2 s (CAD only) | — |
| **concept iteration** | **~627 s** (judged with film, best: 289.4 s) | **327 s** without film; ~539 s with the CAD judge's 212 s of film added | ADR-849 |
| CAD: accept | 987 s (P1's accepted attempt `6c4f3251`, request to result; a task-only edit, no geometry changed) | 1,421 s (a geometry edit reaching every frame and panel) | not the same input; see below |
| CAD: export | 1,844.5 s (§8 before, `--rebuild` was the only road) | 1.1 s | ADR-848 |
| CAD: cut, fidelity, relay | 0.9 s | 1.1 s | — |
| CAD: train | 392.8 s (launch to end) | 363.4 s | ADR-849 |
| CAD: judge | 247.9 s | 244.6 s | — |
| **CAD iteration** | **~3,473 s** (58 min) | **2,031 s** (34 min) | |

- **The concept iteration is about 5 minutes and is training-bound.** The
  judge's measurement is 31 s; drawing its film is 212 s, 40% of a judged
  concept iteration. The trainer's end cut (ADR-849) shows as 47 s; its
  compile cache did not hit, because each route's first model is new.
- **The CAD iteration is now build-bound.** The export no longer rebuilds,
  so the accept is the only build left, and it is 70% of the iteration. The
  part cache (ADR-850) serves only parts the edit does not reach.
  `panel_gap` reaches the frames through their panel bosses, so the accept
  rebuilt `chest_frame` (290 CPU-s), `skull_frame` (184), `pelvis_frame` (86)
  and re-ran the static and swept fits: 2,286 CPU-s in 1,408 s of wall. That
  is close to M0's cold 1,433 s. A task-only edit like P1's should now hit
  every part, but that was **not re-timed** here, so the 987 s before has no
  after on the same input.
- **The next sink is the geometry build of a whole-robot edit**, the fits
  first (static fits 50–90 CPU-s a pair on the panels): §7 rank 3 cut what an
  unchanged rebuild repeated, not what an edit causes. Rank 5 (the engine
  suite, 130 s a commit) is untouched.
- **The concept judge's film failed, and the cause is the open
  `autumn-hawk-8597`, not S1.** The warm-up's `export --rebuild` attempt
  requested no `display` (its `request.json` has no `display` key; P1's
  accepted attempt and this accept's do), yet it became the accepted pin. So
  `evaluate` measured the concept policy and then could not draw it: "the
  accepted attempt retained no tessellation for c_chest_frame".
- **The concept trained at the CAD's mass passes on the export.** It was
  10/10, rated 0.75–0.77 and speed ratio 1.07–1.08. ADR-847's E2 concept, 7.1%
  light, got 0/10 at this budget. Two things changed, the mass and the
  builder (this concept is `cadex_concept.py`'s; E2 is leon V's own build), so
  the mass alone is not shown to be the cause.
