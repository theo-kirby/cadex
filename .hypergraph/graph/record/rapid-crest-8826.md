---
node_id: f9064bc3-0fd1-5f25-90d3-49251022ac97
slug: rapid-crest-8826
title: Verified dashboard private access and repaired narrow-browser layout (ADR-286)
created_at: '2026-09-12T15:50:15+00:00'
parents:
- wild-cove-4437
summary: ''
---
## What

Closed the missing dashboard verification and handoff from iteration 3
(commit 7bd74345568a5b12464b55f6bfe604cd735857d8, ADR-286), and fixed its
narrow-browser layout. The dashboard serves one selected project's accepted
model, recorded historical models/specs, document snapshots and permitted
artifacts without an engine or writes. This record supplies the causal
record omitted by that commit; it does not retroactively claim that
iteration ran passing gates.

## Why

The critic required the missing record, CLI/browser gates and a private-address
smoke before fresh biped work. This unit advances D1/D2 and fixture-level D5
evidence. Fresh product-agent biped creation and training remain the next
unit because this dispatch permits exactly one unit: finish and verify the
existing dashboard. No charter/state/plan edits.

## Method

Read the actor and hypergraph-record skills, repository contracts, VISION,
prior record and dashboard implementation/tests. Adopted the inherited dirty
CSS change, then added browser coverage that narrows a loaded view from
1280 to 1000 pixels, forces eight redraws, checks stable canvas dimensions
and no horizontal page overflow, and exercises real mouse orbit/zoom.
Original HEAD CSS failed the added overflow assertion (1 failed, 14
deselected). The inherited CSS change alone also failed: DOM measurements
showed the artifact table extending to 1179.55 pixels in a 1000-pixel
viewport. Allowing the grid column to shrink and wrapping long artifact
paths fixes the demonstrated defect. The redraw-growth assertion alone did
not fail on original CSS; the demonstrated issue is narrow-page overflow.

Updated docs/CLI.md with the smoke command and evidence limits and appended
the verification follow-up to ADR-286. No new dependency: existing Chromium
is driven by the prior iteration's standard-library DevTools-pipe helper.
No build performed; no engine/protocol/payload/shell changes.

Commands:

```
pixi run python -m pytest cli/tests -q
CADEX_REVIEW_HOST="$(tailscale ip -4)" pixi run python -m pytest cli/tests/test_review_server.py -q -s
pixi run test-engine
git diff --check
```

## Result

Product fix committed as 4a84550b. Full CLI suite: 337 passed, 1 skipped
in 281.17 seconds (the private-address test skips without CADEX_REVIEW_HOST).
That suite started before the added resize assertion; the final focused
suite below separately validates all changed browser behavior.
Engine suite: 2102 passed, 54 skipped in 306.46 seconds, matching the
launch baseline counts. No gate failures remain. git diff --check passed.

Final focused browser/HTTP suite: 15 passed in 7.73 seconds, no skips.
The smoke bound http://100.104.232.88:44657/ and a same-machine headless
Chromium opened it in 0.12 seconds, matching the fixture project name,
accepted revision and actual location.host. The fixture is synthetic and
the server was stopped by the test; no second-device visit is claimed.
Tests also verify historical revision/parameter/model identities, component
names, non-background rendered pixels, orbit/zoom, missing artifacts, stale
server labels, command shutdown without project writes and permitted-path
refusals.

D1 has its stated documented-command and private-address browser smoke
evidence (ticks D1 at fixture scope); leave the human-owned checkbox and
state untouched. D2/D5 remain open: no fresh agent-authored biped browser
validation, real design change/retraining history or retained videos yet.
D3/D4/D6-D9 remain open and are not advanced by synthetic dashboard fixtures.
The command starts the dashboard for a chosen project; no persistent server
was left running by this unit.

Handoff: create a new project under the operator's cadex-projects directory
through the product agent, preserving its own history and avoiding mg-legs.
Compare the real accepted model/spec identities in the browser and exercise
orbit/zoom before the bounded training probe. Live loss telemetry and verified
intermediate/final video publication are still unwired. The UI's live header
means the review server answered, not proof that training telemetry is fresh.

Dispatch closed: 1 unit — verify and repair the dashboard and supply its missing causal handoff.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/ot5
- commit: 4a84550b348b580c3f2351f6e440611325c630f7

## State Impact

- target: jolly-loom-0622 — D1 documented command and same-machine Tailscale-address headless browser smoke passed; fixture scope, no second-device claim.
- target: shy-meadow-0959 — Dashboard accepted/historical identity and orbit/zoom browser tests pass; narrow-browser overflow fixed. Fresh biped validation remains open.
- target: sharp-union-6036 — Fixture browser tests preserve historical model/spec identities; real design-change and retraining history with videos remains open.
