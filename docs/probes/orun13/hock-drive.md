# orun13 O1: the hind hock drive's torque or push-rod ratio — written up, not built

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 14).

`merry-orchard-6896` named the hind hock drive's torque, or its ratio
through the push-rod, as the next O1 lever. Under O1 a model change is
written up before any build: the measurement, the effect expected on the
open measure (`hock_at_toeoff`, 0/10 on every leo screen), and the
clearance risk. This is that write-up. Its conclusion is that the
measurement points the other way, so nothing is built.

## The drive today

| | leo-v02 hind hock |
|---|---|
| drive | CubeMars AK80-9 V3 (`HOCK_SKU`): 9 N·m rated, 22 N·m peak, 490 g, 98 mm × 38.5 mm |
| where | on the shin at the knee axis, output face inboard (`Y_HKD`, y 53) |
| linkage | a parallelogram: crank and horn both `LINK_R` = 35 mm, 45° below forward; **1:1** |
| travel | −70° (heel-side stop) to +40° |

## The measurement, and its sign

`hind_reach.py` on g7-hock75-50 and g4-peak-50 (`g7-hock75.md`, "The
hock in stance"): in flat and toe stance the hock drive's effort is at
peak (median 1.00 on three of four stance rows), and its command minus the
measured angle is **+13 to +79°**.

The sign settles what that means. In `hind_reach.py`'s left-leg sign, the
hock's −70° stop is the heel-side one, and the metatarsus pitch that
`heel_pitch` reads is `chest + 2·spine + hip − knee + hock + 63.9`
(`script.py`, `_META`): a more positive hock lifts the heel. The sole is
flat at +4.5° and a toe stance reads +8.5..+15°.

So a positive command error is **the drive pushing the heel up** — the
push-off — **and the body's weight on the foot holding it down.** The
drive is at peak pushing against the heel-down foot, not failing to hold
a heel-down command. `merry-orchard-6896`'s reading ("the drive cannot
hold the commanded heel-down hock under stance load") had the sign
backwards; the numbers it cites are right.

## Expected effect on `hock_at_toeoff`

`hock_at_toeoff` fails in two ways (`g4-peakc-25.md`, `toeoff_term.py`):
LH rolls onto its toes for a median of 3 frames before the lift, one more
than the 40 ms window allows; RH taps without laying the heel.

- **More torque** (an AK10-9 V3: 53 N·m peak, 2.4×; or a horn longer than
  the crank). With the command as it is, more heel-up torque lifts the heel
  sooner against the same weight. The roll before the lift lengthens, and
  the heel-down share falls. **Expected: `hock_at_toeoff` worse**, and
  `hock_down` too. The trained policy could learn a different command, but
  nothing measured says it would choose a heel-down toe-off with more
  authority to lift the heel.
- **Less torque or a reducing ratio** (a horn shorter than the crank).
  Weight would win sooner, and the heel would stay down to the lift. But
  push-off is where the gallop's speed comes from. The drive is at peak
  already, and every cat's speed has been torque-limited (orun6–orun11).
  It would trade speed (S1, S2) for P1 by weakening the actuator, which is
  what O1's "a drive at peak" example warns against. It also stretches the
  hock's travel at the drive and moves the 4-bar off its parallelogram,
  making the ratio vary with angle.

Neither direction is a change the measurement argues for. **Not built.**

## Clearance risk, for the record

- **AK10-9 at the hock.** It has the same 98 mm case but is 61.7 mm
  long, against 38.5 mm: 23.2 mm deeper inboard of `Y_HKD`. That leaves
  the two knees' drives about 60 mm apart, against about 106 mm today. It
  is 450 g heavier per leg at the knee, where swing inertia costs the
  most. The crank and rod (`yr0` = `Y_HKD` − 12) move inboard with it.
  New swept pairs against the opposite shin and the tail root are likely,
  and the baseline (16 static, 8 swept on v02.1) may not grow (O1).
- **A non-parallel linkage.** A horn longer or shorter than 35 mm changes
  where the rod's eyes sweep. At −70° the crank already works 30° off the
  rod (`script.py`, `RIGID_FOOT`). A ratio far from 1 would bring the
  dead point into the travel.

## What the measurement does argue for

The command, not the drive. The policy asks for push-off through the flat
stance, and the weight on the foot is what keeps the heel down. The levers
are on the policy side: where `heel_pitch` pays, and the clip's hock in
late stance. g8-gate (`g7c-hock75.md`) takes the first.
