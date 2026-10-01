"""Can a gripper's target pose go through the reach path unchanged?  (ot11)

The long-term rung asks for a fourth behaviour -- a gripper closing on a
target pose -- through the same loop with no new code path. Before anything
is pre-registered, this measures whether the existing vocabulary can say it.

A gripper is two jaws on one actuator, so the probe declares the smallest
one the engine accepts: a grounded palm, two fingers on parallel hinges, a
``gears`` coupling (1:1, counter-rotating) between them, and one position
servo on finger A. The target pose is then one number, and a ``point`` goal
on finger A's tip states it exactly (ADR-462). The spec is the reach
vocabulary. Nothing here trains, and nothing in the engine is changed.

It writes the script into a live cadexd, then for every frozen evaluation
seed draws the goals the engine's evaluation would hold (``goals.py``'s
order), recovers the drawn driven angle from each target, and asks two
questions of the pose the mechanism would *really* be in -- finger B where
the gear puts it, not where the draw left it:

* does the drawn target exist, i.e. are the jaws apart at the coupled pose;
* does the draw see the same contacts at its own pose as at the coupled one.

Last, it plays one episode commanding full travel each way, to measure that
the coupling is live in the dynamics (B follows -A) and where the jaws meet.

    pixi run python docs/probes/ot11/runner/grip_probe.py --out OUT.json
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src/Mod/cadex"))
sys.path.insert(0, str(REPO / "src/Mod/cadex/cadex_tests"))

SEEDS = [1101, 1102, 1103, 1104, 1105, 1106, 1107, 1108, 1109, 1110]
LIMIT_DEG = 20.0  # each finger's hinge range is +/- this

_HINGE = {"axis": [1, 0, 0], "angle_degrees": -90}

SCRIPT = f"""
palm_solid = part.box(80, 20, 20, origin=[-40, -10, 180])
finger_solid = part.box(8, 10, 80, origin=[-4, -5, -80])
finger_b_solid = part.box(8, 10, 80, origin=[-4, -5, -80])
palm = assembly.component(palm_solid, grounded=True)
fa = assembly.component(finger_solid, placement=[-20, 0, 180])
fb = assembly.component(finger_b_solid, placement=[20, 0, 180])
ha = assembly.joint("revolute",
    assembly.connector(palm, "origin", offset={{"position": [-20, 0, 180], **{_HINGE!r}}}),
    assembly.connector(fa, "origin", offset={{"position": [0, 0, 0], **{_HINGE!r}}}),
    angle_limits_degrees=[-{LIMIT_DEG}, {LIMIT_DEG}])
hb = assembly.joint("revolute",
    assembly.connector(palm, "origin", offset={{"position": [20, 0, 180], **{_HINGE!r}}}),
    assembly.connector(fb, "origin", offset={{"position": [0, 0, 0], **{_HINGE!r}}}),
    angle_limits_degrees=[-{LIMIT_DEG}, {LIMIT_DEG}])
mesh = assembly.joint("gears",
    assembly.connector(fa, "origin", offset={{"position": [0, 0, 0], **{_HINGE!r}}}),
    assembly.connector(fb, "origin", offset={{"position": [0, 0, 0], **{_HINGE!r}}}),
    radius1_mm=10, radius2_mm=10)
asm = assembly.assembly([palm, fa, fb], [ha, hb, mesh])
diag = assembly.solve(asm)
servo = assembly.actuator(ha, kind="position", control_deg="0",
                          stiffness_nmm_per_deg=400, damping_nmms_per_deg=12)
model = assembly.mjcf(asm, [
    assembly.body(palm, density_kg_m3=2700),
    assembly.body(fa, density_kg_m3=2700, collision=assembly.collision(
        "box", size_mm=[8, 10, 80], offset=[0, 0, -40])),
    assembly.body(fb, density_kg_m3=2700, collision=assembly.collision(
        "box", size_mm=[8, 10, 80], offset=[0, 0, -40])),
], actuators=[servo], observations=[
    assembly.observation(ha, "position", name="jaw"),
])
target = assembly.goal("target", kind="point", tip=fa,
                       tip_offset_mm=[0, 0, -80], min_separation_mm=5,
                       resample_seconds=2.0)
