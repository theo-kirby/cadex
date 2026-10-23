# orun12 P1 (O2a): heel6-s1 at 75 and 100, the flat clip alone is dominated

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 15).

heel6-s1 (`d3b4e838`, task `a74fbf5a`; `heel6-flat.md`, `heel6-25.md`,
`heel6-50.md`) is heel3-s1's task on the `flat_feet` clip, without
`heel_pitch`: cold, 4096 envs, seed 0. It finished its 100 iterations
(7,070 s, reward per step 37.0, still rising slowly). Its iteration-75
checkpoint (`gallop.000075.cxpolicy`, `24091708`) and its final policy
(`gallop.cxpolicy`, `0856cbb9`) were judged on the bundle's `gallop_spec`,
seeds 1001–1010, on the CPU:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000075.cxpolicy heel6-s1-75
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.cxpolicy heel6-s1-100
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/{heel6-s1-75,heel6-s1-100,heel5-s1-100}
pixi run python docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel6-s1-{75,100}
python3 docs/probes/orun12/paw_pin.py ~/cadex-projects/feline-v07/evaluations/heel6-s1-{75,100}
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight share / s | rotary | no_tap | worst RMS/rated | peak margin | loop gap mm | pin >900 deg/s LH / RH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel6-s1-50 | 0/10 | 0.08 / 0.10 | 0.02 / 0.04 | 21 / 23 | 32 / 33 | 2.81 / 2.87 / 2.97 | 2.50 / 2.61 | 1128 / 1146 | 254 / 272 | 1.00 / 0.155 | 45/132 | 0/10 (1.50) | 2.10 (j_spine) | 0.00 | 4.3 | 0.14 / 0.16 |
| heel6-s1-75 | 0/10 | 0.17 / 0.11 | 0.02 / 0.02 | 17 / 14 | 27 / 23 | 3.19 / 3.31 / 3.36 | 2.44 / 2.33 | 1327 / 1317 | 316 / 356 | 1.00 / 0.140 | 17/117 | 0/10 (1.49) | 2.15 (j_spine) | 0.00 | 3.4 | 0.12 / 0.11 |
| **heel6-s1-100** | 0/10 | **0.19 / 0.23** | **0.00 / 0.33** | **12 / 7** | **23 / 17** | 3.14 / 3.20 / 3.27 | 2.44 / 2.33 | 1276 / 1283 | 277 / 323 | 1.00 / 0.185 | 8/148 | 0/10 (1.28) | 2.12 (j_spine) | 0.00 | 3.6 | 0.12 / 0.12 |
| heel5-s1-100 | 0/10 | 0.37 / 0.36 | 0.84 / 0.57 | 3 / 2 | – | 3.17 / 3.21 / 3.25 | 2.33 / 2.44 | 1306 / 1305 | 391 / 366 | 1.00 / 0.240 | 145/181 | 7/10 (1.03) | 2.12 (j_spine) | 0.00 | 3.3 | – |

Every row fails `top_speed`, `hock_down`, `hock_at_toeoff` and `no_tap`;
`completes`, `no_fall`, `upright`, `straight`, `every_stride` and
`overreach` pass 10/10.

- The critic's dead-end rule (metatarsus above 30° and heels under 0.15 at
  100) does not fire. The metatarsus came down to 23/17°, and the heels rose
  to 0.19/0.23.
- The run is still dominated by heel5-s1 (`heel_pitch`) on every heel
  measure:
  - at 100 its heels are 0.19/0.23 against 0.37/0.36;
  - its toe-off is 0.00/0.33 against 0.84/0.57;
  - heel6-s1 at 100 is about where heel5-s1 was at 50–75;
  - its speed is the same (3.20 against 3.21 m/s).
- Its form is worse:
  - only 8 of its 148 ordered strides are rotary, against 145/181;
  - `no_tap` passes 0/10 against 7/10;
  - its overreach is shorter.
- The heel again follows the metatarsus pitch alone. Stance frames at
  5–10° have the heel down 0.77 of the time, and above 15° almost never
  (`stance_pose.py`, both checkpoints).
- Left and right are 17% apart on heel share, 1% on stride and 5% on
  touchdown rate. Toe-off is 0.00 against 0.33, so they are not alike there.
- O9 still fails:
  - the paw pin snaps faster than 900°/s on 11–12% of frames;
  - the loop gap is 3.4–3.6 mm, against the 2 mm bar.

Verdict: `flat_feet` without `heel_pitch` is not a dead end by the rule, but
it is dominated. It reaches heel5-s1's heel share about 25–50 iterations
later, with no toe-off and no rotary order, at the same speed. It is not
extended. The P1 lead stays heel5-s1 → heel5c-s1 (heel5-s1 continued on its
own task 816db7e7 to about 200), which started at 03:53 on 2026-10-20 as
heel6-s1 ended. A `flat_feet` clip combined with `heel_pitch` remains
untried. It would be a new task bundle, so it would train cold.
