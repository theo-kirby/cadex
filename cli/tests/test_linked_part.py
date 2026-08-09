# SPDX-License-Identifier: LGPL-2.1-or-later

"""``cadex link``: a part from another project, and refreshing it (ADR-138).

Two real projects, two real engine runs, one process interface — because the
thing a pipeline branches on is the exit status and the envelope, not the
functions behind them. The engine-needing tests skip without a built engine;
the tool-surface one does not, because it reads ``OP_ARG_SPECS`` off the
source tree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadex_cli.__main__ import main
from cadex_cli.report import EXIT_OK, EXIT_REJECTED, EXIT_USAGE

SENSOR = """
p = params(bore=num(6.0, unit="mm", min=2.0, max=14.0, step=0.5))
block = part.box(40.0, 25.0, 15.0)
bore = part.cylinder(p.bore / 2.0, 25.0, origin=[20.0, 12.5, -5.0])
sensor = part.cut(block, bore)
result = {"sensor": sensor}
"""

CONSUMER = """
sensor = part.import_part("sensor.cxpart")
plate = part.box(80.0, 60.0, 10.0)
mount = part.cut(plate, part.transform(sensor, translation=[10.0, 10.0, 4.0]))
result = {"sensor": sensor, "mount": mount}
"""


def _run(capsys, *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def source_project(engine, tmp_path, capsys):
    """A second project with one accepted solid to pull from."""

    script = tmp_path / "sensor.py"
    script.write_text(SENSOR, encoding="utf-8")
    root = tmp_path / "sensorA"
    code, _ = _run(capsys, "script", "--set", str(script), "--project", str(root))
    assert code == EXIT_OK
    return root


def test_link_brings_a_part_in_and_refresh_is_the_same_command(
    source_project, tmp_path, capsys
) -> None:
    consumer = tmp_path / "consumer"

    code, envelope = _run(
        capsys,
        "link",
        "--from",
        str(source_project),
        "--output",
        "sensor",
        "--project",
        str(consumer),
    )
    assert code == EXIT_OK, envelope
    assert (consumer / "assets" / "sensor.cxpart").is_file()
    assert any("sensor.cxpart" in note for note in envelope["notes"]), envelope

    # Build on it.
    script = tmp_path / "consumer.py"
    script.write_text(CONSUMER, encoding="utf-8")
    code, built = _run(
        capsys, "script", "--set", str(script), "--project", str(consumer)
    )
    assert code == EXIT_OK, built
    first_digest = built["digest"]

    # Running link again with nothing moved rebuilds nothing: a no-op that
    # re-accepted the model would put a meaningless revision in the history
    # every time somebody checked.
    code, again = _run(
        capsys,
        "link",
        "--from",
        str(source_project),
        "--output",
        "sensor",
        "--project",
        str(consumer),
    )
    assert code == EXIT_OK, again
    assert any("nothing moved" in note for note in again["notes"]), again
    assert again["digest"] in ("", first_digest), again

    # Move the source project, then refresh — which is the same command.
    code, moved = _run(
        capsys, "params", "--set", "bore=12", "--project", str(source_project)
    )
    assert code == EXIT_OK, moved

    code, refreshed = _run(
        capsys,
        "link",
        "--from",
        str(source_project),
        "--output",
        "sensor",
        "--project",
        str(consumer),
    )
    assert code == EXIT_OK, refreshed
    assert any("moved from" in note for note in refreshed["notes"]), refreshed
    assert refreshed["digest"] != first_digest, refreshed


def test_link_without_an_output_is_told_what_the_project_declares(
    source_project, tmp_path, capsys
) -> None:
    code, envelope = _run(
        capsys,
        "link",
        "--from",
        str(source_project),
        "--project",
        str(tmp_path / "consumer"),
    )
    assert code == EXIT_REJECTED, envelope
    assert any("declares: sensor" in note for note in envelope["notes"]), envelope


def test_link_without_a_source_is_a_usage_error(tmp_path, capsys) -> None:
    code, envelope = _run(capsys, "link", "--project", str(tmp_path / "consumer"))
    assert code == EXIT_USAGE, envelope
    assert "--from" in envelope["error"], envelope


def test_the_model_can_reach_a_part_in_another_project(protocol) -> None:
    """The tool surface is generated, but the op list is chosen.

    A turn told "use the sensor from ../sensorA" cannot do it unless
    ``link_part`` is offered: nothing else in the surface reaches outside
    this project.
    """

    from cadex_cli.tools import tool_definitions

    by_name = {item["name"]: item for item in tool_definitions(protocol)}
    assert "link_part" in by_name, sorted(by_name)
    schema = by_name["link_part"]["input_schema"]
    assert schema["required"] == ["source_project"], schema
    assert set(schema["properties"]) == {"source_project", "output", "name"}, schema
    assert "part.import_part" in by_name["link_part"]["description"]
