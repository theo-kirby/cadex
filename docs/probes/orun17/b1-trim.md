# orun17 B1: the slow reference read; `gallop_sg` trimmed to 18 terms; sgt-1 launched cold

Verified against source: 2026-10-22. Frozen evidence (orun17, iteration 2).
Follows `sg-s9-50-80.md`. B1's last two items: the `gallop_sg` reference's
slow end read, and a trimmed task's first cold screen launched.

## The slow end of the reference, sample by sample

```
R=~/cadex-projects/leo/runs/sg-s9/train
pixi run python docs/probes/orun16/sg_clip.py $R/gallop_sg-task.json $R/cat_model-model.xml docs/probes/orun17/slow-strides.json /tmp/o17/out
pixi run python docs/probes/orun17/slow_touchdown.py /tmp/o17/out/stride-0.json $R/cat_model-model.xml
```

`slow-strides.json` is sg-s9's two slowest strides (0.35 m × 2.0 Hz, lag
0.35, `heel_from` 0.99; 0.5 m × 2.0 Hz, lag 0.30, 0.99). `sg_clip.py`
regenerates the bundle's clip equal to it (`True`) and each stride on the
schedule's 25-sample grid; `slow_touchdown.py` (new, this run) prints each
hind leg from two samples before the clip's touchdown to its lift: heel,
pad and toe bulbs above the floor (mm) and the pin (toes-up of the
metatarsus).

At 0.7 m/s (sgs), 20 ms a sample, 5 stance samples:

| leg | sample from touchdown | −2 | −1 | **0** | +1 | +2 | +3 | +4 | lift |
|---|---|---|---|---|---|---|---|---|---|
| LH | heel mm | 37.5 | 35.1 | **34.8** | 35.8 | 37.0 | 38.5 | 40.5 | 42.9 |
| | pad mm | 23.6 | 21.0 | **20.3** | 20.9 | 21.4 | 22.2 | 23.1 | 24.3 |
| | toe mm | 3.8 | 1.0 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| RH | heel mm | 37.5 | 42.2 | **47.5** | 51.9 | 55.5 | 58.2 | 60.2 | 62.1 |
| | pad mm | 22.5 | 23.9 | **26.4** | 28.3 | 29.8 | 30.9 | 31.7 | 32.8 |
| | toe mm | 1.5 | 0.1 | **0.0** | 0.0 | 0.0 | 0.0 | 0.0 | 0.6 |

The pin sits at 0 (its flat stop) on every sample of both legs; no heel
sample is held. At 1.0 m/s (sg0) the same shape: LH heel 30 → 47 mm, pad
18 → 26, RH heel 44 → 63, pad 25 → 33, toes on the floor, pin 0..+0.2°.

- **At touchdown** the clip lands each slow hind paw **on the toe bulbs
  alone**, the pad 20–26 mm and the heel 35–48 mm up, and the paw keeps
  its flat-stop angle to the metatarsus (pin 0).
- **In stance** it stays on the toe bulbs and the heel rises (LH +8 mm,
  RH +15 mm to lift): a tip-toe stance with the pin unused. That is not
  O2a's slow foot (toe bulbs **and** pad down, the pin toes-up of the
  metatarsus). The cause is orun16's (`sg-reference.md` §1): the generator
  lays the paw flat only where a heel row exists, and a stride with no
  held sample has none.
