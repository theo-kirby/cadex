---
node_id: f47845dd-ce7d-5ae8-a797-b3f2f77b7cc0
slug: fresh-flint-1505
title: First-visit Git ownership qualified in three disposable projects
created_at: '2026-09-08T08:12:36+00:00'
parents:
- polished-tide-5222
summary: ''
---
## What

Qualified the ordinary first-visit script acceptance command in exactly three external disposable projects: fresh without Git, already its own repository, and nested inside a parent repository. All accepted. Confirmed a narrow documentation/scaffold mismatch about repository ownership and ignore setup; no product source changed.

## Why

Executes the first short unit selected by [rec: polished-tide-5222], following the scratch setup caveat and its accepted remediation. Serves missions 1 and 2 and preserves charter criteria **Project as codebase** and **The walk exists and is tested headlessly** through standing maintenance of project history ownership. The explicit contributor prohibition on reconciliation takes precedence over the stale overseer request, already followed by the supplied maintainer checkpoint and planner bet. No criterion is reopened or newly ticked. This experiment supplies first-visit acceptance evidence, not another lifecycle walk or training result.

## Method

At product HEAD 7a290065, read STATE, the Hypergraph contract/record skill, VISION, docs/CLI.md §project history, examples/lifecycle/README.md, project_docs.py (module guidance, scaffold and ensure_project_repo/commit_project), and existing project_docs tests. Use the existing build/engine/cadex-engine-0.0.0-macos-arm64 stage, without refresh.

Create an external temporary directory with fresh/, own/, and nested/project/ roots. The latter two owners get a baseline Git commit using disposable local command identity. Own and nested parent contain `.gitignore` bytes `# user-owned ignore\nprivate-cache/\n`; nested/project has `# nested user rules\nlocal-cache/\n`. Every project has a user-note.txt. In both existing owner repositories, change the owner note from `baseline user note\n` to `staged user edit\n`, stage it, then change its working bytes to `unstaged user edit\n`. This distinguishes file preservation from index preservation. The nested project's separate note and the fresh note contain `project user note\n`.

For each project P, run exactly once:

```sh
./cadex script --engine "$E" --project "$P" --set examples/lifecycle/hinged-arm/script.py --json
```

Before/after snapshots include all existing user-file bytes (hex encoded), `git ls-files --stage`, `git diff --cached --binary`, and HEAD. Inspect JSON notes, commit subjects, status and tracked paths. Query nonexistent `runs/baseline/train/checkpoint.cxpolicy`, `runs/baseline/job-trace.json`, and `assets/job.cxpolicy` with `git check-ignore -v --no-index`. Do not create checkpoint or rollout files. The policy-disabled example produces geometry, MJCF and a task only. Raw envelopes, stderr and results.json remain outside the repository in the disposable cadex-i192 experiment directory; the commands and substantive results are reproduced here without committing local machine paths. Run the existing focused suite `pixi run python -m pytest cli/tests/test_project_docs.py -q` and explicit assertions over all snapshots.

## Result

Three acceptance exits 0. All pre-existing user-file bytes remained identical. All envelopes report `scaffolded ARCHITECTURE.md, DECISIONS.md, PROGRESS.md in the project root.`

- **Fresh:** additional notes `initialised a git repository in the project root.` and `committed 2b7d62f.`. One commit, subject `cadex script --set script.py`, clean status, nine tracked paths including the unrelated user note and the generated ignore file. No staged artifact paths tracked. Check-ignore matches `.gitignore:10:*.cxpolicy` for the checkpoint and `.gitignore:12:*-trace.json` for the trace. Stored asset query matches the negation `.gitignore:11:!assets/*.cxpolicy`: that is an inclusion exception, not an ignored asset (verbose check-ignore returns 0 even for that negation).
- **Existing root repository:** additional note `committed 8fba723.` with no initialization note. Subjects are `cadex script --set script.py`, then `user baseline`. User-owned ignore bytes are unchanged; no default rules installed. All three hypothetical paths return check-ignore 1 with no match. Seventeen tracked paths include script_artifacts and `.cadex-cli.lock`, consistent with the custom ignore file. No checkpoint or rollout trace exists or is tracked. The accepted run commits all working changes: owner note's index blob changes from 7323955fded7f2913278787dd43fb6dd473d8125 (staged edit) to 89d7f1c8669c764718060bf7b0eff75b5ba24b86 (working edit), then status/cached diff are empty. Working bytes are preserved, but the staged/unstaged distinction is consumed by the documented `git add -A`/commit-all behavior; do not claim the root repository's index is untouched or that its prior staged version is a committed revision.
- **Nested project:** additional note `inside an existing git work tree: not initialised, not committed.`. No project .git, no new commit; only subject `user baseline`. Parent HEAD, full index entries, cached binary diff, both ignore files and both user notes match their snapshots exactly. Parent retains `MM user-note.txt`; newly accepted project docs/script/history/artifacts/lock are untracked. All hypothetical paths return check-ignore 1. Parent ownership is respected.

Snapshot assertions passed: all three acceptances, all existing file bytes preserved, nested HEAD/index/cached diff unchanged, no checkpoint/trace paths tracked. Focused existing project_docs suite: 21 passed in 2.77s. No engine/CLI/shell source was edited, so full source suites/build/payload gate are not claimed; the three actual staged acceptance calls and focused suite validate this experiment. Hypergraph export/check is the recording gate.

**Exact next correction:** docs/CLI.md around lines 505–522 says the first visit writes ignore rules, then says a project already inside a work tree gets no commit. Restrict that no-commit statement to projects nested beneath another root; explicitly distinguish an existing project-root repository (commits, retains its ignore configuration) from a newly initialized root (creates ignore rules only if absent). project_docs.py module prose has the same ambiguity. Its DECISIONS scaffold asserts default ignore protection and its PROGRESS scaffold asserts every row is a commit even in the nested case; qualify these together, with the lifecycle doc as appropriate. Do not change legitimate commit-all ownership or overwrite user ignore rules to force the cases alike. A fresh root with pre-existing .gitignore, linked worktrees, absent Git and failed commits were not exercised; code inspection is not runtime coverage for them.

This completes only qualification. The plan's second, separate documentation correction is now dispatchable. No training, provider, walk rerun, GUI, remote dispatch, durable-project mutation, removal, ADR direction change or landed feature checkbox occurred. The charter's existing completion evidence stands; missing work from this unit is precise Git guidance, not a new lifecycle leg or evidence for ticking additional criteria.

Dispatch closed: 1 unit — three Git ownership cases qualified; exact docs/scaffold mismatch handed off for separate correction.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 7a290065be0000dccd64d817c3f942632b61f3b0

## State Impact

- target: chilly-union-8972 — Three real staged script acceptances distinguish fresh init/ignore/commit, existing root commit with user ignore preserved, and nested parent HEAD/index preservation; CLI docs and scaffold conflate those cases
- target: calm-peak-5247 — Project-as-codebase first-visit qualification confirms repository ownership behavior; precise docs/scaffold correction remains, with no repeated walk or training