spec = assembly.success(
    [{{"id": "arrives", "metric": "final_error_arm_lengths_max", "max": 0.05}},
     {{"id": "in_time", "metric": "time_to_target_s_max", "max": 1.0}},
     {{"id": "no_overshoot", "metric": "overshoot_ratio_max", "max": 0.2}}],
    seeds={SEEDS!r}, tip=fa, tip_offset_mm=[0, 0, -80], episode_seconds=4.0)
job = assembly.task(model, actions=[servo], goals=[target],
                    reward=[assembly.reward(
                        "-sqrt((target_x - target_x)^2)", weight=0.0, label="none")],
                    episode_seconds=4.0, control_hz=50, success=spec,
                    label="grip")
result = {{"palm_solid": palm_solid, "finger_solid": finger_solid,
          "finger_b_solid": finger_b_solid, "palm": palm, "fa": fa, "fb": fb,
          "ha": ha, "hb": hb, "mesh": mesh, "asm": asm, "diag": diag,
          "model": model, "job": job}}
"""


def _contacts(mujoco, model, data) -> list[list[str]]:
    rows = []
    for index in range(int(data.ncon)):
        contact = data.contact[index]
        names = []
        for geom in (int(contact.geom1), int(contact.geom2)):
            body = int(model.geom_bodyid[geom])
            names.append(mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body) or str(body))
        rows.append(sorted(names))
    return rows


def _jaw_gap_mm(mujoco, model, data, a_body: int, b_body: int) -> float:
    """Signed distance between the two fingers' collision geoms, mm."""
    best = math.inf
    fromto = __import__("numpy").zeros(6)
    for ga in range(model.ngeom):
        if int(model.geom_bodyid[ga]) != a_body:
            continue
        for gb in range(model.ngeom):
            if int(model.geom_bodyid[gb]) != b_body:
                continue
            best = min(best, float(mujoco.mj_geomDistance(model, data, ga, gb, 0.2, fromto)))
    return best * 1000.0


