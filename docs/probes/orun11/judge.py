"""Judge one checkpoint on the gallop_spec its own bundle carries (ADR-774's flat sprint spec).

usage: PYTHONPATH=cli pixi run python docs/probes/orun11/judge.py PROJECT RUN_TRAIN_DIR POLICY OUT_NAME [--closure-only]

Runs the engine's own evaluation child over the trained bundle and model,
read in place from the run's ``train/`` directory, and writes
``PROJECT/evaluations/OUT_NAME/`` (``evaluation.json``, the seed traces and
``judged-task.json``). The policy is declared on no project and nothing is
accepted. Derived from orun10's ``judge_gallop.py``, which lived outside
the repository.

It then reads the loop-closure error of every seed trace (the gap an
``equality/connect`` or ``equality/joint`` row in the model leaves open) by
reading the body placements every trace frame carries, and appends a
``closure`` block to the report: per equality row, the median and the
largest error over the evaluation window (from 1 s). A connect is in mm, a
joint coupling in degrees. ``--closure-only`` re-reads that block into an
evaluation already in ``OUT_NAME`` and plays nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "Mod" / "cadex"))

import CadexDynamics as D  # noqa: E402
from cadex_cli.engine import resolve_engine  # noqa: E402
from cadex_cli.evaluate import check_out, run_evaluation  # noqa: E402
from cadex_cli.smoke import retained_attempt  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def closure(model_path: Path, out: Path, warmup_s: float = 1.0) -> dict:
    """Each equality row's error over every seed's window, from the traces' body placements.

    A connect's error is the distance between its two anchors in the world;
    a joint coupling's is how far the first joint's angle is from the
    polynomial of the second's, each angle read as the child body's rotation
    against its parent about the joint's axis, from the model's rest pose.
    """

    import math
    import mujoco
    import numpy as np

    model = mujoco.MjModel.from_xml_path(str(model_path))
    body = lambda i: mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(i))

    def rot(xyzw):
        x, y, z, w = xyzw
        m = np.zeros(9)
        mujoco.mju_quat2Mat(m, np.array([w, x, y, z], dtype=float))
        return m.reshape(3, 3)

    def angle(placements, joint):
        child = int(model.jnt_bodyid[joint])
        parent = int(model.body_parentid[child])
        rel = rot(placements[body(parent)]["rotation_xyzw"]).T @ rot(placements[body(child)]["rotation_xyzw"])
        q0 = np.zeros(9)
        mujoco.mju_quat2Mat(q0, model.body_quat[child])
        delta = q0.reshape(3, 3).T @ rel
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, delta.reshape(9))
        return 2.0 * math.atan2(float(np.dot(quat[1:], model.jnt_axis[joint])), float(quat[0]))

    def anchor(placements, b, local_m):
        p = placements[body(b)]
        return np.asarray(p["position_mm"]) + rot(p["rotation_xyzw"]) @ (1000.0 * np.asarray(local_m))

    rows = {}
    for i in range(model.neq):
        kind = int(model.eq_type[i])
        if kind not in (int(mujoco.mjtEq.mjEQ_CONNECT), int(mujoco.mjtEq.mjEQ_JOINT)):
            continue
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_EQUALITY, i) or f"eq{i}"
        rows[i] = {"name": name, "kind": "connect" if kind == int(mujoco.mjtEq.mjEQ_CONNECT) else "joint",
                   "values": []}
    for path in sorted(out.glob("seed-*-trace.json")):
        trace = json.loads(path.read_text())
        for frame in trace["frames"]:
            t = frame.get("nominal_time_s")
            if t is None or t < warmup_s:
                continue
            placements = frame["component_placements"]
            for i, row in rows.items():
                if row["kind"] == "connect":
                    if int(model.eq_objtype[i]) == int(mujoco.mjtObj.mjOBJ_SITE):
                        s1, s2 = int(model.eq_obj1id[i]), int(model.eq_obj2id[i])
                        a = anchor(placements, model.site_bodyid[s1], model.site_pos[s1])
                        b = anchor(placements, model.site_bodyid[s2], model.site_pos[s2])
                    else:
                        a = anchor(placements, model.eq_obj1id[i], model.eq_data[i][0:3])
                        b = anchor(placements, model.eq_obj2id[i], model.eq_data[i][3:6])
                    row["values"].append(float(np.linalg.norm(a - b)))
                else:
                    q1 = angle(placements, int(model.eq_obj1id[i]))
                    q2 = angle(placements, int(model.eq_obj2id[i]))
                    c = model.eq_data[i]
                    target = c[0] + c[1] * q2 + c[2] * q2 ** 2 + c[3] * q2 ** 3 + c[4] * q2 ** 4
                    row["values"].append(math.degrees(abs(q1 - target)))
    return {"warmup_s": warmup_s,
            "rows": [{"name": r["name"], "kind": r["kind"], "unit": "mm" if r["kind"] == "connect" else "deg",
                      "samples": len(r["values"]),
                      "median": statistics.median(r["values"]) if r["values"] else None,
                      "max": max(r["values"]) if r["values"] else None} for r in rows.values()]}


def main() -> None:
    root, train, policy, name = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    if "--closure-only" in sys.argv:
        trained = json.loads((train / "gallop-task.json").read_text())
        out = root / "evaluations" / name
        report = json.loads((out / "evaluation.json").read_text())
        report["closure"] = closure(train / Path(trained["model"]["path"]).name, out)
        (out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report["closure"], indent=1))
        return
    trained_path = train / "gallop-task.json"
    trained = json.loads(trained_path.read_text())
    model = train / Path(trained["model"]["path"]).name
    header = D.decode_policy(policy.read_bytes(), context="judge")["header"]
    assert header["task"]["sha256"] == sha(trained_path), "policy was not trained on this bundle"
    assert header["model"]["sha256"] == sha(model) == trained["model"]["sha256"], "model mismatch"
    success = trained["success"]
    assert success["label"] == "gallop_spec" and success.get("heels"), "not ADR-774's gallop spec"
    state, _staging, _result = retained_attempt(root)
    # The run's own record names the revision it trained on; the project may have
    # moved on since (orun11 iteration 7: heel1-s1 on 07a92830, judged on ca32a9b4).
    run_json = train.parent / "run.json"
    trained_on = json.loads(run_json.read_text()).get("model", {}) if run_json.is_file() else {}
    if trained_on.get("accepted_revision"):
        state = {"accepted_revision": trained_on["accepted_revision"],
                 "accepted_digest": trained_on.get("digest") or state.get("accepted_digest")}
    components = re.findall(r'<body[^>]*name="([^"]+)"', model.read_text())
    out = check_out(root, root / "evaluations" / name)
    out.mkdir(parents=True, exist_ok=True)
    judged = out / "judged-task.json"
    judged.write_text(json.dumps(trained))
    inputs = {"accepted_revision": str(state["accepted_revision"]),
              "accepted_digest": str(state.get("accepted_digest") or ""),
              "policy_output": "undeclared", "task_output": "gallop", "model_output": "cat_model",
              "policy": policy.resolve(), "policy_sha256": sha(policy), "weights": policy.name,
              "trained_task_sha256": sha(trained_path), "task": judged, "model": model,
              "components": components, "seeds": [int(s) for s in success["seeds"]]}
    report = run_evaluation(resolve_engine(), inputs, out)
    report["judged_spec_task"] = "gallop_spec"
    report["judged_policy"] = str(policy)
    report["closure"] = closure(model, out)
    (out / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(name, report["verdict"], len(report["summary"]["passed"]))


if __name__ == "__main__":
    main()
