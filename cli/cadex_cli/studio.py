# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Load the engine's shared client code: ``CadexStudio`` (ADR-445) and ``CadexFitReport`` (ADR-447).

The renderer, the concept sheet and the dark scene palette are engine code, so
the CLI and the shell draw with one implementation. Loaded by path, as
:mod:`protocol` loads ``CadexdProtocol``, from the engine ``CADEX_ENGINE_ROOT``
names or else the development tree. The module is pure standard library, so
loading it needs no built engine.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from .engine import DEV_MODULE_DIR, EngineError, resolve_engine


class StudioUnavailable(RuntimeError):
    """The engine module directory has no importable ``CadexStudio.py``."""


def load_studio(module_dir: Path | str, name: str = "CadexStudio") -> ModuleType:
    """Load the engine module ``name`` (default the renderer) from ``module_dir``, by path."""
    source = Path(module_dir).resolve() / f"{name}.py"
    if not source.is_file():
        raise StudioUnavailable(f"{source} does not exist; not a cadex engine module directory.")
    spec = importlib.util.spec_from_file_location(
        f"_cadex_cli_{name}_{abs(hash(str(source))):x}", source)
    if spec is None or spec.loader is None:
        raise StudioUnavailable(f"Could not load {source}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_module_dir() -> Path:
    try:
        return resolve_engine(None).module_dir
    except EngineError:
        # No built engine (a bare checkout): the renderer needs none.
        return DEV_MODULE_DIR


#: The engine module directory the CLI reads engine code and data from.
ENGINE_MODULE_DIR = _default_module_dir()
#: The loaded renderer. Every drawing call in the CLI goes through it.
STUDIO = load_studio(ENGINE_MODULE_DIR)
#: The fit and inventory blocks every build reply carries (ADR-447).
FIT_REPORT = load_studio(ENGINE_MODULE_DIR, "CadexFitReport")
#: Which outputs have a surface to print (ADR-156, ADR-158), as the export reads it.
PRINTABLES = load_studio(ENGINE_MODULE_DIR, "CadexPrintables")
#: The anatomy block's bounded view and ``look`` measure (ADR-614). None on
#: an engine staged before it, which then carries no anatomy block at all.
try:
    ANATOMY = load_studio(ENGINE_MODULE_DIR, "CadexAnatomy")
except StudioUnavailable:
    ANATOMY = None
