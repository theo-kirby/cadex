# Finch — a buildable MG90S biped (D5, ADR-334)

Verified against source: 2026-09-13. [Cadex-new]

The charter's D5 (ADR-328): a redesigned biped in a fresh project, built from
catalog hardware — the MG90S from `lib.servo` with catalog horns, bearings and
fasteners — and modelled printable parts that mount them, with an inventory,
a fit check, no world geometry, a viewport in which the hardware is
recognisable, and the collision proxies declared per part. This directory is
that evidence. The project is `~/cadex-projects/ot6-finch` (outside the
repository, as the charter requires); its accepted revision is
`bcce40a82d57be86a6bd9e237ad666d069dfebd84986dc7944be96fb980ef1c1`, its script
is 17 304 bytes with sha256 `5152d1b29a87b256…` (`fit.json` and
`free_base.json` carry both in full), and it was entered with `cadex script
--set` from a script authored for this unit — no model turn, no reuse of
Lark's script. (The D5 unit accepted it as `f0450d9bdf1a…` with the pelvis
grounded for the solver; ADR-335 removed that need and the revision above is
the same design with nothing grounded.)

## The mechanism

Two 2-DoF legs (hip pitch, knee pitch), four MG90S, every joint the **same
module**, dimensioned from the catalog's datasheet numbers:

- The servo sits in a **window through the parent's outboard cheek** with the
  declared 0.3 mm clearance per side, its tabs seated on the cheek's outer
  face and held by **two M2×6 socket screws** into 1.6 mm tap-drilled holes.
  The case stands outboard of the leg, where a real SG90/MG90S biped has it.
- Its **single-arm horn** (the catalog's measured micro horn) nests in a
  2.5 mm form-fit slot on the child block's outboard face with 0.2 mm per
  side, arm pointing forward so it is visible, and is clamped to the spline
  by the **M2×16 centre screw** driven from the inboard end through a
  counterbore in the block.
- The child's **printed 7.9 mm stub** turns in an **MR128 bearing**
  (8 × 12 × 3.5) pressed into the parent's inboard cheek at nominal, with
  0.05 mm radial clearance, 1.0 mm between block and cheek.

Five printed parts: a pelvis (top plate, open electronics bay, two hip
clevises), two thighs (hip block with two knee cheeks), two shins (knee
block, beam, integral 70 × 34 mm sole). Hips ±60°, knees 0–90°, axes on world
+Y, the soles on z = 0. Total mass 243.5 g: 177.5 g printed (PLA 1240 kg/m³),
65.9 g purchased. Catalog roll-up: `servo/mg90s` × 4,
`servo_horn/mg90s-single_arm` × 4, `bearing/mr128` × 4, `bolt/m2x16-socket`
× 4, `bolt/m2x6-socket` × 8. Actuators are the servos' own
`servo.actuator(...)`: position servos bounded by the 4.8 V stall torque
(176.5 N·mm), joint damping from the datasheet no-load speed.

**Nothing in the world is part of the design.** No floor, slab, wall or
stage: every collision geom is a box on a part of the design, and **nothing
is grounded**. Finch is a free base (ADR-335): `assembly.solve` holds the
pelvis — the first component in script order — to find the pose and reports
it as `free_base`, the export gives `pelvis_link` a free joint, and the floor
the soles rest on is the environment's plane `environment/floor` on the
world body at z = 0, recorded in the manifest as `dynamics.environment` and
never in the script. The D5 unit could not do this: both halves then refused
an ungrounded assembly, so the pelvis carried `grounded=True` as a flag and
the export had a static base (ADR-334). That flag is gone.

## The inventory and the fit check

```bash
pixi run python docs/probes/ot6/finch/fit_check.py ~/cadex-projects/ot6-finch ~/cadex-projects/ot6-finch/evidence/d5
```

writes the project's `docs/INVENTORY.md` (every solid: source as catalog
family and part id or *modelled* with its purpose, mass from the mjcf
export's exact inertials, its declared proxies and their relation to the
solid) and `docs/FIT.md`, and `fit.json` here. **85 checks, all hold.** Each
is a published measurement — pair distance and common volume on the exact
BREP at the solved pose (`cadex clearance`, ADR-237), or a contour gap in a
`cadex section` cut through the cheek mid-plane — against the script's
declared clearances or an analytic volume:

| what | measured | expected |
|---|---|---|
| servo seated in its window (4 modules) | distance 0, volume 0 | seated |
| window clearance around the case, section through each cheek | 0.300 mm | 0.3 |
| horn nested in the block slot; horn on the spline top | 0 / 0 | seated |
| spline to hub recess, radial | 1.2 mm | 3.45 + 0.2 − 2.45 |
| bearing pressed in the cheek | 0 / 0 | nominal press fit |
| stub in the bearing bore, radial | 0.05 mm | 0.05 |
| block to inboard cheek | 1.0 mm | 1.0 |
| centre screw engagement in the spline (4) | 7.854 mm³ | π·1²·2.5 |
| tab screw engagement in the cheek (8) | 4.0715 mm³ | π(1²−0.8²)·3.6 |
| intersections other than those 12 engagements | 0 | 0 |
| plane or non-box geoms; initial proxy contacts | 0 / 0 | 0 |

