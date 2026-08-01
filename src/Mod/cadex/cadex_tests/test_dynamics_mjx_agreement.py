# SPDX-License-Identifier: LGPL-2.1-or-later

"""Do MJX and stock MuJoCo agree about a Cadex model? ADR-103's answer, pinned.

Training runs in **MJX**; the engine, the viewport and every local replay run
in **stock MuJoCo**. Same file, same intended physics, two implementations --
and hazard 19 is what it cost when nobody had measured whether they agree:
ADR-101 watched the same quantity move in opposite directions on the same
weights, MJX reporting mean episode length rising 58 -> 149 steps while the
engine measured it peaking at 162 and collapsing to 39. Three training runs
were spent before anything checked.

ADR-103 checked, with ``~/cdx-mjc/mjx_agreement.py``, and the answer is
narrow and useful:

* with **no contact**, the two agree to machine precision -- the integrator,
  the actuators and the joint dynamics are the same physics on both sides;
* with a **plane** floor they still do, to 3e-16 on the median step;
* with a **box** floor -- which is what ``export_mjcf`` writes for a
  grounded body, and what every Cadex model therefore has -- the median
  single-step disagreement is four orders of magnitude worse and the worst
  step is eleven. Precision is not the cause: this is measured in float64 on
  both sides.

So the thing to pin is not one tolerance but the *shape* of the answer, and
the shape is what these tests assert. If a future MJX makes box-against-box
match, `test_the_exported_box_floor_is_what_costs_the_agreement` fails --
and that failure is good news, which its message says.

**Every measurement here re-syncs.** MJX is put back onto MuJoCo's state
after every control step, so each sample is one step's disagreement and
nothing accumulates. That is deliberate and it is the only measurement on a
contacting mechanism that is about the two engines rather than about the
mechanism: a biped in contact is stiff enough that a 1e-7 nudge inside
*stock MuJoCo alone* separates the trajectory just as fast as MJX does
(ADR-103 measured that control too). A test that compared free-running
trajectories would be pinning a Lyapunov exponent and calling it agreement.

Gated on jax and mujoco.mjx, which are the offboard trainer's dependencies
and deliberately absent from the engine environment (ADR-084). Under
``pixi run test-engine`` everything here skips except the one test that
needs no MJX at all -- the export property the rest of the file is about.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest

import dynamics_policy_fixtures as pf


#: Control steps per measurement, and solver steps per control step. 120 x 5
#: at the fixture's 2 ms is 1.2 s -- long enough for the block to settle,
#: bounce and be driven about, and short enough that the whole file is a
#: couple of minutes on a laptop CPU.
STEPS = 120
SUBSTEPS = 5

#: What the two engines are allowed to differ by in one control step, in
#: metres or radians of ``qpos``. Every one of these is an **output** of
#: ADR-103's measurement rather than a guess, quoted with the measured value
#: beside it and roughly two orders of headroom -- enough that a compiler or
#: a point release cannot trip it, tight enough that the finding it encodes
#: cannot quietly stop being true.
NO_CONTACT_MEDIAN = 1.0e-13      # measured 2.220e-16
NO_CONTACT_WORST = 1.0e-7        # measured 6.409e-10
PLANE_MEDIAN = 1.0e-13           # measured 3.331e-16
PLANE_WORST = 1.0e-11            # measured 1.332e-15
BOX_MEDIAN = 1.0e-9              # measured 4.620e-12
BOX_WORST = 1.0e-2               # measured 1.217e-04

#: How much worse the box floor is than the plane one, as a ratio of median
#: single-step disagreement. Measured: 4.620e-12 / 3.331e-16, about 14000x.
#: Asserted at 100x, which is far enough below the measurement to be a claim
#: about a fact rather than about a decimal place.
BOX_PENALTY = 100.0


def _mjx_or_skip():
    """The offboard dependencies, or the skip that explains why they are not here."""

    try:
        import jax
        import mujoco  # noqa: F401
        import mujoco.mjx  # noqa: F401
    except Exception:
        pytest.skip(
            "jax and mujoco.mjx are the offboard trainer's dependencies and "
            "are deliberately absent from the engine environment (ADR-084). "
            "Run this file from a venv built from training/requirements.txt."
        )
    # float64 on the JAX side, because the question is whether the two
    # engines model the same physics and float32 would answer a different
    # one. Global and only honoured by arrays made after it, so it goes here
    # -- before a single MJX array exists. Nothing else in the engine suite
    # imports jax in-process, so there is nothing for it to surprise.
    jax.config.update("jax_enable_x64", True)
    return jax


def _variant(xml_text: str, *, floor: str = "box", contact: bool = True) -> str:
    """The fixture's own model, with one property changed, in memory.

    Never written back: the point of a rung is to say what a property costs,
    and changing the exporter is a separate decision with its own ADR.
    """

    tree = ET.fromstring(xml_text)
    option = tree.find("option")
    if option is None:
        option = ET.SubElement(tree, "option")
    if not contact:
        flag = option.find("flag")
        if flag is None:
            flag = ET.SubElement(option, "flag")
        flag.set("contact", "disable")
    if floor == "plane":
        for geom in tree.iter("geom"):
            if not (geom.get("name") or "").startswith("floor/"):
                continue
            # A plane's surface is its own origin and a box's is its top
            # face, so the plane goes up by the box's half-height and the
            # keyframe still has the block resting on the floor rather than
            # a centimetre inside it.
            half = [float(v) for v in (geom.get("size") or "0 0 0").split()]
            pos = [float(v) for v in (geom.get("pos") or "0 0 0").split()]
            geom.set("type", "plane")
            geom.set("size", "0 0 0.05")
            geom.set("pos", f"{pos[0]} {pos[1]} {pos[2] + (half[2] if len(half) > 2 else 0.0)}")
    return ET.tostring(tree, encoding="unicode")


#: One measurement per distinct model, for the whole file. Each is about
#: fifty seconds of stepping two engines in lockstep and three of the five
#: tests want the same two models, so without this the file spends most of
#: its time recomputing numbers it already has. Keyed by the model's own
#: bytes, so a variant that differs by one attribute is a different entry.
_MEASURED: dict[str, dict] = {}


def _disagreement(xml_text: str) -> dict:
    """One step's disagreement between the two engines, sampled `STEPS` times.

    Driven open loop by a sinusoid at a quarter of each actuator's range: a
    fixed sequence, identical on both sides, so nothing that comes out of
    here is a controller reacting to its own divergence.
    """

    import hashlib

    key = hashlib.sha256(xml_text.encode("utf-8")).hexdigest()
    if key in _MEASURED:
        return _MEASURED[key]

    jax = _mjx_or_skip()
    import jax.numpy as jnp
    import mujoco
    import mujoco.mjx as mjx
    import numpy as np

    model = mujoco.MjModel.from_xml_string(xml_text)
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    mujoco.mj_forward(model, data)

    put = mjx.put_model(model)
    state = mjx.forward(put, mjx.put_data(model, data))

    @jax.jit
    def advance(state, ctrl):
        state = state.replace(ctrl=jnp.asarray(ctrl, dtype=state.ctrl.dtype))

        def one(carry, _):
            return mjx.step(put, carry), None

        state, _ = jax.lax.scan(one, state, None, length=SUBSTEPS)
        return state

    span = np.array([
        max(abs(float(model.actuator_ctrlrange[index][0])),
            abs(float(model.actuator_ctrlrange[index][1])), 1.0)
        for index in range(model.nu)
    ])
    interval = float(model.opt.timestep) * SUBSTEPS

    qpos_errors, qvel_errors, contact_mismatches = [], [], 0
    for step in range(STEPS):
        ctrl = 0.25 * span * math.sin(2.0 * math.pi * 1.5 * step * interval)
        data.ctrl[:] = ctrl
        for _ in range(SUBSTEPS):
            mujoco.mj_step(model, data)
        state = advance(state, ctrl)

        qpos_errors.append(float(np.max(np.abs(
            np.asarray(data.qpos) - np.asarray(state.qpos)))))
        qvel_errors.append(float(np.max(np.abs(
            np.asarray(data.qvel) - np.asarray(state.qvel)))))
        theirs = int((np.asarray(state._impl.contact.dist) < 0.0).sum())
        if int(data.ncon) != theirs:
            contact_mismatches += 1

        # Re-sync: the next sample starts from one state, not two.
        state = mjx.forward(put, mjx.put_data(model, data))

    def percentile(values, fraction):
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1,
                           int(round(fraction * (len(ordered) - 1))))]

    _MEASURED[key] = {
        "median": percentile(qpos_errors, 0.5),
        "p95": percentile(qpos_errors, 0.95),
        "worst": max(qpos_errors),
        "velocity_worst": max(qvel_errors),
        "contact_mismatches": contact_mismatches,
        "samples": len(qpos_errors),
    }
    return _MEASURED[key]


# ---------------------------------------------------------------------------
# The property the whole file is about, which needs no MJX to state.
# ---------------------------------------------------------------------------


def test_a_grounded_body_still_exports_as_a_box_geom() -> None:
    """The model property ADR-103's tolerances are conditioned on.

    ``export_mjcf`` writes a grounded body's collision shape as a
    ``type="box"``, so every Cadex model's floor is a box and every contact
    a machine makes with it is box-against-box -- the primitive pair MJX
    reproduces least well, and the reason `BOX_MEDIAN` is four orders looser
    than `PLANE_MEDIAN`.

    If this fails because the exporter now writes a plane, that is a
    direction change and a good one: it makes the two engines agree to
    machine precision, and the tolerances in this file should be tightened
    to the plane ones in the same commit that changes it. It is not
    something to make the assertion looser about.
    """

    prepared = pf.shoved_bundle()
    tree = ET.fromstring(prepared["model_xml"].decode("utf-8"))
    floors = [geom for geom in tree.iter("geom")
              if (geom.get("name") or "").startswith("floor/")]
    assert floors, "the shoved fixture has no floor geom to be about"
    assert all(geom.get("type") == "box" for geom in floors)


# ---------------------------------------------------------------------------
# What the two engines actually do. MJX-gated.
# ---------------------------------------------------------------------------


def test_the_two_simulators_agree_exactly_when_nothing_touches() -> None:
    """Rung one: with collision off, this is the same physics twice.

    The integrator, the actuators, the joint damping and armature, the
    gravity -- all of it agrees to float64 machine epsilon on the median
    step. That is what makes the contact result below a finding rather than
    a shrug: there is nothing else wrong.
    """

    prepared = pf.shoved_bundle()
    xml = _variant(prepared["model_xml"].decode("utf-8"), contact=False)
    measured = _disagreement(xml)

    assert measured["samples"] == STEPS
    assert measured["median"] < NO_CONTACT_MEDIAN, measured
    assert measured["worst"] < NO_CONTACT_WORST, measured
    assert measured["contact_mismatches"] == 0, measured


def test_a_plane_floor_agrees_to_machine_precision() -> None:
    """Rung two: contact is not the problem. Box-against-box is.

    The same mechanism, the same contacts, the same solver -- with the floor
    written as a plane instead of a box, and the two engines are back to
    3e-16 on the median step. This is the measurement that turns "MJX is
    different" into "one primitive pair is different", and it is what makes
    changing the export a decision worth taking rather than a guess.
    """

    prepared = pf.shoved_bundle()
    xml = _variant(prepared["model_xml"].decode("utf-8"), floor="plane")
    measured = _disagreement(xml)

    assert measured["median"] < PLANE_MEDIAN, measured
    assert measured["worst"] < PLANE_WORST, measured
    assert measured["contact_mismatches"] == 0, measured


def test_the_two_simulators_agree_step_for_step_on_the_model_as_exported() -> None:
    """The guarantee, on the model the engine actually writes.

    Not machine precision and it will not be while the floor is a box, but
    bounded and measured: a median step of 5e-12 and a worst of 1e-4 over
    1.2 s of driven contact. What this pins is that the two engines are
    still doing the same physics on the model as shipped -- so a training
    run and a local replay are runs of the same mechanism, and the numbers
    they produce can be compared statistically even though no two
    trajectories can be compared step for step.
    """

    prepared = pf.shoved_bundle()
    xml = _variant(prepared["model_xml"].decode("utf-8"))
    measured = _disagreement(xml)

    assert measured["median"] < BOX_MEDIAN, measured
    assert measured["worst"] < BOX_WORST, measured


def test_the_exported_box_floor_is_what_costs_the_agreement() -> None:
    """The finding itself, as the thing that fails when it stops being true.

    A failure here means MJX and MuJoCo have come to agree about
    box-against-box, which is the outcome this project wants: retire the
    plane-floor recommendation in docs/MUJOCO.md, tighten `BOX_MEDIAN` to
    `PLANE_MEDIAN`, and note the MJX version it changed in. Do not widen
    `BOX_PENALTY` to make it pass.
    """

    prepared = pf.shoved_bundle()
    xml = prepared["model_xml"].decode("utf-8")
    box = _disagreement(_variant(xml))
    plane = _disagreement(_variant(xml, floor="plane"))

    assert box["median"] > BOX_PENALTY * plane["median"], {
        "box": box, "plane": plane,
        "note": "MJX now matches MuJoCo on box-against-box -- see this "
                "test's docstring, this is good news",
    }
