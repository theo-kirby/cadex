# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused native PartDesign Subtractive Pipe tool."""

from __future__ import annotations

from typing import Any

from . import partdesign_pipe_feature


TOOL_SPEC = {
    "name": "partdesign.subtractive_pipe",
    "description": (
        "Create one native subtractive pipe by sweeping a closed profile through an existing solid "
        "along an exact path in the same Body. Supports native orientation, transition, and "
        "multisection modes for channels, ports, manifolds, and curved passages."
    ),
    "contextual": True,
    "safety": "SAFE_WRITE",
    "workbench": "PartDesignWorkbench",
    "edit_modes": ["none"],
    "parameters": partdesign_pipe_feature.PARAMETERS,
}


def run(service: Any, **arguments: Any) -> dict[str, Any]:
    return partdesign_pipe_feature.run(
        service,
        operation="subtractive_pipe",
        type_id="PartDesign::SubtractivePipe",
        **arguments,
    )
