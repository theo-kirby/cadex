# SPDX-License-Identifier: LGPL-2.1-or-later

"""A part built in one project, used in another, and refreshed (ADR-138).

**This test is the feature.** ADR-134 shipped unusable with all 52 of its
unit tests green, because not one of them went through
``store_project_asset`` — and ADR-135 is the entry that records why. So this
file drives two real cadexd children over the wire: project A builds a sensor
and accepts it, project B pulls it with ``link_part``, imports it with
``part.import_part``, cuts a plate with it and hangs an assembly component on
it; then A changes, B refreshes, and B's geometry and digest follow.

Two things it proves that no unit test can:

- the imported solid is **the same solid**, to floating-point equality of
  volume and to the face count — not a tessellation of it, which is what the
  STL route lands;
- B still **opens** after a refresh. A refresh moves B's digest by design,
  and a digest-moving change that a project cannot restore from would lock it
  out at open (`simple-willow-8989`). Refresh goes through the ordinary
  rebuild path precisely so it cannot, and this is where that is checked
  rather than assumed.

The client, the spawn and the response validation are
``test_cadexd_lifecycle``'s, deliberately: every frame here is checked
against the engine under test's own ``OP_RESPONSE_SPECS``, so this file also
gates ``link_part``'s reply shape against a packaged payload when
``CADEX_ENGINE_ROOT`` is set.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

import pytest

from test_cadexd_lifecycle import FREECADCMD, _spawn_cadexd, _stop

#: Project A: one parametric sensor body. The bore is what moves later, and
#: it moves the volume by an amount no floating-point noise reaches.
SENSOR_SCRIPT = """
p = params(bore=num(6, unit="mm", min=2, max=14, step=0.5))
block = part.box(40, 25, 15)
bore = part.cylinder(p.bore / 2.0, 25, origin=[20, 12.5, -5])
sensor = part.cut(block, bore)
result = {"sensor": sensor}
"""

#: Project B: the same part, in another project, doing every job a part does.
#: ``part.cut`` proves the BREP is a real solid the kernel will boolean;
#: ``assembly.component`` proves a linked part is a component with no change
#: to the assembly domain at all, which is ADR-138's "free by construction".
CONSUMER_SCRIPT = """
sensor = part.import_part("sensor.cxpart")
plate = part.box(80, 60, 10)
mount = part.cut(plate, part.transform(sensor, translation=[10, 10, 4]))
body = assembly.component(sensor, grounded=True)
asm = assembly.assembly([body])
diag = assembly.solve(asm)
result = {"sensor": sensor, "plate": plate, "mount": mount,
          "body": body, "asm": asm, "diag": diag}
