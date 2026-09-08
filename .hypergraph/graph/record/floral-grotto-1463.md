---
node_id: f910be1c-17c5-5215-9f79-df9949537880
slug: floral-grotto-1463
title: Fixed-stroke quill seed reference preserves artifacts and verifies comparison identities
created_at: '2026-09-08T20:50:45+00:00'
parents:
- humble-sky-8445
summary: ''
---
## What

Ran one provider-free stroke-60 quill walk with training seed 0 and recorded its exact reference in docs/CLI.md, the ROADMAP checkbox, and the durable project's PROGRESS.md (project commit f21ae44). No mechanism or runtime change.

## Why

Follows the overseer's explicit first short unit and advances the charter's "The walk exists and is tested headlessly" and "The agent can see its work without a screen" criteria, targeting crisp-reef-5607, calm-peak-5247 and damp-moon-9297. Existing walk evidence stands; this supplies current identity-bearing evidence at fixed geometry before the selected seed continuation. Assumed the existing accepted stroke-60 parameters were authoritative, verified against prior review and exported inputs; no design prompt, parameter edit, provider-capacity probe or remote dispatch.

## Method

On the durable ot4-quill project, ran `JAX_PLATFORMS=cpu ./cadex walk --project "$PROJECT" --out "$PROJECT/runs/stroke60-seed0-33" --name quill_stroke60_seed0_33.cxpolicy --iterations 5 --envs 16 --seed 0 --timeout 600 --leg-timeout 120 --json`. External watchdog sampled process-tree RSS every 0.2 s with 2.9 GB / 850 s cutoffs. Explicit root .gitignore exclusions follow the default asset-policy negation; git check-ignore and ls-files verified fresh paths before dispatch. No generated output is committed by this unit. Older tracked output is preserved.

Recomputed objective and action SHA-256 identities from canonical comparison metadata; verified training seed 0, rollout seed 7, CPU receipt, unchanged full parameter map, byte-identical MJCF and identical full task JSON against stroke60-iterate29. Script differs only in policy filename and digest. All three legs exit 0; 56 top-level engine/source Python files match. Verified all four review paths and all four named-view files exist. Hashed all 48 prior run files before/after, checked project ancestor preservation and changed-file scope, and checked new run/policy/review paths absent from committed tree. An initial overbroad assertion against all review files detected seven historical tracked files; restricting it to the new revision confirmed no new output was committed, with old files untouched.

## Result

Exit 0 in 24.835810 s wall (walk reports 24.685678 s), peak tree RSS 1,986,134,016 bytes. Trainer 3.773088 s, reward/step -1.019690990448, witness error 2.091506422867e-08. Verified rollout total reward 175.487211145051, travel 30.078469436328 mm / 0 degrees, 200 steps / 4 s. Objective v1:ddee1f6a0bae7c4753c06a17fa09dd3db9799de30d823c4e4586e41868a937dc; actions 770b4e2f0899853fed23b8727ea08f607ceef3c383189357f27c02179cc30882. Prior evidence remains unavailable (legacy row). Exact reward/travel agree with the previous seed-0 run; displayed deltas use rounded prior rows and do not indicate improvement.

Four renders exist; XZ section at 3.125 mm cuts housing and misses quill; inventory lists two uncatalogued components; clearance names housing/quill intersection 960 mm³, no unknown pairs. Generated evidence remains local under the project's runs/stroke60-seed0-33 and review revision 68bc8e9dbfef…; no probe dump or machine path is added to the repository. All 48 prior run files retain bytes, project history and unrelated tracked content remain intact, project tree is clean after f21ae44.

Required CLI gate: `pixi run python -m pytest cli/tests` — 245 passed in 229.30s (0:03:49). Full output remains local at `/tmp/cadex-iteration33-cli.log`. `git diff --check` passed. Documentation-only change: no build required.

No walk/scaffold behavior changed, no removal or direction change, so no scaffold edit or ADR is needed. These criteria already carry working implementation evidence; this run does not establish learned control or live provider understanding. Next is exactly the selected seeds 1, 2 and 3 at unchanged geometry/objective/actions/rollout seed and bounds, stopping at the first failure or identity mismatch; no additional seeds follow automatically. The 30 mm action midpoint remains a confound. Three unreconciled records including this one are left for the separate maintainer; no reconciliation performed.

Dispatch closed: 1 unit — establish the fixed-geometry quill seed-0 reference with current identities and retained artifacts.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: 295c7609f583303d0ffebccc8ac32262e5b6a285

## State Impact

- target: crisp-reef-5607 — Fixed-stroke CPU seed-0 walk passes all legs with current objective/actions identities, seed 7 rollout, 24.84 s wall and 1.99 GB peak; seed continuation remains.
- target: calm-peak-5247 — Quill current reference and project PROGRESS preserve prior artifacts and legacy identity limits; reward 175.487211145051 and travel 30.078469436328 mm / 0 degrees.
- target: damp-moon-9297 — All four reference review outputs verified locally; known 960 mm³ intersection and empty quill section remain explicit.
