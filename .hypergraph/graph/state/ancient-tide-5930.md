---
node_id: ec0f61ac-111a-521c-bfec-198fef09dd51
slug: ancient-tide-5930
title: The catalog is broad enough for a robot prompt
created_at: '2026-09-06T19:18:34+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: superseded
## Current

Open charter criterion: **The catalog is broad enough for a robot prompt**: at least five servos, ten actuators, a bearings family, and M2 to M5 nuts and bolts, each with provenance and a real-kernel test. [rec: empty-wolf-3962]

Declared target: `gap-catalog-broad-enough-robot-prompt`. This node tracks the criterion as a gap; it becomes working only with evidence that the criterion is met. Truncated impact wording is resolved from the full charter in the same record [rec: empty-wolf-3962].

**Fifth-servo qualification stopped (ADR-229):** the bounded audit inspected Hitec HS-311 and HS-422; neither qualifies for the unchanged ServoPart recipe. Four servo identities remain, and seven powered identities under an inclusive count leave at least one servo and three powered identities missing. This count does not satisfy the broader provenance, real-kernel or L3 obligations. Replan before candidate proof or delivery; no candidate kernel proof or runtime change occurred [rec: hidden-ridge-7342].

## Negative knowledge

- [scope: HS-311 and HS-422 under unchanged ServoPart | confidence: high | evidence: hidden-ridge-7342] The recipe cannot reproduce the open mounting mouths using the stated circular drills. Output-stack evidence needs further qualification; HS-422 also has inconsistent dimension labels. This bounded refusal does not rule out other candidates or a separately qualified recipe decision.

## Provenance

- empty-wolf-3962 — operator-declared charter gap
- hidden-ridge-7342 — two manufacturer-source candidates fail unchanged-recipe qualification; breadth remains open


## Superseded

Parked by the operator before nt3 (2026-09-07). The criterion moved to `## Later criteria` in the charter, where it seeds no gap. It is not abandoned: the human promotes it back into `## Done criteria` when the nt3 frontier — the lifecycle walk and the headless review calls — lands or blocks. No evidence about the criterion itself changed.
