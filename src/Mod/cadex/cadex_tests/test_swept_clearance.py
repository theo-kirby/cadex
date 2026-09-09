# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Clearance held over a mechanism's whole travel (ADR-130, slice O2b).

ADR-126 gave a mate a static interference check: after placing one part on
another's mount, boolean the two and refuse a non-zero common volume. That
proves the parts fit **in the pose they were mated in**, and a mechanism has
more than one pose. The differentiating check is the swept one, and
`assembly.simulation` already produces the sweep — a trace is the mechanism
at every step of its travel, and nobody was looking at it as geometry.

The pairs are named rather than inferred: two parts joined at a joint are
supposed to touch, so "every pair" would refuse every assembly, and guessing
which touching is intended is exactly the kind of invention a declared
interface exists to prevent.
"""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

import cadex_assembly_worker as worker


# -- the box rejection, which is what makes a swept check affordable --------


class _Box:
    def __init__(self, low, high) -> None:
        self.XMin, self.YMin, self.ZMin = low
        self.XMax, self.YMax, self.ZMax = high


def test_boxes_far_apart_cost_three_comparisons() -> None:
    near = _Box((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    far = _Box((30.0, 0.0, 0.0), (40.0, 10.0, 10.0))
    assert worker._boxes_clear(near, far, 2.0) is True
    assert worker._boxes_clear(far, near, 2.0) is True
    # 20 mm apart is clear of a 2 mm gap and not of a 25 mm one, and the
    # second case is the one that has to fall through to a real distance
    # query rather than being answered by the boxes.
    assert worker._boxes_clear(near, far, 25.0) is False


def test_overlapping_boxes_are_never_clear() -> None:
    first = _Box((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))
    second = _Box((5.0, 5.0, 5.0), (15.0, 15.0, 15.0))
    assert worker._boxes_clear(first, second, 0.0) is False


# -- the pairs, validated before any of it runs -----------------------------


def _api():
    import CadexScriptedDomains as domains
    from cadex_domain_api import create_domain_api

    pack = domains.get_xscript_pack("AssemblyWorkbench")
    return create_domain_api(pack.domain, pack.api_exports, pack.output_types)


def _mechanism(api):
    plate = api.component(_solid(), grounded=True)
    arm = api.component(_solid(), placement=[0, 0, 40])
    joint = api.joint(
        "revolute",
        api.connector(plate, "origin", offset=[12, 0, 4]),
        api.connector(arm, "origin"),
    )
    return plate, arm, api.assembly([plate, arm], [joint]), joint


#: `api.component` takes a stable input reference; in a script the runtime
#: turns a `part` value into one, and here we write it out.
_SOURCES = itertools.count()


def _solid():
    return {"document_uid": "doc", "object_name": f"Solid{next(_SOURCES)}"}


def test_a_gap_with_no_pairs_is_refused() -> None:
    """There is no safe default, so there is no default."""

    api = _api()
    _plate, _arm, model, joint = _mechanism(api)
    with pytest.raises(ValueError) as caught:
        api.simulation(model, [api.motion(joint, "2 * pi * time")], clearance_mm=2.0)
    assert "clearance" in str(caught.value)


def test_pairs_with_no_gap_are_refused() -> None:
    """"More than zero apart" passes on two parts that are touching."""

    api = _api()
    plate, arm, model, joint = _mechanism(api)
    with pytest.raises(ValueError) as caught:
        api.simulation(
            model, [api.motion(joint, "2 * pi * time")], clearance=[(plate, arm)]
        )
    assert "clearance_mm" in str(caught.value)


def test_a_pair_must_be_two_components_of_this_assembly() -> None:
    api = _api()
    plate, arm, model, joint = _mechanism(api)
    stranger = api.component(_solid(), placement=[0, 0, 90])
    for pairs, why in (
        ([(plate, plate)], "a part cannot clear itself"),
        ([(plate, arm), (arm, plate)], "the same pair twice"),
        ([(plate, stranger)], "not a component of this assembly"),
        ([(plate,)], "a pair is two"),
    ):
        with pytest.raises(ValueError) as caught:
            api.simulation(
                model,
                [api.motion(joint, "2 * pi * time")],
                clearance=pairs,
                clearance_mm=2.0,
            )
        assert "clearance" in str(caught.value), why


def test_the_pairs_reach_the_worker_as_a_property() -> None:
    api = _api()
    plate, arm, model, joint = _mechanism(api)
    sim = api.simulation(
        model,
        [api.motion(joint, "2 * pi * time")],
        clearance=[(plate, arm)],
        clearance_mm=2.5,
    )
    assert sim.properties["clearance_mm"] == 2.5
    assert [list(pair) for pair in sim.properties["clearance"]] == [[plate, arm]]


# -- against a live solver, on a mechanism that really does swing into it ---

#: An arm 30 mm long swinging a full turn about the plate's centre, and a
#: post standing in its way. `near` is 6 mm outside the arm's tip: the arm
#: reaches x = 30 and the post's near face is at x = 36, so the closest
#: approach over the sweep is a number this test can name.
_MECHANISM = """
plate = part.box(120, 120, 4, origin=[-60, -60, 0])
arm = part.box(30, 6, 6, origin=[0, -3, 0])
post = part.box(8, 8, 26, origin=[-4, -4, 0])

