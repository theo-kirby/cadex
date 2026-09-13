# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""The review dashboard's design spec, and the ot6 evidence caps (ADR-328).

``docs/REVIEW-DESIGN.md`` is the contract the page is held to. This suite
pins what can be pinned without a browser: the spec has its required
sections, its page-background token is the environment module's dark scene
background (one palette across chrome and viewport), its "before"
measurements agree with the committed receipt, and every ot6 receipt
respects the charter's caps — 16 KB per receipt, 200 KB per image — with no
private address or this machine's hostname in any of them.
"""
from __future__ import annotations

from pathlib import Path
import re
import socket
import struct
import json

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "docs" / "REVIEW-DESIGN.md"
STATIC = REPO / "cli" / "cadex_cli" / "review_static"
EVIDENCE_DIRS = (REPO / "docs" / "probes" / "ot6", REPO / "docs" / "review-design")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
RECEIPT_CAP = 16 * 1024
IMAGE_CAP = 200 * 1024
PRIVATE_ADDRESS = re.compile(r"\b(?:10|100|172|192)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SECTIONS = ("## 1. Purpose", "## 2. Hierarchy", "## 3. Type scale", "## 4. Palette",
            "## 5. Spacing and shape", "## 6. Breakpoints")
TOKENS = ("--bg", "--surface", "--surface-2", "--surface-3", "--rule", "--rule-strong",
          "--ink", "--ink-2", "--accent", "--ok", "--warn", "--bad", "--info")


def evidence_files():
    return sorted(path for root in EVIDENCE_DIRS if root.exists()
                  for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)


def spec_tokens() -> dict[str, str]:
    """The palette table's ``token -> hex`` pairs."""

    found = dict(re.findall(r"^\| `(--[a-z0-9-]+)` \| `(#[0-9a-f]{6})` \|", SPEC.read_text(), re.M))
    assert set(found) == set(TOKENS), sorted(set(found) ^ set(TOKENS))
    return found


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", path
    return struct.unpack(">II", head[16:24])


def test_spec_has_every_required_section_and_a_verified_date():
    text = SPEC.read_text()
    assert re.search(r"^Verified against source: \d{4}-\d{2}-\d{2}\.", text, re.M)
    for section in SECTIONS:
        assert section in text, section


def test_page_background_is_the_environment_dark_scene_background():
    """One palette across chrome and viewport: ``--bg`` is the dark mat's ``scene.bg``."""

    environment = (STATIC / "environment.js").read_text()
    dark = re.search(r"dark:\s*\{.*?scene:\s*\{\s*bg:\s*0x([0-9a-f]{6})", environment, re.S)
    assert dark, "environment.js no longer declares a dark scene background"
    assert spec_tokens()["--bg"] == "#" + dark.group(1)


def test_every_palette_token_is_distinct_and_dark_chrome_is_darker_than_ink():
    tokens = spec_tokens()
    assert len(set(tokens.values())) == len(tokens)
    def luminance(value: str) -> float:
        return sum(int(value[i:i + 2], 16) for i in (1, 3, 5)) / 3
    for surface in ("--bg", "--surface", "--surface-2", "--surface-3", "--rule"):
        assert luminance(tokens[surface]) < luminance(tokens["--ink-2"]) < luminance(tokens["--ink"])


def test_before_receipt_records_the_page_the_spec_describes():
    receipt = json.loads((REPO / "docs/probes/ot6/design/before.json").read_text())
    shots = receipt["shots"]
    desk, phone, narrow = shots["1400"], shots["400x850"], shots["400-desktop"]
    # The operator URL served the active project with a run selected, live.
    for shot in (desk, phone):
        assert shot["project"].endswith(" — review") and shot["view"].startswith("RUN ")
        assert shot["freshness"] == "live" and shot["model"] == "loaded"
    assert desk["innerWidth"] == 1400 and desk["horizontal_overflow_px"] == 0
    # The sliver: the layout viewport widened past the phone, and the canvas collapsed.
    assert phone["innerWidth"] > 400 and phone["canvas"]["width"] < 50
    assert narrow["innerWidth"] == 400 and narrow["horizontal_overflow_px"] > 0
    text = SPEC.read_text()
    for number in (phone["innerWidth"], phone["canvas"]["width"], narrow["horizontal_overflow_px"],
                   desk["canvas"]["width"]):
        assert f"{number}" in text, f"spec §7 no longer cites {number}"


def test_before_screenshots_are_the_two_charter_sizes():
    assert png_size(REPO / "docs/review-design/before-1400.png") == (1400, 900)
    assert png_size(REPO / "docs/review-design/before-400x850.png") == (400, 850)


@pytest.mark.parametrize("path", evidence_files(), ids=lambda p: str(p.relative_to(REPO)))
def test_ot6_evidence_respects_the_charter_caps_and_names_no_private_address(path):
    size = path.stat().st_size
    if path.suffix.lower() in IMAGE_SUFFIXES:
        assert size <= IMAGE_CAP, f"{size} bytes > {IMAGE_CAP}"
        return
    assert size <= RECEIPT_CAP, f"{size} bytes > {RECEIPT_CAP}"
    text = path.read_text(errors="replace")
    assert not PRIVATE_ADDRESS.search(text), "a private-network address is committed"
    assert socket.gethostname() not in text, "this machine's hostname is committed"


def test_the_spec_itself_names_no_private_address():
    text = SPEC.read_text()
    assert not PRIVATE_ADDRESS.search(text)
    assert socket.gethostname() not in text
