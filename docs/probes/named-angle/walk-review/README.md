# Walk review rendering evidence

Verified against source: 2026-09-08. Provenance: [Cadex-new]. ADR-239 follow-up.

The full built-engine CLI suite exercised the existing arm and linear-carriage
walks with the real offboard training venv, one iteration and four CPU
environments per run. The arm also doubled its lift weight and retrained.
Local/remote-flag parity used a local CPU dispatcher stand-in; no SSH or GUI.

Command: `pixi run python -m pytest cli/tests -q` (a fresh temporary basetemp).
Result: **181 passed, zero skipped, 178.77 s**, exit 0. The external monitor
measured 179.3348 s. It sampled trainer RSS every 0.25 s and terminated a
trainer exceeding 3 GiB RSS or 900 s; neither cutoff fired. Eight trainer
processes were observed, maximum sampled RSS 991,632 KiB (968.4 MiB), maximum
observed lifetime 8.835 s. Sampling does not capture between-sample peaks.

After collection, the rendering refusal test gained a second parameter for an
internally consistent rebuilt revision differing from the rollout. Its final
focused run (`pixi run python -m pytest cli/tests/test_walk.py -q -k render_failure`)
passed both cases, 20 deselected, 1.92 s. Production source was unchanged except
comments after the full gate started. Earlier focused walk gate: 21 passed in
83.12 s. An initial development run failed because the new timer import was
missing; the import was fixed before these passing gates.

| case | entry point through review (s) | acquisition (s) | rendering (s) | rollout reward | offending / unknown pairs |
|---|---:|---:|---:|---:|---:|
| arm | 15.2675 | 0.6532 | 0.5205 | -27.1093842 | 1 / 0 |
| arm iterate | 16.6549 | 0.6494 | 0.5191 | -55.3480045 | 1 / 0 |
| carriage | 14.3907 | 0.6915 | 0.6354 | -24159.1953563 | 0 / 0 |
| local parity | 15.2567 | 0.6665 | 0.5221 | -27.1093842 | 1 / 0 |
| remote-flag CPU stand-in | 15.5678 | 0.6554 | 0.5236 | -27.1093842 | 1 / 0 |

`walk_seconds` starts at entry-point dispatch and stops after the review session,
before review.json serialization and the final progress row/project commit.
Acquisition includes display rebuild/snapshot; rendering includes projection,
depth tests and encoding before file writes. Added acquisition/render work is
1.174 s for the arm and 1.327 s for the carriage. The arm's 15.2675 s lies near
earlier individual whole-command samples of 15.2430 s and 14.5173 s, but timing
boundaries differ and these are unpaired observations, not a regression benchmark.
The next planned unit is a separate documented fresh-project walk rerun with
external whole-command timing; it is not bundled into this implementation unit.

Tests decoded every view's embedded PNG, checked actual nonblank contents,
accepted revision agreement with clearance, project-relative paths and tracked
summary/image files. Local and simulated-remote decoded pixels are identical.
The arm's touching base/swing pair remains a below-clearance finding, not a
rendering failure. Failure regressions retain old on-disk review bytes but refuse
the command and expose no new successful review. Sections are explicitly absent.

All eight arm/carriage views from the focused real walk were visually inspected:
front/top/right silhouettes, shaded iso poses, the arm touching its base and the
carriage above its base. The copies here are from the final full-gate projects;
image payloads match those inspected. JSON paths preserve the original project
layout; evidence copies use `arm-` and `carriage-` prefixes only for browsing.
The real projects' commits include the images, summary, review and project docs.
No training checkpoints, policies, or rollout traces are copied into this repo.

Files: `measurements.json`, two `*-review.json`, two `*-summary.json`, eight
`*-{front,top,right,iso}.svg`, `cli-gate.log`, `cli-gate.json`, `refusal-gate.log`.
