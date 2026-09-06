# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
# Plate-and-arm reference from cli/tests/test_train.py.

p = params(policy_on=num(0.0, min=0.0, max=1.0, step=1.0),
           lift_weight=num(1.0e-4, min=1.0e-5, max=1.0e-3, step=1.0e-5))
plate = part.box(60, 60, 6)
arm = part.box(80, 8, 8)
base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
j = assembly.joint("revolute",
                   assembly.connector(base, "origin",
                                      offset={"position": [12, 0, 6],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}),
                   assembly.connector(swing, "origin",
                                      offset={"position": [0, 0, 0],
                                              "axis": [1, 0, 0],
                                              "angle_degrees": 90}))
asm = assembly.assembly([base, swing], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_nmm="120*sin(2*pi*time)",
                          torque_limit_nmm=400)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(swing, density_kg_m3=7850),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="angle"),
    assembly.observation(swing, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(com_z - 60)^2", weight=p.lift_weight,
                                            label="lift"),
                            assembly.reward("abs(effort)", weight=-1.0e-6,
                                            label="control_cost")],
                    episode_seconds=1.0, control_hz=50, label="lift")
result = {"plate": plate, "arm": arm, "base": base, "swing": swing,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
if p.policy_on >= 0.5:
    policy = assembly.policy(job, weights="job.cxpolicy", sha256="0000000000000000000000000000000000000000000000000000000000000000")
    run = assembly.rollout(policy, frames_per_second=25, seed=3)
    result["policy"] = policy
    result["run"] = run
