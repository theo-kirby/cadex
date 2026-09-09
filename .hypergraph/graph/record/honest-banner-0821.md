---
node_id: d50cb324-805e-520c-9a23-78aa49b9c538
slug: honest-banner-0821
title: Quill seeds one through three measure fixed-input lifecycle spread
created_at: '2026-09-08T21:03:05+00:00'
parents:
- first-creek-7901
summary: ''
---
## What

Measured exactly training seeds 1, 2 and 3 against the existing stroke-60 seed-0 quill reference. Added individual results and descriptive four-seed ranges to docs/CLI.md and the durable ot4-quill project's PROGRESS.md (project documentation commit 76c2d9a); ticked the corresponding ROADMAP item. No runtime or scaffold change.

## Why

Executes the selected bet first-creek-7901 and overseer instruction, advancing the charter's "The walk exists and is tested headlessly" and "The agent can see its work without a screen" criteria through fixed-input lifecycle/review evidence. Targets crisp-reef-5607, calm-peak-5247 and damp-moon-9297. Assumed accepted stroke-60 geometry authoritative; verified it against seed 0. No provider, remote dispatch, geometry edit, additional seed or new committed harness.

## Method

For N = 1, 2, 3, sequentially ran `JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/stroke60-seedN-34" --name quill_stroke60_seedN_34.cxpolicy --iterations 5 --envs 16 --seed N --timeout 600 --leg-timeout 120 --json`, substituting N in names and flags. Reused the reference's local external watchdog: process-tree RSS sampled every 0.2 s, cutoffs 2.9 GB / 850 s. No cutoff fired. Checked each run before the next dispatch.

Explicit root run/policy exclusions follow the default policy negation. Before dispatch, check-ignore and ls-files confirmed fresh paths excluded and neither tracked nor staged. Compared full parameter maps, byte-identical exported MJCF and task JSON, recomputed canonical objective/actions hashes and requested training seeds in training/review metadata, and rollout seed 7. Scripts differ only in policy name/digest. Verified all four review outputs and every named render file, all preceding run hashes, prior stored policy hashes, ancestor history, unchanged older script-history source bytes and unrelated tracked scope. New run/policy/review paths are absent throughout all newly created project commits. Verification initially omitted expected script_history additions from its allowed changed-file scope; corrected that local assertion and checked existing history bytes separately, with no product failure or input mismatch.

## Result

All nine legs exit 0. Results (reward; translation mm / rotation deg; monitored wall s; peak tree RSS bytes):

- Seed 0 reference: 175.487211145051; 30.078469436328 / 0; 24.835810; 1,986,134,016.
- Seed 1: 175.935971673601; 31.421759939733 / 0; 23.783088; 1,994,547,200.
- Seed 2: 170.952826823611; 31.360988060147 / 0; 24.625217; 1,986,662,400.
- Seed 3: 172.081298535925; 31.085486620484 / 0; 25.470796; 1,997,832,192.

Four-seed reward range 170.952826823611–175.935971673601 (span 4.983144849990); travel 30.078469436328–31.421759939733 mm (span 1.343290503405); angular travel 0. The 30 mm target remains the action midpoint; near-zero normalized actions already command it. These are descriptive ranges, not significance, a winner or learned improvement. Each rollout is 200 steps / 4 s. Trainer durations 3.628307/3.878131/3.883964 s, reward/step -1.016377091408/-1.313315391541/-1.432229399681, witness errors 2.700e-08/2.926e-08/3.163e-08.

Objective v1:ddee1f6a0bae7c4753c06a17fa09dd3db9799de30d823c4e4586e41868a937dc and actions 770b4e2f0899853fed23b8727ea08f607ceef3c383189357f27c02179cc30882 match seed 0. Comparisons explicitly cite runs/stroke60-seed0-33/review.json and runs/stroke60-seed{1,2,3}-34/review.json. The latter directories hold local walk/monitor/review receipts; no dump is committed. All four review calls succeed per run: four render views, XZ section at 3.125 mm missing the quill, two uncatalogued components, known 960 mm³ housing/quill intersection and no unknown pairs. Each run preserves all prior run bytes (75/102/129 files). Project history and unrelated content remain intact, with generated output excluded and project tree clean.

Required CLI gate: `pixi run python -m pytest cli/tests` — 245 passed in 231.30 s, no skips. Full local output: /tmp/cadex-iteration34-cli.log. `git diff --check` passed for repository and project. Documentation-only unit, no build required. Hypergraph export/check passed before recording; repeated after minting.

No removal, direction change or walk/scaffold behavior change; no ADR or scaffold edit required. Existing working criterion evidence stands; nothing further is required from this seed measurement before those criteria can be ticked, while learned control and live provider understanding remain unproven. Next: this measurement direction is exhausted; no extra seeds or harness. The planned project-history live iterate remains capacity-conditional, with no probe or wait authorized. No reconciliation or state edits performed.

Dispatch closed: 1 unit — measure the three selected fixed-geometry seed continuations and preserve descriptive evidence and artifacts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 18a252798a15d4af6cfc8da14df4c4fabdc15114

## State Impact

- target: crisp-reef-5607 — Three fixed-input CPU walks pass all legs within 26 seconds and 2 GB each; CLI gate 245 passed; seed direction exhausted.
- target: calm-peak-5247 — Four-seed quill reward range 170.952827–175.935972 and travel 30.078469–31.421760 mm / 0 degrees, identities fixed and action-midpoint caveat retained in docs and project PROGRESS.
- target: damp-moon-9297 — All four review outputs verified for each seed; known intersection and empty quill section persist, with new generated artifacts excluded throughout project history.