base = assembly.component(plate, grounded=True)
swing = assembly.component(arm, placement=[0, 0, 40])
tower = assembly.component(post, placement=[{post_x}, 0, 4], grounded=True)
j = assembly.joint("revolute",
                   assembly.connector(base, "origin", offset=[0, 0, 4]),
                   assembly.connector(swing, "origin"))
asm = assembly.assembly([base, swing, tower], [j])
diag = assembly.solve(asm)
spin = assembly.motion(j, "2 * pi * time")
sim = assembly.simulation(asm, [spin], end_time_s=1.0, time_step_s=0.05{extra})
result = {{"plate": plate, "arm": arm, "post": post,
          "base": base, "swing": swing, "tower": tower,
          "j": j, "asm": asm, "diag": diag, "spin": spin, "sim": sim}}
"""


def _source(post_x: float, extra: str = "") -> str:
    return _MECHANISM.format(post_x=post_x, extra=extra)


def _live():
    from test_cadexd_lifecycle import FREECADCMD

    return FREECADCMD is not None


def _write(client, source: str, prefix: str):
    client.request("open_project", {"project_root": tempfile.mkdtemp(prefix=prefix)})
    return client.request("write_script", {"source": source, "expected_revision": ""})


@pytest.mark.skipif(not _live(), reason="No FreeCADCmd binary available.")
def test_a_sweep_that_stays_clear_and_one_that_does_not() -> None:
    """The same mechanism, the same trace, two clearance promises."""

    from test_cadexd_lifecycle import _spawn_cadexd, _stop

    client = None
    try:
        client = _spawn_cadexd()

        # No promise at all: the arm sweeps straight through the post and
        # kinematics does not care, which is the state of the world ADR-130
        # is about.
        through = _write(client, _source(post_x=20.0), "cadexd-clear-none-")
        assert through["ok"] is True, json.dumps(through)[:2000]

        # ...and with the promise, the same script is refused with the
        # millimetres and the frame.
        clause = ', clearance=[(swing, tower)], clearance_mm=2.0'
        hit = _write(client, _source(20.0, clause), "cadexd-clear-hit-")
        assert hit["ok"] is False, json.dumps(hit)[:2000]
        details = (hit.get("observed") or {}).get("details") or {}
        assert details.get("stage") == "simulation_clearance", details
        closest = details["closest_approach"]
        assert sorted(closest["components"]) == ["swing", "tower"], closest
        assert closest["distance_mm"] == 0.0, closest
        assert details["frames_checked"] >= 2, details
        assert details["query_cap_reached"] is False, details

        # The post moved out of reach: the arm's tip is at x = 30 and the
        # post's near face at x = 36, so 2 mm is kept over the whole turn
        # and 8 mm is not — and the refusal quotes the 6.
        clear = _write(client, _source(40.0, clause), "cadexd-clear-ok-")
        assert clear["ok"] is True, json.dumps(clear)[:2000]

        wide = ', clearance=[(swing, tower)], clearance_mm=8.0'
        tight = _write(client, _source(40.0, wide), "cadexd-clear-tight-")
        assert tight["ok"] is False, json.dumps(tight)[:2000]
        measured = (tight.get("observed") or {}).get("details", {})[
            "closest_approach"
        ]["distance_mm"]
        assert 5.0 < measured < 7.0, measured
    finally:
        _stop(client)


# -- the frame the sweep measures a component in (ADR-242) ------------------


REPO_ROOT = Path(__file__).resolve().parents[4]
_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
_FRAME_BINARY = next(
    (candidate for candidate in _FREECADCMD_CANDIDATES if candidate.is_file()), None
)


#: An arm whose transform rides on the *shape* -- which is every ``lib.*``
#: part, because ``lib._place`` moves a canonical body with one
#: ``part.transform`` and ``Shape.translate`` writes a placement instead of
#: moving geometry -- swinging past a post authored in world coordinates.
#: The arm's geometry stands 20..50 mm out along its own +X, so a quarter
#: turn drives it straight through a post at y 36..44. Before ADR-242 the
#: sweep read ``App::Link.Shape``, which *replaces* the linked placement
#: with the link's own, so the arm was measured back at 0..30 mm and the
#: collision was reported as 33 mm of clear air.
_SWEPT_FRAME_DRIVER = r"""
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))
import cadex_assembly_worker as worker

