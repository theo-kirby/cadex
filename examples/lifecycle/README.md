# Two mechanisms through the same lifecycle walk

Verified against source: 2026-09-08. [Cadex-new]. ADR-203, ADR-257, ADR-260.

The hinged arm and vertical linear carriage are synthetic mechanisms with
different joint and actuator types. Both passed the unchanged headless
entry point from xscript geometry through assembly, MJCF/task export,
local CPU training, policy verification, rollout and numerical review.
The walk also writes `docs/inventory.md`; `runs/baseline/review.json`
includes its project-relative path and component/catalogued counts. It also
commits `docs/clearance.md` with the review's `clearance` summary and a
`PROGRESS.md` row of offending/unknown/checked pair counts. At the default
0.1 mm / 1e-6 mm³ thresholds the arm has one below-clearance pair; the
carriage's pair is clear. These are initial-pose findings, not motion checks;
unknown and unavailable measurements remain explicit.
The projects' `PROGRESS.md` files preserve the same metric definitions and
both sets of measured numbers. The carriage's poor height score is recorded,
not a claim of learned control or printable hardware.

With the built engine and training venv from `training/SETUP.md`, run from
the repository root, choosing a fresh project path for each baseline:

```bash
name=linear-carriage  # or hinged-arm
project=build/lifecycle/$name
./cadex script --project "$project" --set "examples/lifecycle/$name/script.py" --json
JAX_PLATFORMS=cpu ./cadex walk --project "$project" \
  --out "$project/runs/baseline" \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

No `--trainer-python` is needed: the CLI discovers `<repo>/.venv`, then
`~/cadex-train-venv` (`training/SETUP.md` §"Which interpreter"). Pass the flag
only to override that, and pass a path that exists on *this* machine — an
earlier revision of this file hard-coded `$PWD/.venv/bin/python`, which is not
where every machine keeps the trainer venv.

The two projects reproduced here have **no domain notes**, and the walk's
review says so: `script --set` installs the recipe and nothing beside it, and a
recipe walk runs no design turn, so the reproduced project's `docs/` holds only
the generated `inventory.md` and `clearance.md`. Both mechanisms declare an
`<actuator>` and a `<sensor>` section, so the ADR-256 documentation eye reports
`0 domain note(s) for 2 declared subject(s); no note for actuators, sensors`
for each. That is the convention working, not a failure — the notes are a
design turn's to write, and the CLI never invents one. The example directories
beside this file carry the notes a maintained project would keep
(`docs/actuators.md`, `docs/sensors.md`), which is where to read what the
convention asks for.

No digest edit, mechanism-specific option, model call or GUI is required.
The committed recipes start with `policy_on=0`; the walk installs the policy
and enables it. Fresh project paths avoid reusing an accepted policy from
an earlier run. For subsequent changes use the documented `walk --set`
iterate convention in `docs/CLI.md`.

The baseline runs were watched at 0.2 s intervals, with a 2.9 GB process-tree
RSS cutoff and an 850 s wall cutoff around each entire walk, in addition
to its 600 s trainer timeout. Observed peaks were below 1 GB and each walk
finished within 16 s. `--timeout` alone does not impose a memory limit;
preserve external monitoring when running under a strict memory budget.

The repo-owned examples retain only source and documentation. Their ignore
files exclude accepted state, exported geometry, policies, checkpoints and
traces. Runtime projects under this repository are also owned by its parent
git work tree: without their own `.git`, the CLI neither initializes nor
commits them and leaves the parent index untouched. In an external project-root
repository, accepted runs attempt to commit all working changes, including
unrelated edits. Default ignore rules are created only during initialization
and only if `.gitignore` is absent; existing repositories keep their rules.
Check those rules before generating checkpoints and traces. A progress row
alone does not confirm a commit; the command notes report `committed <sha>.`.
The examples' sensor notes demonstrate the domain-doc convention.
`cli/tests/test_walk.py` exercises the carriage with the real engine and
trainer and asserts an actual MJCF slide joint and a verified policy trace;
the existing arm test still exercises retraining.

## One entry point, and no branch that knows which mechanism (ADR-260)

The criterion these two examples exist to answer is "the same entry point,
with no code change specific to the mechanism". Both halves are checkable
here rather than taken on trust.

**The entry point** is `cadex walk`, dispatched by `command_walk` in
`cli/cadex_cli/__main__.py`. It runs each leg as a child `cadex` command
through `run_leg` (`cli/cadex_cli/walk.py`), so what the walk decides is
which legs run and with which flags — nothing else. The legs are `train`,
`declare` (a script read, the digest edit, a `script --set`) and `rollout`,
with a `sweep` leg in front of them only when `--set` asks for one, and
design turns in front of that only when `--prompt` does. Which mechanism
the project holds is not an input to any of those decisions.

**The absence of a mechanism-specific path** is pinned by two regressions
in `cli/tests/test_walk.py`:

- `test_the_two_example_mechanisms_dispatch_the_identical_legs` installs
  both recipes below, walks each with identical flags, and requires the
  child argv to be **equal** once the project path is substituted out. A
  single `if` on the joint kind, the actuator kind or the component count
  changes a leg or a flag and fails it. (Checked by mutation: adding
  `--label slider-rig` to the train leg for scripts containing `slider`
  fails the test with the two argv lists printed side by side.)
- `test_the_digest_edit_treats_both_example_mechanisms_alike` covers the
  one leg that reads a script the walk did not write: `declare_policy`
  rewrites the same two string literals on both recipes and leaves every
  other byte alone.

The two mechanisms differ where it matters for the claim: the hinged arm
is a **revolute** joint driven by a torque motor in N·mm, the linear
carriage a **slider** joint driven by a force motor in N. The comparable
numbers for both are in each project's `PROGRESS.md` — the same columns,
the same metric definitions, and the caveat that they do not rank designs:

| Mechanism | Joint, actuator | Rollout `total_reward` | Rollout reward/step | Trainer reward/step | Walk wall s | Peak tree RSS |
|---|---|---:|---:|---:|---:|---:|
| hinged-arm | revolute, torque motor (N·mm) | -27.1093842209 | -0.542187684419 | -0.380198150873 | 15.22 | 986,218,496 |
| linear-carriage | slider, force motor (N) | -24159.1953563 | -483.183907126 | -82.3199081421 | 13.52 | 979,582,976 |

Both at 1 PPO iteration × 4 environments, training seed 0, verified rollout
seed 3, 1 s at 50 Hz, CPU. The `sb1x` re-runs of the same rows are in the
section below and in each `PROGRESS.md`.

**What this does not settle.** The dispatch is mechanism-blind and two
mechanisms prove the loop runs for both; neither is a claim about learned
control. The carriage's policy still lets it fall to -4699 mm in one
second on an ideal guide, and the two `total_reward` columns are different
objectives in different units, so they compare runs of one project and
never rank the designs against each other.

## Reproduced on a second machine — 2026-09-08 (ADR-257)

Both commands above were re-run on `sb1x` (Ubuntu 24.04, 32 cores, CPU
training), into fresh `build/lifecycle/` projects, with the trainer interpreter
passed explicitly for the two measured walks below,
under the same 0.2 s watchdog at 2.9 GB / 850 s. Nothing generated is
committed. All three legs of each walk exited 0.

| Mechanism | Rollout total_reward | Trainer reward/step | `walk_seconds` | Walk wall s | Peak tree RSS | Witness error |
|---|---:|---:|---:|---:|---:|---:|
| hinged-arm | -27.109384220904474 | -0.3801981508731842 | 14.40 | 14.61 | 1,539,432,448 | 2.069844824703626e-09 |
| linear-carriage | -24159.195371510654 | -82.31990814208984 | 13.10 | 13.18 | 1,467,621,376 | 3.736925650865697e-09 |

The trainer means are bit-identical to the 2026-09-06 rows in each
`PROGRESS.md`; the rollout totals agree to 1e-11 (arm) and 1.5e-05 (carriage),
and the stored policy digests differ, because the two machines' JAX builds sum
the update in a different order while the first exploratory batch is fixed by
the seed. The peak RSS is ~1.5× the earlier machine's and still well inside the
budget. Reproducing a recipe walk needs no model call and no network. The flagless
command block above is evidenced by one walk, not three: a third
carriage walk, run exactly as written with no `--trainer-python`,
resolved the home-directory trainer venv on its own and returned the same
`total_reward` -24159.195371510654 in 13.19 s at 1,468,563,456 bytes.
