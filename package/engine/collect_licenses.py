#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Stage the engine payload's license material (ADR-171).

The payload prune deletes ``share/doc`` and ``conda-meta`` — correctly, as
dead weight — but until this script existed that also destroyed the license
texts of everything the payload ships, OCCT's LGPL + exception first among
them. This collector reads the **source environment** (not the payload: the
stage-only path never copies ``conda-meta``, so both staging paths must
harvest from the same place) and writes into the payload:

    licenses/<package>/...     every LICENSE*/COPYING*/*EXCEPTION* under
                               share/doc/<package>/, plus the carried pypi
                               wheels' dist-info licenses
    licenses/MANIFEST.json     schema cadex-licenses-v1 — the machine-
                               readable per-conda-package inventory
    LICENSE, NOTICE, THIRD_PARTY_LICENSES.md   copied from the repo root

and then hard-fails unless the named obligations landed. Run by
``build_engine_payload.sh`` on both staging paths; importable so
``test_licensing_compliance.py`` can unit-test it against a synthetic
environment.
"""

from __future__ import annotations

import ast
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent


def _carried_pypi_packages() -> tuple[str, ...]:
    """CARRIED_PYPI_PACKAGES out of relocate_conda_environment.py — the
    single source of truth for which pypi wheels ship (ADR-076). Read by
    AST rather than import: that module needs conda_pack at module scope,
    and this script must run from a bare python."""
    source = (
        REPO / "package" / "rattler-build" / "scripts" / "relocate_conda_environment.py"
    ).read_text()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CARRIED_PYPI_PACKAGES" for t in node.targets
        ):
            return tuple(ast.literal_eval(node.value))
    raise RuntimeError("CARRIED_PYPI_PACKAGES not found in relocate_conda_environment.py")


CARRIED_PYPI_PACKAGES = _carried_pypi_packages()

# share/doc directory name -> the package name users know it by.
DOC_DIR_ALIASES = {"opencascade": "occt"}

LICENSE_GLOBS = ("LICENSE*", "COPYING*", "*EXCEPTION*", "ThirdPartyLibraries.html")

# The named obligations: staging must not finish without these.
REQUIRED = (
    "licenses/MANIFEST.json",
    "licenses/occt/LICENSE_LGPL_21.txt",
    "licenses/occt/OCCT_LGPL_EXCEPTION.txt",
    "licenses/freecad/LICENSE.html",
    "licenses/mujoco/LICENSE",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_LICENSES.md",
)


def read_conda_inventory(source_env: Path) -> list[dict]:
    """name/version/license/license_family for every conda package in the
    source environment; a package whose metadata carries no license is
    recorded as UNKNOWN rather than dropped."""
    inventory = []
    for meta in sorted((source_env / "conda-meta").glob("*.json")):
        record = json.loads(meta.read_text())
        inventory.append(
            {
                "name": record.get("name", meta.stem),
                "version": record.get("version", "UNKNOWN"),
                "license": record.get("license") or "UNKNOWN",
                "license_family": record.get("license_family") or "UNKNOWN",
            }
        )
    if not inventory:
        raise RuntimeError(f"no conda-meta records under {source_env} - wrong source env?")
    return inventory


def harvest_doc_licenses(source_env: Path, payload: Path) -> dict[str, list[str]]:
    """Copy the license-like files out of share/doc/<pkg>/ before the prune's
    equivalent in the payload is felt: licenses/<pkg>/<file>."""
    harvested: dict[str, list[str]] = {}
    doc_root = source_env / "share" / "doc"
    if not doc_root.is_dir():
        return harvested
    for pkg_dir in sorted(doc_root.iterdir()):
        if not pkg_dir.is_dir():
            continue
        name = DOC_DIR_ALIASES.get(pkg_dir.name.lower(), pkg_dir.name.lower())
        files = sorted({f for glob in LICENSE_GLOBS for f in pkg_dir.glob(glob) if f.is_file()})
        if not files:
            continue
        target = payload / "licenses" / name
        target.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, target / f.name)
        harvested[name] = [f.name for f in files]
    return harvested


def harvest_pypi_licenses(source_env: Path, payload: Path) -> dict[str, list[str]]:
    """The carried wheels' dist-info license files: licenses/<wheel>/<file>.
    Driven by CARRIED_PYPI_PACKAGES so a second carried wheel is covered the
    day it is named, not the day someone remembers this script."""
    harvested: dict[str, list[str]] = {}
    for sp in sorted(source_env.glob("lib/python*/site-packages")):
        for name in CARRIED_PYPI_PACKAGES:
            for dist_info in sorted(sp.glob(f"{name}-*.dist-info")):
                files = sorted(
                    f
                    for pattern in ("licenses/*", "LICENSE*", "COPYING*")
                    for f in dist_info.glob(pattern)
                    if f.is_file()
                )
                if not files:
                    raise RuntimeError(
                        f"{dist_info.name} carries no license file - the wheel "
                        "changed shape; teach this function where its license went"
                    )
                target = payload / "licenses" / name
                target.mkdir(parents=True, exist_ok=True)
                for f in files:
                    shutil.copy2(f, target / f.name)
                harvested[name] = [f.name for f in files]
    return harvested


def copy_repo_notices(payload: Path, repo: Path = REPO) -> None:
    for name in ("LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md"):
        source = repo / name
        if not source.is_file():
            raise RuntimeError(
                f"{source} is missing - the repo root must carry it before a payload can"
            )
        shutil.copy2(source, payload / name)


def write_manifest(
    payload: Path, inventory: list[dict], harvested: dict[str, list[str]]
) -> None:
    manifest = {
        "schema": "cadex-licenses-v1",
        "comment": (
            "Every conda package in the environment the payload was staged "
            "from, with its license metadata; 'harvested' maps package -> "
            "license files copied into this directory. The inventory is the "
            "full environment, which over-discloses: some packages' files do "
            "not survive the engine prune."
        ),
        "packages": inventory,
        "harvested": harvested,
    }
    target = payload / "licenses" / "MANIFEST.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n")


def assert_required(payload: Path) -> None:
    missing = [rel for rel in REQUIRED if not (payload / rel).is_file()]
    if missing:
        raise RuntimeError(
            "license material missing from the staged payload: " + ", ".join(missing)
        )


def collect(source_env: Path, payload: Path) -> None:
    inventory = read_conda_inventory(source_env)
    harvested = harvest_doc_licenses(source_env, payload)
    harvested.update(harvest_pypi_licenses(source_env, payload))
    copy_repo_notices(payload)
    write_manifest(payload, inventory, harvested)
    assert_required(payload)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: collect_licenses.py <source-env> <payload>", file=sys.stderr)
        return 2
    collect(Path(argv[1]), Path(argv[2]))
    print(f"==> license material staged into {argv[2]}/licenses")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
