# SPDX-License-Identifier: LGPL-2.1-or-later

"""Service-backed Cadex tool registration.

Each module in this package owns one provider-visible tool shape and must expose
``run(service, **kwargs)``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

TOOL_MODULE_NAMES = (
    "conversation_ask_user",
    "core_inspect",
    "core_capture_view_screenshot",
    "core_set_view",
    "core_relink_object",
    "file_import_model",
    "file_export_model",
    "file_link_external_part",
    "partdesign_create_body",
    "partdesign_create_sketch",
    "partdesign_edit_sketch",
    "partdesign_create_datum_plane",
    "partdesign_create_datum_axis",
    "partdesign_create_datum_point",
    "partdesign_create_shape_binder",
    "partdesign_create_subshape_binder",
    "partdesign_pad",
    "partdesign_pocket",
    "partdesign_hole",
    "partdesign_revolution",
    "partdesign_groove",
    "partdesign_additive_loft",
    "partdesign_thin_loft",
    "partdesign_subtractive_loft",
    "partdesign_additive_pipe",
    "partdesign_subtractive_pipe",
    "partdesign_additive_helix",
    "partdesign_subtractive_helix",
    "partdesign_linear_pattern",
    "partdesign_polar_pattern",
    "partdesign_mirror",
    "partdesign_multi_transform",
    "partdesign_fillet",
    "partdesign_chamfer",
    "partdesign_draft",
    "partdesign_thickness",
    "partdesign_boolean",
    "partdesign_set_tip",
    "partdesign_find_subelements",
    "partdesign_measure",
    "part_find_subelements",
    "part_measure",
    "part_boolean",
    "part_extrude",
    "part_revolve",
    "part_mirror",
    "part_fillet",
    "part_chamfer",
    "assembly_list_structure",
    "assembly_create_assembly",
    "assembly_insert_component",
    "assembly_ground_component",
    "assembly_create_joint",
    "assembly_delete_joint",
    "assembly_solve",
)


def register_tools(registry: Any, service: Any) -> None:
    for module_name in TOOL_MODULE_NAMES:
        module = import_module(f"{__name__}.{module_name}")
        spec = module.TOOL_SPEC
        if bool(getattr(module, "RUNNER_HANDLED", False)):
            registry.register_spec(spec, None)
            continue
        module_run = getattr(module, "run", None)
        if not callable(module_run):
            raise ValueError(f"Cadex service tool module has no run(): {module_name}")

        def handler(_module=module, **kwargs):
            return _module.run(service, **kwargs)

        registry.register_spec(spec, handler)
