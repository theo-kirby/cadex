---
node_id: c1af8444-7e19-5def-887c-dafca2958a17
slug: misty-trail-1655
title: Retained training export parts visible with honest pose limits; fresh biped browser interaction verified
created_at: '2026-09-12T18:20:08+00:00'
parents:
- merry-star-6951
summary: ''
artifacts:
- docs/HEADLESS-BIPED-REVIEW.md
---
## What

Fixed the missing-model path for retained training exports (ADR-290).
When a run has no recorded rollout trace but names a permitted model_xml
and revision/digest, the dashboard now serves the STL parts beside that
training model. It labels them as individual parts at identity with no
recorded assembly placements, not a solved pose. Added a historical browser
regression and real fresh-biped private-address orbit/zoom evidence.

## Why

Follows the critic's request to trace probe2's missing model and advance D2.
Probe2's successful params export retained eight STL parts beside the exact
model_xml its record names. Its old staging directory has been pruned and
the accepted revision has since moved. The reader previously checked only
rollout meshes or matching current tessellation, leaving these retained
exports invisible. I chose the smallest honest fix: expose actual parts,
explicitly without a guessed assembly pose. I did not reconstruct the old
assembled training view from today's script, infer component links from
names, or transplant checkpoint20's pose into probe2. The assembled-training
snapshot gap remains open; the separate retained checkpoint20 model supplies
real assembled-biped interaction evidence without pretending it is probe2.

## Method

Updated cli/cadex_cli/review_server.py and the existing run mesh allowlist.
Recorded export references must resolve within the run; missing/refused
exports remain unavailable. Symlinked STL files are not served. A missing
recorded rollout still refuses rather than falling through to training or
current geometry. The browser regression selects a historical training
export, checks identity/limitation labels, drags and zooms the WebGL model,
compares served bytes, asserts read-only behavior, and injects missing,
symlinked and escaping references. docs/CLI.md and the biped lifecycle report
document the behavior and limitation. No new dependency or protocol/payload,
shell or engine change; no build needed. No generated roadmap/state edit.

Real check command, from the product checkout:
PYTHONPATH=cli:cli/tests pixi run python "$PROJECT/evidence/check-training-parts.py" "$PROJECT"
where PROJECT is the external cadex-projects/ot5-biped project. The harness
binds the review server to tailscale ip -4 and opens that address in headless
Chromium. It only reads project/trainer inputs and controls its own browser
and server lifetime. No engine or trainer launch, no telemetry write.
External project commit 87da252 retains the script and
 evidence/training-parts-result.json; large existing artifacts stay outside
this repository.

Probe2 revision 6ab8a1d090c812865d70d5d6c9300907dc1076cb19ec3f2d4885a44baeaa12c8,
digest 850acf23a05ade2fa76275a6484caaefc9e2d22230fb002ead681c533e530697
matched its run and successful original export envelope. Eight parts, 96
triangles; orbit yaw 0.8 to -0.2 and pitch 0.5 to 0.9; zoom distance
658.2674 to 459.2576 mm; 219902 non-background pixels. Every mesh response
matched the run's STL bytes. Manifest, run record, progress and all eight
STLs had unchanged hashes across observation. No second-device test.

Then selected the assembled biped at probe2-checkpoint20's own revision
3d28c70c890f79ff6b98ef314dc8bf672746311aae5b3d23b845c89808c387f8,
using its existing retained rollout meshes/mapping/first frame. Eight
components, 96 triangles; same yaw/pitch deltas, zoom distance 731.7874 to
510.5507 mm, 135542 non-background pixels. No historical rebuild.

## Result

D2 advances: retained historical training exports are visible, and real
fresh-biped orbit/zoom passes for both exported parts and the assembled
checkpoint playback. D2 stays open for retained assembled training poses
and complete model/spec history evidence. The patch does not recover the
missing probe2 placement map or its overwritten document snapshot. Future
recording should retain those before training. No claim of D2 completion.

Validation passed: pixi run python -m pytest cli/tests/test_review_server.py
(24 passed, 1 skipped, 51.09 s); pixi run python -m pytest cli/tests
(359 passed, 1 skipped, 326.03 s); pixi run test-engine (2103 passed,
54 skipped, 302.01 s). The focused/default suite skip is the opt-in
private-host fixture; the real private-address browser check ran separately.
git diff --check passes.

The unreconciled tail grows to three records. This work dispatch followed
the explicit no-reconcile instruction and left all state nodes and generated
views untouched. Assumption: the model_xml-relative STL exports belong to
the recorded run just as existing rollout-relative exports do; no new
cryptographic artifact manifest is introduced. No new dependency.
Dispatch closed: 1 unit — expose retained training export parts and verify fresh-biped browser interaction without rebuilding geometry.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 99ab13ea2ae4b37356d7ee9453b6a1e078ac9972

## State Impact

- target: shy-meadow-0959 — ADR-290 exposes run-local training STL parts beside recorded model_xml with revision/digest and explicit missing-assembly-placement labels. Browser regression and real private-address probe2 parts plus assembled checkpoint20 orbit/zoom pass without rebuilding or writing telemetry. D2 remains open for retained assembled training poses and complete spec/history evidence; full CLI and engine suites pass.