- **The policy does not copy it.** sg-s9-80 at 700 stands its hind paws
  on the pad, flat, heel up (`paw_floor.py`'s `R`) on 0.75 / 0.95 of
  on-ground frames, on the toe bulbs (`T`) on 0.02 / 0.00
  (`sg-s9-50-80.md`), pin +16.5 / +17.9° toes-up in stance: the pad lays
  the paw under load, as orun16 predicted. orun16's rule for the option
  (`sg-reference.md`: "if a judged SG policy's slow end stands on its toe
  tips, the lever is a generator option holding the heel at a height
  above the floor with the paw flat") does not fire.

**Can a generator option stand the slow paw on its pad with the heel
up?** Yes in principle, and not with today's options: the only path to a
flat paw is a heel row (`_leg_rows`), and `_eased_heels` eases the heel
down to the floor at the hold; sg1/sg2 show the flat paw with the heel
13–20 mm up only on the way to a held (down) heel. The option would be a
heel row at a height (`heel_height_mm`, the heel held that far above the
floor with `flat_feet="sole"` laying the paw on pad and toes and the pin
taking up the angle): an engine change (ADR from ADR-786, both suites,
`build-engine`, a rebuild). **Not built this iteration**: the policy
already stands the slow paw that way, so the option's measure (`T` at the
slow end) has nothing to move, and the slow end's real faults are
elsewhere (LH's second rhythm at 3.61 Hz, the 153 % overrun). It is the
lever if a trimmed screen's slow end goes to its toe tips.

## The trim (O8: cut before adding)

sg-s9's 24 terms, each against a judged effect on leo:

| term | w | judged effect | trimmed task |
|---|---|---|---|
| `alive`, `near_peak`, `height_over_ground`, `posture`, `straight`, `tail` | | regularisers, every task since orun10 | kept |
| `track_speed` (tent) | 20 | sg-s2: moved the policy off stepping in place | kept |
| `overrun` | −10 | sg-s4: 1000 from 1.48 to 1.31 m/s | kept |
| `heel_sched` (contact-gated) | 6 | sg-s5/s7: LH's heel follows the command | kept |
| `heel_pitch` (gated) | 10 | orun12: put the heel down (O2 "start from it") | kept |
| `hind_lag` | 10 | orun15 `lag-term.md`: the hinds split the clip's way | kept |
| `fore_sync` (gated) | 2 | none alone; the one term pulling the fast fore lag in, RL's failing clause | kept |
| `track_pose`, `track_lift`, `track_contact` | | the clip (O7: the clip carries the gait) | kept |
| `paw_flat` | 10 | orun14: U on the free pin | kept |
| `fore_tap` | −8 | t2-g4: fore mid-swing taps | kept |
| `hind_scuff` | −8 | sg-s6: LH taps 0.88 → 0.64 a stride | kept |
| **`paw_fold`** | −10 | orun15: the spring rate took the fold out, not this term (charter: cut) | **cut** |
| **`outside_hind`** | 4 | never judged on leo (orun10 S3's term) | **cut** |
| **`fore_reach`** | 3 | never judged on leo | **cut** |
| **`hind_overreach`** | 3 | overreach fails at −251…−353 mm on every SG screen | **cut** |
| **`plantigrade`** (gated) | 10 | none on its own since orun12's heel2 (heels 0.03 / 0.11) | **cut** |
| **`hind_flat`** (gated) | 6 | none on its own; heel_pitch and heel_sched carry the heel | **cut** |

The change is in the leo script's `gallop_sg` loop only (`SG_CUT`, a
label filter), so the `gallop` task keeps every term and its bundle is
untouched. Reference (sg-s9's five strides), goal (700–2400), terminations,
observations and actions are sg-s9's. Cold: the trainer refuses a warm
start across a reward change.

## sgt-1, launched

`orun13/queue_run.py ~/cadex-projects/leo sgt-1 10500 120 … --seed 1
--task gallop_sg --envs 4096 --after sg-s9 --build ~/orun17-queue/orun17-sgt1.py`
in its own `systemd-run --user --scope -p MemoryMax=30G`, queued 18:24:41
(`~/orun17-queue/sgt-1.log`). 120 iterations, `budget_s` 10,500 (120 ×
69 s, sg-s9's measured rate, + 20 %, + compile).

- **Built** 18:28:21 as leo revision **`59e37a18`** (leo commit
  `a308c1c`, `cadex script --set orun17-sgt1.py`; build `ok`), launched
  18:28:24 cold. Its `gallop_sg-task.json` against sg-s9's: only `reward`
  moved; 18 terms, the six above gone, the other 18 byte-equal to sg-s9's.
  Model `59bc5407` (sg-s9's, so no geometry and no clearance pair moved);
  the `gallop` bundle is byte-equal to v05-s1's (`9140fb2e`).
- **Timed:** iteration 10 at 922.5 s of trainer wall, 13 at 1,128.9 s:
  **68.8 s an iteration** (sg-s9: 69), so 120 iterations end near 8,500 s
  (about 20:50), inside the 10,500 s budget. Reward per step 19.3 at 0,
  13.5 at 5, 15.3 at 10 (sg-s9's cold start had the same dip), σ 0.849,
  episodes 58 steps at 10.

**The question:** with six terms cut, does the heel's stance share rise
with the command and the pair lag fall with it, at 0.7 / 1.55 / 2.4 m/s,
against sg-s9 at 50 and 80? **Rules, written before judging** (O8: judged
at 50 and at 120, nothing at 25 but a fall-over on every seed):

- at 50 and 120, judged as sg-s9 was (`sg_judge.py --cmd 700 1550 2400`,
  `legs.py`, `paw_floor.py`, `p2_lag.py`, `spine_foot.py`);
- **the trim is kept** if at 120 it is no worse than sg-s9-80 on tracking
  (speed span ≥ 1.6 m/s, 2400 ≥ 2.6 m/s), rotary (≥ 8/10 at every
  command) and U at 2400 (≤ 0.24 / 0.23), and better on either the heel
  schedule (heel share rising with the command on both legs) or the lag
  (fore or hind share falling 700 → 2400);
- otherwise the trim is judged a no-change, the cut terms stay cut only
  where the screen shows they cost nothing (O7), and the next lever is the
  reference (the slow stride's late swing, or the option above);
- extend warm past 120 (200–400, `--critic-warmup`, ~3e-5) only if the
  curve still climbs and the shape (heel rising, rotary slow, tracking)
  is there.
