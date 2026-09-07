# Two mechanisms through the same lifecycle walk

Verified against source: 2026-09-08. [Cadex-new]. ADR-203.

The hinged arm and vertical linear carriage are synthetic mechanisms with
different joint and actuator types. Both passed the unchanged headless
entry point from xscript geometry through assembly, MJCF/task export,
local CPU training, policy verification, rollout and numerical review.
The walk also writes `docs/inventory.md`; `runs/baseline/review.json`
includes its project-relative path and component/catalogued counts.
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
  --out "$project/runs/baseline" --trainer-python "$PWD/.venv/bin/python" \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

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
git work tree; the CLI does not create a nested git repository.
The examples' sensor notes demonstrate the domain-doc convention.
`cli/tests/test_walk.py` exercises the carriage with the real engine and
trainer and asserts an actual MJCF slide joint and a verified policy trace;
the existing arm test still exercises retraining.