"""


def _facts(client, output: str) -> dict:
    reply = client.request(
        "inspect", {"scope": "output", "target": output, "path": "/facts"}
    )
    assert reply["ok"] is True, reply
    return dict(reply["value"])


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the linked-part CI."
)
def test_a_linked_part_travels_between_two_projects_and_refreshes() -> None:
    source_root = Path(tempfile.mkdtemp(prefix="cadex-link-source-"))
    consumer_root = Path(tempfile.mkdtemp(prefix="cadex-link-consumer-"))
    source = consumer = reopened = None
    try:
        # -- project A: build the sensor and accept it --------------------
        source = _spawn_cadexd()
        opened = source.request("open_project", {"project_root": str(source_root)})
        assert opened["ok"] is True, opened
        built = source.request(
            "write_script", {"source": SENSOR_SCRIPT, "expected_revision": ""}
        )
        assert built["ok"] is True, built
        first_revision = built["accepted_revision"]
        sensor_facts = _facts(source, "sensor")
        assert sensor_facts["shape_type"] == "Solid", sensor_facts

        # -- project B: pull it ------------------------------------------
        consumer = _spawn_cadexd()
        opened_b = consumer.request(
            "open_project", {"project_root": str(consumer_root)}
        )
        assert opened_b["ok"] is True, opened_b

        # Omitting the output is how a caller asks what is on offer.
        offered = consumer.request("link_part", {"source_project": str(source_root)})
        assert offered["ok"] is False, offered
        assert offered["failure_code"] == "LINKED_PART_REJECTED", offered
        assert offered["candidates"] == ["sensor"], offered

        linked = consumer.request(
            "link_part", {"source_project": str(source_root), "output": "sensor"}
        )
        assert linked["ok"] is True, linked
        assert linked["name"] == "sensor.cxpart"
        assert linked["source_revision"] == first_revision, linked
        assert linked["previous_revision"] == "", linked
        assert linked["changed"] is True, linked
        assert (consumer_root / "assets" / "sensor.cxpart").is_file()
        assert [item["name"] for item in linked["assets"]] == ["sensor.cxpart"]

        # The same call again, with nothing moved: the container is
        # byte-identical, so refresh reports honestly rather than guessing.
        unchanged = consumer.request(
            "link_part", {"source_project": str(source_root), "output": "sensor"}
        )
        assert unchanged["ok"] is True, unchanged
        assert unchanged["changed"] is False, unchanged
        assert unchanged["previous_revision"] == first_revision, unchanged
        assert unchanged["sha256"] == linked["sha256"], unchanged

        # -- project B: build on it --------------------------------------
        consumed = consumer.request(
            "write_script", {"source": CONSUMER_SCRIPT, "expected_revision": ""}
        )
        assert consumed["ok"] is True, consumed
        consumer_digest = consumed["digest"]

        imported_facts = _facts(consumer, "sensor")
        # It is the same solid, not a picture of one. A shape_from_mesh
        # import of the same part would agree on neither line: its volume is
        # the tessellation's, and its face count is in the thousands.
        assert imported_facts["shape_type"] == "Solid", imported_facts
        assert imported_facts["volume_mm3"] == pytest.approx(
            sensor_facts["volume_mm3"], rel=1e-12
        ), (imported_facts, sensor_facts)
        assert imported_facts["faces"] == sensor_facts["faces"], (
            imported_facts,
            sensor_facts,
        )
        assert imported_facts["faces"] < 100, imported_facts

        # ...and the kernel will boolean against it, which is the whole
        # reason not to ship triangles.
        mount_facts = _facts(consumer, "mount")
        plate_facts = _facts(consumer, "plate")
        assert 0.0 < mount_facts["volume_mm3"] < plate_facts["volume_mm3"], (
            mount_facts,
            plate_facts,
        )

        # -- project A: change the sensor --------------------------------
        moved = source.request(
            "set_params",
            {
                "values": {"bore": 12},
                "expected_revision": built["model_state"][
                    "next_write_expected_revision"
                ],
            },
        )
        assert moved["ok"] is True, moved
        second_revision = moved["accepted_revision"]
        assert second_revision != first_revision, moved
        moved_facts = _facts(source, "sensor")
        assert moved_facts["volume_mm3"] < sensor_facts["volume_mm3"], moved_facts

        # -- project B: refresh, which is the same call again -------------
        refreshed = consumer.request(
            "link_part", {"source_project": str(source_root), "output": "sensor"}
        )
        assert refreshed["ok"] is True, refreshed
        assert refreshed["changed"] is True, refreshed
        assert refreshed["previous_revision"] == first_revision, refreshed
        assert refreshed["source_revision"] == second_revision, refreshed

        # link_part does not rebuild B: the caller issues the ordinary
        # rebuild, so the new geometry lands as one normal accepted revision
        # with one undo step.
        rebuilt = consumer.request("rebuild")
        assert rebuilt["ok"] is True, rebuilt
        assert rebuilt["digest"] != consumer_digest, rebuilt
        refreshed_facts = _facts(consumer, "sensor")
        assert refreshed_facts["volume_mm3"] == pytest.approx(
            moved_facts["volume_mm3"], rel=1e-12
        ), (refreshed_facts, moved_facts)

        # -- and B still opens ------------------------------------------
        # A refresh moves B's digest by design. A digest-moving change a
        # project cannot restore from locks it out at open with no way back
        # in, so this is checked rather than reasoned about.
        _stop(consumer)
        consumer = None
        reopened = _spawn_cadexd()
        again = reopened.request("open_project", {"project_root": str(consumer_root)})
        assert again["ok"] is True, again
        assert again["restore"]["performed"] is True, again
        assert again["restore"]["matches_accepted"] is True, again
        assert again["script"]["accepted"]["digest"] == rebuilt["digest"], again
    finally:
        for client in (source, consumer, reopened):
            _stop(client)
        shutil.rmtree(source_root, ignore_errors=True)
        shutil.rmtree(consumer_root, ignore_errors=True)


@pytest.mark.skipif(
    FREECADCMD is None, reason="No FreeCADCmd binary available for the linked-part CI."
)
def test_link_part_refuses_by_name() -> None:
    """Every refusal names the thing that is wrong, against a real engine."""

    source_root = Path(tempfile.mkdtemp(prefix="cadex-link-source-"))
    consumer_root = Path(tempfile.mkdtemp(prefix="cadex-link-consumer-"))
    source = consumer = None
    try:
        consumer = _spawn_cadexd()
        assert consumer.request(
            "open_project", {"project_root": str(consumer_root)}
        )["ok"] is True

        # A project that has never been opened has nothing to give.
        empty = consumer.request(
            "link_part", {"source_project": str(source_root), "output": "sensor"}
        )
        assert empty["ok"] is False, empty
        assert "no accepted revision" in empty["error"], empty

        source = _spawn_cadexd()
        assert source.request(
            "open_project", {"project_root": str(source_root)}
        )["ok"] is True
        assert source.request(
            "write_script", {"source": SENSOR_SCRIPT, "expected_revision": ""}
        )["ok"] is True

        unknown = consumer.request(
            "link_part", {"source_project": str(source_root), "output": "housing"}
        )
        assert unknown["ok"] is False, unknown
        assert "is not an output of" in unknown["error"], unknown
        assert unknown["candidates"] == ["sensor"], unknown

        itself = consumer.request(
            "link_part", {"source_project": str(consumer_root), "output": "sensor"}
        )
        assert itself["ok"] is False, itself
        assert itself["error"] == "A project cannot link a part from itself.", itself

        missing = consumer.request(
            "link_part",
            {"source_project": str(consumer_root / "nowhere"), "output": "sensor"},
        )
        assert missing["ok"] is False, missing
        assert "is not a project directory" in missing["error"], missing

        # ...and a script naming a container that is not there refuses in the
        # worker, with the fix in the message.
        absent = consumer.request(
            "write_script",
            {
                "source": 'result = {"x": part.import_part("nope.cxpart")}',
                "expected_revision": "",
            },
        )
        assert absent["ok"] is False, absent
        assert "no staged part asset named 'nope.cxpart'" in absent["error"], absent
    finally:
        for client in (source, consumer):
            _stop(client)
        shutil.rmtree(source_root, ignore_errors=True)
        shutil.rmtree(consumer_root, ignore_errors=True)
