# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Additive Helix tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_helix_feature


TOOL_SPEC = {
    "name": "partdesign.additive_helix",
    "description": (
        "Create one native additive helix from a closed profile, explicit axis, and one named "
        "native helix definition. Use for springs, coils, auger flights, helical ribs, and modeled threads."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": partdesign_helix_feature.PARAMETERS,
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_helix_feature.run(
        service,
        operation="additive_helix",
        type_id="PartDesign::AdditiveHelix",
        **arguments,
    )
