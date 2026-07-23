# SPDX-License-Identifier: LGPL-2.1-or-later

"""Sketcher-native Cadex tool registration."""

from __future__ import annotations

from importlib import import_module
from typing import Any

TOOL_MODULE_NAMES = (
    "close_sketch",
    "draw_rectangle",
    "add_polyline",
    "add_arc",
    "add_circle",
    "add_ellipse",
    "add_spline",
    "add_hole_pattern",
    "add_slot",
    "measure",
    "constrain",
    "edit_constraint",
    "move_point",
    "translate_geometry",
    "modify_geometry",
    "add_external_geometry",
    "remove_external_geometry",
    "delete_items",
    "set_construction",
)


def register_tools(registry: Any, service: Any) -> None:
    for module_name in TOOL_MODULE_NAMES:
        module = import_module(f"{__name__}.{module_name}")
        spec = module.TOOL_SPEC
        complete_spec = dict(spec)
        complete_spec.setdefault("workbench", "SketcherWorkbench")
        registry.register_spec(
            complete_spec,
            lambda _module=module, **kwargs: _module.run(service, **kwargs),
        )
