# orun17 RL: `fore_lag` priced on sgt-4's clip (the fallback, not trained)

Verified against source: 2026-10-23. CPU work while sgt-3b trains to 120;
the critic asked for the fallback term scored on sgt-4's bundle so it is
ready if the duty 0.35 / 0.3 slow schedule (`sgt-3b-50.md`) does not stop
the fores doubling at 700.

## What was run

`fore_pair.py` takes `--clip TASK_JSON` now: it scores the judged traces
against another bundle's stride at the same command, recovering each
episode's start sample from the judged task's own reset rows (the clock the
policy ran on) and refusing a stride whose period or sample count differs.
sgt-4's stride 0 (b09a23b5, `gallop_sg-task.json`) shares sgt-3b's 0.5 s
period, 25 samples and fore touchdown samples (LF 4, RF 13); only the
stance is longer (nine samples a fore, was five).

```
pixi run python docs/probes/orun17/fore_pair.py --clip <b09a23b5>/outputs/gallop_sg-task.json \
    runs/sgt-3b/train/cat_model-model.xml evaluations/{sg-s9-80,sgt-1-120,sgt-2-120,sgt-3b-50}-700
```

The term is orun15's, unchanged:
`abs(ref_lf_down - ref_rf_down) * (1 - abs((cfl_down - cfr_down) - (ref_lf_down - ref_rf_down)))`,
`hind_lag`'s form on the fore pair.

## At 700 on sgt-4's clip

| policy | fore touchdowns a stride LF / RF | within 40 ms | `fore_lag` a step, sgt-4 clip (clip 0.721) | same, sgt-3b clip (clip 0.400) | `track_contact` fore half, sgt-4 clip | per seed r (`fore_lag`, within 40) |
|---|---|---|---|---|---|---|
| sg-s9-80 | 1.00–1.33 / 1.00–1.17 | 0.09 | **+0.449** | +0.378 | 0.859 | −0.68 |
| sgt-1-120 | 1.00–2.33 / 1.00–1.78 | 0.30 | +0.387 | +0.314 | 0.831 | −0.74 |
| sgt-2-120 | 1.89–2.00 / 1.78–2.00 | 0.63 | +0.312 | +0.245 | 0.796 | −0.81 |
| sgt-3b-50 | 1.56–2.00 / 1.17–1.44 | 0.48 | **+0.201** | +0.204 | 0.720 | −0.08 |

(sgt-3b clip column from `fore-pair.md` and `sgt-3b-50.md`.)

- **It separates the single strike from the double.** The one policy that
  keeps the fores apart (sg-s9-80) scores highest, the doublers lowest;
  within a policy, seeds with more tied fores score less (r −0.68 to −0.81)
  except sgt-3b-50 (−0.08), whose loss is timing, not ties: LF lands
  40–70 ms late against the clip on every seed.
- **The gap is the old clip's, not wider.** sg-s9-80 over sgt-2-120 is
  0.137 a step on sgt-4's clip, 0.133 on sgt-3b's; sgt-4's longer stance
  raises every score about equally. At weight 10 that is 1.4 a step between
  a single and a double strike; `track_contact` (w10, fores a half) already
  pays 5 × (0.859 − 0.796) = 0.3 a step for the same difference.
- **None of these policies fills sgt-4's stance:** 0.31–0.45 of a 0.72
  clip, so a policy that trains on it has the full 0.27–0.41 a step to
  gain from holding each fore down its nine samples.

## The fallback, if sgt-4-120 still doubles the fores

Add the term above at **weight 10** (the same as `hind_lag`), sgt-4's
18 terms otherwise, 19 in all (cap 32), cold. The known risk is orun15's
fl-sole (`orun15/fl-sole.md`): `fore_lag` w10 on that task split the fores
but gave back the hind split, RH's heel (0.36 → 0.08) and the taps, the two
pair terms competing. So its keep rule must also hold the hinds and heel:
at 120, the fores at 700 at most 1.2 strikes a stride with at most 0.2
within 40 ms, the hinds' within-40 share no worse than sgt-4-120's + 0.05,
and the heel shares per leg no worse than sgt-4-120's − 0.05 at each
command. Not drafted as a bundle: sgt-4's own 120 judgment decides first.
