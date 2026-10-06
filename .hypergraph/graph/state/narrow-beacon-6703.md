---
node_id: d39290c1-4967-5430-9f0a-5df13e26f7c5
slug: narrow-beacon-6703
title: G2. The reference project's lessons are in Cadex
created_at: '2026-10-06T07:42:22+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun4: **G2. The reference project's lessons are in Cadex.** A ledger, `docs/probes/orun4/LESSONS.md`, lists every lesson from the reference project (`~/cadex-projects/biped-sts`, read-only): the general rule, its evidence, and where it went (base, the printed-legged-robot style, a tool default, or not adopted with the reason). It covers contact geometry, target speed against the actuator, lateral clearance, actuator placement, training practice and the look. The proof is a fresh agent session on a scratch `orun4-*` project, with the style chosen, that shows the style's foot, joint and clearance rules unprompted in its first accepted design [rec: light-mist-9160]. The human owns the checkbox.

**Lessons placed and test-pinned; two fresh-session proofs stand; the style's guidance defect they found is closed** [rec: northern-stream-2677] [rec: ancient-trail-9417] [rec: wandering-dune-8500] [rec: witty-bay-1622]. Status working: the ledger's rows are all evidenced and placed; what remains is the owner's checkbox and the confirmations below.

- **Ledger complete** (ADR-565): 19 lessons with evidence (contact L1–L4, speed L5–L6, clearance L7–L8, training L9–L18, look W2/L4); admission needs a recorded change and its effect [rec: civic-stream-8050]. Every row has a destination: 15 to the base, 9 to the style, L18 is a tool fix (F1, ADR-558), W6 (hip-yaw hypothesis) not adopted [rec: northern-stream-2677].
- **Where the rules live** [rec: northern-stream-2677]:
  - Base, engine (`CadexAgentGuidance.md`): measure tangent-primitive solids; set joint limit and spacing together from the sweep; *THE SIMULATED BODY IS THE BUILT BODY*; walking-task rules (speed bounded both sides, target that makes the intended motion easy, command range centred via `command_limits_degrees`, progress only while upright, ceiling on anti-degenerate charges, heading charged from run one). [rec: northern-stream-2677]
  - Base, CLI (`guidance.py`): *TRAIN SO A GOOD POLICY CAN BE KEPT* — checkpoints, keep what `evaluate` passes, warm vs cold start, never tighten `action_filter_alpha` on a warm start. [rec: northern-stream-2677]
  - Style (`CadexAgentStyle.printed-legged-robot.md`): limb look, knee actuator in the thigh, compact twin-keel hull feet with a flat strip, hips wide enough for the feet, *THE STEP IS WHAT IS PAID*. [rec: northern-stream-2677]
  - Pinned by `test_agent_guidance.py` in both suites: each rule in its file and absent from the other, no reference number became a default, the base names no robot type. [rec: northern-stream-2677]
- **First fresh session** (`orun4-fresh-legged`, commit f71fa77a, `FRESH-SESSION.md`): carried the twin-keel strip, horn-sized caps, in-limb actuators, two-way taper and a tighter inward roll limit unprompted; **missed foot compactness** (72 × 40 mm slab under 210 mm), set the roll limit without measuring, rightly declined the level-thigh rule for an upright biped [rec: ancient-trail-9417].
- **Style revised** (ADR-566, commit 10020100): each sole ≤ 1/4 standing height long and ≤ 1/8 wide, ratios recorded; level thigh asked of sprawled legs only [rec: nimble-garden-9555].
- **Second fresh session** (`orun4-fresh-legged-2`, commit d3e027db, `FRESH-SESSION-2.md`, same isolation, prompt and leakage audit): first robot (ordinal 6, `19c0ef2d`) had a 54 × 27 mm sole under 225.6 mm (0.239 × 0.120, inside both bounds), ratios recorded unprompted, and a lean thigh on an upright biped. It set the inward roll limit at −12° at first and later derived −10° from contact at −20° with hips widened 42→46 mm [rec: wandering-dune-8500].
- **Roll-limit procedure fixed** (ADR-567, commit c651ea36): `first_contact` is the first contacting sample counted from the range's low end, so on a negative inward side it is the deepest contact and ADR-566's wording read literally put the limit inside the collision. The style now brackets the meeting angle outward from the standing pose one sweep step at a time, records last-clear and first-contact angles, and sets the limit ≥ 2 sweep steps short of the first contact; it warns about the deepest-contact reading. Engine semantics unchanged by design (`docs/INTEGRATION.md` already documents them). Pinned by `test_the_roll_limit_is_bracketed_outward_from_the_standing_pose` (engine) and a CLI test; `DESIGN-LANGUAGE.md` §5 and LESSONS L7 match [rec: witty-bay-1622]. Assumption: worded for a revolute hip roll with a declared sweep step; slider-limited case not covered [rec: witty-bay-1622].
- **Owner to confirm**: L4 foot phrasing, L5 speed reading, W1 knee placement [rec: northern-stream-2677]; the 1/4 and 1/8 bounds (an upper bound the reference met with margin, not a measured optimum) [rec: nimble-garden-9555]. The ADR-567 roll procedure has not yet been shown to a fresh session (judgement: not required for working; the critic asked for no third revision) [rec: witty-bay-1622].
- Seen in passing, not G2 work and folded nowhere else because no record declared an impact for them: `cadex smoke` false positives in its exact-geometry pre-check — a distance mismatch under 1e-5 mm on a pair 70 mm apart, and threaded screw engagement counted as overlap [rec: wandering-dune-8500] [rec: witty-bay-1622]; the full CLI suite as one command runs past the 600 s shell limit (thirds ~10.4 min) [rec: nimble-garden-9555] [rec: witty-bay-1622].

## Negative knowledge

- [scope: the reference STS3215 biped's target speed | confidence: medium | evidence: civic-stream-8050] "Slow the target down to what the servos hold" is not what the reference project shows: every 100 mm/s run shuffled or buzzed, and 160 mm/s, inside the servo's 252°/s, gave real strides.
- [scope: the printed-legged-robot style, one fresh session | confidence: medium | evidence: ancient-trail-9417] "Compact" with no proportion did not keep a fresh agent's foot compact; it drew a slab. Superseded by ADR-566's ratio bound, which held in the second session [rec: nimble-garden-9555] [rec: wandering-dune-8500].
- [scope: upright bipeds under the printed-legged-robot style | confidence: medium | evidence: ancient-trail-9417] "The thigh runs out level" is wrong for an upright leg; it fits sprawled legs only.
- [scope: inward hip-roll limits on the negative side of a wide sweep | confidence: high | evidence: wandering-dune-8500, witty-bay-1622] Reading the limit off a wide range's `first_contact` puts it inside the collision: that value is the deepest contact counted from the low end, not the onset.

## Provenance

- light-mist-9160 — operator-declared orun4 charter gap (gap-g2-reference-project-s-lessons)
- civic-stream-8050 — ledger skeleton: 19 lessons with evidence, destinations undecided
- northern-stream-2677 — ledger destinations filled; lessons written into base (engine + CLI) and style, test-pinned (ADR-565)
- ancient-trail-9417 — first fresh-session proof: rules carried unprompted except foot compactness; level-thigh rule wrong for bipeds
- nimble-garden-9555 — style revised: foot ratio bound, level thigh scoped, roll limit from measured first_contact (ADR-566); second fresh session owed
- wandering-dune-8500 — second fresh-session proof: foot bound and thigh rule held unprompted; found the first_contact roll-limit defect
- witty-bay-1622 — ADR-567: roll limit bracketed outward from the standing pose; defect closed; status to working