def measure(task: dict, xml: bytes) -> dict:
    import mujoco
    import CadexDynamics as dynamics

    model = mujoco.MjModel.from_xml_string(xml.decode("utf-8"))
    played = dynamics.evaluation_task(task)
    entry = played["goal"][0]
    driven = entry["joints"]
    assert len(driven) == 1, driven
    qa = int(driven[0]["qpos_adr"])
    names = {mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, j): j for j in range(model.njnt)}
    a_body = int(entry["body_id"])
    b_body = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "fb"))
    qb = [int(model.jnt_qposadr[j]) for j in range(model.njnt) if int(model.jnt_bodyid[j]) == b_body][0]
    key = int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, str(played["episode"]["reset_keyframe"])))
    equalities = [
        {"type": int(model.eq_type[i]), "obj1": int(model.eq_obj1id[i]),
         "obj2": int(model.eq_obj2id[i]), "polycoef": [float(v) for v in model.eq_data[i][:5]]}
        for i in range(model.neq)
    ]
    data = mujoco.MjData(model)

    def tip_at(angle: float, follower: float | None) -> tuple[list[float], list, float]:
        mujoco.mj_resetDataKeyframe(model, data, key)
        data.qpos[qa] = angle
        if follower is not None:
            data.qpos[qb] = follower
        mujoco.mj_forward(model, data)
        tip = dynamics._goal_tip_m(data, a_body, entry["local_m"])
        return tip, _contacts(mujoco, model, data), _jaw_gap_mm(mujoco, model, data, a_body, b_body)

    mujoco.mj_resetDataKeyframe(model, data, key)
    rest_a, rest_b = float(data.qpos[qa]), float(data.qpos[qb])
    low, high = float(driven[0]["low"]), float(driven[0]["high"])

    def angle_for(point: list[float]) -> float:
        grid = [low + (high - low) * k / 4000 for k in range(4001)]
        return min(grid, key=lambda a: math.dist(tip_at(a, None)[0], point))

    rows = []
    for seed in SEEDS:
        rng = random.Random(seed)
        dynamics.apply_randomisation(mujoco, model, mujoco.MjData(model), played, rng=rng)
        dynamics.draw_episode_variation(played, rng)
        goals = dynamics.draw_episode_goals(mujoco, model, played, rng)
        for index, segment in enumerate(goals[0]["segments"]):
            point = [value / float(entry["scale"]) for value in segment]
            angle = angle_for(point)
            _tip, drawn_contacts, drawn_gap = tip_at(angle, None)
            coupled = rest_b - (angle - rest_a)
            _tip, real_contacts, real_gap = tip_at(angle, coupled)
            rows.append({
                "seed": seed, "segment": index,
                "driven_deg": round(math.degrees(angle), 3),
                "follower_deg_in_draw": round(math.degrees(rest_b), 3),
                "follower_deg_coupled": round(math.degrees(coupled), 3),
                "jaw_gap_mm_in_draw": round(drawn_gap, 3),
                "jaw_gap_mm_coupled": round(real_gap, 3),
                "contacts_in_draw": drawn_contacts,
                "contacts_coupled": real_contacts,
            })

    # The coupling in the dynamics: command each end of the servo's range.
    def play(sign: float) -> dict:
        """Hold the servo at one end of what it may command, for the episode."""
        last: dict = {}

        def sample(_step, state, final, action):
            if final:
                last.update(
                    action=[float(v) for v in action] if action is not None else None,
                    driven=float(state.qpos[qa]), follower=float(state.qpos[qb]),
                    gap=_jaw_gap_mm(mujoco, model, state, a_body, b_body),
                    contacts=_contacts(mujoco, model, state))
            return None

        trace = dynamics.evaluate_episode(model, played, seed=None, sample=sample,
                                          actions=lambda _s, _o: [sign])
        return {
            "action": sign, "clamped_action": last["action"],
            "termination": trace.get("termination") or trace.get("terminated"),
            "driven_deg": round(math.degrees(last["driven"]), 3),
            "follower_deg": round(math.degrees(last["follower"]), 3),
            "jaw_gap_mm": round(last["gap"], 3),
            "contacts": last["contacts"],
        }

    return {
        "equalities": equalities, "joints": sorted(names),
        "rest_deg": [round(math.degrees(rest_a), 3), round(math.degrees(rest_b), 3)],
        "driven_range_deg": [round(math.degrees(low), 3), round(math.degrees(high), 3)],
        "arm_length_mm": task["success"].get("scale", {}).get("arm_length_mm"),
        "draws": rows,
        "infeasible": sum(1 for r in rows if r["jaw_gap_mm_coupled"] < 0.0),
        "contact_disagrees": sum(1 for r in rows if r["contacts_in_draw"] != r["contacts_coupled"]),
        "played": [play(-1.0), play(1.0)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    from test_dynamics_policy_live import _Session

    root = Path(tempfile.mkdtemp(prefix="grip-probe-"))
    try:
        with _Session(root) as session:
            written = session.write(SCRIPT)
            report: dict = {"accepted": bool(written.get("ok"))}
            if not written.get("ok"):
                report["refusal"] = written
            else:
                bundle_path = Path(written["display"]["job"]["artifact_path"])
                task = json.loads(bundle_path.read_text(encoding="utf-8"))
                xml = Path(written["display"]["model"]["artifact_path"]).read_bytes()
                report.update(measure(task, xml))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "draws"}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
