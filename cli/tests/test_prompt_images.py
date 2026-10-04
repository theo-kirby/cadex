# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""An image attached to a prompt reaches the turn (ADR-507, orun2 D2 item 1).

``cadex -p PROMPT --image FILE`` checks the file is an image by its bytes,
records its name, type, size and SHA-256 in the envelope, and hands it to
the turn. Since the agent has no file tool, ``claude`` gets it on stdin as
one ``stream-json`` user message, text block then image blocks; a prompt
without images keeps the plain ``-p PROMPT`` argument. The dashboard's half
is in ``test_dashboard_writes.py``.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

import pytest

from cadex_cli import agent
from cadex_cli.__main__ import command_prompt, main
from cadex_cli.report import EXIT_OK, EXIT_USAGE, RunReport

from mock_backend import turn_factory


def png(width: int = 4, height: int = 4, rgb: tuple[int, int, int] = (0, 0, 255)) -> bytes:
    """A real, decodable PNG of one colour."""

    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_an_image_is_known_by_its_bytes_not_its_name() -> None:
    assert agent.image_attachment(png(), "sketch.png").media_type == "image/png"
    assert agent.image_attachment(b"\xff\xd8\xff\xe0" + b"\0" * 16, "a.jpg").media_type == "image/jpeg"
    assert agent.image_attachment(b"GIF89a" + b"\0" * 16, "a.gif").media_type == "image/gif"
    assert agent.image_attachment(b"RIFF\0\0\0\0WEBPVP8 ", "a.webp").media_type == "image/webp"
    # A PNG by name only, an empty file and one over the limit are refused.
    for data, name in ((b"%PDF-1.7", "drawing.png"), (b"", "empty.png"),
                       (b"\x89PNG\r\n\x1a\n" + b"\0" * agent.IMAGE_LIMIT, "huge.png")):
        with pytest.raises(agent.ImageRefused):
            agent.image_attachment(data, name)
    image = agent.image_attachment(png(), "/some/dir/sketch.png")
    assert image.summary() == {"name": "sketch.png", "media_type": "image/png", "bytes": len(png()),
                               "sha256": hashlib.sha256(png()).hexdigest()}
    assert base64.b64decode(image.content_block()["source"]["data"]) == png()


def test_claude_gets_the_images_on_stdin_and_a_plain_prompt_as_an_argument(tmp_path) -> None:
    """A real child process stands where ``claude`` stands and keeps what it was given."""

    received = tmp_path / "received.json"
    fake = tmp_path / "claude"
    fake.write_text(
        "#!%s\nimport json, sys\nargv = sys.argv[1:]\n"
        "stdin = sys.stdin.read() if '--input-format' in argv else None\n"
        "open(%r, 'w').write(json.dumps({'argv': argv, 'stdin': stdin}))\n"
        "print(json.dumps({'type': 'result', 'is_error': False, 'result': 'seen', 'session_id': 's1'}))\n"
        % (sys.executable, str(received)), encoding="utf-8")
    fake.chmod(0o755)
    turn = agent.ClaudeTurn(claude_path=str(fake), model="m", system_prompt_text="s",
                            socket_path=str(tmp_path / "sock"), token="t", cwd=tmp_path)
    try:
        image = agent.image_attachment(png(), "sketch.png")
        result = turn.run("make it like this", [image])
        assert result.ok and result.text == "seen"
        seen = json.loads(received.read_text())
        argv = seen["argv"]
        assert argv[argv.index("-p") + 1] == "--input-format"
        assert argv[argv.index("--input-format") + 1] == "stream-json"
        assert "make it like this" not in argv
        (line,) = seen["stdin"].splitlines()
        message = json.loads(line)
        assert message["type"] == "user" and message["message"]["role"] == "user"
        text, block = message["message"]["content"]
        assert text == {"type": "text", "text": "make it like this"}
        assert block["type"] == "image" and block["source"]["media_type"] == "image/png"
        assert base64.b64decode(block["source"]["data"]) == png()

        assert turn.run("no picture").ok
        seen = json.loads(received.read_text())
        assert seen["stdin"] is None and "--input-format" not in seen["argv"]
        assert seen["argv"][seen["argv"].index("-p") + 1] == "no picture"
    finally:
        turn.cleanup()


def _args(tmp_path: Path, images: list[str]) -> argparse.Namespace:
    return argparse.Namespace(prompt="match the sketch", image=images, project=str(tmp_path / "project"),
                              out="", format="step,stl", engine="", json=False, wait=False, resume=False,
                              model="mock", claude="", command=None)


def test_a_refused_image_stops_the_turn_before_any_engine(tmp_path) -> None:
    (tmp_path / "notes.png").write_text("not an image", encoding="utf-8")
    factory = turn_factory([[("done", "never")]])
    report = RunReport()
    assert command_prompt(_args(tmp_path, [str(tmp_path / "notes.png")]), report,
                          turn_factory=factory) == EXIT_USAGE
    assert "not a PNG, JPEG, GIF or WebP" in report.error and factory.made == []
    report = RunReport()
    assert command_prompt(_args(tmp_path, [str(tmp_path / "absent.png")]), report,
                          turn_factory=factory) == EXIT_USAGE
    assert "cannot read" in report.error
    many = []
    for index in range(agent.IMAGES_PER_TURN + 1):
        many.append(str(tmp_path / f"{index}.png"))
        Path(many[-1]).write_bytes(png())
    report = RunReport()
    assert command_prompt(_args(tmp_path, many), report, turn_factory=factory) == EXIT_USAGE
    assert f"at most {agent.IMAGES_PER_TURN}" in report.error and factory.made == []


def test_image_is_only_for_a_prompt(tmp_path, capsys) -> None:
    (tmp_path / "a.png").write_bytes(png())
    with pytest.raises(SystemExit) as stopped:
        main(["--image", str(tmp_path / "a.png"), "params", "--project", str(tmp_path / "p")])
    assert stopped.value.code == 2
    assert "--image attaches to a prompt" in capsys.readouterr().err


@pytest.mark.usefixtures("engine")
def test_the_turn_receives_the_image_and_the_envelope_records_it(tmp_path) -> None:
    sketch = tmp_path / "sketch.png"
    sketch.write_bytes(png(rgb=(255, 0, 0)))
    plate = 'result = {"plate": part.box(30.0, 20.0, 6.0)}\n'
    factory = turn_factory([[("tool", "write_script", {"source": plate}), ("done", "Built it.")]])
    report = RunReport()
    assert command_prompt(_args(tmp_path, [str(sketch)]), report, turn_factory=factory) == EXIT_OK, report.error
    (turn,) = factory.made
    ((image,),) = turn.images
    assert image.data == sketch.read_bytes() and image.media_type == "image/png"
    assert turn.prompts == ["match the sketch"]
    record = {"name": "sketch.png", "media_type": "image/png", "bytes": sketch.stat().st_size,
              "sha256": hashlib.sha256(sketch.read_bytes()).hexdigest()}
    assert report.to_json()["attachments"] == [record]
