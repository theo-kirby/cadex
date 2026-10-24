"""A trained policy beside the clip it trained on, both drawn on leo v06 by the engine's film renderer (orun19 F1).

usage: CUDA_VISIBLE_DEVICES= PYTHONPATH=cli pixi run python docs/probes/orun19/clip_side_film.py \
           PROJECT OUT_WEBM [side_film options] 'TITLE@EVAL_DIR=LABEL,BUNDLE#K=LABEL,...' [...]

orun18's ``side_film.py``, unchanged, with one more kind of panel. ``BUNDLE#K``
(an absolute path to a trained task bundle, ``#`` and the index of a stride in
its ``reference_schedule``) is that stride's ``qpos``, the clip the trainer
tracked, posed by MuJoCo's kinematics on the bundle's own model and played in
loops, each loop moved on by the stride's length. Nothing is simulated: it is
the reference, not a rollout. The model is checked against the bundle's
``model.sha256`` and must place every component the row's first evaluation
places. The clip's frames are written as a trace beside a copy of that
evaluation's report in a temporary directory and drawn by ``side_film.panel``
like any other, so both panels share the stage, camera rule, floor and scale.

A clip is a derivative of the capture (orun18 D5/D5a), so the film goes outside
the repository (``~/mocap/films/``).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("side_film", HERE.parent / "orun18" / "side_film.py")
SF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SF)
F = SF.F

_policy_panel = SF.panel
_last: dict = {}
_work = Path(tempfile.mkdtemp(prefix="clip-side-film-"))


def clip_frames(bundle: Path, index: int, names: list[str], until: float) -> tuple[list[dict], dict]:
    """Solved frames of stride ``index`` from t = 0 to at least ``until``, and what was drawn."""

    task = json.loads(bundle.read_text())
    stride = task["reference_schedule"][index]
    xml = bundle.parent / Path(task["model"]["path"]).name
    digest = hashlib.sha256(xml.read_bytes()).hexdigest()
    F._require(digest == task["model"]["sha256"], f"{xml.name} is not the bundle's model")
    model = mujoco.MjModel.from_xml_path(str(xml))
    data = mujoco.MjData(model)
    ids = {n: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n) for n in names}
    F._require(all(i >= 0 for i in ids.values()), "the bundle's model lacks a component the evaluation places")
    qpos = np.asarray(stride["qpos"], dtype=float)
    F._require(qpos.shape[1] == model.nq, "the clip's qpos does not fit the model")
    dt = float(stride["sample_dt_s"])
    samples = len(qpos)
    length = float(stride["parameters"]["stride_length_m"])
    frames, worst = [], 0.0
    k = 0
    while True:
        t = k * dt
        q = qpos[k % samples].copy()
        q[0] += (k // samples) * length
        data.qpos[:] = q
        mujoco.mj_fwdPosition(model, data)
        if model.neq:
            worst = max(worst, float(np.abs(data.efc_pos[:data.ne]).max()) if data.ne else 0.0)
        frames.append({"frame_index": len(frames) + 1, "frame_kind": "solver_output", "nominal_time_s": t,
                       "component_placements": {
                           n: {"position_mm": [float(v) * 1000 for v in data.xpos[i]],
                               "rotation_xyzw": [float(data.xquat[i][1]), float(data.xquat[i][2]),
                                                 float(data.xquat[i][3]), float(data.xquat[i][0])]}
                           for n, i in ids.items()}})
        if t >= until:
            break
        k += 1
    about = {"bundle_sha256": hashlib.sha256(bundle.read_bytes()).hexdigest(), "stride": index,
             "label": stride["label"].split(":")[0], "speed_m_s": round(stride["parameters"]["speed_m_s"], 3),
             "stride_length_m": round(length, 4), "period_s": round(stride["parameters"]["period_s"], 4),
             "qpos_sha256": hashlib.sha256(json.dumps(stride["qpos"]).encode()).hexdigest(),
             "constraint_residual_mm": round(worst * 1000, 4), "model_sha256": digest}
    return frames, about


def panel(root: Path, directory: Path, seed: int, start: float, span: float) -> dict:
    """A policy's evaluation as ``side_film`` draws it, or a ``BUNDLE#K`` clip in its place."""

    bundle, sep, index = str(directory).rpartition("#")
    if not sep:
        p = _policy_panel(root, directory, seed, start, span)
        _last["dir"] = directory
        return p
    F._require("dir" in _last, "a clip panel must follow an evaluation in its row")
    report = json.loads((_last["dir"] / "evaluation.json").read_text())
    row = next(r for r in report["seeds"] if int(r["seed"]) == seed)
    trace = json.loads((_last["dir"] / row["trace"]["file"]).read_text())
    names = list(next(f for f in trace["frames"] if f["frame_kind"] == "solver_output")["component_placements"])
    frames, about = clip_frames(Path(bundle), int(index), names, start + span)
    out = _work / f"clip-{about['label']}-{index}"
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"schema": F.TRACE_SCHEMA,
                       "frames": [{"frame_index": 0, "frame_kind": "input", "nominal_time_s": None,
                                   "component_placements": frames[0]["component_placements"]}] + frames}).encode()
    (out / "clip-trace.json").write_bytes(body)
    report["seeds"] = [{"seed": seed, "trace": {"file": "clip-trace.json",
                                                "sha256": hashlib.sha256(body).hexdigest()}}]
    report["policy_sha256"] = None
    report["judged_command_mm_s"] = round(about["speed_m_s"] * 1000)
    (out / "evaluation.json").write_text(json.dumps(report))
    print(json.dumps({"clip_panel": about}))
    p = _policy_panel(root, out, seed, start, span)
    p["name"] = f"{about['label']} (clip)"
    return p


SF.panel = panel

if __name__ == "__main__":
    SF.main(sys.argv[1:])
