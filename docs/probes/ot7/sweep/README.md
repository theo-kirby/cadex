# Joint sweep experiment — ot7 F3

Verified against source: 2026-09-14. [Cadex-new]

**Finch's sampled knee travel does not produce the shin-to-thigh contact
predicted in the ot6 README.** Both sides keep a 1 mm minimum gap and zero
common volume from 0° through 90° at 5° steps. This is a completed read-only
experiment, not the product swept checker or a passing-fit claim (ADR-348).

The critic requested the entire F3 implementation. This unit narrows that to
its geometric and runtime premise: reconstruct real solids from an accepted
snapshot, verify their solved pose, then measure one joint at a time. Inspection
currently reads published measurements and cannot produce new poses. The
worker's recorded global connector frames predate solving; using them directly
would measure the wrong motion on a general assembly. Establishing the correct
composition is one bounded experiment before changing publication and clients.

## Method

`probe.py` reads an unchanged copy of Finch's accepted attempt, revision
`b6862234556355f799591f314cde6b1a7caadb7d4659a0051d18a442c098912f`, in
`cadex-projects/ot7-finch-sweep`. It imports each source BREP and composes the
solved component placement with the BREP's own placement. All 406 pairs are
compared with the accepted static clearance before each sweep. Maximum distance
difference: **7.106e-15 mm**; maximum volume difference: **0 mm³**.

The existing `CadexDynamics.extract_tree` supplies the descendant branch. The
joint's coordinate is inverted from solved component and local connector
frames; a rotation about the solved parent connector moves every descendant
by the same rigid transform. Other joint coordinates remain at their solved
values. The check uses exact OCCT distance and common volume, never proxy
contacts. Pair measurements invariant under that common rigid motion are
reused; every pair straddling the branch is measured at each sample.

The probe reports each pair's minimum distance, maximum volume and angle of
first sampled contact (distance ≤ 0.001 mm), scanning from the lower limit to
the upper. Contact already present at the lower limit is reported there. It
includes both endpoints; this is discrete sampling and can miss a collision
between samples. No inference of continuous clearance is made.

This experiment explicitly supports BREP components and tree hinges. It rejects
closed or coupled graphs and static joints; it does not pretend those were
swept. It does not require dynamics declarations or execute the design script.
`pose_witness.py` independently uses Finch's retained MJCF to check the same
component poses at **every sample**, resetting all other coordinates to the
solved keyframe before setting the selected hinge. Maximum discrepancy was
**1.422e-14 mm** in position and **2.221e-16** in rotation-matrix entries. No
physics steps or policy runs occur. Both tools read accepted data only.

## Known-answer fixture and bounds

Two unit spheres have centres on a radius-10 mm circle; the fixed centre is at
90° and the moving centre starts at 20°. Analytic first contact is
`90° − 2 asin(0.1) = 78.521659°`; the 1° sweep reports **79°**. The fixture
also verifies composition with a rotated and translated source and a nonzero
solved angle by checking common volume against an independently placed solid.

The pose budget is **73 samples per joint**, checked before measuring travel.
A request for 361 samples is rejected by the executable fixture. Each geometry
child has a **180 s wall-clock timeout**, including reconstruction and baseline
verification; `subprocess.run` kills and waits for the child on expiry, so a
stuck OCCT call cannot evade the bound. A separate sleeping FreeCAD child was
killed with a 0.2 s test limit in **0.202 s**. A timeout yields an incomplete
receipt, never a clearance claim. These are experiment bounds; no product
runtime bound has been installed.

## Finch measurements

| Joint | Range | Samples | Exact moving-pair queries | Sweep seconds | Whole child seconds |
|---|---:|---:|---:|---:|---:|
| hip_l | −60°…60° | 25 | 4,750 | 57.650 | 62.705 |
| knee_l | 0°…90° | 19 | 1,482 | 20.047 | 25.387 |
| hip_r | −60°…60° | 25 | 4,750 | 57.919 | 63.142 |
| knee_r | 0°…90° | 19 | 1,482 | 19.642 | 24.935 |

Every result has 406 pair rows. Each sweep reports 12 pairs with common volume
over 1e-6 mm³ and 40 touching pairs. No previously non-overlapping pair begins
overlapping at the sampled poses. The 12 overlaps already exist at the solved
pose: ot6's fit probe exempted thread engagements, whereas F2 does not excuse
an overlap merely because contact is intended. This experiment does not apply
F2 intent checks and does not call Finch fit-passing.