doc = App.newDocument("SweptFrame")


def link(name, shape, source_name):
    source = doc.addObject("Part::Feature", source_name)
    source.Shape = shape
    obj = doc.addObject("App::Link", name)
    obj.LinkedObject = source
    return obj


arm_shape = Part.makeBox(30, 6, 6, App.Vector(0, -3, 0))
arm_shape.translate(App.Vector(20, 0, 0))
swing = link("swing", arm_shape, "ArmSource")
tower = link("tower", Part.makeBox(8, 8, 26, App.Vector(-4, 36, 0)), "PostSource")
doc.recompute()

pairs = [("swing", "tower")]
components = {"swing": swing, "tower": tower}


def sweep(gap, angles):
    prepared = worker._clearance_prepare(components, pairs)
    budget = {"spent": 0, "cap": 10 ** 6, "capped": False}
    rows = []
    for index, angle in enumerate(angles):
        swing.Placement = App.Placement(
            App.Vector(), App.Rotation(App.Vector(0, 0, 1), angle)
        )
        for breach in worker._clearance_at_frame(
            components, pairs, gap, budget, prepared
        ):
            rows.append({"frame_index": index, "angle_deg": angle, **breach})
    return rows


print("SWEPT-FRAME " + json.dumps(
    {
        "rest_distance_mm": sweep(100.0, [0.0])[0]["distance_mm"],
        "breaches": sweep(2.0, [5.0 * step for step in range(37)]),
    },
    sort_keys=True,
))
"""


def _drive_swept_frame(tmp_path) -> dict:
    driver = tmp_path / "swept_frame_driver.py"
    driver.write_text(_SWEPT_FRAME_DRIVER, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            str(_FRAME_BINARY),
            "-c",
            (
                "import sys; sys.argv = ['driver', "
                f"{str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    marker = next(
        (
            line
            for line in completed.stdout.splitlines()
            if line.startswith("SWEPT-FRAME ")
        ),
        None,
    )
    assert marker, (
        f"swept driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    return json.loads(marker.removeprefix("SWEPT-FRAME "))


@pytest.mark.skipif(
    _FRAME_BINARY is None,
    reason="No FreeCADCmd binary available to place a component.",
)
def test_a_shape_placed_component_is_swept_where_the_assembly_puts_it(
    tmp_path,
) -> None:
    """A collision the sweep used to report as 33 mm of clear air.

    ADR-241 fixed the static measurement and left this one measured, saying
    a swept breach distance for a ``lib.*``-placed body was not to be
    believed. On the pre-fix source this driver reports an empty breach list
    and a 33.0 mm rest distance: the arm passes through the post and the
    promise the script made is kept by measuring the wrong part.
    """

    report = _drive_swept_frame(tmp_path)

    # The static pose, measured where the assembly puts the arm: the arm's
    # near corner (20, 3) to the post's (4, 36) is sqrt(16^2 + 33^2), not
    # the 33.0 mm the un-composed frame gave.
    assert report["rest_distance_mm"] == pytest.approx(36.6742, abs=5e-4), report

    breaches = report["breaches"]
    assert breaches, "the arm sweeps through the post and nothing was reported"
    assert {tuple(row["components"]) for row in breaches} == {("swing", "tower")}
    # Contact runs across the quarter turn and is a real intersection, not a
    # near miss: the arm reaches y = 50 and the post's near face is at 36.
    assert min(row["distance_mm"] for row in breaches) == 0.0, breaches
    angles = sorted(row["angle_deg"] for row in breaches)
    assert 70.0 <= angles[0] <= 90.0, breaches
    assert 90.0 <= angles[-1] <= 110.0, breaches
    # ...and the frame index is the one the caller would name in the refusal.
    first = min(breaches, key=lambda row: row["frame_index"])
    assert first["frame_index"] == int(first["angle_deg"] / 5.0), breaches



# -- the same check over a trace the solver already wrote (ADR-283) ---------


def _rollout_scene(api):
    """One two-component mechanism with a policy to play, as api values."""

    source = _solid()
    plate = api.component(source, grounded=True)
    arm = api.component(_solid(), placement=[0, 0, 40])
    joint = api.joint(
        "revolute",
        api.connector(plate, "origin", offset=[12, 0, 4]),
        api.connector(arm, "origin"),
    )
    model = api.assembly([plate, arm], [joint])
    motor = api.actuator(joint, kind="motor", control_nmm="0", torque_limit_nmm=500)
    bodies = [api.body(plate, density_kg_m3=7850), api.body(arm, density_kg_m3=7850)]
    exported = api.mjcf(
        model,
        bodies,
        actuators=[motor],
        observations=[api.observation(joint, "position", name="angle")],
    )
    task = api.task(
        exported,
        actions=[motor],
        reward=[api.reward("angle", weight=1.0e-3, label="lift")],
        episode_seconds=1.0,
        control_hz=50,
    )
    return {
        "plate": plate,
        "arm": arm,
        "joint": joint,
        "assembly": model,
        "bodies": bodies,
        "policy": api.policy(task, weights="walk.cxpolicy", sha256="a" * 64),
    }


def test_the_mujoco_solvers_take_the_same_promise_api_simulation_does() -> None:
    """One helper, three solvers: the pairs reach the worker as properties."""

    api = _api()
    scene = _rollout_scene(api)
    pair = [(scene["plate"], scene["arm"])]

    run = api.dynamics(
        scene["assembly"], scene["bodies"], clearance=pair, clearance_mm=2.0
    )
    assert run.properties["clearance_mm"] == 2.0
    assert [list(entry) for entry in run.properties["clearance"]] == [
        [scene["plate"], scene["arm"]]
    ]

    play = api.rollout(scene["policy"], clearance=pair, clearance_mm=1.5)
    assert play.properties["clearance_mm"] == 1.5
    assert [list(entry) for entry in play.properties["clearance"]] == [
        [scene["plate"], scene["arm"]]
    ]


def test_a_half_promise_is_refused_on_the_mujoco_solvers_too() -> None:
    """The two halves mean nothing alone, whichever solver is asked."""

    api = _api()
    scene = _rollout_scene(api)
    pair = [(scene["plate"], scene["arm"])]

    for call in (
        lambda **kw: api.dynamics(scene["assembly"], scene["bodies"], **kw),
        lambda **kw: api.rollout(scene["policy"], **kw),
    ):
        with pytest.raises(ValueError) as gapless:
            call(clearance=pair)
        assert "clearance_mm" in str(gapless.value)
        with pytest.raises(ValueError) as pairless:
            call(clearance_mm=2.0)
        assert "clearance" in str(pairless.value)

    # ...and a component of some other assembly is still not a pair member.
    stranger = api.component(_solid(), placement=[0, 0, 90])
    with pytest.raises(ValueError) as caught:
        api.rollout(
            scene["policy"],
            clearance=[(scene["plate"], stranger)],
            clearance_mm=2.0,
        )
    assert "clearance" in str(caught.value)


#: The ADR-242 mechanism again -- an arm whose transform rides on its shape,
#: swinging past a post -- but posed from a *trace* rather than by a solver.
#: The driver measures each pose twice: once live, the way the kinematics
#: frame loop does, and once by handing ``_clearance_over_trace`` the frames
#: ``_compact_placement`` wrote from those same poses. The two must agree
#: exactly; composing a foreign pose onto a linked component is the defect
#: class ADR-241 and ADR-242 each had to fix once already.
_TRACE_CLEARANCE_DRIVER = r"""
import json
import sys
from pathlib import Path

