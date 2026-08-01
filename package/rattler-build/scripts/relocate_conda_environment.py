#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess

from conda_pack.core import CondaEnv, File, Packer
from conda_pack.formats import NoArchive


# The engine payload has no GUI binary (cadex ADR-022): bin/freecad is not
# produced by a BUILD_GUI=OFF build, so it cannot be required here.
REQUIRED_FILES = {
    "bin/freecadcmd",
    "bin/python",
    "Mod/cadex/Init.py",
}
PYTHON_RUNTIME_PROBE = (
    "import encodings, pathlib, sys; "
    "prefix = pathlib.Path(sys.prefix).resolve(); "
    "target = pathlib.Path(encodings.__file__).resolve().relative_to(prefix); "
    "print(target.as_posix())"
)

# Site-packages directories carried verbatim even though no conda package
# owns them. Named one by one, never a pattern: shipping an unmanaged file
# is the exception this script exists to prevent, so each one is a decision
# with a reason next to it.
#
# mujoco (cadex ADR-075) -- the dynamics engine. Its correct home is
# conda-forge `mujoco-python`, which cannot be installed until the manifest
# is re-solvable again; see ADR-075 for why that is a separate problem with
# a separate risk. Carrying the wheel is safe in a way a wheel usually is
# not: it bundles its own libmujoco.<version>.dylib beside the extension
# modules and reaches it through `@loader_path`, so it references nothing in
# the conda prefix and is relocatable by construction.
#
# relocate_macos_runtime_rpaths.py then walks it like anything else, and
# wants to: the wheel ships a stale absolute build rpath
# (/Volumes/BuildData/...) alongside @loader_path. The sanitizer deletes the
# stale one, keeps the working one, re-points the experimental/studio
# extensions at @loader_path/../.., and re-signs. Verified by relocating a
# copy and importing from it -- same free-fall integration to six decimals.
CARRIED_PYPI_PACKAGES = ("mujoco",)


class CopyArchive(NoArchive):
    """Conda-pack directory writer that never hardlinks into source caches."""

    def _add(self, source: str, target: str) -> None:
        target_path = Path(self._absolute_path(target))
        self._ensure_parent(str(target_path))
        source_path = Path(source)
        if source_path.is_dir() and not source_path.is_symlink():
            target_path.mkdir(exist_ok=True)
            shutil.copystat(source_path, target_path, follow_symlinks=False)
            return
        if os.path.lexists(target_path):
            if target_path.is_dir() and not target_path.is_symlink():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
        shutil.copy2(source_path, target_path, follow_symlinks=False)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Relocate only package-managed files from a conda/Pixi environment "
            "into a deterministic application prefix."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    return parser.parse_args()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _relative_target(target: str) -> Path:
    path = Path(target)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise RuntimeError(f"Invalid conda environment target path: {target!r}")
    return path


def _installed_managed_files(
    source: Path,
    managed_files: list[File],
) -> list[File]:
    installed_by_target: dict[str, File] = {}
    missing_sources: list[str] = []
    for file in managed_files:
        relative = _relative_target(file.target)
        installed_source = source / relative
        if not os.path.lexists(installed_source):
            missing_sources.append(file.target)
            continue
        candidate = File(
            str(installed_source),
            file.target,
            is_conda=True,
            file_mode=file.file_mode,
            prefix_placeholder=file.prefix_placeholder,
        )
        previous = installed_by_target.get(file.target)
        if previous is not None:
            previous_metadata = (
                previous.file_mode,
                previous.prefix_placeholder,
            )
            candidate_metadata = (
                candidate.file_mode,
                candidate.prefix_placeholder,
            )
            if candidate_metadata != previous_metadata:
                raise RuntimeError(
                    "Conflicting package metadata for shared environment target "
                    f"{file.target}: {previous_metadata!r} != {candidate_metadata!r}"
                )
            continue
        installed_by_target[file.target] = candidate
    if missing_sources:
        rendered = ", ".join(sorted(missing_sources)[:20])
        suffix = "" if len(missing_sources) <= 20 else " ..."
        raise RuntimeError(
            "Package-managed files are missing from the installed environment: "
            f"{rendered}{suffix}"
        )
    return list(installed_by_target.values())


