# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Engine contract tests for the scripted (xscript/xscript) surfaces.

The build123d and OpenSCAD engines were removed, so this file now only carries
the engine-agnostic contracts that survived that teardown: stage-aware GUI
failure rendering, the private scripted-carrier / view-attachment service
contracts, and the XScript default-preference locks.
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




class _UnsetPreferences:
    """Stub ParamGet group where every key is unset: each getter echoes the
    fallback default it was called with, exactly like FreeCAD does for keys
    that were never written."""

    def GetBool(self, name: str, default: bool = False) -> bool:
        return default

    def GetString(self, name: str, default: str = "") -> str:
        return default

    def GetFloat(self, name: str, default: float = 0.0) -> float:
        return default

    def GetInt(self, name: str, default: int = 0) -> int:
        return default


class _RecordingPreferences(_UnsetPreferences):
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def GetBool(self, name: str, default: bool = False) -> bool:
        return bool(self.values.get(name, default))

    def GetString(self, name: str, default: str = "") -> str:
        return str(self.values.get(name, default))

    def GetFloat(self, name: str, default: float = 0.0) -> float:
        return float(self.values.get(name, default))

    def GetInt(self, name: str, default: int = 0) -> int:
        return int(self.values.get(name, default))

    def SetBool(self, name: str, value: bool) -> None:
        self.values[name] = bool(value)

    def SetString(self, name: str, value: str) -> None:
        self.values[name] = str(value)

    def SetFloat(self, name: str, value: float) -> None:
        self.values[name] = float(value)

    def SetInt(self, name: str, value: int) -> None:
        self.values[name] = int(value)

    def RemBool(self, name: str) -> None:
        self.values.pop(name, None)

    def RemString(self, name: str) -> None:
        self.values.pop(name, None)

    def RemFloat(self, name: str) -> None:
        self.values.pop(name, None)

    def RemInt(self, name: str) -> None:
        self.values.pop(name, None)


class TestEngineSettingDefaults:
    """The engine's own settings, split out of the Qt preferences (ADR-021).

    Phase 6 asserted an "XScript enabled" opt-in here. xscript is now the
    only engine there is, so the defaults that still mean something are the
    sandbox budgets a worker run is given.
    """

    def test_budget_defaults_are_positive(self) -> None:
        from CadexEngineSettings import (
            DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
            DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
        )

        assert DEFAULT_SCRIPTED_TIMEOUT_SECONDS > 0
        assert DEFAULT_SCRIPTED_MEMORY_LIMIT_MB > 0

    def test_unset_preferences_fall_back_to_the_defaults(self, monkeypatch) -> None:
        import CadexEngineSettings as settings

        class _Unset:
            @staticmethod
            def GetFloat(_name, default):
                return default

            @staticmethod
            def GetInt(_name, default):
                return default

        monkeypatch.setattr(settings, "preferences", lambda: _Unset())
        assert settings.load_engine_budgets() == {
            "timeout_seconds": settings.DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
            "memory_limit_mb": settings.DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
        }

    def test_a_nonsense_preference_value_falls_back(self, monkeypatch) -> None:
        """A zero or negative budget is not a budget."""
        import CadexEngineSettings as settings

        class _Nonsense:
            @staticmethod
            def GetFloat(_name, _default):
                return -1.0

            @staticmethod
            def GetInt(_name, _default):
                return 0

        monkeypatch.setattr(settings, "preferences", lambda: _Nonsense())
        assert settings.load_engine_budgets() == {
            "timeout_seconds": settings.DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
            "memory_limit_mb": settings.DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
        }

    def test_caller_budgets_win_when_complete(self) -> None:
        from CadexEngineSettings import resolve_budgets

        assert resolve_budgets(
            {"timeout_seconds": 12.0, "memory_limit_mb": 256}
        ) == {"timeout_seconds": 12.0, "memory_limit_mb": 256}


