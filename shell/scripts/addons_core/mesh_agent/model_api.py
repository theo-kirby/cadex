# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Parameter value coercion.

This module used to be the script-facing API of a *local* model system —
``mesh_model``, importable inside a model script that Blender ``exec()``ed
against ``bpy``, with ``params()``, ``Float``/``Int``/``Bool``/``Color`` and
an execution context that collected declarations as the script ran. The
model script now runs in the cadex engine, which declares its own parameters
and returns them as ``param_specs``; nothing here is imported by a script any
more, and the ``mesh_model`` alias in ``sys.modules`` is gone (ADR-030).

What survived is the one function the engine path also needed: coercing a
value from a slider, a saved .blend or a ``set_params`` tool call into the
type and range its spec declares. Spec dicts still carry the same shape
(``type``, ``default``, ``min``, ``max``) — ``cadex_backend`` bridges the
engine's specs into it — so this is unchanged.
"""


def clamp(spec, value):
    """Coerce ``value`` to the spec's type and range; fall back to default."""
    try:
        if spec["type"] == 'FLOAT':
            value = float(value)
            return min(max(value, spec["min"]), spec["max"])
        if spec["type"] == 'INT':
            value = int(round(float(value)))
            return min(max(value, spec["min"]), spec["max"])
        if spec["type"] == 'BOOL':
            return bool(value)
        if spec["type"] == 'COLOR':
            rgb = [min(max(float(c), 0.0), 1.0) for c in list(value)[:3]]
            if len(rgb) == 3:
                return rgb
    except (TypeError, ValueError):
        pass
    return spec["default"]