import FreeCAD as App
import Part

cadex_root = Path(sys.argv[-1])
sys.path.insert(0, str(cadex_root))
import cadex_assembly_worker as worker

doc = App.newDocument("TraceClearance")


def link(name, shape, source_name):
    source = doc.addObject("Part::Feature", source_name)
    source.Shape = shape
    obj = doc.addObject("App::Link", name)
    obj.LinkedObject = source
    return obj


arm_shape = Part.makeBox(30, 6, 6, App.Vector(0, -3, 0))
arm_shape.translate(App.Vector(20, 0, 0))
swing = link("swing", arm_shape, "ArmSource")
tower = link("tower", Part.makeBox(8, 8, 26, App.Vector(-4, 36, 0)), "PostSource")
doc.recompute()

pairs = [("swing", "tower")]
components = {"swing": swing, "tower": tower}
angles = [5.0 * step for step in range(37)]

# Half one: pose the arm live and measure, which is what the kinematics
# frame loop does -- and record the frame it would have written.
prepared = worker._clearance_prepare(components, pairs)
budget = {"spent": 0, "cap": 10 ** 6, "capped": False}
live = []
frames = []
for index, angle in enumerate(angles):
    swing.Placement = App.Placement(
        App.Vector(), App.Rotation(App.Vector(0, 0, 1), angle)
    )
    frames.append(
        {
            "frame_index": index,
            "nominal_time_s": index * 0.1,
            "component_placements": {
                name: worker._compact_placement(component.Placement)
                for name, component in components.items()
            },
        }
    )
    for breach in worker._clearance_at_frame(
        components, pairs, 2.0, budget, prepared
    ):
        live.append({"frame_index": index, **breach})

