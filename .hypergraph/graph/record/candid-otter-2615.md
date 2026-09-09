---
node_id: e6488149-e9e4-507c-b784-06118b2e2614
slug: candid-otter-2615
title: Plan the training leg offline with cadex train --dry-run
created_at: '2026-09-08T16:45:20+00:00'
parents:
- soft-crane-2369
summary: ''
---
## What

`cadex train --dry-run` (ADR-255): the training leg can be **planned** rather than
run. The command rebuilds and exports the bundle for real, then reports a
`training_plan` field in the `--json` envelope instead of training — the four
files the leg would touch (`bundle`, `model`, `policy`, `stored_asset`) and the
ordered `steps` that touch them, with `executed: false` so a pipeline can never
mistake a plan for a receipt. `resolve_bundle_model` in `cli/cadex_cli/train.py`
is the Python of the model resolution `remote_train.sh` does inline (recorded
relative path against the bundle's grandparent, then the basename beside it), so
a bundle whose model is beside neither is a refusal here rather than a failure on
the box after the copy started.

Charter criterion advanced: **Three modes, one shape** (`witty-spark-2613`), the
remote-training limb, on the overseer's dispatch. Diff: `cli/cadex_cli/{train,
report,__main__}.py`, `cli/tests/test_train.py`, `docs/{CLI,DECISIONS,ROADMAP}.md`,
`training/SETUP.md` — 348 insertions, commit `007b4735`.

## Why

ADR-200 put the walk's train leg on `training/remote_train.sh` and claimed the two
modes land the same artifacts. Until now that claim was checkable only two ways:
by a test with an injected stand-in dispatcher, or by dispatching to a real box.
The first is not available to a person at a terminal; the second is forbidden by
this run's constraints and is exactly what a preflight is supposed to avoid. A dry
run makes the claim checkable from the command line, offline, and gives
`cadex walk --remote` the preflight it lacked: today its remote leg fails only
after the design and assembly legs have already run and spent their time.

Assumptions taken without asking, per the question policy (prefer the reversible):
`--dry-run` is a `train` flag and `walk` gains none — a half-run walk is not a
preflight, and adding the flag to `walk` would mean a walk that leaves a project
half-written. The plan deliberately does **no** ssh and reads **no** `.remote.env`,
so it is not and does not replace `remote_train.sh check`; both docs say so in as
many words. That keeps ADR-089's fail-loud shape and the CLI's rule that it adds no
remote configuration of its own.

## Method

- `training_plan(command, *, bundle, out, remote, allow_cpu, store_as)` and
  `resolve_bundle_model(bundle)` in `cli/cadex_cli/train.py`; the two transport
  step names are the module constant `REMOTE_TRANSPORT_STEPS = ("copy-out",
  "copy-back")`, so the test asserts against the source rather than a literal.
- `RunReport.training_plan`, serialized as `training_plan` and rendered in the
  human output as one `plan` line plus the artifact paths.
- `--dry-run` on the `train` parser; in `command_train` the branch sits after the
  command is built and before `_progress(" · train …")`, so it plans exactly the
  command that would have run, then returns `EXIT_OK` without the trainer or the
  `put_asset`.
- Two regressions in `cli/tests/test_train.py`: the real-engine parity one runs
  the same argv twice, once local and once `--remote --allow-cpu`, and the
  model-resolution one covers the fallback and the refusal.
- Docs in the same commit: `docs/CLI.md` §2 (the command table row and a new
  bullet ahead of the `check` bullet, which now says what a plan does *not*
  prove), `training/SETUP.md` §d, ADR-255, and a ROADMAP bullet.

## Result

**Gate green.** `pixi run python -m pytest cli/tests` — **225 passed, 0 skipped,
0 failed** in 210.7 s (223 before; the two new tests). Targeted first:
`test_train.py` 18 passed in 49.9 s.

What the parity regression actually asserts, against the real engine: both plans
carry the identical `artifacts` object (`out/job-task.json`, `out/model-model.xml`,
`out/job.cxpolicy`, `job.cxpolicy`); local `steps` are `export → train → verify →
store`; remote `steps` minus `REMOTE_TRANSPORT_STEPS` equal them exactly and the
set difference is exactly those two; the trainer's own flags after `--` are
byte-identical to the local command's after `--out POLICY`. And it ran nothing:
no `job.cxpolicy` in `--out`, no asset in the project store, no `training` key in
either envelope, and the stand-in dispatcher's argv log was never created.

ADR numbering: 252 was taken while this was being written (`ADR-252 — Pin
successful walk recovery`), so this is ADR-255; the source references were
renumbered before the commit.

**Not claimed.** No dispatch, no ssh, no box was reached, and nothing about
remote transport reliability is proven by this. A plan proves the *shape* of the
leg — which files, which order, which flags — never that the box is reachable, its
venv exists, or its trainer matches; that stays `remote_train.sh check`, and both
docs now say the dry run is no substitute for it. `--dry-run` with a warm start
still hits ADR-200's cold-run usage error before any of this, unchanged.

**Still missing before `witty-spark-2613` could be ticked beyond where it stands:**
nothing on the remote limb as the criterion words it — it asks for the handoff
documented and scripted while the local-only constraint holds, which it is, and
this makes it verifiable rather than merely asserted. What remains genuinely
unexercised is actual remote dispatch and actual GUI attachment, both blocked by
this run's standing constraints, not by missing work.

The unreconciled tail is 3 nodes with this one; a maintainer pass is due at 3.

Dispatch closed: 1 unit — `cadex train --dry-run` plans the training leg in either
mode without running it, with real-engine local/remote artifact parity pinned and
the CLI gate green at 225 passed.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 007b473548a20905dec6fae188ab339344b3e1e6

## State Impact

- target: witty-spark-2613 — the remote limb of the criterion gains an offline check a person can run: cadex train --dry-run reports the files and ordered steps the training leg would touch in either mode, with a real-engine regression asserting identical artifacts and local steps plus copy-out/copy-back; still no dispatch, no ssh, and no substitute for remote_train.sh check
- target: chilly-union-8972 — the headless CLI gains a train --dry-run flag and a training_plan envelope field (ADR-255); gate 225 passed, 0 skipped
