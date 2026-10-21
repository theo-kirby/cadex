# orun13 P1/O5: the RH toes-up foot is the policy's hand, and g4-peak at 25 fails its keep rule

Verified against source: 2026-10-21. Frozen evidence (orun13, iteration 7).

## 1. g3-flat-50's RH foot under the mirror (O5)

`g3-flat-50.md` left the RH foot at 0.11 heel share, with 0.87 of its
heel-down frames toes-up (heel down, toes off the floor). Before adding a
lever, the mirror tests were run on g3-flat's final policy (`28e10c6c`),
as `g2-heel5-50.md` ran them:

```
pixi run python docs/probes/orun12/mirror_policy.py RUN/train/cat_model-model.xml \
    RUN/train/gallop.cxpolicy RUN/train/gallop.mirror-50.cxpolicy
PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py ~/cadex-projects/leo RUN/train \
    RUN/train/gallop.mirror-50.cxpolicy g3-flat-50m
```

The mirror's forward pass equals M_a π(M_o o) to 4.3e-14 on 32 witness
samples. The model already mirrors (`g2-heel5-50.md`: under 10 g of
panel mass apart).

| measure (median over seeds 1001–1010) | g3-flat-50 LH / RH | mirror LH / RH |
|---|---|---|
| engine heel share of stance | 0.39 / 0.11 | 0.13 / 0.40 |
| heel at toe-off | 0.50 / 0.24 | 0.28 / 0.43 |
| heel mm in stance | 2 / 12 | 11 / 2 |
| heel-down frames flat / toes-up (`spine_foot.py`) | 0.68 / 0.32 — 0.13 / 0.87 | 0.14 / 0.86 — 0.73 / 0.27 |
| on-ground flat / toes-up / toe (`heel_band.py`) | 0.33 / 0.16 / 0.51 — 0.07 / 0.42 / 0.51 | 0.07 / 0.42 / 0.51 — 0.35 / 0.13 / 0.52 |
| median sole pitch when toes-up | +1.4° — −7.9° | −8.1° — −0.2° |
| stride mm | 1130 / 1121 | 1114 / 1120 |
| overreach mm | 572 / 516 | 491 / 563 |

The rest is unchanged: 2.78 m/s (2.65–2.87) against 2.80, P1 0/10
(`hock_down` 0.128, `hock_at_toeoff` 0.277), `no_tap` 1.21 on both,
`overreach` 10/10, flight 0.22 s, spine 36.9° a stride with 0.00 at a
stop, j_spine 1.82× rated with peak margin 0, loop gap 4.5 mm.
`straight` is 9/10 (18.6°) against 10/10.

**The toes-up foot moves to the left under the mirror.** It is a handed
habit the policy learned, as the heel split was on g2-heel5-50. It is not
the model.

**Nor is it the reward.** `heel_expr.py` sets the model to each of the
21 clip samples and evaluates heel_pitch's per-leg angle from the
trainer's observed channels next to each paw's world pitch. Both legs read
the real sole at a constant +63.9° offset on every sample. The clip asks
the same of both legs: each heel is flat (+4.48°) on 4 of its 5 stance
samples. LH lands at +22.9° and RH at +32.2°, the same
toes-down touchdown.

**Why nothing corrected it.** The ≤10° band that g3-flat trained on pays
a toes-up sole in full. On g3-flat-50's on-ground frames it pays the
toes-up RH 0.88 a frame and the LH 0.90 (`heel_band.py`, "pay now"). The
policy had no gradient towards a flat RH. The peaked band pays them 0.31
and 0.62. That is the case for g4-peak, the only lever aimed at this
fault.

## 2. g4-peak at 25 (`gallop.000025.cxpolicy`)

This is g3-flat's task with `heel_pitch` peaked on the flat sole
(`g3-flat-50.md`), revision `b4680361`, cold, 4096 envs, seed 0. It was
judged at 25 against g3-flat at 25 (same model XML, same everything but
the band). The tools are `orun11/judge.py`, `orun12/legs.py`,
`orun13/spine_foot.py`, `orun13/heel_band.py` and `orun13/p2_lag.py`.

| evaluation | pass | top 2 s m/s min / med / max | straight | hock_down LH / RH | at toe-off LH / RH | heel-down frames flat LH / RH | toes-up LH / RH | heel mm LH / RH | no_tap | every_stride | overreach mm LH / RH | stride mm LH / RH | touchdown Hz LH / RH | flight share, s | worst RMS/rated | peak margin | loop gap mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| g3-flat-25 | 0/10 | 0.58 / 0.62 / 0.86 | 10/10 (21.3) | 0.23 / 0.11 | 0.16 / 0.04 | 0.85 / 0.62 | 0.15 / 0.38 | 4 / 7 | 0/10 (1.73) | 9/10 | −152 / −148 | 217 / 228 | 3.22 / 4.00 | 0.66, 0.020 | 2.24 (j_tail1) | 0.00 | 2.2 |
| g4-peak-25 | 0/10 | 0.81 / 0.94 / 1.16 | 7/10 (22.3) | 0.13 / 0.14 | 0.10 / 0.00 | 0.49 / 0.73 | 0.51 / 0.27 | 9 / 10 | 1/10 (1.93) | 9/10 | −168 / −198 | 203 / 199 | 2.89 / 4.28 | 0.69, 0.040 | 1.88 (j_tail1) | 0.00 | 2.1 |

- **The keep rule is not met.** The rule set when g4-peak launched was
  that both heels rise at no lower speed. The RH heel share rose from
  0.11 to 0.14, but the LH fell from 0.23 to 0.13. The heels now sit
  9–10 mm up in stance, against 4 and 7. Toe stances (heel up) are 0.75
  and 0.83 of on-ground frames, against 0.73 and 0.82.
- **Speed rose**, from 0.62 to 0.94 m/s at the median. `completes` and
  `upright` are 9/10 and `straight` 7/10.
- **The toes-up habit changed sides at 25.** It is 0.51 / 0.27 of
  heel-down frames, against 0.15 / 0.38. The peaked band has not removed
  it this early. Neither policy has a gait yet: hind strides of
  200–230 mm, fore paws stepping 1.7–1.9 times a hind stride.
- **Footfalls.** The fore and hind lags are 0.365 and 0.391 of a cycle,
  with the pairs alternating, not galloping. One seed in ten is rotary.
- **Spine.** 24.8° a stride, 0.21 of frames at a stop, cable within
  0.30°.
- The trainer read 15.9 reward/step at iteration 24. It was rising from
  12.8 at 16, after the cold dip.

**Decision: run g4-peak on to 50, then judge it against g3-flat-50.**
This departs from the 25-iteration rule. The fault it targets, RH
toes-up 0.87, appeared only between 25 and 50 on g3-flat: at 25,
g3-flat's RH was toes-up 0.38. Both policies shuffle at 25, so 25 cannot
yet show toes-up in a gallop. The other 25 iterations take about 22
minutes of GPU, and nothing else is queued. g4-peak is kept at 50 only if
both of these hold against g3-flat-50:
- the RH's toes-up share of heel-down frames falls well below 0.87, with
  both heel shares at or above 0.39 / 0.11;
- speed stays near 2.80 m/s.

Otherwise it is a dead end, and the band goes back to the ≤10° form.
