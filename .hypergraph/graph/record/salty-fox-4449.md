---
node_id: 51032352-a780-5a5a-8297-a3f7fab7e9f2
slug: salty-fox-4449
title: 'Robin accepted after measured reset repair: inventory and fits, live review, restore mismatch blocks training'
created_at: '2026-09-14T02:06:32+00:00'
parents:
- northern-trail-4014
summary: ''
artifacts:
- docs/probes/ot6/robin/ACCEPTED.md
- docs/probes/ot6/robin/repair.json
- docs/probes/ot6/robin/fit.json
- docs/probes/ot6/robin/operator.json
- docs/probes/ot6/robin/operator-1400.png
- docs/probes/ot6/robin/operator-400.png
---
## What

Accepted Robin's complete product-agent-authored balancer after changing only
its reset lift from [1,3] to [3,5] mm. Generated project-local inventory and
measured-fit report, and moved the persistent review server to Robin. ADR-337
and docs/probes/ot6/robin/ACCEPTED.md carry the outcome and limitations.

## Why

Advances D7 (`ready-sand-2621`) following the critic's instruction: the complete
candidate already existed, so another provider turn was unnecessary. The literal
repair follows the engine's measured 1.31 mm extra penetration; +2 mm minimum
lift leaves roughly 0.69 mm arithmetic headroom. The engine independently accepts
it with no added penetration at the sampled azimuths. Original mechanism authorship
and actor repair have separate source digests. No alias retries or D9 filler.

## Method

Ran `cadex script --set repaired-candidate.py --replace --json` on the external
`ot6-robin` project, explicitly replacing `probe_motor`, with normal transaction,
worker and acceptance checks. Accepted revision 71709063d6af7ee357d5bb5b409e3332730a1465e0caa62f92f93535ec04cd84.
Read the retained accepted result: 24 valid single solids, 276 measured BREP
pairs, 84 passing fit checks, 139.60133 g. Five printable parts and nineteen
catalog parts; inventories include all masses and proxy relations. Pocket gaps
0.30 mm, shaft/hub gap 0.05 mm, only eight matching screw/insert intersections
(4.852224 mm3 each). No design floor, no grounded dynamics component; joint
residuals zero. No training. Full data remain under operator cadex-projects;
compact receipt paths and digests are committed in repair.json and fit.json.

Attempted `cadex section --plane XY --offset-mm 50`; exit 1 on restore digest
mismatch. Kept both result artifacts and acceptance unchanged. A comparison found
right-wheel subelement order differences and small inertia differences, not a
proven causal diagnosis. No re-acceptance or validation weakening.

Start model API showed Finch's 29 components. After complete acceptance, moved
the persistent user service to Robin. Fresh headless browsers at 1400x900 and
400x850 show accepted revision, 24 components, 57044 triangles, solids by default,
and nine proxy outlines under the labelled toggle; no horizontal overflow.
Screenshots visually show the bay, board mounts, wheels and fasteners; motors are
mostly concealed. Server stays running on the private address (redacted in repo).
`pixi run python -m pytest cli/tests/test_review_design.py -k evidence -q`:
70 passed, 16 deselected. No product-code change or full build; no redundant D9 run.

## Result

D7 advances to a complete accepted mechanism with inventory and retained measured
fits, but remains open. **Reopen is broken for Robin**: section restore reports
digest 806ab1343b7c... versus d7e568d29a53..., blocking training. Do not treat the
retained dashboard as proof of successful reopen. Fix the reproducibility failure
before training, recording and seed measurements. The failed section means bay,
boss-gap and engagement dimensions are source-derived, not independent section
evidence. Wheel fit measures clearance, not tested press-fit or axial retention;
motor shoulder clearance is 0.3 mm, not face registration. Original stdout's
12.566 mm3 screw engagement was incorrect and is explicitly corrected by the
4.852224 mm3 measured overlap in the report. No new dependencies. The mechanism
was preserved as instructed; no extra geometry repair was smuggled in. Three
records now lie after the checkpoint; this work dispatch did not reconcile.

Dispatch closed: 1 unit — accept Robin's reset repair, inventory and review it, and expose the reopen blocker.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot6
- commit: 170b597c6101d0f8f3e3efad92fd4486baecff01

## State Impact

- target: ready-sand-2621 — Robin complete authored mechanism accepted at 71709063d6af after literal reset lift repair; 24 solids, 84 retained fit checks, 139.601 g, live dashboard on accepted Robin. D7 stays open: subsequent section restore refused changed digest; repair reproducibility before training. Physical retention and independent bay section remain unverified.
