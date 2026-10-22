# orun16 RL: what LH's mid-swing tap earns under sg-s7's terms, and two stronger levers scored

Verified against source: 2026-10-22. Frozen evidence (orun16, iteration 15).

sg-s6's `hind_scuff` (w −8) took LH's taps at 1.0 m/s from 0.88 to 0.64 a
clip stride in 25 iterations (`sg-s6-25.md`), short of its rule's 0.3, and
the 1000 hind lag still reads 30 ms. sg-s7 (`sg-s7-rules.md`) gates
`heel_sched` on the paw's contact, so a tap on the toes at 1.0 m/s now earns
the slow end's heel-up pay. Before a stronger tap lever is built, this
scores what a tap earns, summed over its frames against the same frames in
the air, under sg-s7's terms, on sg-s6-25's judged traces:

```
R=~/cadex-projects/leo/runs/sg-s6/train; E=~/cadex-projects/leo/evaluations
CUDA_VISIBLE_DEVICES= pixi run python docs/probes/orun16/tap_lever.py \
    ~/cadex-projects/leo/runs/v05-s1/train/gallop-task.json $R/gallop_sg-task.json \
    $R/cat_model-model.xml $E/sg-s6-25-{1000,1700,2400}
```

| cmd | leg | taps a clip stride | frames a tap | `track_contact` a tap | `heel_sched` (contact gate) a tap | `hind_scuff` a tap w −8 / w −16 | net a tap w −8 / w −16 | tap reset: seeds ended; median first fire s; share of firing frames on taps |
|---|---|---|---|---|---|---|---|---|
| 1000 | LH | **0.64** | 1.2 | −2.89 | **+1.29** | −4.62 / −9.24 | **−6.22 / −10.84** | **10/10; 1.17; 1.00** |
| 1000 | RH | 0.01 | 1.0 | −2.50 | 0.00 | 0 / 0 | −2.50 | ″ |
| 1700 | LH / RH | 0.00 / 0.00 | | | | 0 | | 0/10 |
| 2400 | LH / RH | 0.00 / 0.00 | | | | 0 | | 0/10 |

(1700 and 2400 have a handful of ≤ 40 ms contacts in the clip's stance,
under 0.005 a stride, which no swing-gated term charges; the tap reset is a
termination on `chl_down * g(ref_lh_lift) + chr_down * g(ref_rh_lift)`
above 0.99, `g = sat01((lift − 10) / 20)`, a paw down where the clip has it
30 mm or more up.)

**Read.**
- **sg-s7's contact gate hands back about a quarter of the scuff charge on
  each tap** (+1.29 of −4.62): under sg-s7 a tap at 1.0 m/s nets −6.2 at
  w −8, against −7.5 under sg-s6's clip gate (the same frames without the
  heel pay). sg-s7 makes the tap slightly cheaper; its 25 judgement should
  read the taps with that in mind.
- **`hind_scuff` at w −16** charges −9.2 a tap and nets −10.8, 1.7× sg-s6's
  net, and still charges nothing at 1700 or 2400 (no taps there): a
  bounded, local step up of the lever that moved the taps 0.88 → 0.64.
- **A tap reset is exact but blunt.** All of its firing frames fall on taps
  (1.00), and it never fires at 1700 or 2400; but at 1000 it ends **every**
  seed, at a median 1.17 s, 0.17 s after the settle. Trained, it would cut
  nearly every slow-command episode short, giving the slow end almost no
  data until the taps are gone: a cliff, not a slope.

**The next tap lever, if sg-s7's 25 still fails on the taps:** `hind_scuff`
at w −16 on sg-s7's task, one weight changed. The reset stays scored, not
built, as the fallback if w −16 does not move the taps either.