For `thigh_l_link`/`shin_l_link` and `thigh_r_link`/`shin_r_link`, the minimum
distances are respectively 0.9999999999999822 and 0.9999999999999893 mm, maximum
volume is 0 mm³, and first contact is null. The ot6 README's “past about 60°”
sentence was a prediction, not a measurement. The F3 expectation of a contact
angle on this retained Finch revision is therefore not supported by these
samples. There is no invented angle in this receipt.

## Reproduction and evidence

Copy `script.py`, `script.json` and the entire accepted staging directory from
read-only `ot6-finch` into `ot7-finch-sweep`; do not rewrite or re-accept anything.
From the checkout, with `PROJECT` pointing at that copy:

```bash
pixi run python docs/probes/ot7/sweep/probe.py "$PROJECT" "$PROJECT/evidence/sweep"
pixi run python docs/probes/ot7/sweep/pose_witness.py "$PROJECT" "$PROJECT/evidence/sweep"
```

The first real run's children completed, but OCCT progress text prefixed the
result marker on the same line. The old parser reported errors despite native
exit 0. The corrected parser finds the marker within the stream and decodes
one JSON object. `probe.py --collect "$PROJECT/evidence/sweep"` recovered all
four completed results from the retained logs, exit 0, without repeating the
geometry. Both the prefixed marker and absent-result cases are asserted by the
final fixture, which was rerun successfully after the parser fix. The initial
full driver exited 1; recovery, independent pose witness and final verification
exited 0. This is not a claim that the initial full driver exited cleanly.

`summary.json` records the input digests and unchanged-input assertion. A final
comparison verified every listed input against both the copy and original:
script, accepted identity, result and all 29 source BREPs matched. No actor
design edit, acceptance change, new dependency or build occurred. No engine,
CLI, shell or packaged suite was rerun for these probe/document changes. F9's
recorded CLI telemetry failure remains open.

All large receipts and logs stay under
`cadex-projects/ot7-finch-sweep/evidence/sweep/`:

| Artifact | SHA-256 |
|---|---|
| summary.json | `5f09108fab07f69ece3b57a1571ec23339d3851e3a52e995eae94d076af24f26` |
| fixture.json | `626926d7454ca2b7c7ea98756d44382c7c1961bfc0d692ea2756bd4550fb8462` |
| hip_l.json | `c8cb396a2b208cfb538216e11b3bf61a7232a8b7398814fe325b3c1f181de956` |
| knee_l.json | `09361c954466a8462ae7bdece78e1babb35937a6fafb6deb84d997a144f548ac` |
| hip_r.json | `c047cb23ab8a33112fbf98a25bb1f6cb2e92053d62f6a9a5a95a2de54ea9b282` |
| knee_r.json | `82878a2e2451d49f0fb922edce85edbc131646a914ee165830a9155b89bce034` |
| pose-witness.json | `72dbc8d3cc7f943d63da8574497b5d58afca628069f887f2df9da862a6060494` |
| final-verification.json | `bca1819e006bb3eb499c47157dcf26e4d4db77ef04c4ac666ba2d8f572b54baf` |
| hip_l.log | `1adcd6a1d01e58c7a99a952692e148418df64b95270c3cd567941342a650198c` |
| knee_l.log | `419eebddb30e027764f0b7aa9f67b3de2f4ad99045dabd82511e16f89dceb96a` |
| hip_r.log | `c2cc9688fcb1dcf5234e196cab072aa8688b9214f837f54d4fcfddf2a6e9d5b2` |
| knee_r.log | `d277d46c667f526624466bc32dcfc2e91b4ac3df959af6c3ea28cb6fbfbde69b` |

**What this experiment left open** was product publication, agent inspection,
`cadex clearance --sweep`, a declared sampling policy, suite-integrated
known-angle tests and product runtime bounds. ADR-349, ADR-350 and ADR-351
installed those; the section below is the product checker run on Finch.
General limited-joint semantics still need care: holding every other coordinate
fixed can be incompatible with a closed or coupled graph, and the product
reports such graphs `incomplete` rather than silently severing constraints.

## Product measurement — one product-agent turn on a Finch copy

The charter forbids the actor editing a design in an `ot7-*` project, so the
product checker was requested through the product agent itself. A fresh copy
of read-only `ot6-finch` (everything but its `evidence/` and `runs/`
trees) was made at `cadex-projects/ot7-finch-product-sweep`, and one
`./cadex -p` turn was given
[`finch.product-sweep.prompt.txt`](finch.product-sweep.prompt.txt)
(sha256 `d15a271942951f5b69277cb765921b46986da7543593e0ec6c45bb6ebbf3a407`). It asks
for one script change, a 5° sweep declaration, one coarsening to at most 10°
if and only if the budget is exceeded, and the published report read back.
This prompt is a measurement request, not one of the frozen design
continuations, and it names no defect. The turn ran under model
`claude-fable-5`, exited 0, and its only script edit is
`sweep_step_degrees=` on `assembly.assembly(...)`; every other line of the
script is byte-identical to ot6-finch's.

