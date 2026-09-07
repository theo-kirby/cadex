# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
# Ideal vertical linear guide; no contact or physical actuator geometry.
p = params(policy_on=num(0.0, min=0.0, max=1.0, step=1.0),
           lift_weight=num(1.0e-4, min=1.0e-5, max=1.0e-3, step=1.0e-5))
plate = part.box(60, 60, 6)
carriage = part.box(20, 20, 20)
base = assembly.component(plate, grounded=True)
slide = assembly.component(carriage, placement=[12, 0, 40])
j = assembly.joint("slider",
                   assembly.connector(base, "origin", offset={"position": [12, 0, 40]}),
                   assembly.connector(slide, "origin"))
asm = assembly.assembly([base, slide], [j])
diag = assembly.solve(asm)
motor = assembly.actuator(j, kind="motor", control_n="0", force_limit_n=4)
model = assembly.mjcf(asm, [
    assembly.body(base, density_kg_m3=2700),
    assembly.body(slide, density_kg_m3=2700),
], actuators=[motor], observations=[
    assembly.observation(j, "position", name="travel"),
    assembly.observation(slide, "centre_of_mass", name="com"),
    assembly.observation(motor, "actuator_force", name="effort"),
])
job = assembly.task(model, actions=[motor],
                    reward=[assembly.reward("-(com_z - 60)^2", weight=p.lift_weight,
                                            label="lift"),
                            assembly.reward("abs(effort)", weight=-1.0e-6,
                                            label="control_cost")],
                    episode_seconds=1.0, control_hz=50, label="lift")
result = {"plate": plate, "carriage": carriage, "base": base, "slide": slide,
          "j": j, "asm": asm, "diag": diag, "model": model, "job": job}
if p.policy_on >= 0.5:
    policy = assembly.policy(job, weights="job.cxpolicy", sha256="0000000000000000000000000000000000000000000000000000000000000000")
    run = assembly.rollout(policy, frames_per_second=25, seed=3)
    result["policy"] = policy
    result["run"] = run
