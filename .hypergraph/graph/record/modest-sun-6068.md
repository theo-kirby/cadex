---
node_id: f1538654-41aa-509a-bc51-d07098e02a21
slug: modest-sun-6068
title: Fresh hinged-arm walk verifies integrated previews and committed review
created_at: '2026-09-07T23:47:00+00:00'
parents:
- square-path-1173
summary: ''
artifacts:
- docs/probes/named-angle/fresh-walk/PROGRESS.md
- docs/probes/named-angle/fresh-walk/README.md
- docs/probes/named-angle/fresh-walk/clearance.md
- docs/probes/named-angle/fresh-walk/cli-gate.log
- docs/probes/named-angle/fresh-walk/cli-monitor.log
- docs/probes/named-angle/fresh-walk/front.svg
- docs/probes/named-angle/fresh-walk/inventory.md
- docs/probes/named-angle/fresh-walk/iso.svg
- docs/probes/named-angle/fresh-walk/monitor.py
- docs/probes/named-angle/fresh-walk/review.json
- docs/probes/named-angle/fresh-walk/right.svg
- docs/probes/named-angle/fresh-walk/script.log
- docs/probes/named-angle/fresh-walk/summary.json
- docs/probes/named-angle/fresh-walk/top.svg
- docs/probes/named-angle/fresh-walk/verification.json
- docs/probes/named-angle/fresh-walk/walk.log
---
## What

Ran the planned fresh-project hinged-arm lifecycle rehearsal after named-angle
walk integration. Captured commands, exits, bounded memory/wall measurements,
policy witness and reward, four inspected previews, revision/digest agreement,
and proof that review artifacts and project docs match committed HEAD bytes.
Evidence is in docs/probes/named-angle/fresh-walk/.

## Why

Advance charter criterion “The agent can see its work without a screen”
(damp-moon-9297), missions 6 and 2, and short-plan item 2 following
square-path-1173. This is the requested separate evidence unit before section
promotion. The reversible choice is the documented recipe in a fresh external
scratch project, existing engine and training venv, with no product change.
No question or human step was needed. The overseer's reconciliation request
conflicts with this dispatch's explicit prohibition: leave the now-three-record
tail for the separate maintainer; never edit state, plan or charter here.

## Method

From repository root, set PROJECT to a fresh external scratch path and run:
`./cadex script --project "$PROJECT" --set examples/lifecycle/hinged-arm/script.py --json`
then `JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/baseline" --trainer-python "$PWD/.venv/bin/python" --iterations 1 --envs 4 --seed 0 --timeout 600 --json`.
Wrap each with the committed evidence monitor.py, which samples all descendant
RSS every 0.2 s and stops above 2.9 billion bytes or 850 s. The full command
bounds also bound each training run below 3 GB/15 minutes. Sampling can miss
between-sample peaks. Run `JAX_PLATFORMS=cpu pixi run python -m pytest cli/tests -q -rs`
under the same monitor. The gate began while the walk was still active;
whole-walk timing is a contended sample, not a regression benchmark.

Extract embedded PNGs and visually inspect front/top/right/iso separately.
Assert accepted revision and digest agree across envelope, rollout leg,
render summary and review, with clearance revision matching. Assert required
project docs, four SVGs, summary and review equal their git HEAD bytes and
project status is clean. Retain SHA256 image hashes, coverage and project
commit in verification.json. Policies, checkpoints and traces remain outside
this repository; copied docs redact scratch/checkout absolute paths.

## Result

Script: exit 0, 1.52 s, sampled peak 235,945,984 bytes. Walk: exit 0,
17.07 s, sampled peak 1,054,818,304 bytes; no cutoff. Child legs all exit 0:
train 12.03 s, declare 1.32 s, rollout 1.45 s. Internal walk_seconds 16.9196 s
ends before final review serialization/commit. Acquisition 0.7027 s plus
rendering 0.5262 s = 1.2289 s. Whole-command sample is +1.8270 s versus
15.2430 s and +2.5527 s versus 14.5173 s, individual earlier samples only.
External monitor timing also includes sampling delay.

One local CPU iteration/four environments/training seed zero: trainer compute
1.1906 s, training reward/step -0.3801981509. Engine receipt verifies 32
witness samples at error 1.3841167412e-09 against 1e-4 tolerance. The 50-step
rollout (script-declared seed 3) reproduces reward -27.109384220927513.
Revision 6ebea031c261333a679d269c318298f4ccb826219dc9a0b56d86aefc18e0d089
and digest 0c74e228cc723dea636a707cbbc5debcae53604d7ee68a4eb9268346fe1e0d68
agree across the verified artifacts. All four images are nonblank and visibly
show the plate and arm in the correct initial pose; iso shows shaded depth.
The project is clean and its HEAD tracks images, summary, review and docs.
No best checkpoint or rollout trace is tracked; the accepted policy asset is
tracked by the existing product, not copied into this evidence commit.

Inventory: two uncatalogued synthetic components. Clearance retains base/swing
at distance 0 mm, common volume 0 mm³: one below-clearance pair, zero unknown
pairs, at 0.1 mm/1e-6 mm³ thresholds. This is contact in the initial pose,
not a swept check. Sections remain explicitly unavailable.

Full built-engine CLI gate: exit 0, 182 passed, zero skipped, 178.80 s.
Suite monitor 179.59 s, sampled peak 1,164,541,952 bytes, no cutoff. Existing
real toy training tests and local CPU remote-flag stand-in ran without SSH.
No GUI, remote checkout, cloud spend, build or engine/payload change occurred.
No product behavior/removal/work-item implementation changed, hence no ADR
or ROADMAP checkbox update applies. Export/check and diff whitespace checks
are required after minting, before the single evidence commit.

Next: named-plane section delivery and its separate walk integration remain
missing before the headless-review charter criterion can be ticked. No failed
leg was found. Three records now await the maintainer pass; this contributor
performs no reconciliation. The entire goal is not claimed complete.
Dispatch closed: 1 unit — fresh hinged-arm walk verifies committed named-angle review, bounded CPU training and preserved clearance findings.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: c5a0d72ddf792e6e9f69b373fbd54915092ef37e

## State Impact

- target: damp-moon-9297 — Fresh documented arm walk passes with four visually inspected revision-matched committed previews; clearance remains one touching pair and zero unknowns. Sections remain open.
- target: calm-peak-5247 — Separate fresh-project CPU rehearsal passes in 17.07 s at 1.055 GB sampled tree RSS, reproduces verified reward -27.1093842209; full CLI gate 182 passed with zero skips.
