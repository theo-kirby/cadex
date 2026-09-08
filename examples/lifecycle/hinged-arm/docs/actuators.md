# Actuators

Verified against source: 2026-09-08. [Cadex-new]

One actuator drives the one joint: `j/motor`, a `motor`-kind actuator on the
revolute joint `j`, exported as an MJCF `<general>` with
`forcerange="-0.4 0.4"` — a torque limit of 400 N·mm, written in the recipe as
`torque_limit_nmm=400`.

The recipe's open-loop control is `120*sin(2*pi*time)` N·mm. The task replaces
it: `j` is the task's one action, so a trained policy writes the actuator's
control and the sine is what the mechanism does with no policy installed.

Assumed, not selected: no joint damping, friction, backlash, gear ratio or
armature is declared, so the joint is ideal and the motor is an ideal torque
source inside its limit. No real servo was chosen — nothing here is a
manufacturer part, and `docs/inventory.md` reports 0 catalogued components.
The observed `effort` is this actuator's force in N·mm; the carriage's is in N,
which is why the two projects' control-cost terms are not comparable
(see `../PROGRESS.md`).
