# Fresh hinged-arm walk after preview integration

Verified against source: 2026-09-08. [Cadex-new]. Evidence for ADR-239.

The documented `examples/lifecycle/README.md` entry point passed on a fresh
external scratch project, using the existing built engine and training venv.
No product source changed. The only remaining headless-review leg is the
named-plane section call and its walk integration; this run does not close it.

Reproduce from the repository root (`PROJECT` is a fresh path outside the repo;
`LOGS` is an existing scratch directory). `monitor.py` is the exact external
monitor used, sampling the full descendant tree every 0.2 seconds and stopping
at 2.9 billion RSS bytes or 850 seconds. Those whole-command bounds also bound
each training run below 3 GB and 15 minutes; the trainer timeout is 600 seconds.
Sampling cannot capture between-sample memory peaks. No cutoff fired.

```bash
monitor=docs/probes/named-angle/fresh-walk/monitor.py
python3 "$monitor" ./cadex script --project "$PROJECT" \
  --set examples/lifecycle/hinged-arm/script.py --json \
  > "$LOGS/script.json" 2> "$LOGS/script.log"
JAX_PLATFORMS=cpu python3 "$monitor" ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/baseline" --trainer-python "$PWD/.venv/bin/python" \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json \
  > "$LOGS/walk.json" 2> "$LOGS/walk.log"
JAX_PLATFORMS=cpu python3 "$monitor" pixi run python -m pytest cli/tests -q -rs \
  > "$LOGS/cli-gate.log" 2> "$LOGS/cli-monitor.log"
```

Script acceptance: exit 0, 1.52 s, sampled peak 235,945,984 bytes.
Walk: exit 0, **17.07 s**, sampled peak **1,054,818,304 bytes**. All three
child legs exit 0: train 12.03 s, declare 1.32 s, rollout 1.45 s. The full
CLI gate began while the walk was still active, so this is a contended sample.

Internal `walk_seconds` is 16.9196 s, ending after review inspection but before
review serialization and final project commit. Display acquisition costs
0.7027 s and rendering 0.5262 s (1.2289 s combined). The external whole-command
sample is +1.8270 s versus 15.2430 s and +2.5527 s versus 14.5173 s. These
individual observations, with concurrency and different runtime conditions,
are not a regression benchmark. External timing includes monitor sampling delay.

Training is CPU, one iteration, four environments, seed zero; recorded trainer
compute time 1.1906 s, training reward/step -0.3801981509. Engine policy receipt
verifies 32 witness samples at **1.3841167412e-09** error against 1e-4 tolerance.
The verified 50-step rollout (script-declared rollout seed 3) has reward
**-27.109384220927513**, matching earlier arm baselines.
This proves the pipeline, not useful learned control.

All four extracted PNGs were visually inspected: front shows the arm atop and
extending past the plate; top shows their footprints; right shows the narrow arm
above the plate; iso shows shaded depth and both solids. The images depict the
initial solved pose, with the tessellation limits preserved in `summary.json`.
All are nonblank; coverage and PNG hashes are in `verification.json`.

Assertions checked exact accepted revision and digest agreement between command
envelope, rollout leg, render summary and review (and clearance revision), and
byte equality of every required artifact against project HEAD. The project is
clean. `verification.json` records the project commit and required paths. Project
HEAD tracks the four SVGs, summary, review, architecture/decision/progress docs,
inventory and clearance. No best checkpoint or rollout trace is tracked; the
product retains its accepted policy asset. No policy, checkpoint, geometry export
or rollout trace is copied into this repository's evidence.

Inventory contains two uncatalogued synthetic components. Clearance preserves
**base/swing: 0 mm distance, 0 mm³ common volume**, one below-clearance pair at
0.1 mm / 1e-6 mm³ thresholds, **zero unknown pairs**. This is contact, not an
intersection-volume finding or a swept-motion check. Section availability stays
false. `PROGRESS.md` records reward and clearance counts.

Evidence copies retain project-relative artifact paths; `PROJECT` replaces the
scratch absolute path in the copied progress log, and `REPO` replaces the local
checkout in stderr. Full command envelopes stay local because they contain
machine paths. No GUI, SSH, remote dispatch, provisioning or build was run.

Full built-engine CLI gate: **182 passed, zero skipped, 178.80 s**, exit 0.
The whole-suite monitor measured 179.59 s and peak descendant RSS
1,164,541,952 bytes, with no cutoff. `cli-gate.log` and `cli-monitor.log`
retain the output. This includes the real arm/carriage and local CPU
remote-flag stand-in tests; no SSH dispatch occurred. No engine, protocol,
payload or shell edit required an additional zone gate. No behavior, removal
or new implementation work item landed, so no ADR or ROADMAP checkbox changed.
