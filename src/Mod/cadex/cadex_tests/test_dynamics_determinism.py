# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The solver flags, measured both ways (docs/MUJOCO.md M3, phase 0).

M2's lesson, charged by ``balanceinertia``: *a flag is only a promise about
a default*. Hazard 4 said "force single-threaded" as though that were one
switch. It is not, and measuring turned up three things this suite now
pins.

**Islands are on by default, not off.** ``mjDSBL_ISLAND`` is a *disable*
bit and a default compile has ``disableflags == 0``. So the name reads
backwards from what it does, and a translator that "left islands off"
by writing nothing had them on.

**On a model with no geoms the flag changes nothing, and once geoms exist
it does.** The four-bar runs 300 steps to bit-identical qpos either way.
Three boxes settling on a plane -- the M3 scenario, in raw MuJoCo, so the
measurement does not wait on our own collision work -- come out about
2e-14 apart after 1500 steps. That is small, it is not zero, and a digest
does not care which.

**Both settings are reproducible; only one is written down.** Islands off
is the single monolithic constraint solve, whose row ordering does not
depend on how contacts happen to partition into islands, and it costs
nothing because MuJoCo only parallelises an ``mjData`` that has been handed
a thread pool -- which this module never does. So the flag is set
explicitly, and asserted on the *compiled* model, where a MuJoCo release
changing a default would land.

``mjENBL_SLEEP`` gets the same treatment for a louder reason: a sleeping
body stops integrating, and what M3 simulates is a mechanism settling.
"""

from __future__ import annotations

import pytest

import CadexDynamics as dyn
import dynamics_fixtures as fx

mujoco = pytest.importorskip("mujoco")

#: Three bodies on a plane, in raw MuJoCo. Deliberately not built through
#: our translator: this measures what *MuJoCo* does with contact, and it
#: had to be answerable in phase 0, before phase 1 existed to build a geom.
CONTACT_XML = """
<mujoco>
  <option timestep="0.002"/>
  <worldbody>
    <geom name="floor" type="plane" size="5 5 0.1"/>
    <body name="a" pos="0 0 0.3"><freejoint/><geom type="box" size="0.05 0.05 0.05"/></body>
    <body name="b" pos="0.4 0 0.5"><freejoint/><geom type="box" size="0.06 0.04 0.03"/></body>
    <body name="c" pos="-0.3 0.2 0.9"><freejoint/><geom type="sphere" size="0.04"/></body>
  </worldbody>
