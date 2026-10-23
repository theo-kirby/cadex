# orun12 Q2 (O9): the hind paw pin's damping, a measured candidate

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 14).
Not trained on: the heel comes first (O2a), and the critic held it until P1
moves.

`paw_pin.py` (`heel6-25.md`) read the passive hind paw pin (`j_pawpin_*`)
snapping faster than 900°/s on 8–15% of evaluation frames and overrunning
its −24°/+100° stops by 13–14°, on every judged v07 policy. O1 lets the loop
tune the pin's damping (`pin_damp`, a declared parameter, 0–5 N·mm·s/deg)
and its stop (`limit_time_constant_s`, impedance). This probe measures what
each would do, on the trained model, before any of them is trained on.

```
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun12/pin_tune.py \
    ~/cadex-projects/feline-v07/runs/heel6-s1/train/cat_model-model.xml
```

It plays the pin alone in the run's MJCF: every other degree of freedom held
at the keyframe each step, gravity and contacts off, the paw's own inertia
about the pin (1,222 g·cm², both legs). `snap` starts the pin at its spring
rest at 2,000°/s toward the toes-up stop. `loaded` starts it at rest under a
constant toes-up torque, the floor's push in stance.

| candidate (both legs alike) | ζ free | snap: past stop deg | snap: deg/s 20 ms on | 0.5 N·m: peak deg/s / past stop | 1 N·m | 2 N·m |
|---|---|---|---|---|---|---|
| **now**: pin_damp 0.4, τ 4 ms | 1.53 | 0.0 | 31 | 988 / 0.0 | 1996 / 3.0 | 4003 / 5.2 |
| pin_damp 1.5 | 5.7 | 0.0 | 12 | 310 / 0.0 | 623 / 0.9 | 1250 / 2.9 |
| pin_damp 3.0 | 11.5 | 0.0 | 5 | 160 / 0.0 | 321 / 0.9 | 643 / 2.6 |
| pin_damp 5.0 (max) | 19.1 | 0.0 | 2 | 97 / 0.0 | 195 / 0.0 | 391 / 2.2 |
| pin_damp 0.4, stop impedance 0.99/0.999 | 1.53 | 0.0 | 31 | 988 / 0.0 | 1996 / 2.9 | 4003 / 4.8 |
| pin_damp 3.0, stop impedance 0.99/0.999 | 11.5 | 0.0 | 5 | 160 / 0.0 | 321 / 0.8 | 643 / 2.3 |

What it shows:

- **The pin does not flap by itself.** Free, it is already overdamped
  (ζ 1.53). A 2,000°/s kick dies within one trace frame and never reaches
  its stop. The snaps on the traces are **forced**: the floor drives the
  pin, and its rate is about load ÷ damping (1 N·m → 2,000°/s at 0.4). The
  traces' 1,500–2,100°/s worst rates fit about 1 N·m on the paw.
- **Damping is the lever.** pin_damp 3.0 holds a 1 N·m push to 321°/s,
  under the 900°/s line, and a 2 N·m push to 643°/s. 1.5 still lets 2 N·m
  through at 1,250°/s.
- **The stop is not.** τ is already at MuJoCo's floor (2 × the 2 ms step),
  and raising the stop's impedance to 0.99/0.999 takes 0.1–0.4° off the
  overrun. A steady 2 N·m overruns by only 5°. The traces' 13–14° must come
  from larger, shorter loads (landing) than this probe applies. It does
  not reproduce them, so it does not claim to fix them.

**Candidate:** `--set pin_damp=3.0`, nothing else. It is a declared
parameter inside its range (O1). Its cost is unmeasured: a slower pin lays
the paw flat more slowly at touchdown, which could move the heel either
way. So it goes to a screen only once P1 moves. It is then judged with
`paw_pin.py` for the snap share, and `legs.py` for the heel share.
