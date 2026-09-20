---
node_id: efc02a3c-ff8a-5fcc-9d08-05a6a7f60794
slug: long-falcon-7461
title: 'F4: measure the real preserved seed without changing accepted identity'
created_at: '2026-09-14T22:42:29+00:00'
parents:
- true-wolf-3979
summary: ''
artifacts:
- docs/probes/ot7/retained/repair-measurement.json
- docs/probes/ot7/runner/README.md
---
## What

Ran the real ot7 measurement child against the preserved F4 Heron seed and
published a compact integration receipt plus the runner's measured baseline.

## Why

Advances F4 (polished-forest-0215). The critic requested real integration after
two synthetic pagination units. This follows that request without another
pagination variant. At arrival it was 22:40 UTC / 18:40 America/New_York,
before the documented 20:20 provider reset; no repair was dispatched.

## Method

Validated the original seed using runner.validate_seed, saved seed_identity
before and after, and launched the existing --child-measure in a subprocess
using runner.execute with its 300-second bound. The child uses restore=False
and reads published clearance and inventory through the real inspect reader.
All outputs stay in cadex-projects/ot7-heron-repair/evidence/iteration29-measurement/.
The committed docs/probes/ot7/retained/repair-measurement.json enumerates their
sizes and SHA-256 hashes and the project-local receipt hash. Assertions checked
every artifact hash and size, 105 unique pairs, 15 inventory components,
matching accepted revision across all three reports, identical before/after
identity files and metadata bytes, and the known shoulder overlap and horn gap.

## Result

The real child exited 0 in 0.163735 seconds. Accepted revision remains
7e9eff5c4ff2640fbaaedd475f7394c0aeae54ce59f6effc067cffeaca8b4475.
Static fit fails with 15 entries: 8 intersecting pairs, 6 below-clearance pairs
and 1 world-geometry failure; 91 pairs are clear. The shoulder servo/base
common volume is 248.20162986795066 mm³. Horn/link gaps are
0.19999999999999732 and 0.19999999999993 mm. They are measured but not failing:
the old seed has no declared contact intent and the default minimum is 0.1 mm.
Thus an eventual zero-failure summary alone does not prove all three original
defects repaired. Swept coverage is explicitly unavailable for this accepted
revision; this was a published-data read, not a new sweep or a rebuild.

All experiment assertions passed. No product code or test changed; no full
suite, build or packaged gate was required or rerun for this documentation and
integration-measurement unit. No dependency, actor design edit, provider call,
prompt change, dashboard change or state edit. The repair slot remains unused;
after reset the existing collector can compare its guarded before-read with
this baseline, then dispatch only the frozen repair prompt. F4 remains open.
This record reaches three pending records; the next dispatch owes reconcile
when permitted, but this work dispatch expressly forbids it.
Dispatch closed: 1 unit — real preserved-seed measurement integration and identity receipt.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot7
- commit: ee923d449c4ede5f4c62d30ee8162e4e87910a1f

## State Impact

- target: polished-forest-0215 — Real child integration collected 105 pairs and 15 failures from the preserved seed with unchanged script and metadata; horn gaps lack contact intent and sweep is unavailable. Baseline artifacts retained; no pre-reset provider call, F4 remains open.