Read-only `cadex clearance --sweep` on the copy before the turn reported
`status: unavailable` at the ot6 revision `b6862234…`. The turn accepted two
revisions, each read back here from the stored `result.json`, not from the
agent's reply:

| Revision | Step | Coverage | hip_l | knee_l | hip_r | knee_r | Total |
|---|---:|---|---:|---:|---:|---:|---:|
| `a2fb2c07…` | 5° | incomplete | 25 samples, 66.2 s | 19, 27.3 s | 25, 75.1 s | **runtime budget exceeded** at 11.3 s | 180.0 s |
| `61303150…` | 10° | complete | 13, 35.7 s | 10, 16.2 s | 13, 36.2 s | 10, 16.3 s | 104.4 s |

Bounds in force: 90 s per joint, 180 s shared, 73 poses, 2,000 pairs; ranges
−60°…60° for the hips and 0°…90° for the knees, initial 0°, solved-pose
agreement true on every completed joint. The 5° run is the enforced bound
doing its job: three hinges consumed 168.6 s of the shared 180 s and the fourth
was cut off and reported, not skipped. The engine and CLI suites were running
on the same 32-core machine during both builds (load average 24 at the 5° build), so those
elapsed times are an upper bound on an idle box; the read-only experiment above
measured 24.9–63.1 s per joint idle.

Every completed joint reports all 406 pairs. In each, 40 pairs have a first
contact and every one of them is at the joint's lower limit (−60° or 0°): the
permanent seatings and 12 thread engagements at ≤ 7.854 mm³, present at the
solved pose and at every sample. **No pair first touches inside any range**,
at either step. The knee pairs: `thigh_l_link`/`shin_l_link` and
`thigh_r_link`/`shin_r_link` keep a minimum distance of 1.0 mm
(0.9999999999999964 at worst), 0 mm³ common volume, first contact null, at 5°
and at 10°. The product checker therefore agrees with the experiment: the
knee-to-thigh contact the ot6 README predicted is absent on this revision, and
the angle F3 asked for is reported as none, not invented.

One discrepancy between the agent's words and the measurements is recorded
rather than smoothed over: the reply says "exactly the same 44 pairs report a
first contact", while the published sweep has 40. The other four are the four
bearing-stub pairs, which sit at their designed 0.05 mm radial clearance in the
static report (below the default minimum, so among the 44 static failures) and
never touch through the sweep. The numbers the agent quoted for coverage,
timings and the knee pairs match the published data.

Evidence stays in the project copy under `evidence/`; `turn1.envelope.json`
is the CLI's `--json` reply, `turn1.stderr.txt` the tool trace and reply,
`turn1.transcript.jsonl` the agent CLI session (236 lines), and the two
`result.json` files are the accepted attempts under `script_artifacts/`:

| Artifact | SHA-256 |
|---|---|
| turn1.envelope.json | `8edd4d9ac77369ce82b3968d2360b20a16188f3d91cb370a6f6d4ae440ee54cc` |
| turn1.stderr.txt | `64fb678ed041f322664611e7e7d662b2068d0881a31c0c51dab8bb71068fb743` |
| turn1.transcript.jsonl | `d0c31e1c78511289b48e300a2fb2744c636159f4ba0171c6d0246f5333b3f4c6` |
| a2fb2c07…/result.json (5°) | `9b2ce9c67c42874cf21f18fd01f9ca50243cc460d9807dc814fb93a1000e6c2b` |
| 61303150…/result.json (10°) | `c9952aa3b10bf6564867def8121eb578750ea0e7d488eed14a61a1e3fc8f0d4f` |
| docs/clearance-sweep.md after the turn | `06a686ed4fa3c39ed5946c21e3aeaec14b93caf029a8bbb20b9436e921971fad` |
| script.py after the turn | `5a73e48749c8a7112b0f347ee19c8d49f6bd13a8d97220246e95f8951b1525d4` |

Gates run in the same iteration against the committed source, after one
`pixi run build-engine` and `stage-engine`: engine 2,127 passed and 53
skipped; CLI 641 passed and 1 skipped; packaged lifecycle 18 passed.
