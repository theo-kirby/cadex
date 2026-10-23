# orun12 P1 (O2a): a clip whose heel-down pose the sim can stand in (ADR-780)

Verified against source: 2026-10-20. Frozen evidence (orun12, iteration 10).

## The defect

`heel5-pitch.md` found that in simulation the hind heel is down only while
the metatarsus's world pitch is under about 15°. The plantigrade clip held
the heel down with the metatarsus at 18–22°, so tracking it could not lay
the heel.

The cause is in the generator. The hind paw's sprung pin (`j_pawpin_*`) is
in the leg's chain, and in the heel-down samples the solve has one more
degree of freedom than rows: the paw point (3 rows), the heel (1), and the
hock's parallelogram. That freedom went to the pull toward home, which
rolled the paw 52–62° toes-up onto its rear pad (the paw body's world
pitch). With the paw on its rear pad, the heel can only reach the floor
with the metatarsus near 20°. In the sim the floor lays the paw flat
instead (pin about +77°).

## The fix: `flat_feet`

`assembly.gait(..., flat_feet=True)` (ADR-780) adds one row while a heel is
held: the foot body's world pitch, held at the pitch it stands at in the
home pose. The rest of the clip is solved as before. Without the option the
clip is byte-equal to the old one: `clip_flat.py` regenerates heel5-s1's
bundled clip and compares `qpos` exactly.

```
pixi run python docs/probes/orun12/clip_flat.py \
    ~/cadex-projects/feline-v07/runs/heel5-s1/train/gallop-task.json \
    ~/cadex-projects/feline-v07/runs/heel5-s1/train/cat_model-model.xml
```

On heel5-s1's settings (0.7 m at 2.4 Hz, duty 0.2, `heel_from` 0.2, a 60 mm
drop, 6° nose-up, a 120 mm stance shift), over the heel-down samples:

| clip | leg | heel-down samples | metatarsus pitch ° | paw pin ° | largest step per sample ° (hip, knee, ankle, paw pin) |
|---|---|---|---|---|---|
| without `flat_feet` | LH | 4 | 18.4–22.2 | −20.1 to −6.1 | 7.6, 18.2, 10.1, 7.4 |
| without `flat_feet` | RH | 4 | 18.4–22.2 | −20.1 to −6.1 | 7.6, 18.2, 10.1, 7.4 |
| `flat_feet` | LH | 4 | 7.5 | +56.7 | 7.5, 23.2, 10.8, 57.9 |
| `flat_feet` | RH | 4 | 7.5 | +56.7 | 7.5, 23.2, 10.8, 57.9 |

- The metatarsus is now at 7.5°. That is inside the 5–10° bin where
  heel3-s1-100's stance frames had the heel down on 0.72 of them.
- The paw lies at +57°, flat on the floor at the paw's standing pitch.
  The legs are mirror-equal.
- Every `heel_from` from 0 to 0.5 is still reachable (0.0, 0.2 and 0.5 were
  checked).
- The paw pin steps 58° at the ends of the hold, where the solve hands it
  back to the pull toward home. The pin is passive and no term tracks it
  (`REF_OF` maps only the drives), so the step is in the clip's playback
  only. The knee's largest step rises from 18° to 23°.

## heel6-s1

heel6 is heel3-s1's task (`plant_w` 10, speed pay capped at 2 m/s, the chest
box, 17 terms) with the clip laid flat. heel5-s1's `heel_pitch` is held out,
so the screen tests the clip alone; heel5-s1 judges `heel_pitch`. If both
move the heel, a later screen combines them.

heel6 is feline-v07 revision `d3b4e838`, digest `63da7c13`. It kept
revision 14's model with no new tessellation bytes. Its gallop task has
17 terms, without `heel_pitch` or `track_ankle`. `clip_flat.py`, run on
the built bundle, regenerates its clip exactly with `flat_feet` on, and
`flat_pitch_deg` is recorded for both heels.

It is cold, 100 iterations, 4096 envs, seed 0, `budget_s` 9,000. heel5-s1,
on the same model and envs, runs at 67 s an iteration (iterations 5–10,
886 s to iteration 10), so 100 iterations come to about 8,060 s with the
first compile. It is queued with `queue_run.py --expect-revision` behind
heel5-s1 and starts when heel5-s1 ends.

The stop rule is O2a's: if both heels are under 0.15 at 50, stop it.