The 406-pair clearance table has no unmeasured pair. The engagements are the
only intersections and they are the threads: the catalog spline is a solid
cylinder and the tap-drilled holes are 1.6 mm, so an M2 shank overlaps both
by exactly the volume the check predicts.

## The operator URL

```bash
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review --project "$HOME/cadex-projects/ot6-finch" \
  --host "$(tailscale ip -4)" --port 8765
PYTHONPATH=cli pixi run python docs/probes/ot6/finch/operator_probe.py "http://<private-address>:8765/" ~/cadex-projects/ot6-finch/evidence/d5
```

The persistent dashboard (port 8765) now serves Finch — one project per
server, and this is the project being worked on. `operator.json` is the
receipt; the frames are 256-colour copies under the cap:

- [operator-solids.png](operator-solids.png): the accepted model, `showing:
  tessellated solids`, 29 components, 51 556 triangles, 61 665 model pixels.
- [operator-proxies.png](operator-proxies.png): the labelled toggle on —
  `showing: tessellated solids with collision proxies (20 outlines from the
  accepted attempt's finch_model …)`, 62 492 pixels. On Lark the toggle moved
  the count by 29 because its box proxies were its box parts; here the
  pelvis proxy spans the open bay and the cheek proxies span their windows,
  so the outlines stand off the solids and the difference is visible. This is
  the real-biped operator evidence D4 was waiting for.
- [operator-knee-close.png](operator-knee-close.png),
  [operator-hip-close.png](operator-hip-close.png): solids only. The MG90S
  cases stand outboard of the cheeks as boxes with the tab plate and the two
  screw heads; the horn arms protrude forward from the blocks with their
  link holes; the bearing rim and centre-screw counterbore show on the inboard
  faces. What cannot be seen from outside: the horn hub and the spline, which
  are inside the slot by design.
- [operator-iso.png](operator-iso.png), [operator-front.png](operator-front.png):
  the whole mechanism on the dark mat with the PROTOTYPE / 1 METER labels.

## The free base on the environment's floor (ADR-335)

```bash
pixi run python docs/probes/ot6/finch/free_base_probe.py ~/cadex-projects/ot6-finch docs/probes/ot6/finch
```

`free_base_probe.py` opens the accepted attempt's exported MJCF with MuJoCo
alone (no Cadex on the path) and writes `free_base.json`: the solve verdict
(`grounded_components: []`, `free_base: pelvis_link`), the model (30 bodies — the world, 5 printed and 24 catalog parts —
`nq` 11 = one free joint and four hinges, 21 geoms = 20 declared boxes and the
world's floor), the solved pose (pelvis at 120 mm, eight sole-corner contacts
with `world` at 0.000 mm), and three short rollouts from the `solved`
keyframe:

| rollout | actuation | 2 s / 4 s pelvis z | outcome |
|---|---|---|---|
| held | `ctrl = 0`, servos hold their zero targets | 119.85 mm, upright | stands |
| passive | disabled | 119.85 mm, upright | stands on straight legs — a balanced equilibrium the integrator never leaves |
| shoved | disabled, 0.3 m/s forward on the free joint | 30.26 mm at 4 s, pelvis inverted | falls onto the floor, never through it |

Deepest floor penetration: 0.15 mm at rest, 2.79 mm at the shoved impact
(MuJoCo's default soft contact under a 244 g fall of 90 mm). Eight checks in
the receipt hold: nothing grounded, the pelvis is the free base, the floor is
the world's, only the soles touch it at t = 0, held stands for 2 s, passive
stays on the floor, shoved falls onto it and not through it, impact
penetration under 5 mm. `fit_check.py` gained two rules for the same fact —
only the two soles rest on the floor at t = 0, and nothing is grounded — and
its proxy-contact rule now excludes `world`: 87 checks, all hold, at the new
revision.

## What this does not claim

- Not a swept check: every measurement is at the solved standing pose. Knee
  flexion past about 60° would bring the sole toward the thigh cheeks; the
  90° limit is a policy bound, not a proven-clear travel.
- The free-base rollouts below are stock-MuJoCo physics on the accepted
  export, not a policy and not training: they show the base is free and the
  floor is there. D6's task declaration and bounded training run are the next
  unit.
- Screw-driver access to the tab screws is from inside the leg's gap (7.5 mm
  between cheek and block); a real build would reach them before fitting the
  child block.

## Training (D6, ADR-336) — `training.json`

