# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""ADR-981: ``--drive-torque-scale``, a fixed drive peak the trainer and the player share.

Run: ``CUDA_VISIBLE_DEVICES= python -m pytest training/test_drive_torque_scale.py`` from the repo.
"""

from __future__ import annotations

import numpy as np
import pytest

import cadex_goto
import cadex_train as T
from test_distill import header_of
from test_flag_randomisation import TWO_DRIVES, drawn, options
from test_race_terrain_training import WALKER, walker_task

HELD = """
<mujoco><option timestep="0.002" gravity="0 0 0"/>
  <worldbody><body><joint name="j" type="hinge" axis="0 0 1" damping="1e6"/>
    <geom type="cylinder" size="0.05 0.01" mass="1"/></body></worldbody>
  <actuator><general joint="j" forcelimited="true" forcerange="-14 14" gainprm="1"/>
    <motor joint="j" gear="1"/></actuator>
</mujoco>"""


def test_the_flag_is_one_by_default_and_checked() -> None:
    assert options().drive_torque_scale == 1.0
    assert T.resolved_drive_torque_scale(options()) == 1.0
    assert T.resolved_drive_torque_scale(options("--drive-torque-scale", "1.3")) == 1.3
    for bad in ("0", "-1.3", "nan"):
        with pytest.raises(SystemExit):
            T.resolved_drive_torque_scale(options("--drive-torque-scale", bad))


def test_only_force_limited_drives_are_scaled() -> None:
    limit = np.array([[-14.0, 14.0], [-1.0, 2.0]])
    out = T.scaled_drive_range(np, limit, np.array([True, False]), 1.3)
    assert np.allclose(out, [[-18.2, 18.2], [-1.0, 2.0]])
    assert T.scaled_drive_range(np, limit, np.array([True, True]), 1.0) is limit


def test_the_trained_model_carries_the_scaled_peak_and_draws_scale_it() -> None:
    import mujoco

    plain = mujoco.MjModel.from_xml_string(TWO_DRIVES)
    host, fields = drawn(walker_task(), "--drive-torque-scale", "1.3", xml=TWO_DRIVES)
    assert fields == {}                                   # a fixed scale is no draw
    on = plain.actuator_forcelimited.astype(bool)
    assert np.allclose(host.actuator_forcerange[on], 1.3 * plain.actuator_forcerange[on])
    assert np.array_equal(host.actuator_forcerange[~on], plain.actuator_forcerange[~on])
    _h, both = drawn(walker_task(), "--drive-torque-scale", "1.3",
                     "--randomise-drive-torque", "0.9", "1.1", xml=TWO_DRIVES)
    _h, alone = drawn(walker_task(), "--randomise-drive-torque", "0.9", "1.1", xml=TWO_DRIVES)
    assert np.allclose(both["actuator_forcerange"], 1.3 * alone["actuator_forcerange"])


def test_the_header_carries_the_scale() -> None:
    assert header_of(options(), None)["training"]["drive_torque_scale"] == 1.0
    pushed = header_of(options("--drive-torque-scale", "1.3"), None)
    assert pushed["training"]["drive_torque_scale"] == 1.3


def _player(scale, no_load=0.0, heat=None):
    import mujoco

    player = cadex_goto.Player.__new__(cadex_goto.Player)
    player.np, player.mujoco = np, mujoco
    player.no_load_speed, player.drive_heat, player.heat_start, player.heat = no_load, heat, 0.0, None
    player.drive_torque_scale, player._ranges = scale, {}
    return player


@pytest.mark.parametrize("scale,heat", [(1.0, None), (1.3, None), (1.3, (0.45, 3.0))])
def test_the_player_applies_the_scaled_peak_and_heat_rates_it(scale, heat) -> None:
    import mujoco

    model = mujoco.MjModel.from_xml_string(HELD)
    data = mujoco.MjData(model)
    data.ctrl[:] = [100.0, 0.0]
    player = _player(scale, heat=heat)
    forces = []
    for _ in range(15000 if heat else 3):
        player.step(model, data)
        forces.append(float(data.actuator_force[0]))
    assert forces[0] == pytest.approx(14.0 * scale, rel=1e-6)
    if heat:                                              # folds back to 0.45 of the scaled peak
        assert forces[-1] == pytest.approx(0.45 * 14.0 * scale, rel=2e-2)


def test_the_player_reads_the_header_and_a_judge_overrides_it() -> None:
    import inspect

    source = inspect.getsource(cadex_goto.Player.__init__)
    assert 'get("drive_torque_scale", 1.0)' in source
    assert "float(drive_torque_scale) if drive_torque_scale is not None else trained_scale" in source
