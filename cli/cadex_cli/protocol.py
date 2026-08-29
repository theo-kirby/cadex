# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""Load ``CadexdProtocol`` out of the engine the CLI is actually driving.

The CLI already has to resolve an engine's ``module_dir`` in order to spawn
``cadexd`` at all, so the protocol module is free to import — and importing
*that* one rather than restating its tables is what stops a third client
from drifting away from the contract. It is the same move
``test_cadexd_lifecycle.py`` makes for the same reason: validating a
packaged payload's frames against the source tree's spec would check the
wrong thing (ADR-023).

Loaded by path rather than by mutating ``sys.path``, so two engines can be
resolved in one process (the tests do exactly that) without one shadowing
the other.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

_CACHE: dict[str, ModuleType] = {}


class ProtocolUnavailable(RuntimeError):
    """The resolved engine has no importable ``CadexdProtocol.py``."""


def load_protocol(module_dir: Path | str) -> ModuleType:
    """Import ``CadexdProtocol`` from ``module_dir``; cached per directory."""

    key = str(Path(module_dir).resolve())
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    source = Path(key) / "CadexdProtocol.py"
    if not source.is_file():
        raise ProtocolUnavailable(
            f"{source} does not exist; {key!r} is not a cadex engine module "
            "directory."
        )
    spec = importlib.util.spec_from_file_location(
        f"_cadex_cli_protocol_{abs(hash(key)):x}", source
    )
    if spec is None or spec.loader is None:
        raise ProtocolUnavailable(f"Could not load {source}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CACHE[key] = module
    return module
