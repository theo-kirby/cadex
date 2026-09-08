---
node_id: 423fc9c1-9eca-5b6f-ac6f-6f2b96f10d4c
slug: scarlet-journey-0203
title: Scratch rehearsal artifacts untracked without deleting local evidence
created_at: '2026-09-08T08:05:13+00:00'
parents:
- lucid-snow-0350
summary: ''
---
## What

Fixed forward the scratch project artifact-tracking error rejected by the iteration-190 critic. External scratch project cadex-nt3-i190-arm now carries the documented CLI ignore rules and a new commit removing generated files from the index only. No product code changed.

## Why

Directly answers the overseer's must-fix rejection of [rec: lucid-snow-0350]: add documented ignore rules, untrack generated checkpoints and rollout traces, preserve files and history, and do not rerun training or claim first-visit scaffolding coverage. This maintains charter criterion **The walk exists and is tested headlessly** (crisp-reef-5607), including its project artifact discipline, and preserves evidence for **The agent can see its work without a screen** (damp-moon-9297). The reversible choice is manual scratch repair using existing CLI rules, with assets/job.cxpolicy retained as the authoritative stored policy. This is not a product ignore defect or a new behavior change.

## Method

Read docs/CLI.md's project-git contract (ADR-194/199) and cli/cadex_cli/project_docs.py's _GITIGNORE_TEMPLATE. P denotes the existing external scratch directory cadex-nt3-i190-arm; E its sibling cadex-nt3-i190-evidence. Confirm clean status and record HEAD and SHA-256 of all 68 tracked files. Extract the literal template with Python ast without importing or invoking CLI behavior, write P/.gitignore with its header accurately describing manual application, and enumerate matching tracked files with `git -C "$P" ls-files -ci --exclude-standard -z`. Run `git rm --cached --` on that exact list. Append scratch DECISIONS.md ADR-002 correcting ADR-001's generated implication that ignore scaffolding occurred. Verify every preexisting file other than the deliberately updated DECISIONS.md is SHA-256-identical, every removed path passes `git check-ignore -q`, no tracked file matches ignore rules, and assets/job.cxpolicy remains tracked. Stage only the two document additions/changes beyond those index removals, check the staged diff, and create one new scratch commit. Verify HEAD's parent equals the former HEAD and status is clean. External E/i191-remediation.json enumerates removed and retained paths and verification results; no local machine paths or generated artifacts enter the product repository.

## Result

Scratch fix commit faeced2bca3cf68a52710878e1f7a02b80c42f82, parent 406976fbdd7c21de002ca7281c469cf7427706d2, subject `Keep generated rehearsal artifacts local; preserve history and verify hashes`. Removed 33 paths from tracking: the CLI lock, runs/baseline/train/job.best.cxpolicy and job.cxpolicy, runs/baseline/rollout/assembly-simulation-trace.json, and 29 staged script_artifacts files including policy copies and two traces. All 33 remain locally present, hash-identical, ignored and untracked. There are now 36 tracked and 33 ignored files; zero tracked files match ignore rules. All 67 existing files other than DECISIONS.md are byte-identical, including PROGRESS.md, review.json, four named SVG previews, XZ section, inventory/clearance docs, accepted script/state and stored assets/job.cxpolicy. Scratch status and staged diff check pass. Earlier commits still contain the generated files: no history rewrite was performed.

The previous clean rehearsal measurements stand unchanged; this unit runs no walk, training, provider, GUI, remote command or build. No CLI/engine/shell source zone changed, so no source suite gate applies; verification is the actual scratch Git/index/ignore/hash audit plus the required hypergraph export/check before the record commit. No product removal, changed lifecycle behavior or landed ROADMAP work item: no product ADR/ROADMAP/scaffold edits are warranted; scratch ADR-002 records this index-only removal.

Next: separate maintainer/planner pass should reconcile and replan; the tail reaches three unreconciled nodes with this record. This contributor does not reconcile or edit state/plan/charter. The existing criteria remain supported, with no new execution leg missing from this repair; first-visit git/ignore scaffolding remains unexercised by the rehearsal and must not be claimed. Live resumed provider repair remains parked, not a reason to repeat the clean baseline. No whole-goal completion or charter checkbox change is claimed.

Dispatch closed: 1 unit — critic rejection fixed forward; generated scratch artifacts ignored and untracked with local bytes and rehearsal evidence preserved.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 673cc0f1efd7a55b782ef7c33d078776015b4479

## State Impact

- target: crisp-reef-5607 — Critic rejection of rehearsal artifact tracking repaired in scratch commit faeced2: 33 generated/transient paths ignored and untracked, local bytes and history preserved; first-visit scaffolding remains unexercised
- target: damp-moon-9297 — Rehearsal review evidence remains tracked and byte-identical after scratch index repair; no review or walk rerun
