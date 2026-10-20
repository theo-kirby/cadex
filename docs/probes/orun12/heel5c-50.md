# orun12 P1 (O2a): heel5c-s1 at 50, both heels past 0.40; toe-off is the gap

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 17).

heel5c-s1 continues heel5-s1 on its own task (`816db7e7`, revision
`44411418`; see `heel5c-25.md`). Its second checkpoint
(`gallop.000050.cxpolicy`, `05c53ba6`, about 145 actor iterations in all)
was judged on the bundle's `gallop_spec`, seeds 1001–1010, on the CPU. Its
mirror image (`mirror_policy.py`, witness error 4.6e-14) was judged on the
same seeds:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000050.cxpolicy heel5c-s1-50
pixi run python docs/probes/orun12/mirror_policy.py RUN/train/cat_model-model.xml \
    RUN/train/gallop.000050.cxpolicy /tmp/o12/gallop.mirror-000050.cxpolicy
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train /tmp/o12/gallop.mirror-000050.cxpolicy heel5c-s1-50m
python3 docs/probes/orun12/legs.py EVALS/{heel5c-s1-25,heel5c-s1-50,heel5c-s1-50m}
python3 docs/probes/orun12/paw_pin.py EVALS/{heel5c-s1-25,heel5c-s1-50,heel5c-s1-50m}
pixi run python docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml EVALS/heel5c-s1-50
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight share / s | rotary | no_tap | worst RMS/rated | peak margin | loop gap mm | pin >900 deg/s LH / RH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5c-s1-25 | 0/10 | 0.35 / 0.48 | 0.74 / 0.93 | 6 / 1 | 13 / 9 | 3.00 / 3.15 / 3.21 | 2.33 / 2.33 | 1255 / 1255 | 346 / 338 | 1.00 / 0.240 | 172/178 | 5/10 (1.10) | 2.11 (j_spine) | 0.00 | 2.8 | 0.14 / 0.15 |
| **heel5c-s1-50** | 0/10 | **0.44 / 0.51** | **0.82 / 0.95** | 3 / 1 | 10 / 9 | 3.05 / 3.22 / 3.27 | 2.33 / 2.44 | 1290 / 1300 | 351 / 365 | 1.00 / 0.240 | 107/175 | 6/10 (1.03) | 2.03 (j_spine) | 0.00 | 2.7 | 0.11 / 0.15 |
| heel5c-s1-50 mirror | 0/10 | 0.47 / 0.43 | 0.93 / 0.84 | 1 / 3 | – | 3.04 / 3.16 / 3.30 | 2.33 / 2.33 | 1275 / 1277 | 364 / 343 | 1.00 / 0.240 | 2/204 | 4/10 (1.14) | 2.02 (j_spine) | 0.00 | 2.6 | 0.14 / 0.11 |

It fails `top_speed`, `hock_at_toeoff` (0/10) and `no_tap` (6/10), and
`hock_down` on seed 1007. `completes`, `no_fall`, `upright`, `straight`,
`every_stride` and `overreach` pass 10/10.

Per seed, per leg: heel share / toe-off share (toe-offs with the heel down
of all toe-offs). P1 needs share ≥ 0.40 and toe-off = 1 on each leg, on 8
of 10 seeds:

```
seed   LH                    RH
1001   0.44 / 0.81 (17/21)   0.53 / 1.00 (21/21)
1002   0.46 / 0.90 (19/21)   0.48 / 0.95 (20/21)
1003   0.43 / 0.81 (17/21)   0.52 / 0.95 (20/21)
1004   0.43 / 0.81 (17/21)   0.54 / 0.95 (20/21)
1005   0.43 / 0.82 (18/22)   0.48 / 0.86 (19/22)
1006   0.44 / 0.82 (18/22)   0.48 / 1.00 (22/22)
1007   0.40 / 0.77 (17/22)   0.49 / 1.00 (22/22)   (LH 0.399, fails)
1008   0.44 / 0.91 (20/22)   0.49 / 0.86 (19/22)
1009   0.44 / 0.90 (19/21)   0.52 / 1.00 (22/22)
1010   0.44 / 0.91 (20/22)   0.52 / 0.95 (21/22)
```

| leg | hock_down ≥ 0.40 | hock_at_toeoff = 1 |
|---|---|---|
| LH | 9/10 (0.40–0.46) | 0/10 (0.77–0.91) |
| RH | **10/10** (0.48–0.54) | 4/10 (0.86–1.00) |

- **The left heel climbed back**, from 0.35 to 0.44. Both legs now pass
  `hock_down` on at least 9 of 10 seeds. That is half of P1 on one policy.
  The other half, `hock_at_toeoff`, still fails: the left lifts its heel
  before 1–5 of its 21–22 toe-offs on every seed, and the right on 0–3.
- The left/right spread fell from 27% to 14% on heel share and from 20% to
  14% on toe-off. Stride is 1% apart and touchdown rate 5%, so all three of
  Q1's measures are inside 20% on this checkpoint. P1 does not pass yet, so
  Q1 is not judged on it.
- **The mirror check (O3) says the remaining handedness is the policy's.**
  Mirrored, the lower heel moves to the other leg (0.44 / 0.51 becomes
  0.47 / 0.43, toe-off 0.82 / 0.95 becomes 0.93 / 0.84), on the model
  `mirror.py` showed symmetric. Speed, torque, loop gap and falls are
  unchanged. A symmetry term is still not needed to explain anything. The
  spread is inside Q1's bar and is shrinking with training.
- The heel still follows metatarsus pitch alone. Stance frames at 5–10°
  have the heel down 0.89 of the time, and from 10° up never. The stance
  medians are 10° (left) and 9° (right). The left stands on the line.
- Form: overreach 10/10 and flight every stride hold. Rotary fell from
  172/178 to 107/175, and on the mirror to 2/204. The lead is close to a
  tie between rotary and transverse at this checkpoint, so the rotary count
  is not stable. P2 is not worked until P1 passes.
- O4: the worst drive is `j_spine` at 2.03× rated RMS, and the peak margin is
  0.00 (a drive at its clamp, as on every v07 policy).
- O9 still fails: the paw pin snaps faster than 900°/s on 11–15% of frames.
  The loop gap is 2.7 mm. heel7-s1 (`heel7-plan.md`) tests `pin_damp` 3.0.

Verdict: heel5c-s1 continues and is judged at 75 and 100 (about 05:55). It
is the P1 lead. The gap is toe-off: the heel has to stay down through the
last frame of stance on every stride, where it now does on 77–91% (left)
and 86–100% (right). The speed command is not raised. heel7-s1 is still
queued behind it (`--expect-revision de868f8f`).