# Half two: forget the poses, then measure from the frames alone.
resting = App.Placement(App.Vector(3, 4, 5), App.Rotation(App.Vector(0, 0, 1), 17.0))
swing.Placement = resting
summary = worker._clearance_over_trace(components, pairs, 2.0, frames)

print("TRACE-CLEARANCE " + json.dumps(
    {
        "live": live,
        "swept": summary,
        "restored": worker._compact_placement(swing.Placement),
        "resting": worker._compact_placement(resting),
        "no_pairs": worker._clearance_over_trace(components, [], 0.0, frames),
    },
    sort_keys=True,
))
"""


def _drive(source: str, marker: str, tmp_path) -> dict:
    driver = tmp_path / "driver.py"
    driver.write_text(source, encoding="utf-8")
    cadex_root = Path(__file__).resolve().parent.parent
    completed = subprocess.run(
        [
            str(_FRAME_BINARY),
            "-c",
            (
                "import sys; sys.argv = ['driver', "
                f"{str(cadex_root)!r}]; "
                f"exec(open({str(driver)!r}).read())"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=900,
        env={**os.environ, "PYTHONHASHSEED": "0"},
        check=False,
    )
    line = next(
        (row for row in completed.stdout.splitlines() if row.startswith(marker)),
        None,
    )
    assert line, (
        f"driver produced no report; exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout[-6000:]}\nstderr:\n{completed.stderr[-6000:]}"
    )
    return json.loads(line.removeprefix(marker))


@pytest.mark.skipif(
    _FRAME_BINARY is None,
    reason="No FreeCADCmd binary available to place a component.",
)
def test_a_trace_pose_measures_exactly_what_the_live_pose_did(tmp_path) -> None:
    """The agreement check this producer is only worth having if it passes.

    A trace frame is the numbers the solver left behind; re-posing a
    component from it has to put the part back where the solver had it, or
    the whole measurement is a number about a mechanism that never existed.
    """

    report = _drive(_TRACE_CLEARANCE_DRIVER, "TRACE-CLEARANCE ", tmp_path)

    live = report["live"]
    swept = report["swept"]
    assert live, "the live sweep found nothing to agree about"

    # Frame for frame, the same worst approach.
    worst_live = min(row["distance_mm"] for row in live)
    assert swept["closest_approach"]["distance_mm"] == worst_live
    assert sorted(swept["closest_approach"]["components"]) == ["swing", "tower"]
    live_frames = sorted({row["frame_index"] for row in live})
    assert swept["closest_approach"]["frame_index"] in live_frames
    assert swept["frames_checked"] == swept["frames_available"] == 37
    assert swept["held"] is False
    assert swept["query_cap_reached"] is False
    assert swept["pose"].startswith("every trace frame")

    # The arm really is measured where the trace put it: this is the
    # ADR-242 mechanism, whose pre-fix reading was 33 mm of clear air.
    assert worst_live == 0.0, live

    # ...and the poses are put back, because a check is not allowed to move
    # the assembly it measured.
    assert report["restored"] == report["resting"]

    # No pairs, no promise, and no cost: the empty summary is what keeps a
    # trace that declared nothing free of a clearance block.
    assert report["no_pairs"] == {}
