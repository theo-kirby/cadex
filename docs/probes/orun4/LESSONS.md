# orun4 — Lessons from the reference project (G2 ledger)

Verified against source: 2026-10-06. Skeleton: every lesson with its
evidence, written **before** deciding where any of them goes. The
*Destination* column is `undecided` on every row until the G1
base-plus-styles structure exists; a later unit fills it in with base,
the printed-legged-robot style, a tool default, or *not adopted*, with
the reason.

**Source.** The reference project is the owner's printed biped on Feetech
STS3215 bus servos (`~/cadex-projects/biped-sts`, read only): `script.py`,
`DECISIONS.md` ADR-001…011 (cited below as **P-ADR-n**, to keep them apart
from Cadex's own ADRs), `PROGRESS.md`, `script_history/` revisions
0008–0032, `runs/walk-r1`…`walk-r13` (each run's `stop-requested.json`
reason and `run.json` request), and three evaluations: r4 i200 fail 0/10
(rev `5a0a8701`), r11 i300 fail (rev `7c0cb1c4`), r13 i140 **pass 10/10**
(rev `14b7223e`, policy sha256 `235b65eb…`). This ledger may cite it;
nothing in Cadex's guidance, tests or defaults may (charter G1).

**Admission rule** (charter question policy). A row is a lesson only if
the project records a change *and what it did* to the walk or the fit.
A choice made once with no recorded effect is listed under *Weighed,
no recorded effect* so the charter's six areas are all visibly weighed,
but it is not a lesson on this evidence.

The rules are phrased generally; the project's numbers are its
instance, never a default.

## Lessons (a change with a recorded effect)

### 1. Contact geometry

| # | Lesson, as a general rule | Evidence (change → effect) | Destination |
|---|---|---|---|
| L1 | A support whose cross-section is a single round edge gives no base in the direction across it; when a mechanism must stand on one support at a time, give that support a flat strip (two contact lines) across the direction it must not tip. | r5 and r7 plateaued in a 16–24 mm shuffle whatever the reward (counted steps 0–2; r7 stop: "single-keel foot gives no sideways base on one foot"). Twin-keel hull (flat 8 mm strip between round bilges, rev `17810396`) → r9 5/6 seeds survive 10 s with yaw ≤ 11°, and r11 (with L5) gave the first real gait, ~40 mm counted steps. P-ADR-009. | undecided |
| L2 | Centre the resting support under the centre of mass, measured on the model, not estimated. | MuJoCo probe: stance fell in 0.75 s from an 80 mm/s nudge with the keel 6 mm behind the COM; `foot_fwd` = 6 mm → survives 80 mm/s pushes. Ranked 2nd in "what made it work". P-ADR-008, P-ADR-011. | undecided |
| L3 | Make the printed contact surface exactly a union of the simulator's primitive collision shapes, so the physics walks on the part that is printed. | Half-ellipsoid foot (rev `26ca52da`) rejected: no primitive matches it, so step metrics would have measured a different foot. Half-capsule, then two-capsule hull, collide exactly as printed; final evaluation passes on that geometry. P-ADR-004, P-ADR-009. | undecided |
| L4 | Contact parts stay compact: the feet that passed are 64 × 32 × 12 mm hulls on a ~31 cm, 0.65 kg robot; widening the base came from a flat strip, not from a bigger foot. | Owner request "no large or flat feet" (P-ADR-004) honoured through every revision, and the 10/10 pass (P-ADR-011) was on the compact hull. The size is an owner constraint that held, not a measured optimum. | undecided |

### 2. Target speed against the actuator

| # | Lesson, as a general rule | Evidence (change → effect) | Destination |
|---|---|---|---|
| L5 | Choose the target speed so that the intended motion (full strides) is the *easiest* way to reach it, then check it against the actuator's speed headroom. A target so low that a degenerate motion (a shuffle, a buzz) reaches it lets training settle there. | Every 100 mm/s run (r5, r7, r9, r10) settled in a shuffle or buzz (r9: 70–80 hops/foot of 0.02–0.04 s), while r3 at ~200 mm/s took real steps. Target raised to 160 mm/s, still within the STS3215's 252°/s at 6 V → r11 first real gait; r13 passed at 158–168 mm/s. P-ADR-007, P-ADR-010, P-ADR-011 item 4. **Note:** the charter's phrase "a speed the servos can actually hold" is borne out as *headroom checked*, but the move was **up**, not down. | undecided |
| L6 | Bound the speed reward on both sides: a bell peaking at the target plus a charge above it, never raw speed. | r3 stepped well but ran away to 160–235 mm/s and tipped in 1–3 s; narrower bell (σ = 0.6 V) + overspeed charge above 1.4 V → r4 i200 naive replay walked 8/8 at ~110 mm/s. P-ADR-008. | undecided |

### 3. Lateral clearance

| # | Lesson, as a general rule | Evidence (change → effect) | Destination |
|---|---|---|---|
| L7 | Sweep each joint through its full range and check that moving parts clear each other; set the spacing *and* the joint limit from the sweep, asymmetric where the geometry is. | Hip half-spacing 46 mm: the sweep showed the feet meeting at 10° inward roll → spacing 50 mm and inward roll limited to 8° (outward 20°), per side (`hinge("roll_…", …, -8/20)` in `script.py`). P-ADR-003. | undecided |
| L8 | When a part that sits beside its mirror grows, re-check the clearance and move the spacing with it. | Twin-keel feet widened 28 → 32 mm beam → `hip_y` 50 → 52 so they clear at 8° inward roll (run params r9–r13 carry `hip_y` 52). P-ADR-009. | undecided |

### 4. Training practice

| # | Lesson, as a general rule | Evidence (change → effect) | Destination |
|---|---|---|---|
| L9 | Centre the policy's command range on the rest pose, so a zero action holds the pose rather than a joint range's midpoint. | r1 stuck at ~28-step episodes: the action midpoint of asymmetric ranges commanded a crouch (knee +20°, roll ±6°). Command limits centred on stance (roll ±8°, pitch ±40°, knee ±40°) → r2 learned to move. Ranked 1st in "what made it work". P-ADR-008, P-ADR-011. | undecided |
| L10 | Gate progress rewards (speed, stride) on staying upright, so a tilting stumble earns nothing. | r2 at i100: every seed a 2–3 step lunge tipping at ~1.2 s, episodes shortening 65 → 52. Gating + body-rate cost + discount 0.995 → r3 stepped clearly (20 mm lifts). P-ADR-008. | undecided |
| L11 | Reward the swing itself (the lifted foot advancing relative to the planted one) and charge a planted foot for sliding; that pays for steps rather than for any motion that moves the body. | Stride term `tanh(Δz)·tanh(Δvx)` and slip charge in place from r1 (P-ADR-007); with hover charge after r9's buzz. Final reward carries stride, slip, hover; pass has slip share ≤ 0.19, step_count_ratio 1.04–1.5. P-ADR-007, P-ADR-010, P-ADR-011. | undecided |
| L12 | Anti-shuffle charges have a ceiling: overweighted, they make standing still the best policy. Raise them in small steps and replay after each. | r10: slip ×3 plus a hover charge froze the policy standing (5–10 mm/s, no steps, all 6 seeds) → moderated to slip ×1.5, hover ×0.75 in r11. P-ADR-010. **Dead end recorded.** | undecided |
| L13 | Charge heading/yaw drift and left–right asymmetry explicitly when the evaluation bounds heading. | r11 i300 evaluation: heading 37–59° on 10/10 seeds, step_count_ratio up to 3 (lopsided). Yaw cost + hip common-mode pitch charge in r13 → heading 19.5–23.9°, ratio 1.04–1.5, 10/10 pass. P-ADR-010, P-ADR-011. | undecided |
| L14 | Keep checkpoints on and pick the policy by replaying checkpoints, not by taking the last iteration. | All 13 runs trained with `checkpoint_every` 20. r4 was warm-started from r3's *steadier i40*, not its runaway i100; the passing policy is r13's i140 checkpoint, stopped early. P-ADR-008, P-ADR-011, `runs/*/run.json`. | undecided |
| L15 | Warm-start from a checkpoint for reward, episode or disturbance changes; cold-start after any change to the model or to what the policy reads or emits. | Warm starts r4, r5, r7, r10, r12, r13 carried balance forward (r13 from r11 i380 passed at i140). r8 *failed*: "a curriculum step may not change what the network reads or emits"; model change (twin keel) forced r9 cold. P-ADR-009, `runs/walk-r8/training-status.json`. | undecided |
| L16 | Do not tighten the command filter on a warm start; a policy balanced through one filter cannot balance through a stronger one. | r6: filter 0.5 → 0.35 on a warm start collapsed episodes ~240 → ~35 steps in 15 iterations → restarted at 0.5. P-ADR-009, `runs/walk-r6`. | undecided |
| L17 | Judge a checkpoint under the evaluator's own conditions (its reset perturbations and its step rule), not a friendlier replay. | r4 i200: naive replay walked 8/8 at ~110 mm/s; evaluation failed 0/10 (tipped 1.4–6 s, heading up to 92°, 0 counted steps) because the evaluator's reset tilts ≤ 2° and spins ≤ 20°/s and counts a step only at ≥ 0.1 s airborne and 35 mm advance. P-ADR-008. | undecided |
| L18 | (Tool fact, not a design rule.) The evaluator and rollout ignore the policy's recorded `action_filter_alpha`, so a filtered policy is evaluated unfiltered. | r11 i300 filtered replay 8/8 at 15–29° heading; evaluation, and an unfiltered replay, 124–143 mm/s and 34–63°. r13 trained at alpha 1.0 as the workaround. P-ADR-010. **This is charter F1**; once fixed, the workaround is obsolete. | undecided |

### 5. Build and measurement

| # | Lesson, as a general rule | Evidence (change → effect) | Destination |
|---|---|---|---|
| L19 | Measure the volume of a solid built from tangent primitives; a fuse of tangent cylinders and spheres can silently drop pieces. Build such hulls another way (a slab with every edge filleted) and check the volume against the expected value. | Capsule-fuse foot lost its keel cylinders: 12,840 of 18,300 mm³. Slab with R − 0.01 fillets, lower half kept → 18,284 mm³. P-ADR-009, `script.py` foot block. | undecided |

## Weighed, no recorded effect

The charter names these areas; the project records the choice but not
what it did to the walk or the fit, so on this evidence they are not
lessons. They stay listed so a later unit can decide whether they enter
a style as **taste** (the owner liked the result) rather than as a rule.

| # | Choice | What the project records | Why not a lesson on this evidence | Destination |
|---|---|---|---|---|
| W1 | **Where the actuators sit:** the knee servo screwed to the thigh's inner face, case running up the thigh, shin hanging inboard of it. | P-ADR-002 and P-ADR-003 (carried from another of the owner's projects); `script.py` places the foot under the shin's tapered end from the knee face (`YF = YK - GAP - 3.0`). | No revision changed it and no run measured its effect. Its link to clearance (feet sit inboard of the knee face) is geometric, not measured. | undecided |
| W2 | **The look:** tapered thigh plate widening toward the knee with a tapered lightening window; round bosses at both joint axes; a shin lofted to taper in width *and* depth; a compact accent-coloured hull foot as its own part. | P-ADR-002 (style source named); `script.py` thigh, shin and foot blocks. Owner accepted the look (orun4 charter, Mission). | Effect is the owner's approval, not a measurement. Valid evidence for a *style*, not for a base rule. | undecided |
| W3 | Exposed mechanism over panelled skin; servo cases as the real volumes. | P-ADR-002. | No alternative tried. Taste. | undecided |
| W4 | Regulate supply to the actuator's rating (2S pack 8.4 V → 6 V regulator for a 7.4 V servo). | P-ADR-005. | Sound practice, but no recorded failure or measurement in this project. | undecided |
| W5 | Link length ≥ 2.5× hub diameter (110 and 120 mm on a 26 mm hub). | P-ADR-003 cites Cadex's existing guidance. | Already guidance; the project only complied. | undecided |
| W6 | A 3-DoF leg with no hip yaw drifts in heading (~20° over 10 s even at pass). | P-ADR-011 open items. | Observed, never changed; a hypothesis for the next design, not a lesson. | undecided |

## Tool defects the project surfaced (not lessons; routed to criteria)

| Defect | Evidence | Criterion |
|---|---|---|
| Evaluation and rollout ignore the trained command filter. | L18. | F1 |
| A run stopped on purpose reads as failed. | All twelve runs stopped through `stop-requested.json` have `training-status.json` `state: stopped` but `run.json` `status: failed`. | F2 |