One bounded real GPU run, `finch1`, on the stand task declared in the script
(400 steps at 50 Hz, fall below 84.0 mm pelvis height, seed set 0–9; ADR-336
§1). The task was accepted as revision `a3dc4e9a0f84…`; the driver's
`params --set policy_on=0` export recorded the same script text and the same
geometry digest `6ccf922e66f8…` as revision `a6e043dde0fe…`, and that is the
revision the trainer's model and task bundle came from. Requested 240 PPO
updates on 1024 environments, checkpoints every 20, under `systemd-run` with
`MemoryMax=20G` and a 3600 s timeout. The trainer exited 0 in 2048.7 s of wall
clock (state `done`, device `gpu`, iteration 239); host peak 9.72 GB in the
scope, GPU peak 15 695 MiB. Every trainer-committed update interval is in the
receipt: 204 plain updates with a median of 4.90 s (4.80–5.06 s), the
first-update compile at 78 s and each checkpoint step at 43–84 s.

`train.py` drove it; `evaluate.py` rolled each retained policy in a fresh
scratch project over the ten seeds (seed 0 reproduces the retained trace
byte for byte, and the source run is unchanged afterwards); `report_training.py`
wrote `training.json` from those artifacts and decoded one frame from each
retained video. Everything else — traces, videos, the trainer log, the 241-row
timeline, the observer's samples — stays in the project under `evidence/` and
`runs/finch1*/`, cited by path and digest.

**The two policies over the declared seed set** (pelvis x-displacement over
the episode, survival, falls; the retained trace is seed 0):

| policy | video | stood the full 8 s | falls | survival s (mean, min–max) | x displacement mm (mean, min–max) |
|---|---|---|---|---|---|
| checkpoint 20 (`83bf27c5…`, iteration 19) | `video-finch1-checkpoint20.png` at 0.15 s of 0.3 s | 0 / 10 | 10 / 10 | 0.296, 0.20–0.34 | −60.2, −69.8 to −51.2 |
| final (`0f0997e1…`, iteration 239) | `video-finch1-final.png` at 4.0 s of 8.0 s | 10 / 10 | 0 / 10 | 8.0, 8.0–8.0 | +361.1, +319.4 to +432.7 |

The bar the charter names is standing for the full episode. The checkpoint
fails it on every seed: the frame at 0.15 s shows the pelvis already pitched
forward past the feet, and the pelvis crosses 84 mm at 0.2–0.34 s. The final
policy meets it on every seed, and does more than stand: it shuffles
forward about 36 cm in 8 s, with the seed-0 pelvis also drifting 167 mm to
the side, on the alive bonus plus the small forward term. The reward curve
in the receipt rises from −0.071 per step at update 0 to 0.62 at update 239
(best 0.655 at update 164). The trainer's own running mean episode length at
the last update was 211 of 400 steps across its 1024 environments; the ten
CLI rollouts of the retained policy each reached the 400-step limit. Those
are different measurements — the trainer's batch while learning against the
retained policy replayed through the engine's rollout op — and the receipt
records both without reconciling them.

**In the new look.** Both videos are `cadex-prototype-dark-v1` from the
shared environment module: the near-black grid mat with its PROTOTYPE and
1 METER labels, fog to the horizon, the contact shadow under the soles, the
follow rig holding the subject at its declared framing fraction, and the
timer pill (0.20 s and 4.00 s in the two frames). Each video's identity
strip says `tessellated solids of the accepted revision; collision proxies
not drawn` (ADR-333), and each frame shows exactly that: the 29 solids — the
pelvis with its open bay, the orange MG90S cases standing outboard of the
legs, the horns on the child blocks, the thighs and shins with their soles —
rather than the 14 declared collision boxes. Both browser checks decoded the
downloaded file to the recorded frame count (4 and 81) with differing frames
and matching digests.

**Published while the trainer was active, on the persistent URL.** The
driver's own checkpoint publication failed at the video render with
`incomplete or excessive component geometry`: the recorder's 20 000-triangle
cap, sized for Lark's boxes, against Finch's 95 212 (ADR-336 §2). The rollout,
the script revision `22cbb1638d10…` and the run record were the driver's, made
at trainer update 22–23; the video was rendered by hand on the fixed recorder
at update 54 (3.47 s) and browser-checked on the persistent dashboard at
update 54, both while the trainer was still training, and the run record is
unchanged by either. The trainer's committed update intervals around that
render — 15 before, 2 overlapping, 2 after — have medians of 4.934, 4.909 and
4.949 s, so one bounded concurrent render cost the trainer nothing
measurable. The observer's live check during training saw the persistent
server select `RUN finch1` on a fresh visit with 29 components loaded and
seven successive trainer updates each reach the page within 2.28 s of being
committed, after one reload.

**The dashboard at the end** serves `ot6-finch` at accepted revision
`b68622345563…` with three runs — `finch1`, `finch1-checkpoint20` (marked
historical, same training run by policy identity) and `finch1-final` — and a
fresh visit selects `finch1-final`. The final video's accepted revision is the
one the browser saw, and the D5 run records that preceded training are
unchanged (their digests are in the driver's result).

**What this does not claim.** One run, one seed for training, ten for
evaluation; no shove band, no gait metric beyond pelvis displacement, no
claim about how a printed Finch would behave under these targets. The
checkpoint video is 0.3 s long because that is how long the checkpoint stood.
The final policy's forward shuffle is a measured behaviour of a stand task
with a forward term, not a walking result.
