# SPDX-License-Identifier: LGPL-2.1-or-later

"""Experimental-mode preference contract: chat-first is the default, the setting
round-trips through load/save/reset, and the session flag is cached once."""

from __future__ import annotations

import pytest

import CadexPreferences as prefs


class _RecordingPreferences:
    """Stub ParamGet group that records writes and serves stored values,
    echoing the caller's default for unset keys like FreeCAD does."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.removed: list[str] = []

    def _get(self, name: str, default):
        return self.values.get(name, default)

    def _set(self, name: str, value) -> None:
        self.values[name] = value

    def _rem(self, name: str) -> None:
        self.values.pop(name, None)
        self.removed.append(name)

    GetBool = _get
    GetString = _get
    GetFloat = _get
    GetInt = _get
    SetBool = _set
    SetString = _set
    SetFloat = _set
    SetInt = _set
    RemBool = _rem
    RemString = _rem
    RemFloat = _rem
    RemInt = _rem


@pytest.fixture
def stub_prefs(monkeypatch: pytest.MonkeyPatch) -> _RecordingPreferences:
    stub = _RecordingPreferences()
    monkeypatch.setattr(prefs, "preferences", lambda: stub)
    return stub


def test_settings_dataclass_defaults_to_experimental_mode() -> None:
    assert prefs.CadexSettings().experimental_mode is True


def test_load_settings_with_unset_key_defaults_to_experimental_mode(
    stub_prefs: _RecordingPreferences,
) -> None:
    # Existing users have no ExperimentalMode key; everyone lands in experimental mode.
    assert prefs.load_settings().experimental_mode is True


def test_load_settings_reads_persisted_experimental_mode(
    stub_prefs: _RecordingPreferences,
) -> None:
    stub_prefs.values["ExperimentalMode"] = False
    assert prefs.load_settings().experimental_mode is False


def test_save_settings_persists_experimental_mode(
    stub_prefs: _RecordingPreferences,
) -> None:
    prefs.save_settings(prefs.CadexSettings(experimental_mode=False))
    assert stub_prefs.values["ExperimentalMode"] is False
    assert prefs.load_settings().experimental_mode is False

    prefs.save_settings(prefs.CadexSettings(experimental_mode=True))
    assert stub_prefs.values["ExperimentalMode"] is True
    assert prefs.load_settings().experimental_mode is True


def test_reset_settings_removes_experimental_mode_key(
    stub_prefs: _RecordingPreferences,
) -> None:
    prefs.save_settings(prefs.CadexSettings(experimental_mode=False))
    prefs.reset_settings()
    assert "ExperimentalMode" in stub_prefs.removed
    assert prefs.load_settings().experimental_mode is True


def test_reset_settings_clears_first_run_prompt_flag(
    stub_prefs: _RecordingPreferences,
) -> None:
    # Resetting to defaults should let the first-run welcome prompt ask again.
    stub_prefs.values["ExperimentalModePrompted"] = True
    prefs.reset_settings()
    assert "ExperimentalModePrompted" in stub_prefs.removed


def test_session_flag_is_cached_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """The session flag must not follow later preference writes: experimental mode
    takes effect on restart only."""
    import importlib
    import sys

    class _ParamGroup:
        def __init__(self, value: bool) -> None:
            self.value = value

        def GetBool(self, name: str, default: bool = False) -> bool:
            assert name == "ExperimentalMode"
            return self.value

    group = _ParamGroup(True)
    monkeypatch.setattr(
        sys.modules["FreeCAD"],
        "ParamGet",
        lambda path: group,
        raising=False,
    )
    sys.modules.pop("CadexExperimentalMode", None)
    try:
        experimental_mode = importlib.import_module("CadexExperimentalMode")
        assert experimental_mode.is_experimental_mode_session() is True
        group.value = False
        assert experimental_mode.is_experimental_mode_session() is True
    finally:
        sys.modules.pop("CadexExperimentalMode", None)
