# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Which engine the CLI drives, and how it was found.

Three sources, in order of decreasing explicitness:

1. ``--engine <root>`` — a staged payload directory carrying
   ``cadex-engine.json``.
2. ``CADEX_ENGINE_ROOT`` — the same thing from the environment, which is how
   ctest's ``CadexEnginePayloadSmoke`` and the latency harness already point
   at a payload (ADR-020, ADR-023).
3. The development tree — a built ``FreeCADCmd`` plus ``src/Mod/cadex``.

The manifest is the payload's discovery contract, so reading it is what makes
``--engine`` mean *the shipped engine* rather than *a directory laid out the
way a build tree happens to be*. The resolved engine names itself in the
``--json`` envelope for the same reason the latency harness reports it: two
runs against two engines have to be tellable apart in a log.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from types import ModuleType

from .protocol import load_protocol

#: ``cli/cadex_cli/engine.py`` → ``cli/cadex_cli`` → ``cli`` → the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The installed prefix first, then the build tree — the order
#: ``test_cadexd_lifecycle.py`` uses, and for its reason: the installed
#: binary loads everything from one prefix, so type registration is sound.
DEV_FREECADCMD_CANDIDATES = (
    REPO_ROOT / ".pixi" / "envs" / "default" / "bin" / "FreeCADCmd",
    REPO_ROOT / "build" / "release" / "bin" / "FreeCADCmd",
)
DEV_MODULE_DIR = REPO_ROOT / "src" / "Mod" / "cadex"

MANIFEST_NAME = "cadex-engine.json"
MANIFEST_SCHEMA = "cadex-engine-v1"


class EngineError(RuntimeError):
    """No usable engine, or a payload whose manifest does not check out."""


@dataclass(frozen=True)
class Engine:
    """A resolved engine: what to run, what to put on its ``sys.path``."""

    freecadcmd: Path
    module_dir: Path
    #: ``"explicit"``, ``"payload"`` or ``"dev-tree"`` — how it was found.
    source: str
    #: The payload root, when there was one.
    root: Path | None = None

    @property
    def protocol(self) -> ModuleType:
        """This engine's own ``CadexdProtocol`` module."""

        return load_protocol(self.module_dir)

    def describe(self) -> dict[str, str]:
        """The engine identity a report carries."""

        return {
            "source": self.source,
            "freecadcmd": str(self.freecadcmd),
            "module_dir": str(self.module_dir),
        }


def _from_manifest(root: Path, source: str) -> Engine:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise EngineError(
            f"{root} has no {MANIFEST_NAME}; the payload's manifest is its "
            "discovery contract (ADR-020)."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EngineError(f"{manifest_path} is not readable JSON: {exc}") from exc
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise EngineError(
            f"{manifest_path} declares schema {manifest.get('schema')!r}; "
            f"expected {MANIFEST_SCHEMA!r}."
        )
    base = manifest_path.parent
    try:
        binary = base.joinpath(*str(manifest["freecadcmd"]).split("/"))
        module_dir = base.joinpath(*str(manifest["module_dir"]).split("/"))
    except KeyError as exc:
        raise EngineError(f"{manifest_path} is missing {exc}.") from exc
    if not binary.is_file():
        raise EngineError(f"{manifest_path} names a missing binary: {binary}")
    if not module_dir.is_dir():
        raise EngineError(f"{manifest_path} names a missing module dir: {module_dir}")

    engine = Engine(binary, module_dir, source, root=base)
    # The payload states the protocol it speaks; the module dir carries the
    # implementation. Disagreement here means a payload assembled out of two
    # trees, which is worth failing on before a single frame is sent.
    declared = str(manifest.get("protocol") or "")
    actual = str(getattr(engine.protocol, "PROTOCOL_SCHEMA", ""))
    if declared and actual and declared != actual:
        raise EngineError(
            f"{manifest_path} declares protocol {declared!r} but its "
            f"CadexdProtocol says {actual!r}."
        )
    return engine


def _dev_tree() -> Engine:
    binary = next(
        (candidate for candidate in DEV_FREECADCMD_CANDIDATES if candidate.is_file()),
        None,
    )
    if binary is None:
        raise EngineError(
            "No engine found. Build one with `pixi run build-engine`, or point "
            "the CLI at a staged payload with --engine / CADEX_ENGINE_ROOT.\n"
            "Looked for: "
            + ", ".join(str(path) for path in DEV_FREECADCMD_CANDIDATES)
        )
    if not DEV_MODULE_DIR.is_dir():
        raise EngineError(f"{DEV_MODULE_DIR} does not exist.")
    return Engine(binary, DEV_MODULE_DIR, "dev-tree")


def resolve_engine(explicit: str | os.PathLike[str] | None = None) -> Engine:
    """Resolve the engine to drive; raise :class:`EngineError` if there is none."""

    if explicit:
        root = Path(explicit).expanduser()
        if not root.is_dir():
            raise EngineError(
                f"--engine {str(explicit)!r} is not a directory. It names a "
                f"staged engine payload root, the directory holding "
                f"{MANIFEST_NAME}."
            )
        return _from_manifest(root.resolve(), "explicit")

    env_root = os.environ.get("CADEX_ENGINE_ROOT", "").strip()
    if env_root:
        root = Path(env_root).expanduser()
        if not root.is_dir():
            raise EngineError(f"CADEX_ENGINE_ROOT={env_root!r} is not a directory.")
        return _from_manifest(root.resolve(), "payload")

    return _dev_tree()
