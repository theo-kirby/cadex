# orun12 O3 / Q1: the hind asymmetry is the policy's, not the simulation's

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 5).

## The test

O3 asks for three checks before any hardware or reward explanation of a
left/right difference. Two were already done (`heel2-clip.md`): the model
mirrors and the hind clip is symmetric. This is the third. Instead of
mirroring the engine's seed draws, it mirrors the **policy**:
`mirror_policy.py` writes pi'(o) = M_a pi(M_o o), a policy that sees the
world through the sagittal plane and acts mirrored, folded into the
network's normaliser and first and last layers, so the engine judges it
unchanged. On a model that mirrors, pi' runs the mirror image of pi's gait.
Judged on the same ten seeds:

- if the difference **swaps sides**, the policy learned a handed gait;
- if it **stays**, the simulation, the evaluation or the seed draws are
  handed.

```
pixi run python docs/probes/orun12/mirror_policy.py \
    RUN/train/cat_model-model.xml RUN/train/gallop.<tag>.cxpolicy RUN/train/gallop.mirror-<tag>.cxpolicy
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.mirror-<tag>.cxpolicy <name>m
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/<name> .../<name>m
```

Each joint's sign comes from its world axis in the keyframe, and the script
refuses a sign that disagrees with the action ranges. The pitch joints have
sign −1 between their partners, and so do the haa and scap joints,
`j_spine_yaw` and `j_tail2`. `j_spine` and `j_tail1` have sign +1. The IMU
quaternion maps to (w, −x, y, −z) and the gyro to (−x, y, −z). The scan
points swap y for −y, and the clip phase is unchanged. On each policy's 32
witness samples, the engine's forward pass on the new weights equals
M_a pi(M_o o) to 4e-14.

## Result: every seed swaps sides

Hind heel values, left / right, medians over seeds (`legs.py`):

| evaluation | hock down LH / RH | hock at toe-off | heel stance height mm | overreach mm | touchdown Hz | top 2 s m/s (med) |
|---|---|---|---|---|---|---|
| v07-g1-25 | 0.28 / 0.03 | 0.19 / 0.01 | 6 / 24 | −322 / −418 | 3.17 / 3.44 | 0.69 |
| v07-g1-25 mirror | 0.04 / 0.27 | 0.03 / 0.21 | 25 / 7 | −419 / −317 | 3.44 / 3.11 | 0.69 |
| heel2-s1-25 | 0.12 / 0.04 | 0.07 / 0.05 | 14 / 31 | −351 / −407 | 3.00 / 3.33 | 0.71 |
| heel2-s1-25 mirror | 0.06 / 0.12 | 0.07 / 0.09 | 30 / 15 | −410 / −337 | 3.33 / 3.00 | 0.77 |
| v07-g1-100 | 0.00 / 0.00 | 0.00 / 0.00 | 31 / 75 | 358 / 234 | 2.33 / 2.44 | 3.22 |
| v07-g1-100 mirror | 0.00 / 0.00 | 0.00 / 0.00 | 76 / 31 | 236 / 359 | 2.44 / 2.33 | 3.22 |

Per seed, 1001–1010, LH / RH heel-down share (heel height in mm at 100):

```
v07-g1-25      0.28/0.02 0.27/0.04 0.25/0.03 0.23/0.02 0.26/0.04 0.35/0.04 0.29/0.03 0.30/0.02 0.27/0.05 0.30/0.01
v07-g1-25m     0.06/0.31 0.01/0.30 0.04/0.25 0.03/0.25 0.02/0.31 0.04/0.27 0.07/0.22 0.05/0.24 0.03/0.26 0.05/0.29
heel2-s1-25    0.17/0.03 0.18/0.00 0.11/0.05 0.12/0.08 0.16/0.03 0.11/0.07 0.11/0.04 0.08/0.05 0.13/0.06 0.12/0.03
heel2-s1-25m   0.08/0.13 0.06/0.12 0.07/0.09 0.04/0.15 0.04/0.14 0.03/0.12 0.08/0.09 0.06/0.11 0.05/0.12 0.08/0.09
v07-g1-100     31/75 31/73 31/74 31/75 31/73 31/75 31/77 31/76 32/78 31/78
v07-g1-100m    76/31 74/31 73/30 77/31 78/30 76/31 74/30 76/30 77/31 78/31
```

On all thirty seed pairs the leg that keeps its heel lower swaps sides. The
mirrored values match the original's opposite leg to within a few
hundredths and 1–2 mm. Speed, torque (the worst drive's RMS is 1.31–2.07×
rated, swapping `j_wrist_l` for `j_wrist_r`), the loop gap (2.7–3.5 mm)
and falls (none) are unchanged. All six evaluations score 0/10 with a peak
margin of 0.00. Every seed has the same handedness, so the seed draws do
not cause it, and mirroring the draws would add nothing.

**The model, the simulation and the evaluation are symmetric. The
difference between the left and right hind is a handed gait that the
policy learned.** It needs neither a reward explanation nor a hardware
one. Between them, this test, `mirror.py` and the hind clip check close
O3's three checks.

## Where the handedness can come from, and what is not yet known

- **The clip is handed at the fore.** The hinds land together, but RF lands
  one sample (20 ms) before LF:

  ```
  LF 000000000000111100000
  RF 000000000001111000000
  LH 111110000000000000000
  RH 111110000000000000000
  ```

- **v07-g1 and heel2-s1 both trained from trainer seed 0.** They start from
  the same initial network, so their shared left-hind preference is one
  sample, not two.

Which of these sets the side is still open. A cold screen with a different
trainer seed, or with the fore lead swapped to LF, would separate them. If
the side follows the seed, the handedness is symmetry breaking. If it
follows the clip, the fore lead sets it.

A fix that works either way is policy-only (O1): train with mirror
symmetry, using mirrored samples or a mirrored-pair loss, or use a fore
schedule with no lead. This report only measures; it changes nothing.

Caveat: on `v07-g1-100 mirror`, `legs.py` reports 0/210 rotary strides and
a stride rate of 3.85 Hz. It clocks strides on the left fore's landings,
and in the mirror that is the paw that taps (`RF` taps in the original). A
handed gait needs the stride clocked on the non-tapping fore.
