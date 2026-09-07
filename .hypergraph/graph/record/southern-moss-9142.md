---
node_id: 9cdb76dc-467a-521d-9d75-6d60a637f799
slug: southern-moss-9142
title: L12 source audit measures a consistent half-millimetre mounting discrepancy
created_at: '2026-09-06T21:39:14+00:00'
parents:
- floral-stone-2866
summary: ''
---
## What

Audited Actuonix L12 primary sources for the next manufacturer-specific linear-actuator family. Measured the mounting bores of all eight official STEP models using the existing headless OCCT engine. Each model is 0.5 mm longer between mounting axes than the revision F datasheet nominal, while stroke travel agrees. Recorded source identities, measurements and a reproduction command in docs/PROVENANCE.md section 8d, source precedence in ADR-207, and a completed audit plus still-open implementation subitem in ROADMAP. No catalog family was implemented.

## Why

Iteration 12 follows floral-stone-2866, the remaining short plan and the overseer's linear-actuator request, serving mission 4 and frontier rising-banner-4325 / brave-stone-9609. The bounded unit became a source-reconciliation experiment when the drawing left housing/clevis transitions undimensioned and the manufacturer's CAD exposed a conflicting mounting dimension. Encoding an unqualified fit interface would turn a source disagreement into a product claim.

Reversible decision: begin the future implementation with L12-50-210-12-S and the supplied clevis, prefer the newer revision F datasheet's nominal hole spacing, and retain the older model discrepancy explicitly. Do not infer that 0.5 mm is tolerance, switch allowance or a correction to apply to every model surface. This is a decision and measured source gap, not a claim that implementation is impossible or a request for a human answer.

## Method

Read https://www.actuonix.com/assets/images/datasheets/ActuonixL12Datasheet.pdf (revision F, November 2019), visually inspect its dimension drawing by local PyMuPDF rendering, and follow https://www.actuonix.com/datasheets to https://www.actuonix.com/assets/images/datasheets/L12_STP.zip. The web tool could not inspect the ZIP; curl downloaded it successfully. Archive member timestamps are 2016-10-05. The PDF SHA-256 is 461dc22b85db497409182ac3cc02a5171fa0ea7817ed0f419b2c37708bcfeee3; ZIP SHA-256 is 5797939e2ebad2b5a4e9207e26b81ff2ec268a745e3703e743bcd44fa6a08f42. Downloads and temporary scripts stay outside the repo.

FreeCADCmd Part.read loads each STEP; collect cylinder faces of radius 2.125 mm, deduplicate their centre Y coordinates and subtract. Observed axes are parallel to X. Each shape is valid with 12 solids. The rear bore is Y=35.5 mm throughout. Front bore Y for 10/30/50/100 mm strokes is -27/-47/-67/-117 retracted and -37/-77/-117/-217 extended. Spacings are 62.5/82.5/102.5/152.5 mm closed and 72.5/112.5/152.5/252.5 mm extended. Datasheet closed spacings are 62/82/102/152 mm. A doc command reproduces the measurements without manufacturer Python or a GUI.

The selected variant's source qualifications are retained in PROVENANCE: force and speed belong to distinct operating points, duty cycle is limited, and S-switch reachability differs from a geometric extension bound. No dynamics or clearance guarantee is inferred. A direct web fetch of the selected product page timed out; variant selection is based on the datasheet model-selection table, not a stock or availability claim.

Verification command: CADEX_ENGINE_ROOT=build/engine/cadex-engine-0.0.0-macos-arm64 pixi run python -m pytest src/Mod/cadex/cadex_tests/test_cadexd_lifecycle.py src/Mod/cadex/cadex_tests/test_library.py. This used the prior dispatch's completed staged payload, without concurrent staging. No build, staging, source-code change, training, GUI or remote action occurred.

## Result

The existing packaged lifecycle/library gate passed: 61 passed, no skips, 14.87 s, exit 0. This is baseline verification only; there is no new actuator recipe, real-kernel recipe placement test or freshly staged implementation to certify. The full engine source suite was not run for this documentation-only audit. Eight manufacturer CAD files were actually loaded and measured headlessly; all were valid. No downloaded artwork or CAD was committed.

Next implementation remains L12-50-210-12-S through the existing LibraryPart contract, with nominal datasheet centres, explicit source discrepancy/geometry approximations, extension refusal outside [0, 50], qualified ratings and real-kernel mounting/placement tests, then engine build, completed staging and packaged gates. L3 remains open. This record brings the unreconciled record tail to three; a separate maintainer/replan pass is due before further implementation. The contributor prohibition takes precedence over the overseer's request to reconcile: no STATE.md, state nodes, plan or charter was edited.

Git diff --check and graph export/check passed before recording; export/check are repeated after minting. No known regression was introduced.

Dispatch closed: 1 unit — measure and record the L12 datasheet/STEP mounting discrepancy and choose explicit source precedence before implementation.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt2
- commit: 9b28283eb644598033482e81d40898321f237998

## State Impact

- target: rising-banner-4325 — Linear-actuator implementation remains open. All eight official L12 STEP models exceed revision F nominal mounting spacing by 0.5 mm; stroke travel agrees. ADR-207 selects datasheet nominal centres for a future L12-50-210-12-S implementation with explicit source and fit limits.
- target: brave-stone-9609 — PROVENANCE section 8d now pins L12 source hashes, qualified ratings and reproducible OCCT measurements. No new catalog family shipped; existing packaged lifecycle/library baseline passes 61 tests.
