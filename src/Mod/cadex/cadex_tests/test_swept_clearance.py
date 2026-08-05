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
import tempfile

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
