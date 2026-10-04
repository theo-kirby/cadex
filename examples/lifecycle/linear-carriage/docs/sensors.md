# Sensors

Verified against source: 2026-10-04. [Cadex-new]

The exported task observes joint position `travel (mm)`, the moving body's
`com` (centre of mass XYZ, mm), and the motor's `effort` (N).
The joint position is read through the one declared sensor, `encoder`
(`joint_encoder` on `j`), which is the only channel the policy reads on the
machine; `com` and `effort` are `role="privileged"`, simulation-only
quantities for the reward and the critic (ADR-408). All are ideal simulator
observations, not selected physical parts.
The task has five scalar observation channels; the policy reads one of them
and drives one action.
The reward uses `com_z` and `effort`; see PROGRESS.md for units and scores.
