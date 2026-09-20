---
node_id: b559fe8b-feec-54a0-b127-8753719a1965
slug: amber-lantern-9712
title: 'F3 experiment: bounded exact-solid Finch sweeps and known-angle fixture; predicted knee contact absent'
created_at: '2026-09-14T18:48:51+00:00'
parents:
- crisp-ember-0302
summary: ''
artifacts:
- docs/probes/ot7/sweep/README.md
- docs/probes/ot7/sweep/probe.py
- docs/probes/ot7/sweep/pose_witness.py
---
## What

Completed one bounded F3 geometry experiment (ADR-348), with executable read-only probes and a user-facing receipt at docs/probes/ot7/sweep/README.md. Four exact-BREP hinge sweeps on an unchanged copy of accepted ot6-finch finish within a 180-second process bound per joint. A known-angle fixture and an independent MJCF kinematics witness validate the pose composition. This is experimental evidence, not a product swept-check implementation.

## Why

Targets curious-quill-9036, following F2 record crisp-ember-0302. The critic asked for full F3 implementation and exposure through agent inspection and cadex clearance --sweep. I narrowed that request to its geometric and runtime premise to complete one unit: inspection currently only reads published data, and stored global connector frames predate solving. A full producer/publication/client change plus real-project measurement spans a larger unit. No partial product implementation or stub was added. The experiment determines whether the existing tree and accepted geometry can support the sweep and whether the charter's predicted Finch contact is present. The latter prediction does not survive this measurement. F9's telemetry failure remains open and no owner dashboard file was touched.

## Method

Copied script.py, script.json and the complete accepted staging directory from read-only ot6-finch to cadex-projects/ot7-finch-sweep. Read accepted revision b6862234556355f799591f314cde6b1a7caadb7d4659a0051d18a442c098912f without executing, rebuilding or accepting its script. Compose each source BREP's placement with the solved component placement; compare all 406 pairs against published clearance. Extract the existing CadexDynamics spanning tree and rotate the whole descendant branch about the solved parent connector at each joint sample, preserving every other joint coordinate. Only cross-branch pairs require new exact distance/common-volume queries. Reports include every pair's minimum distance, maximum common volume and first sampled contact angle, scanning low to high with endpoints. The explicit experiment support is BREP tree hinges; closures/couplings are rejected, not silently cut.

Known-answer fixture: two unit spheres on a radius-10 circle first contact analytically at 78.521659 degrees; a 1-degree sweep starting at a nonzero solved angle reports 79 degrees. Rotated/translated source composition is checked against an independently placed solid. The 73-pose cap rejects 361 samples. A subprocess timeout kills and waits for a sleeping FreeCAD child in 0.202 seconds with a 0.2-second test limit. The real joint process limit is 180 seconds, including baseline measurements. Finch's independent pose_witness.py resets its accepted MJCF solved keyframe, sets one hinge and uses forward kinematics at every sample: all component poses match the exact-solid sweep's subtree transform.

Commands: pixi run python docs/probes/ot7/sweep/probe.py PROJECT PROJECT/evidence/sweep; after fixing the native-output parser, the same script with --collect PROJECT/evidence/sweep; pixi run python docs/probes/ot7/sweep/pose_witness.py PROJECT PROJECT/evidence/sweep. The initial full driver exited 1 because OCCT progress text prefixed the result marker on the same line, even though every native child exited 0 with complete JSON. Corrected parsing and collection recovered those completed results without recomputation, exit 0. Final fixture rerun verifies the prefixed marker and absent-result cases and passes. Retained logs, raw pair reports, final verification, input hashes and their digests are indexed in the receipt. No new dependency: FreeCAD, OCCT, existing engine tree utilities, numpy and MuJoCo already exist here. No physics rollout or training.

## Result

All 406 solved pairs agree before every sweep: maximum distance error 7.106e-15 mm, volume error zero. At 5-degree steps: hip_l 25 poses/4750 moving-pair queries/57.650 sweep seconds/62.705 whole-child seconds; knee_l 19/1482/20.047/25.387; hip_r 25/4750/57.919/63.142; knee_r 19/1482/19.642/24.935. Every process stays below 180 seconds. Independent MJCF witness maximum pose discrepancy is 1.422e-14 mm and rotation-matrix discrepancy 2.221e-16. Original and copied script, accepted identity, result and all 29 source BREPs retain identical digests.

Neither knee has shin-to-thigh contact over the sampled 0-to-90-degree range. Each minimum distance is 1 mm to floating-point precision, common volume zero and first contact null. No previously non-overlapping pair starts overlapping in any of the four sampled sweeps. Each sweep still has 12 overlapping pairs (the pre-existing thread engagements ot6 explicitly exempted) and 40 touching pairs. This is not a passing F2 fit claim, and 5-degree sampling cannot exclude between-sample contact. The ot6 README's prediction of knee contact past about 60 degrees and the charter's expected angle are not supported by this retained revision; report the negative result rather than invent an angle.

F3 remains open: no product producer/publication, agent sweep inspection, cadex clearance --sweep, product sampling declaration/bound, general limited-joint semantics or suite-integrated known-angle test was installed. Closed/coupled mechanisms cannot generally vary one coordinate while all others stay fixed and need explicit unknown reporting. Acceptance behaviour is unchanged. No build or engine/CLI/packaged suite was run for probe/document-only changes; F9 retains the earlier CLI telemetry failure, not a green-suite claim. No actor design edit, new project acceptance, dependency, policy training or generated-state edit. Graph export/check and one commit close this experiment. The unreconciled tail grows by one record; no reconcile was performed.

Dispatch closed: 1 unit — bounded real-solid joint-sweep experiment, with verified poses and Finch's predicted knee contact absent at sampled poses.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: 00da88dd6d5c96ab28ed8966857f01ffe0023f80

## State Impact

- target: curious-quill-9036 — Read-only F3 experiment validates solved BREP composition, known-angle first contact and all four Finch hinge sweeps under 180 seconds each. Both knees keep a 1 mm sampled shin-to-thigh gap, contradicting the predicted contact; product sweep publication and CLI/agent exposure remain open. See docs/probes/ot7/sweep/README.md.
