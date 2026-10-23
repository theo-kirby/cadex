# orun12 P1 (O2a): heel6-s1 at 25, the paw pin, and heel5-s1's continuation

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 13).

## heel6-s1 at 25: the flat clip alone stands on its toes

heel6-s1 (`d3b4e838`, task `a74fbf5a`; `heel6-flat.md`) is heel3-s1's task
on the `flat_feet` clip, without `heel_pitch`: cold, 4096 envs, seed 0. Its
iteration-25 checkpoint (`gallop.000025.cxpolicy`, `7ddb0109`) was judged
on the bundle's `gallop_spec`, seeds 1001–1010, on the CPU, while the run
went on:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000025.cxpolicy heel6-s1-25
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel{5,6}-s1-25
python3 docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel6-s1-25
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight s | no_tap | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5-s1-25 | 0/10 | 0.13 / 0.16 | 0.06 / 0.06 | 14 / 12 | 23 / 22 | 1.10 / 1.16 / 1.86 | 2.56 / 2.44 | 405 / 424 | −81 / −142 | 0.22 | 4/10 (1.11) | 1.43 (j_spine) | 0.00 | 3.8 |
| **heel6-s1-25** | 0/10 | **0.03 / 0.05** | **0.00 / 0.00** | **71 / 51** | **71 / 60** | 1.21 / 1.37 / 1.68 | 4.00 / 3.89 | 407 / 439 | −204 / −209 | 0.04 | 0/10 (1.74) | 1.62 (j_spine) | 0.00 | 3.9 |

At the same iteration, heel5-s1 had its metatarsus at 22–23° in stance with
the heel down on 0.13–0.16 of stance. heel6-s1 has it at 60–71°: the cat
stands on its toes. Its hind legs step at about 4 Hz, against 2.5 Hz for
heel5-s1. Only 0.71 of its strides have a flight phase, and 65 of its 140
ordered strides are rotary (`legs.py`: 120 unordered; heel5-s1-25 had 97 of
158, 51 unordered). Its clip asks for 7.5° in the heel-down
samples (`heel6-flat.md`). Without `heel_pitch`, nothing pays the policy to
follow that pitch at this stage.

The two runs are not yet comparable: heel3-s1 was also on its toes until
50. heel6-s1 goes on to 100, and its 50, 75 and 100 checkpoints decide
whether the flat clip moves the heel. Until then, there is no basis for
the `heel_pitch` + `flat_feet` warm start.

## The hind paw pin flaps and overruns its stops on every v07 policy

`paw_pin.py` reads the passive pin (`j_pawpin_*`; range −24° to +100°,
spring 0.46 N·m/rad about 36°, damping 0.023 N·m·s/rad) from the trace
placements. The pin is read as the paw's rotation relative to the
metatarsus about y. The off-axis residue is 0.0° on every frame, so the
reading is the hinge alone. Frames are 20 ms apart, so the rates are lower
bounds.

```
python3 docs/probes/orun12/paw_pin.py ~/cadex-projects/feline-v07/evaluations/{heel5-s1-25,heel5-s1-100,heel6-s1-25}
```

| evaluation | leg | pin deg median (min..max) | rate deg/s p99 / max | steps > 900 deg/s |
|---|---|---|---|---|
| heel5-s1-25 | LH | +37 (−34..+72) | 1518 / 1812 | 0.106 |
| heel5-s1-25 | RH | +38 (−34..+100) | 1468 / 1879 | 0.079 |
| heel5-s1-100 | LH | +43 (−31..+77) | 1740 / 1965 | 0.136 |
| heel5-s1-100 | RH | +48 (−33..+104) | 1722 / 2072 | 0.143 |
| heel6-s1-25 | LH | +38 (−37..+114) | 1409 / 2008 | 0.110 |
| heel6-s1-25 | RH | +34 (−37..+111) | 1589 / 2113 | 0.146 |

- The pin snaps at more than 900°/s, the flapping the owner saw on v06-g1,
  on 8–15% of frames. This holds on both clips and at every judged
  iteration. Laying the clip flat does not cause it. heel5-s1-100, the
  best heel so far, flaps the most.
- The pin runs past both of its stops by up to 13–14°: −37° against −24°,
  and +114° against +100°. The limit is soft (`solreflimit` 0.004).
- Both are tuning parameters that O1 allows the loop to change: pin
  damping, spring and stop stiffness. Both are Q2 (O9) items. They are
  measured here, not changed: the heel comes first (O2a).

## heel5-s1 continues on its own task

heel5-s1 was 0/10 at 100 with heels 0.37 / 0.36 and its reward still
rising (`heel5-final.md`), so by O7 it is extended. The accepted revision
had moved on to heel6's `d3b4e838`. It was put back with
`cadex revision restore 44411418`, which reported `exact` and
`same_geometry`. The retained `gallop` task is again `816db7e7`, with model
`a4d83920`, byte-equal to heel5-s1's. The trainer refuses an `--init-from`
policy whose task or model digest differs.

`queue_run.py` now takes `--init-from`, `--critic-warmup` and
`--learning-rate`. **heel5c-s1** is queued behind heel6-s1 (from 02:27:26,
`--expect-revision 44411418`). It starts from heel5-s1's final
`gallop.cxpolicy` (`42494591`): 105 iterations, the first 5 critic-only
(ADR-740), then 100 actor iterations at the run's own learning rate of
3e-4, for about 200 in all. It uses 4096 envs and seed 0, with a
checkpoint every 25. Its 25/50/75/100 checkpoints are heel5's iterations
of about 120/145/170/195. `budget_s` is 9,500: heel5-s1 took 70 s an
iteration, so 105 × 75 s × 1.2 ≈ 9,450.

The learning rate is the run's own, not the 3e-5 of a fine-tune. This is
the same task, and the same objective, continued. Watch the right leg's
toe-off share first: it is 0.57 at 100, against a bar of 1.0.