</mujoco>
"""


def _settle(disable: int, steps: int = 1500) -> list[float]:
    model = mujoco.MjModel.from_xml_string(CONTACT_XML)
    model.opt.disableflags = int(model.opt.disableflags) | int(disable)
    data = mujoco.MjData(model)
    for _step in range(steps):
        mujoco.mj_step(model, data)
    return [float(value) for value in data.qpos]


def test_island_is_a_disable_bit_so_a_bare_compile_has_islands_on() -> None:
    """The measurement that made the flag worth setting at all."""

    bare = mujoco.MjModel.from_xml_string("<mujoco/>")
    assert int(bare.opt.disableflags) == 0
    assert not int(bare.opt.disableflags) & int(mujoco.mjtDisableBit.mjDSBL_ISLAND), (
        "mjDSBL_ISLAND is a disable bit: a zero disableflags word means "
        "islands are ON, which is the opposite of how the hazard read"
    )


def test_islands_change_nothing_on_a_model_with_no_contact() -> None:
    """Why M2 could ignore the flag, stated as a number rather than a hope."""

    components, joints, _placements = fx.four_bar()
    traces = []
    for disable in (0, int(mujoco.mjtDisableBit.mjDSBL_ISLAND)):
        built = dyn.build_model(components, joints, time_step_s=1.0 / 600.0)
        model = built["model"]
        model.opt.disableflags = disable
        data = mujoco.MjData(model)
        data.qpos[:] = built["qpos_solved"]
        mujoco.mj_forward(model, data)
        rows = []
        for _step in range(300):
            mujoco.mj_step(model, data)
            rows.append([float(value) for value in data.qpos])
        traces.append(rows)
    assert traces[0] == traces[1], "no geoms, no islands to form, no difference"


def test_islands_do_change_numbers_once_contact_exists() -> None:
    """And this is the whole reason the flag is set rather than inherited.

    The delta is around 1e-14 -- physically nothing, digest-wise decisive.
    Asserting it is non-zero rather than asserting its size keeps the test
    honest across MuJoCo patch releases: what matters is that the setting
    is observable, not how far apart it puts two boxes.
    """

    islands_on = _settle(0)
    islands_off = _settle(int(mujoco.mjtDisableBit.mjDSBL_ISLAND))
    assert islands_on != islands_off
    worst = max(abs(a - b) for a, b in zip(islands_on, islands_off, strict=True))
    assert worst > 0.0
    assert worst < 1.0e-9, (
        "a difference this large would be a physics difference, not an "
        "ordering one, and would mean the flag does more than we think"
    )


@pytest.mark.parametrize(
    "disable", [0, int(mujoco.mjtDisableBit.mjDSBL_ISLAND)], ids=["islands-on", "islands-off"]
)
def test_each_island_setting_is_reproducible_on_its_own(disable: int) -> None:
    """Neither setting is *non*-deterministic; they simply differ.

    Which is what makes this a choice about what gets written down rather
    than a bug being worked around.
    """

    assert _settle(disable) == _settle(disable)


def test_the_translator_disables_islands_and_leaves_sleep_off() -> None:
    """Asserted on the compiled model, which is where a default change lands."""

    built = dyn.build_model(*fx.pendulum()[:2])
    model = built["model"]
    assert int(model.opt.disableflags) == int(mujoco.mjtDisableBit.mjDSBL_ISLAND)
    assert int(model.opt.enableflags) == 0
    assert not int(model.opt.enableflags) & int(mujoco.mjtEnableBit.mjENBL_SLEEP), (
        "a sleeping body stops integrating, and a settling mechanism is "
        "exactly what M3 simulates"
    )
    assert built["disableflags"] == int(model.opt.disableflags)
    assert built["enableflags"] == 0


def test_a_flag_the_translator_did_not_set_is_refused() -> None:
    """The guard is an equality, not a bit test, and this is why.

    A future MuJoCo whose compiler sets some new default bit is exactly as
    digest-moving as one that drops ours, and only an equality notices
    both. The refusal is loud so the re-measurement happens deliberately.
    """

    built = dyn.build_model(*fx.pendulum()[:2])
    model = built["model"]
    dyn._verify_solver_flags(mujoco, model)  # as compiled, it passes

    model.opt.enableflags = int(mujoco.mjtEnableBit.mjENBL_SLEEP)
    with pytest.raises(dyn.DynamicsError) as sleep_error:
        dyn._verify_solver_flags(mujoco, model)
    assert sleep_error.value.reason == "solver_flags_changed"
    assert sleep_error.value.observed["enableflags"] == int(
        mujoco.mjtEnableBit.mjENBL_SLEEP
    )

    model.opt.enableflags = 0
    model.opt.disableflags = 0  # islands quietly back on
    with pytest.raises(dyn.DynamicsError) as island_error:
        dyn._verify_solver_flags(mujoco, model)
    assert island_error.value.reason == "solver_flags_changed"


def test_the_evidence_records_which_flags_the_trace_ran_under() -> None:
    """A reader should not have to infer them from a MuJoCo version."""

    components, joints, _placements = fx.pendulum()
    run = dyn.simulate(
        components, joints, start_time_s=0.0, end_time_s=0.1, frames_per_second=30
    )
    evidence = run["evidence"]
    assert evidence["solver_disableflags"] == int(mujoco.mjtDisableBit.mjDSBL_ISLAND)
    assert evidence["solver_enableflags"] == 0
