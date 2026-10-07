---
node_id: b2b0df87-d16d-5a36-ad96-e1d50c52e409
slug: western-basin-2846
title: S2. A grounded sensor reads an actuator's load
created_at: '2026-10-07T17:58:12+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: working

## Current

Charter criterion for run orun5: **S2. A grounded sensor reads an actuator's load.** A new sensor kind reads an actuator's applied force or torque as a bus servo or current sensor reports it, with declared resolution and noise (A1); the catalog's bus servos say they report load, a hobby PWM servo refuses with a reason; tests show the channel tracking a held load and saturating at the stall line. The human owns the checkbox [rec: honest-bay-2056].

**Implemented, evidence complete** (ADR-591, commit `4d28ba67`) [rec: tiny-lake-4065]. Reconcile judgement: status `working` — no `met` in the vocabulary, and the human owns the box.

- **Surface**: `assembly.sensor(actuator, "load_sensor", name=, resolution_nmm=, noise_nmm=, rate_hz=)` (`_n` twins on a sliding coordinate) grounds that actuator's `actuator_force`. Reading: MuJoCo `actuatorfrc` plus per-step trainer noise, held within ±full scale, rounded to resolution; full scale is the actuator's own `torque_limit_nmm` / `force_limit_n` (stall line) — an actuator without one is refused. A slow sensor is refused (`load_sensor_slower_than_control`) [rec: tiny-lake-4065].
- **Catalog**: the STS3215 row carries `load_feedback` (Present Load, 0.1 % of full drive per count; 1 % noise and 100 Hz polling assumed, listed in `approximate`). `lib.servo(sku).load_sensor(actuator, name=)` fills these from the stall torque; every PWM servo (sg90, mg90s, mg996r, ds3218) refuses with the reason. A direct `assembly.sensor(..., "load_sensor")` is documented as a claim the machine carries a current-sense part [rec: tiny-lake-4065].
- **Trainer**: `load_reading` (jnp); `tracker_noise_std` / `tracker_variance_floor` became `sensor_noise_std` / `sensor_variance_floor` covering both kinds [rec: tiny-lake-4065].
- **Tests** (`test_dynamics_load_sensor.py`, 7): a position servo holding an arm reads 1816 N·mm against 1815.7 N·mm gravity torque (2 N·mm resolution); a servo with half that stall reads exactly 908 N·mm and sags 13.2°; trainer equals engine on 300 draws, noise spread 15.0 ±6 % [rec: tiny-lake-4065].
- **Gates**: `pixi run test-engine` 2650 passed, 60 skipped; CLI (GPU hidden) 1217 passed, 1 skipped; no protocol change [rec: tiny-lake-4065].

## Negative knowledge

- [scope: load_sensor fidelity on STS bus servos | confidence: medium | evidence: tiny-lake-4065] The STS Present Load register reads drive duty, which equals load only near stall; at speed the real reading runs above the simulated one. Named in `docs/MUJOCO.md`, not modelled [rec: tiny-lake-4065].
- [scope: PWM refusal placement | confidence: high | evidence: tiny-lake-4065] The refusal lives on `lib.servo(sku).load_sensor`, not `assembly.sensor`: marking library actuators would change every library-servo task's export bytes and policy digests. QDD actuators are not catalogued as load-reporting [rec: tiny-lake-4065].

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-s2-grounded-sensor-reads-actuator)
- tiny-lake-4065 — load_sensor landed (ADR-591): bus servos ground actuator_force, PWM refused, held load and stall measured
