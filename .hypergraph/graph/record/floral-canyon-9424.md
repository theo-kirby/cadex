---
node_id: 832032eb-0756-5ac2-8ae9-77aa953b1a36
slug: floral-canyon-9424
title: Shorten the carriage iterate guide without losing comparison limits
created_at: '2026-09-08T15:22:29+00:00'
parents:
- still-harvest-7242
summary: ''
---
## What

Shortened only the model-free carriage iterate rehearsal in docs/CLI.md by 16 lines. Kept its runnable command, width 70 to 80 mm, fixed objective/task fields, rollout seed 7 and 200-step horizon, reward 3.296298 to 2.760187 (delta -0.536111), baseline preservation and initial-pose/single-seed limitations. Linked ADR-251 and immutable record mellow-quartz-8093 for detailed timings, witness, component volumes and project commit evidence. Added the ADR removal line and landed ROADMAP checkbox; verified dates remain current at 2026-09-08.

## Why

Selected short-horizon unit 2, explicitly directed by the overseer, following still-harvest-7242 and the bet in frosty-wolf-4770. This advances the operational documentation of charter criteria “The walk exists and is tested headlessly”, “The walk holds on a second mechanism” and “The agent can see its work without a screen” under missions 2 and 6. Assumption: the immutable measured rehearsal remains authoritative; removing duplicated guide prose needs no new walk or runtime change. No parked criterion is promoted.

## Method

Compared the exact rehearsal block against mellow-quartz-8093 and ADR-251. Retained the command verbatim and moved no evidence into another document. Checked the project-doc scaffold's existing comparison conventions; no behavior or scaffold content changes are needed for this editorial shortening. Ran pixi run python -m pytest cli/tests, with output outside the repository at /tmp/ot4-carriage-guide-cli.log, and git diff --check. No new tests, build, GUI, remote work or generated artifacts.

## Result

CLI suite: 223 passed, no skips, 228.27 seconds, exit 0. git diff --check passed. Guide diff is 12 added / 28 removed lines; including ADR and ROADMAP, documentation shrinks by 8 lines. The binary/loaded-module provenance caveat remains in the guide's existing engine-report explanation. All requested operational details and limitations survive, with detailed evidence linked rather than repeated.

The cited criteria remain working in reconciled state; this maintenance exposes no missing leg before they can be ticked at the stated toy scale, and human-owned charter boxes remain unchanged. Next: both selected short units are spent; honor the dispatch bound, with no repeated green walk or manufactured audit. Further actor work requires a concrete failure or contradiction and a fresh planning decision. This adds the third unreconciled record; reconciliation is reserved for the separate maintainer pass. No state or plan files were edited.

Dispatch closed: 1 unit — shortened the carriage iterate guide while preserving its command, comparison and limits.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot4
- commit: a6197fb00436d1715baca2ec4cd05b17edf7f67f

## State Impact

- target: calm-peak-5247 — Carriage iterate guide is 16 lines shorter with its runnable command, fixed task and rollout settings, reward decrease and baseline retained; detailed evidence linked; CLI suite 223 passed.
- target: damp-moon-9297 — Condensed rehearsal retains initial-pose and single-seed limitations and links the immutable four-eye evidence instead of duplicating it.
