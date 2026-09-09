# Actuators

Verified against source: 2026-09-08. [Cadex-new]

One actuator drives the one joint: `j/motor`, a `motor`-kind actuator on the
slider joint `j`, exported as an MJCF `<general>` with `forcerange="-4 4"` —
a force limit of 4 N, written in the recipe as `force_limit_n=4`.

The recipe's open-loop control is `0` N. The task replaces it: `j` is the
task's one action, so a trained policy writes the actuator's control and the
uncontrolled carriage simply falls.

Assumed, not selected: no joint damping, friction, lead screw, gearing or
armature is declared, and the guide has no end stops, so the joint is an ideal
unlimited vertical slide and the motor an ideal force source inside its limit.
4 N against the carriage's weight is what makes the baseline score what it is —
`../PROGRESS.md` records the fall to z = -4699 mm at 1 s. No real actuator was
chosen; `docs/inventory.md` reports 0 catalogued components. The observed
`effort` is this actuator's force in N, where the arm's is N·mm.
