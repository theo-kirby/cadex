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



def test_private_xscript_carriers_are_not_provider_document_objects() -> None:
    from CadexCore import CadexService

    for role in ("implementation", "publication_target", "parameters"):
        assert CadexService._is_private_scripted_object(
            SimpleNamespace(CadexScriptedRole=role)
        )
    for role in ("model", "publication", ""):
        assert not CadexService._is_private_scripted_object(
            SimpleNamespace(CadexScriptedRole=role)
        )
    native = SimpleNamespace(Name="Native", Label="Native", TypeId="Part::Box")
    published = SimpleNamespace(
        Name="Published",
        Label="Published",
        TypeId="App::Link",
        CadexScriptedRole="publication",
        CadexScriptedEngine="xscript",
        CadexScriptedModelId="a" * 32,
        CadexScriptedOutputKey="Housing",
    )
    private_target = SimpleNamespace(
        Name="PrivateTarget",
        Label="Private Target",
        TypeId="Part::Feature",
        CadexScriptedRole="publication_target",
    )
    service = object.__new__(CadexService)
    service._active_document = lambda: SimpleNamespace(
        Name="ContextDoc",
        Objects=[native, published, private_target],
    )

    summary = service.provider_part_summary()

    assert [item["name"] for item in summary["objects"]] == [
        "Native",
        "Published",
    ]
    assert summary["objects"][1]["published_output_key"] == "Housing"


def test_view_attachment_is_one_shot_and_identity_guarded() -> None:
    from CadexCore import CadexService

    service = object.__new__(CadexService)
    service._last_view_screenshot = {
        "captured": True,
        "path": "/project/screenshots/current.png",
        "pending_attachment": True,
    }

    pending = service.view_screenshot_summary()
    assert pending["pending_attachment"] is True
    stale = service.consume_view_screenshot_attachment(
        {"captured": True, "path": "/project/screenshots/older.png"}
    )
    assert stale["consumed"] is False
    assert service.view_screenshot_summary()["captured"] is True

    consumed = service.consume_view_screenshot_attachment(pending)
    assert consumed == {
        "consumed": True,
        "path": "/project/screenshots/current.png",
    }
    assert service.view_screenshot_summary() == {"captured": False, "path": None}


# ---------------------------------------------------------------------------
# XScript default preferences
# ---------------------------------------------------------------------------


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


class TestXScriptDefaults:
    """Lock the out-of-box defaults: the XScript preference is enabled and
    xscript is the default global modeling engine. These tests fail if either
    default silently regresses."""

    _SCOPE = {"project_id": "f" * 32, "title": "Default Test", "document": {}}

    def test_settings_dataclass_enables_xscript_by_default(self) -> None:
        import CadexPreferences as prefs

        assert prefs.CadexSettings().xscript_enabled is True
        assert not hasattr(prefs.CadexSettings(), "xscript_on_bim_enabled")

    def test_load_settings_with_unset_key_enables_xscript(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import CadexPreferences as prefs

        monkeypatch.setattr(prefs, "preferences", lambda: _UnsetPreferences())
        settings = prefs.load_settings()
        assert settings.xscript_enabled is True
        assert not hasattr(settings, "xscript_on_bim_enabled")

    def test_removed_bim_opt_in_is_not_written_or_reset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import CadexPreferences as prefs

        stored = _RecordingPreferences()
        monkeypatch.setattr(prefs, "preferences", lambda: stored)
        prefs.save_settings(prefs.CadexSettings())
        assert "XScriptOnBIMEnabled" not in stored.values
        prefs.reset_settings()
        assert "XScriptOnBIMEnabled" not in stored.values

    def test_default_engine_constant_is_xscript_and_valid(self) -> None:
        from CadexProject import DEFAULT_MODELING_ENGINE, MODELING_ENGINES

        assert DEFAULT_MODELING_ENGINE == "xscript"
        assert DEFAULT_MODELING_ENGINE in MODELING_ENGINES

    def test_fresh_manifest_seeds_xscript_engine(self, tmp_path: Path) -> None:
        from CadexProject import CadexProjectStore

        store = CadexProjectStore("test-session", index_path=tmp_path / "index.db")
        manifest = store._default_manifest(dict(self._SCOPE))
        assert manifest["modeling_engine"] == "xscript"
        assert "partdesign_engine" not in manifest

    def test_merge_preserves_explicit_engine_choices(self, tmp_path: Path) -> None:
        from CadexProject import MODELING_ENGINES, CadexProjectStore

        store = CadexProjectStore("test-session", index_path=tmp_path / "index.db")
        for engine in sorted(MODELING_ENGINES):
            merged = store._merge_manifest_defaults(
                {"partdesign_engine": engine}, dict(self._SCOPE)
            )
            assert merged["modeling_engine"] == engine
            assert "partdesign_engine" not in merged

    def test_merge_defaults_missing_or_none_engine_to_xscript(
        self, tmp_path: Path
    ) -> None:
        from CadexProject import CadexProjectStore

        store = CadexProjectStore("test-session", index_path=tmp_path / "index.db")
        for manifest in ({}, {"modeling_engine": None}, {"partdesign_engine": None}):
            merged = store._merge_manifest_defaults(dict(manifest), dict(self._SCOPE))
            assert merged["modeling_engine"] == "xscript"

    def test_modeling_engine_accessor_falls_back_to_xscript(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from CadexProject import CadexProjectStore

        store = CadexProjectStore("test-session", index_path=tmp_path / "index.db")
        monkeypatch.setattr(store, "load_manifest", lambda: {})
        assert store.modeling_engine() == "xscript"
        assert not hasattr(store, "partdesign_engine")
        assert not hasattr(store, "set_partdesign_engine")

    def test_engine_only_manifest_reader_supports_legacy_field(
        self, tmp_path: Path
    ) -> None:
        from CadexProject import PROJECT_SCHEMA, CadexProjectStore

        manifest_path = tmp_path / "project.cadex.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": PROJECT_SCHEMA,
                    "version": 1,
                    "partdesign_engine": "xscript",
                }
            ),
            encoding="utf-8",
        )

        assert (
            CadexProjectStore.read_modeling_engine_manifest(manifest_path)
            == "xscript"
        )
        assert (
            CadexProjectStore.read_modeling_engine_manifest(tmp_path / "missing.json")
            == "xscript"
        )
