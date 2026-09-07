---
node_id: d2b805ce-05d5-57c6-a391-7ee86ef5eb1e
slug: square-path-1173
title: Walk review commits revision-bearing named-angle previews
created_at: '2026-09-07T23:41:06+00:00'
parents:
- nimble-beacon-7598
summary: ''
artifacts:
- docs/probes/named-angle/walk-review/README.md
- docs/probes/named-angle/walk-review/measurements.json
- docs/probes/named-angle/walk-review/cli-gate.log
- docs/probes/named-angle/walk-review/cli-gate.json
- docs/probes/named-angle/walk-review/refusal-gate.log
- docs/probes/named-angle/walk-review/arm-front.svg
- docs/probes/named-angle/walk-review/arm-iso.svg
- docs/probes/named-angle/walk-review/arm-right.svg
- docs/probes/named-angle/walk-review/arm-top.svg
- docs/probes/named-angle/walk-review/carriage-front.svg
- docs/probes/named-angle/walk-review/carriage-iso.svg
- docs/probes/named-angle/walk-review/carriage-right.svg
- docs/probes/named-angle/walk-review/carriage-top.svg
- docs/probes/named-angle/walk-review/arm-review.json
- docs/probes/named-angle/walk-review/carriage-review.json
- docs/probes/named-angle/walk-review/arm-summary.json
- docs/probes/named-angle/walk-review/carriage-summary.json
---
## What

Integrated the delivered named-angle renderer into `cadex walk` review using
its existing engine session. Display is rebuilt and snapshotted before later
inventory/clearance requests can invalidate attempt buffers. Walk images and
summary live under `review/render/<accepted-revision>/`, retaining earlier
revision references. The review contains availability, revision/digest,
front/top/right/iso paths, approximation/limits and acquisition/render timings;
`walk_seconds` measures entry-point dispatch through the review session.
Inventory and clearance remain intact. Sections are explicitly unavailable.
Updated project scaffold, shared mode-artifact table, CLI/MuJoCo docs, ADR-239
and the ROADMAP checkbox. Added real image, commit and CPU mode-parity assertions
plus refusals for malformed acceptance and a rebuild differing from rollout.

## Why

Advance charter criterion “The agent can see its work without a screen”
(damp-moon-9297), short-plan item 1 from nimble-beacon-7598, serving missions 6
and 2. Remove the caller's manual render leg by reusing existing bounded code.
The overseer requested a reconcile/planner pass first; the explicit work-iteration
prohibition overrides that request. No state node, STATE.md, plan or charter was
edited. The checkpoint had one unreconciled record, so a maintainer must decide
its own due pass. No human decision or permission was needed.

## Method

Used existing built engine, training venv and public walk entry point via
`pixi run python -m pytest cli/tests -q`, in a fresh temporary basetemp.
Full suite includes real linear-carriage, arm baseline and arm changed-policy
walks, then local/remote-flag parity with a real local CPU dispatcher stand-in.
Each lifecycle run uses one training iteration/four environments. An external
monitor samples trainer RSS every 0.25 s and stops trainers above 3 GiB or 900 s.
No SSH, remote checkout, GUI, cloud spend, engine build or payload change.

Tests decode actual embedded PNGs and assert nonblank pixels, angles,
revision agreement, limits/approximation and tracked summary/image artifacts.
Parity compares all four decoded images exactly. Visually inspected all eight
arm/carriage views from the focused run and verified final evidence images have
identical PNG bytes. Evidence and logs are under
`docs/probes/named-angle/walk-review/`; its README explains filenames, timing
boundaries and reproduction. No policies/checkpoints/traces copied into this repo.

## Result

Full built-engine CLI gate: exit 0, **181 passed, zero skipped, 178.77 s**.
External monitor: 179.3348 s, eight trainer processes, maximum sampled RSS
991,632 KiB (968.4 MiB), maximum observed training lifetime 8.835 s, no cutoff.
An initial development run failed on the missing timer import; fixed before
passing gates. Focused walk gate: 21 passed in 83.12 s. After full-suite
collection the refusal test gained its second parameter (rebuilt revision
mismatch); final refusal subset: 2 passed, 20 deselected, 1.92 s. No production
behavior changed after the full gate started. No baseline failures remain.

Final arm baseline: 15.2675 s through review, 0.6532 s acquisition, 0.5205 s
rendering; reward -27.1093842209. Arm iterate: 16.6549 s, reward -55.3480045452.
Carriage: 14.3907 s, 0.6915 s acquisition, 0.6354 s rendering; reward
-24159.1953563045. Local parity 15.2567 s; CPU remote-flag stand-in 15.5678 s;
images identical and reward -27.1093842209 in both. Arm retains one
below-clearance pair and zero unknowns; carriage zero offending/unknowns.

Added acquisition/render work is 1.174 s arm and 1.327 s carriage. These are
individual samples, not a regression benchmark against earlier 15.2430 s and
14.5173 s whole-command samples: walk_seconds excludes review serialization and
final progress/commit, and earlier samples had external timing boundaries.
Project commits track four images, summary, review and docs; failed render
attempts expose no new successful review even when old files remain on disk.

No engine/protocol/payload/shell edit, so no additional zone build/gate applies.
git diff --check and pre-record hypergraph export/check passed (zero violations
or warnings). Post-mint export/check must pass before the single work commit.
This adds the second unreconciled record after the checkpoint, not a state edit.

Next: short-plan item 2, a separate documented fresh-project local toy walk
rerun with external timing. Named-plane sections and their walk integration
are still missing before the charter headless-review criterion can be ticked.
The whole goal is not claimed complete; no broken leg remains from this unit.
Dispatch closed: 1 unit — walk review now commits revision-bearing named-angle previews with tested real-mechanism and CPU mode parity.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 5d77ff1fea4cf181c9f5cc54dad67e3e5276dd43

## State Impact

- target: damp-moon-9297 — Walk now integrates and commits four accepted-revision previews with limits, paths and timings; real arm/carriage and CPU mode parity pass. Named-plane sections remain open.
- target: calm-peak-5247 — Walk review reuses one render/inspection session, preserves inventory and clearance, rejects revision mismatch, and tracks images with project docs; full CLI gate 181 passed, zero skipped.
