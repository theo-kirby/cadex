# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The envelope names a policy the open found stale (ADR-520)."""

from __future__ import annotations

from cadex_cli.__main__ import stale_policy_note


def test_a_stale_policy_open_gets_a_note():
    opened = {"restore": {"performed": False, "stale_policy": {
        "output": "policy", "reason": "policy_task_mismatch"}}}
    note = stale_policy_note(opened)
    assert "'policy'" in note and "policy_task_mismatch" in note
    assert "ADR-520" in note and "Retrain" in note


def test_an_ordinary_open_gets_none():
    assert stale_policy_note({"restore": {"performed": True, "digest": "d",
                                          "matches_accepted": True}}) == ""
    assert stale_policy_note({"restore": {"performed": False}}) == ""
    assert stale_policy_note({}) == ""
