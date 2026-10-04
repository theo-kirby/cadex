# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine contract tests for the scripted (xscript/xscript) surfaces.

The build123d and OpenSCAD engines were removed, so this file now only carries
the engine-agnostic contracts that survived that teardown: stage-aware GUI
failure rendering, the private scripted-carrier / view-attachment service
contracts, and the engine's sandbox-budget defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# GUI transcript: stage-aware failure rendering
# ---------------------------------------------------------------------------


class TestFailureEnvelopeContract:
    """The stage vocabulary and the ``tool_failure`` envelope, unrendered.

    Phase 6 asserted this through ``CadexGui._format_progress_event``: eight
    tests that a transcript line said "rejected before execution" or
    "executed and rolled back" for each stage. The renderer was Qt and dies
    with it (ADR-021), but the contract it rendered is engine-side and
    load-bearing — the Blender shell's ``_failure_report`` reads the same
    fields. So the contract is asserted directly instead of through a UI.
    """

    def test_every_declared_stage_is_accepted_by_tool_failure(self) -> None:
        from CadexTools import FAILURE_STAGES, tool_failure

        assert FAILURE_STAGES, "the stage vocabulary must not be empty"
        for stage in sorted(FAILURE_STAGES):
            envelope = tool_failure(
                "xscript.project.write_script", "SOME_CODE", stage,
                "Something went wrong.")
            assert envelope["failure_stage"] == stage
            assert envelope["ok"] is False

    def test_an_undeclared_stage_is_refused(self) -> None:
        from CadexTools import tool_failure

        with pytest.raises(Exception):
            tool_failure("xscript.project.write_script", "CODE",
                         "not_a_stage", "Something went wrong.")

    def test_the_envelope_shape_is_stable(self) -> None:
        """Shell clients parse these keys by name, across a process
        boundary and a repository boundary; they are the contract."""
        from CadexTools import tool_failure

        envelope = tool_failure(
            "xscript.project.set_params", "STALE_PROGRAM_REVISION",
            "precondition", "The revision guard refused the write.",
            requested={"values": {"hole": 3.0}},
            observed={"expected_revision": "abc"})
        assert envelope["ok"] is False
        assert envelope["tool"] == "xscript.project.set_params"
        assert envelope["failure_code"] == "STALE_PROGRAM_REVISION"
        assert envelope["failure_stage"] == "precondition"
        assert envelope["error"] == "The revision guard refused the write."
        assert envelope["requested"] == {"values": {"hole": 3.0}}
        assert envelope["observed"] == {"expected_revision": "abc"}


class TestEngineSettingDefaults:
    """The engine's own settings, split out of the Qt preferences (ADR-021).

    The sandbox budgets a worker run is given: the project's when the CLI
    sends them (ADR-517), else the engine's defaults. No FreeCAD preference
    group sits between them any more (ADR-530).
    """

    def test_budget_defaults_are_positive(self) -> None:
        from CadexEngineSettings import (
            DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
            DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
            default_budgets,
        )

        assert DEFAULT_SCRIPTED_TIMEOUT_SECONDS > 0
        assert DEFAULT_SCRIPTED_MEMORY_LIMIT_MB > 0
        assert default_budgets() == {
            "timeout_seconds": DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
            "memory_limit_mb": DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
        }

    def test_a_nonsense_caller_budget_falls_back(self) -> None:
        """A zero, negative or unparsable budget is not a budget."""
        from CadexEngineSettings import default_budgets, resolve_budgets

        assert resolve_budgets(
            {"timeout_seconds": -1.0, "memory_limit_mb": "lots"}
        ) == default_budgets()

    def test_the_engine_reads_no_preference_group(self) -> None:
        """Nothing writes a FreeCAD preference any more, so nothing reads one
        (ADR-530): the Qt dialog went in Phase 7, the shell in ADR-498."""
        import CadexEngineSettings as settings

        for name in ("preferences", "PREFERENCE_GROUP", "load_engine_budgets"):
            assert not hasattr(settings, name), name
        engine = Path(__file__).resolve().parents[1]
        readers = sorted(
            path.name for path in engine.glob("*.py")
            if "ParamGet" in path.read_text(encoding="utf-8")
        )
        assert readers == []

    def test_caller_budgets_win_when_complete(self) -> None:
        from CadexEngineSettings import resolve_budgets

        assert resolve_budgets(
            {"timeout_seconds": 12.0, "memory_limit_mb": 256}
        ) == {"timeout_seconds": 12.0, "memory_limit_mb": 256}

    def test_caller_budgets_win_per_field(self) -> None:
        """A project that sets one budget keeps the engine's other (ADR-517)."""
        import CadexEngineSettings as settings

        assert settings.resolve_budgets({"timeout_seconds": 900.0}) == {
            "timeout_seconds": 900.0, "memory_limit_mb": 6144}
        assert settings.resolve_budgets({"memory_limit_mb": 8192, "timeout_seconds": 0}) == {
            "timeout_seconds": 300.0, "memory_limit_mb": 8192}
        assert settings.resolve_budgets(None) == {
            "timeout_seconds": 300.0, "memory_limit_mb": 6144}


