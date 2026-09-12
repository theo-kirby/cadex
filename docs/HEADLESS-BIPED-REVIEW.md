# Fresh biped review evidence

Verified against source: 2026-09-12. [Cadex-new]

The first creation attempt for `ot5-biped` did **not** create a model.
The product agent (`claude-fable-5`) returned exit 1 with “You've hit your
session limit”, reporting a reset at 2:30pm America/New_York. The project
is under the operator's `cadex-projects` directory, outside this checkout.
It contains its own Git repository and scaffold documents, plus the captured
CLI envelope and stderr under `evidence/create.json` and `create.stderr`.
No old project, mechanism, checkpoint or history was imported. No training
was started. There is no `script.json`, accepted revision, or component list.

A same-machine headless Chromium opened this project's dashboard through
its Tailscale address. It displayed `nothing accepted: no script.json ·
0 run(s)`, revision/digest `none`, model state `missing`, and `specs
unavailable: no script.json`. The next-action note names `cadex -p`.
The scaffold's PROGRESS document opened in the browser. The server was
stopped afterward; no second-device test is claimed. Observations are
retained in `evidence/refusal-browser.json` in the project.

A refused initial prompt does not produce a training/run record or an
accepted progress row. Its provider error is **not shown in dashboard
history**: retain the CLI envelope when diagnosing this case. The dashboard
correctly distinguishes missing geometry from a completed model, but this
is not evidence of D8's interrupted/failed training handling. The regression
`test_browser_unaccepted_project_reports_missing_model_and_next_cli_action`
pins the missing-state labels, document access, next CLI action and absence
of writes. D2/D9 still need the actual biped and model interaction checks.

To retry after provider capacity is available, preserve this project and
its evidence. From the repository root, with `PROJECT` set to that existing
project directory, run:

```bash
./cadex --project "$PROJECT" --resume --json -p \
  'Create Reed, a fresh parametric biped from scratch: compact torso, two articulated legs with hips, knees and broad feet, simple analytic geometry, editable dimensions, documented specs and rationale. Declare masses, collision, actuators, free root, ground and a forward locomotion task for a bounded GPU PPO probe. Read the API, save and inspect a validated accepted revision. Import no previous project or policy. Do not train yet.' \
  > "$PROJECT/evidence/create-retry.json" 2> "$PROJECT/evidence/create-retry.stderr"
./cadex review --project "$PROJECT" --host "$(tailscale ip -4)" --port 8765
```

Verify the envelope's accepted identity against the browser, component names,
parameters and specs, then exercise orbit/zoom on rendered geometry. A quota
reset time is a provider report, not proof a subsequent attempt will succeed.
