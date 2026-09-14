---
node_id: 02de9e75-f5fb-5ea7-9215-3870abbd7be0
slug: honest-ivy-8824
title: F8. A smoke rollout is one command
created_at: '2026-09-14T17:28:05+00:00'
parents:
- mild-ledge-7157
summary: ''
---
Status: working

## Current

**F8's bounded smoke command is implemented and fixture-verified (ADR-352), pending owner/critic review.** `cadex smoke --out DIR` reads pinned accepted artifacts under the project lock without restore, rebuild or acceptance, preserves accepted identity, and writes trace/geometry receipts and a complete measured verdict. Zero action or held position actuators run within a shared wall-time deadline capped at 300 seconds. Finite state is checked every solver step; exact posed BREP checks cover all component pairs at sampled times, including parts without collision proxies. Initial measurements must agree with published clearance; missing solids or disagreement cannot pass [rec: lean-fountain-9707].

Known-answer evidence includes a grounded pass across 101 poses, a falling arm whose proxies pass but exact solids overlap by 1,463.7845106574737 mm³ at 1.64 s, and analytic overlapping boxes at 400 mm³. Fixtures also cover floor support/burial, missing floor, instability, hold versus zero action, termination, sampling, timeouts, stale receipts, tampering and preservation of accepted state with a broken working script. Focused smoke: 25 passed; staged lifecycle plus smoke: 43 passed. Evidence index: `docs/probes/ot7/f8-smoke.json` [rec: lean-fountain-9707].

Limits: component checks are sampled, not continuous; floor penetration/support use collision proxies; unsupported non-BREP components cannot pass. No new dependency or protocol/payload change [rec: lean-fountain-9707].

Charter criterion: one bounded accepted-design smoke command checks finite state, component interpenetration and floor support or a grounded base, with passing/failing fixtures and receipts cited by F5–F7 [rec: kind-dusk-1609]. Reconcile judgement: `working` for the implementation and known-answer evidence explicitly reported as ticking F8; this does not supply the still-outstanding unassisted-design receipts or edit the owner's checkbox [rec: lean-fountain-9707].

## Negative knowledge

None yet.

## Provenance

- kind-dusk-1609 — the ot7 directive (ADR-341) declared this criterion as gap `gap-f8-smoke-rollout-one-command`

- lean-fountain-9707 — ADR-352 accepted-artifact smoke, exact sampled BREP checks, bounded execution, fixtures and staged verification
