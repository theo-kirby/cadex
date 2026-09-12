# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The committed second-fresh-project lifecycle receipt stays consistent
with its claims.

``docs/probes/wren-fresh/lifecycle.py`` reopens a run-less agent-authored
project copy through two fresh engine processes, inspects the original on the persistent
operator server over the private-network address, and proves the earlier
Reed projects unchanged by hash inventory. ``evidence.json`` is that receipt
for ``ot5-wren``, committed without its images. The project lives outside
this checkout, so these tests hold the receipt to itself and to the documents
that cite it: an accepted revision with no runs is the current view, every
declared parameter reached the page, the model was drawn and orbited, the
poll kept the empty run state, and the previous projects were intact.
Nothing here needs a browser, an engine or the project.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT

PROBE = REPO_ROOT / "docs" / "probes" / "wren-fresh"


@pytest.fixture(scope="module")
def receipt() -> dict:
    return json.loads((PROBE / "evidence.json").read_text())


def test_receipt_names_a_fresh_accepted_project_with_no_runs(receipt):
    assert receipt["project"] == "ot5-wren"
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["accepted_revision"])
    assert re.fullmatch(r"[0-9a-f]{64}", receipt["accepted_digest"])
    assert receipt["api_runs"] == 0
    state = receipt["page_state"]
    assert state["selected"] == "accepted" and state["runs"] == []
    assert not state["stale"] and state["error"] is None


def test_every_declared_parameter_reached_the_page(receipt):
    values = receipt["param_values"]
    assert receipt["params_shown"] == len(values) >= 12
    for name in ("torso_w", "thigh_len", "shin_len", "foot_len", "policy_on", "printed_density"):
        assert name in values, name
    assert values["policy_on"] == 0


def test_the_model_was_drawn_and_orbited_over_the_private_address(receipt):
    assert receipt["url_host"].endswith(":8765") and not receipt["url_host"].startswith("127.")
    model = receipt["model"]
    assert model["components"] == 8 and model["triangles"] > 0 and model["drawn_pixels"] > 1000
    assert model["style"] == "cadex-prototype-light-v1"
    orbit = receipt["orbit"]
    assert orbit["after_drag"]["yaw"] != orbit["default"]["yaw"]
    assert orbit["after_drag"]["distance"] == orbit["default"]["distance"]
    assert orbit["after_zoom"]["distance"] < orbit["after_drag"]["distance"]
    assert orbit["drawn_pixels"] > 1000
    assert receipt["private_address_same_machine"] is True
    assert set(receipt["screenshots"]) == {"persistent-accepted.png", "persistent-page.png"}


def test_two_engine_reopens_restored_the_accepted_revision(receipt):
    assert receipt["engine_reopen_scope"] == "disposable full copy; served project byte-checked"
    opens = receipt["engine_opens"]
    assert len(opens) == 2 and opens[0]["pid"] != opens[1]["pid"]
    assert all(item["matches_accepted"] is True for item in opens)
    assert receipt["retained_files"] > 0


def test_the_earlier_reed_projects_were_intact(receipt):
    intact = receipt["intact"]
    assert set(intact) >= {"ot5-biped", "ot5-biped-copy29"}
    assert all(item["unchanged"] is True and item["files"] > 0 for item in intact.values())


def test_documents_cite_the_receipt(receipt):
    readme = (PROBE / "README.md").read_text()
    operator = (REPO_ROOT / "docs" / "probes" / "operator-review" / "README.md").read_text()
    review = (REPO_ROOT / "docs" / "HEADLESS-BIPED-REVIEW.md").read_text()
    short = receipt["accepted_revision"][:12]
    assert short in readme and "ot5-wren" in readme
    assert "ot5-wren" in operator and short in operator
    assert "ot5-wren" in review and short in review


def test_inventory_excludes_only_invocation_outputs(tmp_path):
    # Load the helper without executing the real-project command-line probe.
    import ast
    import hashlib

    tree = ast.parse((PROBE / 'lifecycle.py').read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'inventory')
    namespace = {'hashlib': hashlib}
    exec(compile(ast.Module(body=[helper], type_ignores=[]), '<inventory>', 'exec'), namespace)
    inventory = namespace['inventory']
    current = tmp_path / 'evidence' / 'current'
    previous = tmp_path / 'evidence' / 'previous'
    current.mkdir(parents=True)
    previous.mkdir()
    (previous / 'retained.png').write_bytes(b'old evidence')
    (tmp_path / 'script.py').write_text('accepted source')
    before = inventory(tmp_path, exclude=current)
    (current / 'screenshot.png').write_bytes(b'new output')
    assert inventory(tmp_path, exclude=current) == before
    (previous / 'retained.png').write_bytes(b'changed evidence')
    assert inventory(tmp_path, exclude=current) != before
    assert 'script.py' in before and 'evidence/previous/retained.png' in before
