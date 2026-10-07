---
node_id: 97f8996f-7b07-5294-9932-09cbb20cde4f
slug: tiny-lake-4065
title: 'ADR-591: load_sensor, a grounded reading of an actuator''s load (S2)'
created_at: '2026-10-07T20:52:21+00:00'
parents:
- smooth-stream-7287
summary: ''
---
## What

S2: a grounded sensor for an actuator's load (ADR-591, commit `4d28ba67`).
`assembly.sensor(actuator, "load_sensor", name=, resolution_nmm=, noise_nmm=,
rate_hz=)` (`_n` twins on a sliding coordinate) grounds that actuator's
`actuator_force` channel. The reading is MuJoCo's `actuatorfrc` plus the
trainer's per-step noise, held within ±full_scale, rounded to the
resolution; full_scale is the actuator's own `torque_limit_nmm` /
`force_limit_n` (its stall line), and an actuator without one is refused.
The catalog's STS3215 row carries `load_feedback` (Present Load register,
0.1 % of full drive per count; 1 % noise and 100 Hz polling assumed and
listed in `approximate`). `lib.servo(sku).load_sensor(actuator, name=)` fills
those as fractions of the actuator's stall torque; every PWM servo (sg90,
mg90s, mg996r, ds3218) refuses with the reason.

## Why

The critic named S2, the highest-ranked open capability, and asked for
exactly this: a datasheet declaration, bus servos saying they report load,
PWM refused with a reason, an ADR, and tests of a held load and stall
saturation. Done as asked. The two items the critic deferred (P1 circle
laps spec; a noisy-readings evaluation of the centring policy) were left
for before C1, as instructed.

## Method

Mirrored the position tracker (ADR-588) end to end: `_SENSOR_KINDS`
gains `load_sensor` on an `actuator` measuring `actuator_force`;
`_load_datasheet` validates units and the stall line; the observation
carries `load`; the worker forwards it; `CadexDynamics.observation_records`
/ `task_records` carry it on the row; `load_reading` applies it in
`observation_values`; `_check_tracker_rates` also refuses a slow load
sensor (`load_sensor_slower_than_control`); the smoke runner applies it; the
trainer gains `load_reading` (jnp) and its `tracker_noise_std` /
`tracker_variance_floor` become `sensor_noise_std` / `sensor_variance_floor`
covering both kinds in observation order (the tracker tests updated to the
new names). describe_api's assembly page was 91 characters over the
21,500 budget after the signature grew; the listing's units sentence and
reset-variation sentence were tightened (no content dropped) to 21,4xx.

Assumption (no question asked): the PWM refusal lives on
`lib.servo(sku).load_sensor`, not in `assembly.sensor`, because marking
library-made actuators would change every library-servo task's export
bytes and policy digests, and the API holds no per-script state. A direct
`assembly.sensor(actuator, "load_sensor", ...)` is documented as a claim
that the machine carries a current-sense part (real hardware, A1).

## Result

New test file `test_dynamics_load_sensor.py`, 7 tests. Measured in the
held-load test: an arm held by a position servo reads 1816 N·mm against
the joint's gravity torque of 1815.7 N·mm (2 N·mm resolution); a servo
with half that stall (908 N·mm) reads exactly 908 and sags 13.2° off its
setpoint. Trainer copy equals engine on 300 draws; noise spread 15.0 ±6 %.

Gates: `pixi run test-engine` 2650 passed, 60 skipped (run twice, after the
code and after the listing trim); `pixi run build-engine`, then
`pixi run python -m pytest cli/tests` with the GPU hidden 1217 passed,
1 skipped. No protocol, op or tool change, so no packaged gate.

Not modelled, named in docs/MUJOCO.md: the STS register reads drive duty,
which equals load only near stall; at speed the real reading runs above the
simulated one. QDD actuators are not catalogued as load-reporting; they
take an explicit declaration. Next by the charter: R1 (goal in a body's
frame), then L1, then P2, which now has its load channel. Tail: 2
unreconciled records after this one.

`hypergraph export` succeeded; `hypergraph check` exits 1 with 274 I2 violations, all on older records whose impacts target the unconfigured `plan` view, the same 274 with this record removed (known since ot10's C1 report); none name this record.

Dispatch closed: 1 unit — S2 load_sensor (ADR-591): bus servos ground actuator_force, PWM refused, held load and stall saturation measured

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/orun5
- commit: 4d28ba6796870da8ad42d7eeb566a65c3aafb826

## State Impact

- target: western-basin-2846 — S2 evidence: load_sensor (ADR-591, 4d28ba67) grounds actuator_force; STS3215 load_feedback fills it, PWM servos refused; held arm reads 1816 vs 1815.7 N·mm gravity, half-stall servo reads its 908 N·mm stall and sags 13.2°; engine 2650 / CLI 1217 green
