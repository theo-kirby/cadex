# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The engine's own settings: the sandbox budgets a worker run is given.

Split out of ``CadexPreferences`` in Phase 7 (ADR-021). Budgets belong to
the project (ADR-517): the CLI sends them at ``open_project``, and any it
does not send are the engine's defaults below. The engine reads no FreeCAD
preference group; the dialogs that wrote one are gone (ADR-530).

Read by ``cadexd`` (once, at ``open_project``) and by
``CadexScriptedRuntime`` (when the calling service carries no budgets,
e.g. headless rebuild).
"""

from __future__ import annotations

from typing import Any, Mapping

DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0
DEFAULT_SCRIPTED_MEMORY_LIMIT_MB = 6144


def _positive_float(value: object, default: float) -> float:
    try:
        clean = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return clean if clean > 0 else default


def _positive_int(value: object, default: int) -> int:
    try:
        clean = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default
    return clean if clean > 0 else default


def default_budgets() -> dict[str, Any]:
    """The engine's sandbox budgets for one xscript worker run."""

    return {
        "timeout_seconds": DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
        "memory_limit_mb": DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
    }


def resolve_budgets(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Each caller-supplied budget that is positive, else the engine default.

    Per field (ADR-517): a project that stores only a longer timeout keeps
    the engine's memory ceiling rather than losing the timeout it asked for.
    """

    budgets = dict(raw or {})
    resolved = default_budgets()
    resolved["timeout_seconds"] = _positive_float(
        budgets.get("timeout_seconds"), resolved["timeout_seconds"])
    resolved["memory_limit_mb"] = _positive_int(
        budgets.get("memory_limit_mb"), resolved["memory_limit_mb"])
    return resolved
