# Sensors

Verified against source: 2026-09-06. [Cadex-new]

The exported task observes joint position `angle (degrees)`, the moving body's
`com` (centre of mass XYZ, mm), and the motor's `effort` (N·mm).
These are ideal simulator observations, not selected physical sensors.
The policy has five scalar observation inputs and one action.
The reward uses `com_z` and `effort`; see PROGRESS.md for units and scores.
