---
node_id: 80b0db17-2105-598d-8ec9-21e6eac7024b
slug: copper-timber-8947
title: Walk review commits sections from its shared accepted snapshot
created_at: '2026-09-08T00:08:21+00:00'
parents:
- placid-lily-5624
summary: ''
artifacts:
- docs/probes/named-section/walk-review/README.md
- docs/probes/named-section/walk-review/measurements.json
- docs/probes/named-section/walk-review/cli-gate.log
- docs/probes/named-section/walk-review/monitor.log
- docs/probes/named-section/walk-review/arm-local-section.svg
- docs/probes/named-section/walk-review/arm-local-section.json
- docs/probes/named-section/walk-review/arm-remote-section.svg
- docs/probes/named-section/walk-review/arm-remote-section.json
- docs/probes/named-section/walk-review/carriage-local-section.svg
- docs/probes/named-section/walk-review/carriage-local-section.json
- docs/probes/named-section/walk-review/carriage-remote-section.svg
- docs/probes/named-section/walk-review/carriage-remote-section.json
---
## What

Integrated named-plane sections into `cadex walk` review, replacing its unavailable placeholder with committed section SVG/JSON from the preview's accepted snapshot. Updated CLI and walk docs, shared mode-artifact table, project-doc scaffold, ADR-240 and the ROADMAP integration checkbox together.

## Why

Advances the charter criterion **The agent can see its work without a screen**, target damp-moon-9297, and follows placid-lily-5624's delivered section writer. The overseer selected this integration unit. The reversible convention is world XZ at Y = 3.125 mm: a meaningful interior cut through both reference mechanisms, with no mechanism-specific dispatch or protocol change. Other models can legitimately produce empty or unsupported cuts; those remain explicit rather than guessing a new plane. The criterion remains open until the separate fresh two-mechanism complete-review rehearsal.

## Method

Factored display acquisition into one helper, and let render and section writers consume that same bounded in-memory snapshot. Both preserve expected-revision checks; the walk additionally refuses a rollout digest mismatch before writing. Review carries section availability/status, revision/digest, plane/offset/units, approximation, limits, acquisition/contour timings and project-relative SVG/summary paths. Empty reports remain available with no contours, unsupported reports unavailable with per-object reasons. Acquisition, revision and write failures fail the walk without presenting retained old files as current success. No new engine operation, payload, shell code, dependency or build.

Built-engine tests exercise both documented mechanism scripts with the unchanged public script/walk entry points, one training iteration/four environments/seed zero, and both local and remote-flag paths. The remote dispatcher is a local CPU stand-in using the training venv, never SSH or the GPU box. Tests inspect actual SVG paths, nonempty positive-area contours, accepted identity, committed output paths and clean project trees; contour geometry and rendered pixels match between modes. Additional regressions cover empty/unsupported reports, refusal after old success, no section reacquisition, digest mismatches and the scaffold/table contract.

Actual arm and carriage sections from both modes and their measurements are retained under docs/probes/named-section/walk-review/. Visually inspected local SVGs through headless CairoSVG: blue bases, orange arm/carriage, contact for the arm and separation for the carriage, legible cut qualification. Direct uv invocation initially lost libcairo discovery; setting the existing pixi library path inside the inspection Python process resolved it. CairoSVG stays inspection-only. No checkpoints or rollout traces are committed to this repository.

## Result

Initial built-engine targeted gate: `pixi run python -m pytest cli/tests/test_walk.py -q --basetemp /tmp/cadex-section-walk-tests`, 24 passed, zero skipped, 116.19 s, before four further section-outcome tests and scaffold assertions were added. Initial training was not continuously memory-sampled; one trainer sample was 989,200 KiB RSS. The subsequent full gate contains all final assertions and is monitored as a whole process tree with a 2.9 GB/850 s cutoff.

Four retained integration samples: arm local/remote whole-walk 15.563/15.754 s, carriage local/remote 14.348/14.697 s; acquisition 0.645–0.668 s, contour generation 0.000064–0.000069 s. Shared acquisition counts once; section timing excludes serialization/writes; whole walk excludes final project commit. Rewards and witnesses match between mode pairs. These are observations, not benchmarks or useful learned robotics performance. Sections retain their qualified tessellation/initial-pose limits, and the arm's known contact remains reported. No GUI or remote execution.

Next: the separately planned fresh two-mechanism complete-review rehearsal, including all named views, meaningful section, catalog inventory and named-pair clearance with comparable project numbers. This unit does not close the headless-review criterion. This record makes three unreconciled nodes; the separate maintainer owns reconciliation and no state/plan/charter files were changed.

Full final gate: `pixi run python -m pytest cli/tests -q --basetemp /tmp/cadex-section-full-tests`, **195 passed, zero skipped, 216.88 s**. The process-tree monitor exited 0 in 217.42 s with sampled peak RSS **1,175,715,840 bytes**, below the 2.9 GB cutoff. Gate and monitor output are retained beside the artifacts. `git diff --check` passed.

Dispatch closed: 1 unit — accepted-snapshot sections integrated into walk review, both mechanisms and CPU mode parity verified.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 85f895c9d4d2b3e3f741a020618f0dca89da29e4

## State Impact

- target: damp-moon-9297 — Walk sections integrated with explicit statuses, accepted snapshot identity and tracked artifacts; both mechanisms and CPU mode parity verified; separate fresh complete-review rehearsal remains open.
- target: calm-peak-5247 — Walk review now includes XZ Y=3.125 mm section SVG/JSON from the same accepted snapshot as named views; documentation and scaffold agree.