def _python_runtime_target(prefix: Path) -> str:
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [str(prefix / "bin" / "python"), "-I", "-S", "-c", PYTHON_RUNTIME_PROBE],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    target = result.stdout.strip()
    if result.returncode != 0 or not target or "\n" in target:
        diagnostic = f"{result.stdout}\n{result.stderr}".strip()
        raise RuntimeError(
            f"Python runtime is incomplete in {prefix}:\n{diagnostic}"
        )
    _relative_target(target)
    return target


def _carried_pypi_files(source: Path, python_runtime_target: str) -> list[File]:
    """Files of the CARRIED_PYPI_PACKAGES, as unmanaged copy-verbatim entries.

    ``is_conda=False`` and no ``prefix_placeholder``, which is what tells
    conda-pack to copy the bytes and rewrite nothing -- the whole reason
    carrying these is safe. A named package that is not installed is an
    error, not a silent omission: it would ship a payload missing the
    dynamics engine and fail at the user.
    """

    # site-packages sits beside the runtime's own encodings/ package.
    site_packages = Path(python_runtime_target).parent.parent / "site-packages"
    carried: list[File] = []
    for name in CARRIED_PYPI_PACKAGES:
        roots = sorted(
            path
            for path in (source / site_packages).glob(f"{name}*")
            if path.name == name or path.name.startswith(f"{name}-")
        )
        if not roots:
            raise RuntimeError(
                f"{name!r} is named in CARRIED_PYPI_PACKAGES but is not installed "
                f"in {source / site_packages}. Install it or remove the name; "
                "shipping a payload without it fails at the user, not here."
            )
        for root in roots:
            for path in sorted(root.rglob("*")):
                if path.is_dir() and not path.is_symlink():
                    continue
                if "__pycache__" in path.parts:
                    continue
                target = path.relative_to(source)
                carried.append(File(str(path), target.as_posix(), is_conda=False))
    return carried


def _copy_relocated_environment(
    source: Path,
    destination: Path,
    managed_files: list[File],
) -> None:
    destination.mkdir(parents=True)
    archive = CopyArchive(str(destination), "")
    packer = Packer(str(source), archive, str(destination))
    with archive:
        for file in managed_files:
            packer.add(file)
        packer.finish()


def main() -> int:
    arguments = _parse_arguments()
    source = arguments.source.resolve()
    destination = arguments.destination.resolve()
    if not source.is_dir():
        raise SystemExit(f"Source conda environment does not exist: {source}")
    if source == destination or _is_relative_to(destination, source):
        raise SystemExit(
            f"Destination must be outside the source conda environment: {destination}"
        )
    if destination.exists():
        raise SystemExit(f"Destination already exists and will not be overwritten: {destination}")

    environment = CondaEnv.from_prefix(str(source))
    managed_files = [file for file in environment.files if file.is_conda]
    unmanaged_count = len(environment.files) - len(managed_files)
    managed_targets = {file.target for file in managed_files}
    python_runtime_target = _python_runtime_target(source)
    required_files = REQUIRED_FILES | {python_runtime_target}
    missing = sorted(required_files - managed_targets)
    if missing:
        raise RuntimeError(
            "The package-managed environment is incomplete; required files are missing: "
            + ", ".join(missing)
        )

    carried_files = _carried_pypi_files(source, python_runtime_target)
    print(
        f"Relocating {len(managed_files)} package-managed files from {source} to "
        f"{destination}; excluding {unmanaged_count - len(carried_files)} unmanaged "
        f"files; carrying {len(carried_files)} verbatim from "
        f"{', '.join(CARRIED_PYPI_PACKAGES)}.",
        flush=True,
    )
    installed_files = _installed_managed_files(source, managed_files) + carried_files
    _copy_relocated_environment(source, destination, installed_files)
    missing_after_copy = sorted(
        target for target in required_files if not (destination / target).is_file()
    )
    if missing_after_copy:
        raise RuntimeError(
            "The relocated environment is incomplete; required files are missing: "
            + ", ".join(missing_after_copy)
        )
    relocated_runtime_target = _python_runtime_target(destination)
    if relocated_runtime_target != python_runtime_target:
        raise RuntimeError(
            "The relocated Python runtime resolved a different standard library: "
            f"source={python_runtime_target}, destination={relocated_runtime_target}"
        )
    print(f"Relocated conda environment is ready: {destination}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
