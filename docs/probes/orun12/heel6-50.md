# orun12 P1 (O2a): heel6-s1 at 50, the flat clip still behind heel_pitch

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 14).

heel6-s1 (`d3b4e838`, task `a74fbf5a`; `heel6-flat.md`, `heel6-25.md`) is
heel3-s1's task on the `flat_feet` clip, with no `heel_pitch`: cold, 4096
envs, seed 0. Its iteration-50 checkpoint (`gallop.000050.cxpolicy`) was
judged on the bundle's `gallop_spec`, seeds 1001–1010, on the CPU, while the
run went on:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000050.cxpolicy heel6-s1-50
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/{heel5-s1-50,heel6-s1-25,heel6-s1-50}
pixi run python docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel6-s1-50
python3 docs/probes/orun12/paw_pin.py ~/cadex-projects/feline-v07/evaluations/heel6-s1-50
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight share / s | rotary | no_tap | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5-s1-50 | 0/10 | 0.19 / 0.18 | 0.32 / 0.09 | 11 / 8 | 18 / 18 | 2.90 / 2.99 / 3.11 | 2.44 / 2.44 | 1189 / 1203 | 339 / 314 | 1.00 / 0.180 | 117/149 | 0/10 (1.62) | 2.11 (j_spine) | 0.00 | 2.8 |
| heel6-s1-25 | 0/10 | 0.03 / 0.05 | 0.00 / 0.00 | 71 / 51 | 71 / 60 | 1.21 / 1.37 / 1.68 | 4.00 / 3.89 | 407 / 439 | −204 / −209 | 0.71 / 0.040 | 65/140 | 0/10 (1.74) | 1.62 (j_spine) | 0.00 | 3.9 |
| **heel6-s1-50** | 0/10 | **0.08 / 0.10** | **0.02 / 0.04** | **21 / 23** | **32 / 33** | 2.81 / 2.87 / 2.97 | 2.50 / 2.61 | 1128 / 1146 | 254 / 272 | 1.00 / 0.155 | 45/132 | 0/10 (1.50) | 2.10 (j_spine) | 0.00 | 4.3 |

- From 25 to 50, heel6-s1 came down off its toes: its stance metatarsus went
  from 71/60° to 32/33°, and its heel from 71/51 mm to 21/23 mm. Its gait
  turned into heel5-s1's: 2.5 Hz touchdowns, 1.1 m strides, overreach on
  10/10, and flight on every stride.
- It is still well behind heel5-s1 at the same iteration. Its heels are
  0.08/0.10 against 0.19/0.18, its toe-off 0.02/0.04 against 0.32/0.09, and
  its metatarsus is at 32° against 18°. Only 45 of its 132 ordered strides
  are rotary, against 117/149 for heel5-s1.
- The heel follows the metatarsus pitch alone, as it did on heel5
  (`heel5-pitch.md`). heel6-s1-50 has its heel down on 0.79 of stance
  frames with the metatarsus at 5–10°, on 0.27 at 10–15°, and on none
  above 15°. The flat clip asks for 7.5° in heel-down samples.
- The legs are alike: heel share 19% apart (on the 20% line), stride 2%,
  touchdown 4%.
- The paw pin snaps faster than 900°/s on 14% (LH) and 16% (RH) of frames.
  This is its worst share yet. See `pin-candidate.md`.
- The loop gap is 4.3 mm, against O9's 2 mm.

Verdict at 50: the flat clip alone moves the heel, but more slowly than
`heel_pitch` does. It is not a dead end yet. By the critic's rule, flat_feet
alone becomes a dead end if heel6-s1 at 100 still has its metatarsus above
30° and its heels under 0.15. 75 and 100 decide it, along with heel5c-s1's
first checkpoints.
