---
node_id: 2e2909dd-4b8a-5dbc-901d-b784d3e0bd4c
slug: soft-crane-2369
title: Measure and clarify the walk inventory history boundary
created_at: '2026-09-08T16:33:32+00:00'
parents:
- scarlet-ocean-2920
summary: ''
---
## What

Measured the saved-walk inventory boundary with a public model-free hinged-arm walk followed by a component rename and standalone inventory. Replaced repeated inventory prose in docs/CLI.md and the project scaffold with the latest-report versus historical-count contract; recorded ADR-254 and a ROADMAP checkbox. Runtime remains unchanged.

## Why

Follows scarlet-ocean-2920 short unit 1 and maintains charter criteria “The agent can see its work without a screen” and “The walk exists and is tested headlessly” (missions 1/2/6). The concrete limitation is that the saved inventory block discards named rows and revision while linking to a report later calls overwrite. This rehearsal targets inventory history, not the completed CPU/recovery direction. Assumption: use the documented policy-off iterate switch before accepting a task-changing component rename; do not retrain solely to measure inventory. Reconciliation is reserved for the separate maintainer, as required by this dispatch.

## Method

In an isolated temporary project repository, accepted examples/lifecycle/hinged-arm/script.py through the public script command and copied its sensors document. Ran exactly one rehearsal training invocation:

```bash
JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" \
  --out "$PROJECT/runs/baseline" --name inventory16.cxpolicy \
  --iterations 1 --envs 4 --seed 0 --timeout 600 --json
```

Monitored aggregate descendant RSS every 0.2 s with 2.9 GB and 850 s whole-walk cutoffs. Initial monitor invocation used unavailable `python`; reran with python3 before any training. Read the accepted script through `cadex script`, changed only the published component key from `"swing": swing` to `"rocker": swing`, and submitted through `script --set --replace`. With policy_on still 1 this correctly refused a changed task digest. Then `params --set policy_on=0 --out "$PROJECT/runs/rename-prep"`, the same script submission and `cadex inventory` all exited 0. No additional rehearsal training, model call, GUI or remote dispatch.

Evidence remains outside this repository in temporary project cadex-inventory16-0j_zeroc, runs/baseline/review.json, docs/inventory.md, PROGRESS.md and project Git; temporary cadex-inventory16-* logs hold envelopes and gate output. No generated dump, policy or rollout is committed to this product repository. Compared old review bytes before/after and original report bytes against `git show 1de6507:docs/inventory.md`; checked review artifact existence, policy witness, leg exits, section status and clearance bounds.

## Result

Walk exit 0, 14.6115 s elapsed, peak aggregate RSS 1,540,816,896 bytes. CPU receipt: trainer 1.2591 s, reward/step -0.38019815, witness error 2.0698448e-9 below 1e-4. Verified rollout total reward -27.10938422. Train, declare and rollout exited 0; the existing script supplied design/assembly/MJCF/task. All four named render files are nonempty, XZ section status ok, inventory two uncatalogued components, clearance one touching base/swing pair, zero common volume and unknowns, bounds check pass. Engine/source comparison matched 56 top-level Python files; no binary-provenance claim.

Baseline report revision ca5336093456 named base/plate and swing/arm. Latest revision efd11c898d0b names base/plate and rocker/arm. Old review bytes remained identical; its inventory block still contains only available=true, component_count=2, catalogued_count=0 and path=docs/inventory.md. Project commit 1de6507 retains the original report exactly; later commits 276115e, 2146375 and 7a8f780 record switch, rename and inventory. Project working tree clean. Other review blocks already carry some names and revisions; this is not lost Git history or loss of all named review evidence.

Next: selected short unit 2 can preserve existing inventory revision/component/source/catalog fields in saved reviews, with an existing regression covering differing inventories. That self-contained inventory evidence is still missing; this unit documents the boundary rather than claiming to fix it. Charter criteria already have working evidence; no checkbox is retired. Initial-pose toy review does not prove policy improvement, swept safety, GUI execution or remote dispatch.

Validation: `pixi run python -m pytest cli/tests` without an outer CPU override: 223 passed, no skips, 208.33 s (temporary cadex-inventory16-tests.log). `git diff --check` passed. This edits scaffold prose and docs only; no engine/payload/protocol/shell gate or build applies. Verified dates remain 2026-09-08. Hypergraph export/check are required before the single commit.

Dispatch closed: 1 unit — measure and clarify historical walk inventory versus the latest report.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 03c5b4284afe4fcae42a9a0d8c880e8af14cad1d

## State Impact

- target: damp-moon-9297 — Measured renamed component after public walk: saved inventory counts and link stay fixed, latest named rows advance, original report remains in Git; guide and scaffold clarify this boundary. Named inventory snapshot remains next.
- target: crisp-reef-5607 — Inventory-boundary rehearsal passed public toy walk in 14.6 s at 1.54 GB with verified policy and all four reviews; CLI gate 223 passed, no skips.
