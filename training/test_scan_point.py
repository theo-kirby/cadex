"""ADR-983: a height-scan row's ``point_mm`` reads a point fixed in the body's frame.

The trainer's ``height_scan_vector`` and the engine's ``height_scan_values`` both move the scan from the body's
origin to ``xpos + xmat @ point`` (metres, then the row's scale), turned with the body, and agree with MuJoCo's own
``geom_xpos`` for a geom placed at that point. A row without ``point_mm`` reads as before.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "Mod" / "cadex"))
import CadexDynamics  # noqa: E402

from cadex_train import height_scan_vector  # noqa: E402

XML = """<mujoco><worldbody>
  <body name="leg" pos="0.1 0.2 0.5"><joint name="free" type="free"/>
    <geom name="core" size="0.02" mass="1"/>
    <body name="paw"><geom name="ball" size="0.015" pos="-0.195 0.1012 0.015" mass="0.1"/></body>
  </body></worldbody></mujoco>"""


def _row(point, offsets=((0.0, 0.0),)):
    row = {"body_id": 2, "scale": 1000.0, "offsets_mm": [list(o) for o in offsets],
           "channels": [f"s{k}" for k in range(len(offsets))]}
    if point is not None:
        row["point_mm"] = list(point)
    return row


def _posed(angle):
    import mujoco
    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)
    half = angle / 2.0
    data.qpos[3:7] = [math.cos(half), 0.3 * math.sin(half), math.sqrt(1 - 0.09 - 0.16) * math.sin(half),
                      0.4 * math.sin(half)]
    mujoco.mj_forward(model, data)
    return model, data


def test_point_reads_the_geom_centre_turned_with_the_body():
    for angle in (0.0, 0.7, -1.9):
        model, data = _posed(angle)
        task = {"scans": [_row((-195.0, 101.2, 15.0))]}
        want = 1000.0 * data.geom_xpos[1][2]
        got = height_scan_vector(np, task, np.asarray(data.xpos), np.asarray(data.xmat))
        assert abs(float(got[0]) - want) < 1e-6
        eng = CadexDynamics.height_scan_values(task, data.xpos, data.xmat, None)
        assert abs(eng["s0"] - want) < 1e-6


def test_no_point_reads_the_origin_as_before():
    model, data = _posed(0.7)
    task = {"scans": [_row(None)]}
    got = height_scan_vector(np, task, np.asarray(data.xpos), np.asarray(data.xmat))
    assert abs(float(got[0]) - 1000.0 * data.xpos[2][2]) < 1e-9
    eng = CadexDynamics.height_scan_values(task, data.xpos, data.xmat, None)
    assert abs(eng["s0"] - 1000.0 * data.xpos[2][2]) < 1e-9


def test_trainer_and_engine_agree_with_offsets_and_batch():
    model, data = _posed(1.1)
    task = {"scans": [_row((10.0, -20.0, 30.0), offsets=((0.0, 0.0), (100.0, 50.0)))]}
    xpos = np.stack([np.asarray(data.xpos)] * 3)
    xmat = np.stack([np.asarray(data.xmat)] * 3)
    got = height_scan_vector(np, task, xpos, xmat)
    eng = CadexDynamics.height_scan_values(task, data.xpos, data.xmat, None)
    assert got.shape == (3, 2)
    for k in range(2):
        assert np.allclose(got[:, k], eng[f"s{k}"], atol=1e-6)
