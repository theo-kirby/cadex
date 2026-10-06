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

**Lessons placed and test-pinned; the style has been revised once on fresh-session evidence; a second fresh session is owed** [rec: northern-stream-2677] [rec: ancient-trail-9417] [rec: nimble-garden-9555]. Status stays open: the revised style has not yet been shown to a fresh agent.

- **Ledger complete** (ADR-565): 19 lessons with evidence (contact L1–L4, speed L5–L6, clearance L7–L8, training L9–L18, look W2/L4); admission needs a recorded change and its effect [rec: civic-stream-8050]. Every row now has a destination: 15 to the base, 9 to the style, L18 is a tool fix (F1, ADR-558), W6 (hip-yaw hypothesis) not adopted [rec: northern-stream-2677].
- **Where the rules live** [rec: northern-stream-2677]:
  - Base, engine (`CadexAgentGuidance.md`): measure tangent-primitive solids; set joint limit and spacing together from the sweep; *THE SIMULATED BODY IS THE BUILT BODY*; walking-task rules (speed bounded both sides, target that makes the intended motion easy, command range centred via `command_limits_degrees`, progress only while upright, ceiling on anti-degenerate charges, heading charged from run one). [rec: northern-stream-2677]
  - Base, CLI (`guidance.py`): *TRAIN SO A GOOD POLICY CAN BE KEPT* — checkpoints, keep what `evaluate` passes, warm vs cold start, never tighten `action_filter_alpha` on a warm start. [rec: northern-stream-2677]
  - Style (`CadexAgentStyle.printed-legged-robot.md`): limb look, knee actuator in the thigh, compact twin-keel hull feet with a flat strip, hips wide enough for the feet, *THE STEP IS WHAT IS PAID*. [rec: northern-stream-2677]
  - Pinned by `test_agent_guidance.py` in both suites: each rule in its file and absent from the other, no reference number became a default, the base names no robot type. [rec: northern-stream-2677]
- **First fresh session** (`orun4-fresh-legged`, commit f71fa77a, `docs/probes/orun4/FRESH-SESSION.md`): isolated agent, guidance + style only; first accepted biped (rev 29e99e01) carried the twin-keel strip centred on the COM, horn-sized caps, in-limb actuators, two-way taper and a tighter inward hip-roll limit unprompted. It **missed foot compactness** (a 72 × 40 mm slab under a 210 mm robot), set the roll limit without measuring where the feet meet, and rightly declined the level-thigh rule for an upright biped [rec: ancient-trail-9417].
- **Style revised** (ADR-566, commit 10020100): each sole ≤ 1/4 standing height long and ≤ 1/8 wide, ratios recorded, stability credited to the strip under the COM; level thigh asked of sprawled legs only; inward roll limit set ≥ 2 sweep steps short of the measured `first_contact` from `inspect scope=clearance`. Base unchanged; both test files pin the new phrases [rec: nimble-garden-9555].
- **Owner to confirm**: L4 foot phrasing, L5 speed reading, W1 knee placement [rec: northern-stream-2677]; the 1/4 and 1/8 bounds (an upper bound the reference met with margin, not a measured optimum) [rec: nimble-garden-9555].
- Seen in passing: the fresh agent reported `cadex smoke` timing out in its exact-geometry stage on 64 components [rec: ancient-trail-9417]; the full CLI suite as one command runs ~625 s, past the 600 s shell limit [rec: nimble-garden-9555]. Not G2 work; noted, not folded elsewhere because neither record declared an impact for them.

## Negative knowledge

- [scope: the reference STS3215 biped's target speed | confidence: medium | evidence: civic-stream-8050] "Slow the target down to what the servos hold" is not what the reference project shows: every 100 mm/s run shuffled or buzzed, and 160 mm/s, inside the servo's 252°/s, gave real strides.
- [scope: the printed-legged-robot style, one fresh session | confidence: medium | evidence: ancient-trail-9417] "Compact" with no proportion did not keep a fresh agent's foot compact; it drew a slab. Superseded in guidance by ADR-566's ratio bound [rec: nimble-garden-9555].
- [scope: upright bipeds under the printed-legged-robot style | confidence: medium | evidence: ancient-trail-9417] "The thigh runs out level" is wrong for an upright leg; it fits sprawled legs only.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-g2-reference-project-s-lessons)
- civic-stream-8050 — ledger skeleton: 19 lessons with evidence, destinations undecided
- northern-stream-2677 — ledger destinations filled; lessons written into base (engine + CLI) and style, test-pinned (ADR-565)
- ancient-trail-9417 — first fresh-session proof: rules carried unprompted except foot compactness; level-thigh rule wrong for bipeds
- nimble-garden-9555 — style revised: foot ratio bound, level thigh scoped, roll limit from measured first_contact (ADR-566); second fresh session owed
