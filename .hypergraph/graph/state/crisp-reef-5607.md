---
node_id: f9d8b739-9a02-5f30-89eb-3a1cb1a32b7a
slug: crisp-reef-5607
title: The walk exists and is tested headlessly
created_at: '2026-09-06T19:18:33+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion: **The walk exists and is tested headlessly.** One documented entry point takes a mechanism from design → assembly → MJCF → task → toy-scale local CPU training → policy verify → rollout → review, on this machine, with no human step. Declared target `gap-walk-exists-tested-headlessly-one`; truncated impact wording resolved from the full charter [rec: empty-wolf-3962].

**Met on the repo-owned toy, 2026-09-06 (ADR-199, commit a4248b26)** [rec: shy-cabin-0798]. `cadex walk` is the documented headless entry point (`docs/CLI.md` walk section, `docs/MUJOCO.md` §7c note, ROADMAP tick). It was qualified through two real walks on the plate-and-arm toy: a placeholder digest to a verified rollout (`total_reward -27.1094`), then a reward change with a warm start (`-55.3480`, `Δ -28.2 vs 2c1ad3fb at -27.1` in the project's `PROGRESS.md`), eight project commits, the audit's numbers exactly. The two gaps the real run showed were fixed forward: `review.json` now lands under `--out` as the walk's own artifact and commit, and the scaffolded `.gitignore` keeps the trainer's checkpoints, the `train/` copies and `*-trace.json` rollouts out of the project's history while `assets/*.cxpolicy` stays committed. `cli/tests/test_walk.py` (13 tests) pins the digest edit, the review reader, leg order and flags against a fake `cadex`, and both real walks with the real engine and trainer; the full CLI suite was 130 passed, no skips. Domain docs are exercised by the caller: the real test writes `docs/sensors.md` and the walk's legs commit it.

Reconcile judgement: flipped to `working` on that evidence. Two limits stay derivable from the record and are not hidden by the flip: the qualification ran without `--prompt` (the toy is repo-owned, so the design and assembly legs were not re-driven by a model turn inside the walk — they are proven by the rehearsal and the audit, not by this run), and the domain-doc convention is exercised rather than generated. The earlier audit's gaps — the helper's digest edit, exports beside the project, no review in the project — are closed by this record [rec: fond-mesa-1562] [rec: shy-cabin-0798]. The general criteria the charter keeps separate — a second mechanism, the GUI-attached and remote modes — are their own gap nodes (`witty-spark-2613` for the modes) and remain open [rec: shy-cabin-0798].

## Negative knowledge

- [scope: what the walk commits from a training leg | confidence: medium | evidence: shy-cabin-0798] Before ADR-199 the `train` leg's commit carried `job.cxpolicy`, `job.best.cxpolicy` and the store copy — three copies of one policy. The store's asset is the project (ADR-194); checkpoints and traces are not, and the `.gitignore` says so. Reversible per project, because the file is editable.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- fond-mesa-1562 — fixed-toy evidence does not close the general entry point
- shy-cabin-0798 — ADR-199: cadex walk qualified on the toy through two real walks, review.json in the project, checkpoints and traces out of its history, 13 tests
