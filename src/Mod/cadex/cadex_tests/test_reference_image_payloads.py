# SPDX-License-Identifier: LGPL-2.1-or-later

"""Proof that attached reference images reach every provider payload.

The GUI attach/paste paths both land in the project references directory and
are re-sent every turn via ``_context_image_blocks``. These tests pin the
provider-facing encodings: Anthropic base64 ``image`` blocks, OpenAI
``input_image`` data URLs, and the Codex inline-JPEG budget — plus the
explicit ``R_MISS`` delivery notes when a file disappears.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

import CadexProvider as provider

# A valid 1x1 PNG.
PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png_path(tmp_path: Path) -> Path:
    path = tmp_path / "target.png"
    path.write_bytes(base64.b64decode(PNG_1X1_BASE64))
    return path


def _context_with_reference(path: Path | str) -> dict:
    return {
        "reference_images": {
            "count": 1,
            "images": [
                {"id": "ref_1", "name": "target.png", "path": str(path)}
            ],
        }
    }


def test_anthropic_content_carries_labeled_base64_image(png_path: Path) -> None:
    content = provider._anthropic_user_content(
        "build this", _context_with_reference(png_path)
    )
    assert isinstance(content, list)
    assert content[0] == {"type": "text", "text": "build this"}
    labels = [
        str(item.get("text"))
        for item in content
        if item.get("type") == "text"
    ]
    assert any(label.startswith("R1/1:target.png") for label in labels)
    images = [item for item in content if item.get("type") == "image"]
    assert len(images) == 1
    source = images[0]["source"]
    assert source["type"] == "base64"
    assert source["media_type"] == "image/png"
    assert source["data"]
    assert base64.b64decode(source["data"]) == base64.b64decode(PNG_1X1_BASE64)


def test_anthropic_missing_file_yields_note_and_no_image(tmp_path: Path) -> None:
    context = _context_with_reference(tmp_path / "gone.png")
    content = provider._anthropic_user_content("build this", context)
    assert isinstance(content, list)
    assert not [item for item in content if item.get("type") == "image"]
    notes = [
        str(item.get("text"))
        for item in content
        if item.get("type") == "text" and str(item.get("text")).startswith("R_MISS:")
    ]
    assert notes and notes[0].startswith("R_MISS:target.png|")


def test_delivery_notes_report_missing_files(tmp_path: Path) -> None:
    context = _context_with_reference(tmp_path / "gone.png")
    assert provider._context_image_blocks(context) == []
    notes = provider._context_image_delivery_notes(context)
    assert len(notes) == 1
    assert notes[0].startswith("R_MISS:target.png|")


def test_openai_message_carries_input_image_data_url(png_path: Path) -> None:
    message = provider._openai_user_input_message(
        "build this", _context_with_reference(png_path)
    )
    assert message["role"] == "user"
    content = message["content"]
    assert content[0] == {"type": "input_text", "text": "build this"}
    labels = [
        str(item.get("text"))
        for item in content
        if item.get("type") == "input_text"
    ]
    assert any(label.startswith("R1/1:target.png") for label in labels)
    images = [item for item in content if item.get("type") == "input_image"]
    assert len(images) == 1
    assert images[0]["image_url"].startswith("data:image/png;base64,")
    assert images[0]["detail"] == "high"


def test_openai_message_reports_missing_file(tmp_path: Path) -> None:
    message = provider._openai_user_input_message(
        "build this", _context_with_reference(tmp_path / "gone.png")
    )
    content = message["content"]
    assert not [item for item in content if item.get("type") == "input_image"]
    assert any(
        str(item.get("text")).startswith("R_MISS:target.png|")
        for item in content
        if item.get("type") == "input_text"
    )


def test_codex_turn_input_carries_data_url(png_path: Path) -> None:
    items = provider._codex_turn_input(
        "build this", _context_with_reference(png_path)
    )
    assert items[0] == {"type": "text", "text": "build this"}
    images = [item for item in items if item.get("type") == "image"]
    assert len(images) == 1
    assert images[0]["url"].startswith("data:image/png;base64,")


def test_codex_builder_enforces_inline_image_budget(monkeypatch) -> None:
    captured: dict = {}

    def fake_blocks(context, *, max_bytes=None, prefer_jpeg=False):
        captured["max_bytes"] = max_bytes
        captured["prefer_jpeg"] = prefer_jpeg
        return []

    monkeypatch.setattr(provider, "_context_image_blocks", fake_blocks)
    assert provider._codex_context_image_blocks({}) == []
    assert captured == {
        "max_bytes": provider.CODEX_INLINE_IMAGE_MAX_BYTES,
        "prefer_jpeg": True,
    }
