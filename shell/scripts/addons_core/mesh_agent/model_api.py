# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Script-facing API of the Mesh model system, importable as ``mesh_model``
inside model scripts (an alias is installed in sys.modules when the add-on
registers).

A model script declares its tunable parameters at the top:

    from mesh_model import params, Float, Int, Bool, Color

    p = params(
        height=Float(1.8, min=0.5, max=4.0, name="Height",
                     description="Overall height in meters"),
        arms=Bool(True, name="Arms"),
    )

``params()`` returns the *current* values (stored slider values when the
script is rebuilt by Mesh, declared defaults otherwise), so the same script
also runs unmodified in a vanilla Blender text editor.
"""

from types import SimpleNamespace

# Active execution context while model.rebuild() runs the script; None when
# the script is executed outside Mesh (e.g. vanilla Blender).
_context = None


class _ExecContext:
    def __init__(self, values):
        self.values = dict(values or {})
        self.specs = []
        self.effective = {}


def _begin(values):
    global _context
    _context = _ExecContext(values)
    return _context


def _end():
    """Returns (specs, effective_values) collected by params() calls."""
    global _context
    context = _context
    _context = None
    if context is None:
        return [], {}
    return context.specs, context.effective


def Float(default, min=None, max=None, name=None, description=""):
    default = float(default)
    if min is None:
        min = 0.0 if default >= 0.0 else default * 4.0
    if max is None:
        max = default * 4.0 if default > 0.0 else 1.0
    return {"type": 'FLOAT', "default": default,
            "min": float(min), "max": float(max),
            "name": name, "description": description}


def Int(default, min=None, max=None, name=None, description=""):
    default = int(default)
    if min is None:
        min = 0 if default >= 0 else default * 4
    if max is None:
        max = default * 4 if default > 0 else 10
    return {"type": 'INT', "default": default,
            "min": int(min), "max": int(max),
            "name": name, "description": description}


def Bool(default=False, name=None, description=""):
    return {"type": 'BOOL', "default": bool(default),
            "name": name, "description": description}


def Color(default=(0.8, 0.8, 0.8), name=None, description=""):
    return {"type": 'COLOR', "default": [float(c) for c in default][:3],
            "name": name, "description": description}


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


def params(**kwargs):
    """Declare the model's parameters; returns their current values as a
    namespace. Keyword order defines the UI order."""
    namespace = SimpleNamespace()
    for key, spec in kwargs.items():
        if not isinstance(spec, dict) or "type" not in spec:
            raise TypeError(
                "params(): {!s} must be a Float/Int/Bool/Color declaration"
                .format(key))
        spec = dict(spec)
        spec["id"] = key
        if spec["name"] is None:
            spec["name"] = key.replace("_", " ").title()
        if _context is not None:
            _context.specs.append(spec)
            if key in _context.values:
                value = clamp(spec, _context.values[key])
            else:
                value = spec["default"]
            _context.effective[key] = value
        else:
            value = spec["default"]
        setattr(namespace, key, value)
    return namespace
