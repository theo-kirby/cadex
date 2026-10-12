# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""One product version, everywhere it is stated (ADR-673).

``VERSION`` is the source. ``package/bump_version.sh`` writes the rest;
this fails the moment a copy is edited by hand or left behind.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from cadex_cli import __version__, mcp

REPO = Path(__file__).resolve().parents[2]
VERSION = (REPO / "VERSION").read_text(encoding="utf-8").strip()


def test_version_is_a_plain_semver() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION), VERSION


def test_the_cli_and_the_mcp_server_report_the_version() -> None:
    assert __version__ == VERSION
    assert mcp.SERVER_VERSION == VERSION
    shown = subprocess.run([sys.executable, "-m", "cadex_cli", "--version"],
                           capture_output=True, text=True, check=True,
                           cwd=REPO / "cli").stdout.strip()
    assert shown == f"cadex {VERSION}"


def test_cmake_and_the_pixi_manifests_carry_the_version() -> None:
    data = json.loads((REPO / "version.json").read_text(encoding="utf-8"))
    assert f"{data['version_major']}.{data['version_minor']}.{data['version_patch']}" == VERSION
    manifest = (REPO / "pixi.toml").read_text(encoding="utf-8")
    assert re.search(rf'^version = "{re.escape(VERSION)}"$', manifest, re.M)


def test_the_payload_is_named_from_version() -> None:
    script = (REPO / "package/engine/build_engine_payload.sh").read_text(encoding="utf-8")
    assert '< "${repo}/VERSION"' in script
