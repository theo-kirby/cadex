---
node_id: b2b0df87-d16d-5a36-ad96-e1d50c52e409
slug: western-basin-2846
title: S2. A grounded sensor reads an actuator's load
created_at: '2026-10-07T17:58:12+00:00'
parents:
- nimble-pine-0740
summary: ''
---
Status: open

## Current

Charter criterion for run orun5: **S2. A grounded sensor reads an actuator's load.** The human owns the checkbox; roles report results and do not tick it [rec: honest-bay-2056].

- A new sensor kind reads an actuator's load: the force or torque it
  applies, as the bus servo or a current sensor reports it, with the
  declared resolution and noise (A1). [rec: honest-bay-2056]
- The catalog's bus servos say they report load; a hobby PWM servo
  does not, and declaring a load sensor on one is refused with a reason. [rec: honest-bay-2056]
- Tests: the channel tracks the actuator's applied force under a held
  load and saturates at the stall line; a PWM servo's load sensor is
  refused. [rec: honest-bay-2056]

Not started: no record yet claims work against this criterion [rec: honest-bay-2056].

## Negative knowledge

None yet.

## Provenance

- honest-bay-2056 — operator-declared orun5 charter gap (gap-s2-grounded-sensor-reads-actuator)
