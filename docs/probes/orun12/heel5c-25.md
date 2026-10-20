# orun12 P1 (O2a): heel5c-s1 at 25, the right heel passes and the left does not

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 16).

heel5c-s1 continues heel5-s1 (`heel5-final.md`) on its own task
(`816db7e7`, revision `44411418`), from its final policy (`42494591`):
105 iterations (5 critic-only), 4096 envs, seed 0, lr 3e-4. It runs at
69 s an iteration (1,724 s to iteration 25), so it ends at about 05:55 on
2026-10-20. Its first checkpoint (`gallop.000025.cxpolicy`, `b906406d`,
about 120 actor iterations in total) was judged on the bundle's
`gallop_spec`, seeds 1001–1010, on the CPU:

```
CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000025.cxpolicy heel5c-s1-25
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/{heel5-s1-100,heel5c-s1-25}
python3 docs/probes/orun12/paw_pin.py ~/cadex-projects/feline-v07/evaluations/{heel5-s1-100,heel5c-s1-25}
pixi run python docs/probes/orun12/stance_pose.py RUN/train/cat_model-model.xml \
    ~/cadex-projects/feline-v07/evaluations/heel5c-s1-25
```

| checkpoint | pass | hock down LH / RH | at toe-off LH / RH | heel mm LH / RH | metatarsus pitch LH / RH | top 2 s m/s min / med / max | touchdown Hz LH / RH | stride mm LH / RH | overreach mm LH / RH | flight share / s | rotary | no_tap | worst RMS/rated | peak margin | loop gap mm | pin >900 deg/s LH / RH |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| heel5-s1-100 | 0/10 | 0.37 / 0.36 | 0.84 / 0.57 | 3 / 2 | – | 3.17 / 3.21 / 3.25 | 2.33 / 2.44 | 1306 / 1305 | 391 / 366 | 1.00 / 0.240 | 145/181 | 7/10 (1.03) | 2.12 (j_spine) | 0.00 | 3.3 | 0.14 / 0.14 |
| **heel5c-s1-25** | 0/10 | **0.35 / 0.48** | **0.74 / 0.93** | 6 / 1 | 13 / 9 | 3.00 / 3.15 / 3.21 | 2.33 / 2.33 | 1255 / 1255 | 346 / 338 | 1.00 / 0.240 | 172/178 | 5/10 (1.10) | 2.11 (j_spine) | 0.00 | 2.8 | 0.14 / 0.15 |

It fails `top_speed`, `hock_down`, `hock_at_toeoff` and `no_tap` (5/10).
`completes`, `no_fall`, `upright`, `straight`, `every_stride` and
`overreach` pass 10/10.

Per seed, per leg (P1 needs each leg on 8 of 10):

| checkpoint | leg | hock_down ≥ 0.40 | heel share per seed | hock_at_toeoff = 1 | toe-off share per seed |
|---|---|---|---|---|---|
| heel5-s1-100 | LH | 0/10 | 0.36–0.40 | 0/10 | 0.77–0.95 |
| heel5-s1-100 | RH | 2/10 | 0.30–0.43 | 0/10 | 0.43–0.82 |
| heel5c-s1-25 | LH | 0/10 | 0.32–0.36 | 0/10 | 0.62–0.86 |
| heel5c-s1-25 | RH | **10/10** | 0.44–0.53 | 2/10 | 0.77–1.00 |

- **This is the first time a hind leg passes `hock_down` on all 10 seeds**,
  and two seeds pass `hock_at_toeoff` on the right. The left leg went the
  other way: its heel share fell from 0.37 to 0.35 and its toe-off from
  0.84 to 0.74. This is the same trade heel3-s1 showed with the legs
  swapped (`heel3-final.md`).
- Left and right are 27% apart on heel share and 20% on toe-off, so they
  are not alike (Q1's bar is 20%). Stride is 0% apart and touchdown rate
  0%. On heel5-s1-100 the heel share was 3% apart.
- The heel again follows the metatarsus pitch alone. Stance frames at 5–10°
  have the heel down 0.86 of the time, and from 10° up never. The right
  stance metatarsus median is 9° and the left 13°: the left stands just
  above the line.
- Form improved: 172 of 178 ordered strides are rotary (was 145/181), and
  the loop gap is 2.8 mm (was 3.3). Speed fell slightly to 3.15 m/s, and
  `no_tap` went from 7/10 to 5/10 (median 1.10, at the bar).
- O9 still fails: the paw pin snaps faster than 900°/s on 14–15% of frames.
  heel7-s1 (`heel7-plan.md`) tests `pin_damp` 3.0.

Verdict: heel5c-s1 continues and is judged at 50, 75 and 100. The left
heel is the gap to P1: about 0.05 of heel share and about 3° of metatarsus
pitch. The speed command is not raised. Before any symmetry fix, O3's
checks come first. On the same model and task, heel5-s1-100's heels were
3% apart, so this spread came with training. It did not come from the
model.
