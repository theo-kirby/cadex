# hinged-arm — Architecture

Verified against source: 2026-09-08. [Cadex-new]

`script.py` declares one revolute joint, an 80×8×8 mm steel arm and a grounded plate.
OCCT geometry supplies exact inertias to the MJCF. This is an ideal joint
model without collision geometry, hardware or travel stops.

`policy_on` switches policy verification and rollout on after training;
`lift_weight` sets the height reward coefficient. The source starts with
policy disabled and a placeholder hash. `cadex walk` supplies the hash.

Outputs include geometry, assembly solve diagnostics, MJCF, the training
task, then policy verification and the rollout. Training is local CPU
from the offboard venv, 1 iteration and 4 environments. Paths are
`runs/baseline/train`, `runs/baseline/rollout`, `runs/baseline/review.json`.
The walk commits `docs/inventory.md` and `docs/clearance.md` alongside the
review. Clearance counts in `PROGRESS.md` use the initial solved pose,
0.1 mm minimum distance and 1e-6 mm³ maximum volume; unknown is not clear.
The source and measured PROGRESS.md live in the parent repository;
generated outputs and policies are excluded from version control.

See [sensors](docs/sensors.md), [decisions](DECISIONS.md),
[results](PROGRESS.md), and [reproduction](../README.md).
