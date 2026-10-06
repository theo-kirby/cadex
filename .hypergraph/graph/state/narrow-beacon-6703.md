---
node_id: d39290c1-4967-5430-9f0a-5df13e26f7c5
slug: narrow-beacon-6703
title: G2. The reference project's lessons are in Cadex
created_at: '2026-10-06T07:42:22+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun4: **G2. The reference project's lessons are in Cadex.** A ledger, `docs/probes/orun4/LESSONS.md`, lists every lesson from the reference project (`~/cadex-projects/biped-sts`, read-only): the general rule, its evidence, and where it went (base, the printed-legged-robot style, a tool default, or not adopted with the reason). It covers contact geometry, target speed against the actuator, lateral clearance, actuator placement, training practice and the look. The proof is a fresh agent session on a scratch `orun4-*` project, with the style chosen, that shows the style's foot, joint and clearance rules unprompted in its first accepted design [rec: light-mist-9160]. The human owns the checkbox.

**Ledger skeleton exists; destinations undecided** [rec: civic-stream-8050]. Still open: every Destination cell must be filled once G1's base/style structure lands, and then the fresh-session proof run.

- `docs/probes/orun4/LESSONS.md`: 19 lessons written as general rules with evidence (project ADR, revision, run or evaluation, and change → effect). They cover all six areas: contact L1–L4, speed L5–L6, clearance L7–L8, training L9–L18, look W2/L4. Six choices are listed as *weighed, no recorded effect*, and two tool defects are routed to F1/F2. Admission rule: a lesson needs a recorded change and its effect [rec: civic-stream-8050].
- **The speed lesson runs opposite to the charter's wording.** The reference raised its target from 100 to 160 mm/s: every 100 mm/s run shuffled or buzzed, and 160 mm/s, still inside the servo's 252°/s, gave real strides. So the rule is "pick the target that full strides reach most easily, then check actuator headroom" (L5) [rec: civic-stream-8050].
- **Actuator placement (W1) and the look (W2) have no measured effect**; they rest only on the owner's approval. Proposed home: the style, as taste, marked "owner to confirm" [rec: civic-stream-8050].

## Negative knowledge

- [scope: the reference STS3215 biped's target speed | confidence: medium | evidence: civic-stream-8050] "Slow the target down to what the servos hold" is not what the reference project shows: every 100 mm/s run shuffled or buzzed, and 160 mm/s, inside the servo's 252°/s, gave real strides.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-g2-reference-project-s-lessons)
- civic-stream-8050 — ledger skeleton: 19 lessons with evidence, destinations undecided
