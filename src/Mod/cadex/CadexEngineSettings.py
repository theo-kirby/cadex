# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later

"""The engine's own settings: sandbox budgets and the preference group.

Split out of ``CadexPreferences`` in Phase 7 (ADR-021). That module is a Qt
shell concern — provider selection, models, API-key state, prompt starters,
debug capture — and it imports ``CadexAuth`` / ``CadexDebug`` /
``CadexPromptStarters`` at module scope, all of which die with the shell.
The engine needed exactly two numbers out of it, so those two numbers live
here instead and the engine stops depending on the shell's preference tree.

Read by ``cadexd`` (once, at ``open_project``) and by
``CadexScriptedRuntime`` (as the fallback when the calling service carries
no budgets, e.g. headless rebuild).
"""

from __future__ import annotations

from typing import Any, Mapping

import FreeCAD as App

#: Shared with the shell's preference tree; the group name is the branding
#: contract asserted by the engine identity tests.
PREFERENCE_GROUP = "User parameter:BaseApp/Preferences/Mod/cadex"

DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0
DEFAULT_SCRIPTED_MEMORY_LIMIT_MB = 6144


def preferences():
    """The cadex preference group."""

    return App.ParamGet(PREFERENCE_GROUP)


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


def load_engine_budgets() -> dict[str, Any]:
    """Sandbox budgets for one xscript worker run, from preferences."""

    pref = preferences()
    return {
        "timeout_seconds": _positive_float(
            pref.GetFloat("ScriptedTimeoutSeconds", DEFAULT_SCRIPTED_TIMEOUT_SECONDS),
            DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
        ),
        "memory_limit_mb": _positive_int(
            pref.GetInt("ScriptedMemoryLimitMB", DEFAULT_SCRIPTED_MEMORY_LIMIT_MB),
            DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
        ),
    }


def resolve_budgets(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Caller-supplied budgets when complete, else the preference values."""

    budgets = dict(raw or {})
    timeout = _positive_float(budgets.get("timeout_seconds"), 0.0)
    memory_mb = _positive_int(budgets.get("memory_limit_mb"), 0)
    if timeout > 0.0 and memory_mb > 0:
        return {"timeout_seconds": timeout, "memory_limit_mb": memory_mb}
    return load_engine_budgets()
