# The heel eased into its hold (orun11 iteration 10, ADR-778)

Verified against source: 2026-10-19. Frozen evidence.

## Why

ADR-777's plantigrade clip on orun11-cat holds each hind hock case on the
floor for the second half of a four- or five-sample stance. Outside the hold
the heel is free, so it fell 31–42 mm to the floor in one 19.8 ms sample and
lifted 66 mm in the next after toe-off. Iteration 8 found the hock servo
saturates after 17° of error (`hind-asymmetry.md`), and the clip asked for
22–46° steps at the hip, knee and hock. This is the "gradual heel-down"
change iteration 8 proposed as the smaller second change after the hock
drive. hock80-s1, the screen on the AK80-9 drive, was at iteration 19 of 150
when this was done, so the drive and the clip stay separate variables.

## The change

`CadexGait.generate` solves a clip with held heels twice (ADR-778). The
second pass aims the heel row at a height around the hold. From touchdown
it falls linearly to the first held sample. After toe-off it rises over
three swing samples to the height the first pass's free swing gave it.
The held samples are unchanged.

## The clip, stepped and eased

`heel_ease.py` regenerates a bundle's clip on its exported model. With
ADR-777's code it is byte-equal to hock80-s1's bundle (orun11-cat
2c5a51e6), and to orun10-cat t2-g4's, which has no heels.

```
pixi run python docs/probes/orun11/heel_ease.py \
  ~/cadex-projects/orun11-cat/runs/hock80-s1/train/gallop-task.json /tmp/eased-task.json
```

| | LH stepped | LH eased | RH stepped | RH eased |
|---|---|---|---|---|
| heel over floor, touchdown to lift-off (mm) | 25 33 42 **0 0** 66 81 91 | 25 17 8 **0 0** 25 50 75 | 31 39 **0 0** 66 79 | 31 15 **0 0** 25 50 |
| hip, largest step (deg) | 24.8 | 9.6 | 25.2 | 10.5 |
| knee, largest step (deg) | 43.2 | 20.9 | 45.8 | 23.7 |
| hock, largest step (deg) | 24.7 | 15.1 | 22.6 | 17.1 |

Rise lengths of 1, 2, 3 and 4 swing samples give a largest LH knee step of
30.7, 24.5, 20.9 and 18.5°. Three was kept. Past three, the knee's
remaining step is the foot's own swing lift at toe-off, which the heel
does not set.

## M1's static check

`clip_static.py` on the eased bundle (`/tmp/eased-task.json`), with the sole's
pitch positive toes-down:

| foot | sample | stepped: sole, case | eased: sole, case |
|---|---|---|---|
| LH | 0 touchdown | −2.5°, 24.9 mm | −2.5°, 24.9 mm |
| LH | 1 | +4.3°, 33.0 mm | −0.2°, 16.6 mm |
| LH | 2 | +11.2°, 42.2 mm | +1.3°, 8.3 mm |
| LH | 3 held | +2.1°, 0.0 mm | +2.1°, 0.0 mm |
| LH | **4 push-off** | **+6.2°, 0.0 mm** | **+6.2°, 0.0 mm** |
| RH | 2 touchdown | +0.8°, 30.5 mm | +0.8°, 30.5 mm |
| RH | 3 | +8.3°, 39.0 mm | +1.0°, 15.3 mm |
| RH | 4 held | −0.2°, 0.0 mm | −0.2°, 0.0 mm |
| RH | **5 push-off** | **+5.1°, 0.0 mm** | **+5.1°, 0.0 mm** |

Push-off still passes M1 on both legs. The foot now lays down flat, its
sole within 2.5° of the floor through the descent, where the stepped clip
rolled it 8–11° onto its toes, heel high, the sample before the hold.

## The rebuilt bundle

orun11-cat's script was set again unchanged on the new engine (project
commit `e971d83`). The revision is still **2c5a51e6**; its accepted digest
moves from `1a19a30c` (hock80-s1's bundle) to **`158a8c12`**:

- fit **pass**: 0 failing of 7,626 pairs;
- mounting **pass**: 30 of 30;
- panels: 0 failing of 45, 12 advisory;
- sweep **pass**: 36 of 36 limited joints.

Its gallop bundle differs from hock80-s1's only in `reference` and the
clip-derived `tracking` (`table`, `reset_qpos`, `reset_qvel`), and its heels
carry the eased targets above (LH 17, 8, **0, 0**, 25, 50, 75 mm; RH 15,
**0, 0**, 25, 50, 75 mm). It is the bundle for the next screen, cold, with
the same 17 terms: the clip is the one variable against hock80-s1.
