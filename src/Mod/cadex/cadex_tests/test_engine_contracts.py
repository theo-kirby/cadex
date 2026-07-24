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


class TestStageAwareFailureRendering:
    """Transcript lines state whether a failed call was rejected pre-execution
    or executed and rolled back, based on the payload's failure_stage."""

    @staticmethod
    def _gui():
        import CadexGui

        return CadexGui

    def test_pre_execution_stages_render_as_rejected(self) -> None:
        gui = self._gui()
        for stage in ("schema", "surface", "edit_state", "precondition"):
            text = gui._format_progress_event(
                {
                    "event": "tool_call_completed",
                    "ok": False,
                    "tool_name": "xscript.project.write_script",
                    "result": {"error": "bad input", "failure_stage": stage},
                }
            )
            assert "rejected before execution" in text
            assert stage in text
            assert "rolled back" not in text

    def test_rolled_back_stages_render_as_executed_and_rolled_back(self) -> None:
        gui = self._gui()
        for stage in ("native_call", "native_recompute", "postcondition"):
            text = gui._format_progress_event(
                {
                    "event": "tool_call_completed",
                    "ok": False,
                    "tool_name": "xscript.project.write_script",
                    "result": {"error": "recompute failed", "failure_stage": stage},
                }
            )
            assert "failed during execution, rolled back" in text
            assert stage in text
            assert "rejected" not in text

    def test_external_process_stage_renders_document_unchanged(self) -> None:
        gui = self._gui()
        text = gui._format_progress_event(
            {
                "event": "tool_call_completed",
                "ok": False,
                "result": {"error": "worker died", "failure_stage": "external_process"},
            }
        )
        assert "external process" in text
        assert "document unchanged" in text

    def test_missing_stage_degrades_to_blocked(self) -> None:
        gui = self._gui()
        for result in ({"error": "no stage"}, {}, None, "not-a-dict"):
            text = gui._format_progress_event(
                {
                    "event": "tool_call_completed",
                    "ok": False,
                    "tool_name": "xscript.project.write_script",
                    "result": result,
                }
            )
            assert "blocked" in text

    def test_unknown_stage_degrades_to_blocked(self) -> None:
        gui = self._gui()
        text = gui._format_progress_event(
            {
                "event": "tool_call_completed",
                "ok": False,
                "result": {"error": "x", "failure_stage": "weird_future_stage"},
            }
        )
        assert "blocked" in text

    def test_successful_call_still_renders_ok(self) -> None:
        gui = self._gui()
        text = gui._format_progress_event(
            {
                "event": "tool_call_completed",
                "ok": True,
                "result": {"title": "Created Body"},
            }
        )
        assert "ok" in text
        assert "blocked" not in text

    def test_provider_tool_result_sent_is_stage_aware(self) -> None:
        gui = self._gui()
        rejected = gui._format_progress_event(
            {
                "event": "provider_tool_result_sent",
                "ok": False,
                "tool_name": "xscript.project.write_script",
                "error": "schema mismatch",
                "failure_stage": "schema",
            }
        )
        assert "rejected before execution" in rejected
        rolled_back = gui._format_progress_event(
            {
                "event": "provider_tool_result_sent",
                "ok": False,
                "tool_name": "xscript.project.write_script",
                "error": "boolean failed",
                "failure_stage": "native_recompute",
            }
        )
        assert "failed during execution, rolled back" in rolled_back
        missing = gui._format_progress_event(
            {
                "event": "provider_tool_result_sent",
                "ok": False,
                "tool_name": "xscript.project.write_script",
                "error": "anything",
            }
        )
        assert "blocked" in missing

    def test_every_declared_failure_stage_has_specific_rendering(self) -> None:
        """New stages added to CadexTools.FAILURE_STAGES must not silently
        degrade to the generic 'blocked' rendering."""
        import CadexTools

        gui = self._gui()
        covered = (
            gui._PRE_EXECUTION_FAILURE_STAGES
            | gui._ROLLED_BACK_FAILURE_STAGES
            | {"external_process"}
        )
        assert covered == CadexTools.FAILURE_STAGES


# ---------------------------------------------------------------------------
# Service: private scripted carriers and one-shot view attachment
# ---------------------------------------------------------------------------


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
