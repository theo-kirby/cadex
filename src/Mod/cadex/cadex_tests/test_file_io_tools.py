# SPDX-License-Identifier: LGPL-2.1-or-later

"""Contracts for the file.* tool path/format resolution helpers."""

from __future__ import annotations

from pathlib import Path

from tool_impl.service import file_io_runtime


def test_classify_extension_covers_every_supported_format() -> None:
    assert file_io_runtime.classify_extension(Path("/a/b.FCStd")) == "project"
    for ext in (".step", ".stp", ".iges", ".igs", ".brep", ".brp"):
        assert file_io_runtime.classify_extension(Path(f"/a/b{ext}")) == "solid"
    for ext in (".stl", ".obj", ".ply"):
        assert file_io_runtime.classify_extension(Path(f"/a/b{ext}")) == "mesh"
    assert file_io_runtime.classify_extension(Path("/a/b.txt")) is None


def test_resolve_source_path_exact_file(tmp_path: Path) -> None:
    target = tmp_path / "bracket.step"
    target.write_bytes(b"solid")
    resolved = file_io_runtime.resolve_source_path(str(target))
    assert resolved["ok"] and resolved["path"] == target


def test_resolve_source_path_completes_bare_stem(tmp_path: Path) -> None:
    target = tmp_path / "chassis-v10.FCStd"
    target.write_bytes(b"pk")
    resolved = file_io_runtime.resolve_source_path(str(tmp_path / "chassis-v10"))
    assert resolved["ok"] and resolved["path"] == target
    assert resolved["resolved_from"] == str(tmp_path / "chassis-v10")


def test_resolve_source_path_case_insensitive_name(tmp_path: Path) -> None:
    target = tmp_path / "Wing.STEP"
    target.write_bytes(b"solid")
    resolved = file_io_runtime.resolve_source_path(str(tmp_path / "wing.step"))
    # On a case-insensitive filesystem the exact-path branch answers first, so
    # only samefile equality is guaranteed.
    assert resolved["ok"] and resolved["path"].samefile(target)


def test_resolve_source_path_ambiguous_stem(tmp_path: Path) -> None:
    (tmp_path / "part.step").write_bytes(b"a")
    (tmp_path / "part.stl").write_bytes(b"b")
    resolved = file_io_runtime.resolve_source_path(str(tmp_path / "part"))
    assert not resolved["ok"]
    assert resolved["reason"] == "AMBIGUOUS_PATH"
    assert len(resolved["candidates"]) == 2


def test_resolve_source_path_missing_lists_candidates(tmp_path: Path) -> None:
    (tmp_path / "other.step").write_bytes(b"a")
    resolved = file_io_runtime.resolve_source_path(str(tmp_path / "nope.step"))
    assert not resolved["ok"]
    assert resolved["reason"] == "FILE_NOT_FOUND"
    assert resolved["candidates"] == [str(tmp_path / "other.step")]


def test_resolve_source_path_rejects_relative_and_empty() -> None:
    assert file_io_runtime.resolve_source_path("")["reason"] == "EMPTY_PATH"
    assert file_io_runtime.resolve_source_path("parts/a.step")["reason"] == "RELATIVE_PATH"


def test_resolve_source_path_rejects_unsupported_extension(tmp_path: Path) -> None:
    target = tmp_path / "notes.txt"
    target.write_bytes(b"x")
    resolved = file_io_runtime.resolve_source_path(str(target))
    assert not resolved["ok"]
    assert resolved["reason"] == "UNSUPPORTED_EXTENSION"
    assert ".step" in resolved["allowed_extensions"]


def test_resolve_source_path_restricted_extensions(tmp_path: Path) -> None:
    target = tmp_path / "model.step"
    target.write_bytes(b"solid")
    resolved = file_io_runtime.resolve_source_path(
        str(target), allowed_extensions=file_io_runtime.PROJECT_EXTENSIONS
    )
    assert not resolved["ok"]
    assert resolved["reason"] == "UNSUPPORTED_EXTENSION"


def test_resolve_export_path_accepts_new_file(tmp_path: Path) -> None:
    resolved = file_io_runtime.resolve_export_path(
        str(tmp_path / "out.step"), overwrite=False
    )
    assert resolved["ok"] and resolved["path"] == tmp_path / "out.step"


def test_resolve_export_path_requires_overwrite_for_existing(tmp_path: Path) -> None:
    target = tmp_path / "out.stl"
    target.write_bytes(b"x")
    denied = file_io_runtime.resolve_export_path(str(target), overwrite=False)
    assert not denied["ok"] and denied["reason"] == "FILE_EXISTS"
    allowed = file_io_runtime.resolve_export_path(str(target), overwrite=True)
    assert allowed["ok"]


def test_resolve_export_path_rejects_bad_destinations(tmp_path: Path) -> None:
    assert (
        file_io_runtime.resolve_export_path(
            str(tmp_path / "missing" / "out.step"), overwrite=False
        )["reason"]
        == "NO_SUCH_DIRECTORY"
    )
    assert (
        file_io_runtime.resolve_export_path(str(tmp_path / "out.xyz"), overwrite=False)[
            "reason"
        ]
        == "UNSUPPORTED_EXTENSION"
    )
    assert (
        file_io_runtime.resolve_export_path(str(tmp_path), overwrite=True)["reason"]
        == "UNSUPPORTED_EXTENSION"
    )
    # A directory whose name carries a supported extension is still rejected.
    trap = tmp_path / "fake.step"
    trap.mkdir()
    assert (
        file_io_runtime.resolve_export_path(str(trap), overwrite=True)["reason"]
        == "IS_DIRECTORY"
    )
