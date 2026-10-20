# orun12 P1 (O2a): heel2-s1 stopped at 75, heel3-s1 pays the heel first

Verified against source: 2026-10-19. Frozen evidence (orun12, iteration 6).

## heel2-s1 is a dead end: the clip alone does not lay the heel down

heel2-s1 (`26f8972b`, clip heel from 0.2 of stance, cold, 8192 envs) was
stopped by request after its iteration-75 checkpoint (O2a lets a heel screen
that is not laying the heel down stop early). Each checkpoint was judged on
the bundle's `gallop_spec`, seeds 1001–1010, on the CPU:

```
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py \
    ~/cadex-projects/feline-v07 RUN/train RUN/train/gallop.000075.cxpolicy heel2-s1-75
python3 docs/probes/orun12/legs.py ~/cadex-projects/feline-v07/evaluations/heel2-s1-{25,50,75}
```

| checkpoint | pass | hock down LH / RH | heel height mm LH / RH | top 2 s m/s (median) | overreach mm LH / RH | worst RMS/rated | peak margin |
|---|---|---|---|---|---|---|---|
| 25 | 0/10 | 0.12 / 0.04 | 14 / 31 | 0.71 | −351 / −407 | 1.35 (j_wrist_l) | 0.00 |
| 50 | 0/10 | 0.03 / 0.11 | 24 / 19 | 2.21 | 88 / 10 | 1.75 (j_spine) | 0.00 |
| 75 | 0/10 | 0.00 / 0.00 | 35 / 82 | 3.04 | 327 / 135 | 2.15 (j_spine) | 0.00 |

`hock_at_toeoff` is 0.00 on both legs at 50 and 75. As speed rose, the
heels came up. This is the same course v07-g1 took (0.00 / 0.00 at 100,
31 / 75 mm, `b1-baseline.md`). At 75 the form improves elsewhere: overreach
passes on 10/10, flight comes on every stride (0.18 s) and no_tap passes
on 3/10.

## Why the heel lost: the speed pay

Both bundles pay `track_speed` at weight 20, linear in forward speed up to
**7 m/s**. The clip runs at **1.68 m/s** (0.7 m at 2.4 Hz). So a policy
earns more for every m/s it adds past the clip. The only heel pay was
`plantigrade` at 4, for the paw and heel touching together. At 3 m/s the
speed term pays about 8.6 a step. At most 4 a step goes to the heel.

## heel3-s1: the heel paid in the clip's stance, speed capped at 2 m/s

feline-v07 was rebuilt with two task changes and nothing else (O1, O2a):

| | before (`ee2168d2`) | heel3-s1 (`ac32d3b0`, digest `814e5213`) |
|---|---|---|
| `plantigrade` | `(chl_down * khl_down + chr_down * khr_down) / 2`, weight 4 | `(ref_lh_down * khl_down + ref_rh_down * khr_down) / 2`, weight `plant_w` 10 |
| `track_speed` | linear to `sprint_speed` 7000 mm/s | linear to `sprint_speed` 2000 mm/s (the parameter's floor) |

- The heel term is now paid while the clip has that hind foot in stance.
  At `heel_from` 0.2 the clip lays the heel on 0.8 of the stance. No paw
  contact is required.
- The speed cap follows O2a: "do not push the speed command up while the
  heel is still off the floor".
- The model is `ee2168d2`'s, so the chest box is folded in (`o9-chest.md`,
  conaffinity 11). The clip is unchanged: heel_from 0.2, duty 0.2, 0.7 m
  at 2.4 Hz.
- The bundle keeps 17 terms.

The screen is cold, 100 iterations, at **4096 envs** (O2a allows fewer for
a heel screen), seed 0. It was queued with `queue_run.py --envs 4096`
behind heel2-s1, and it launched when heel2-s1 stopped.

The screen changes two terms at once on purpose. The question is whether
any task change puts both heels down. If it does, the next screen takes
one of the two changes back to see which term earned its place (O5).
