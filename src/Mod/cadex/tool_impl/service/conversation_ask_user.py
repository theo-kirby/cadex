# SPDX-License-Identifier: LGPL-2.1-or-later

"""Interactive model-to-user question request."""

from __future__ import annotations

TOOL_SPEC = {
    "name": "conversation.ask_user",
    "description": (
        "Ask the user a compact round of design questions when their answer "
        "would materially change geometry, mechanism, fit, or manufacturing. "
        "Provide useful choices, your recommended answer, and a custom-answer "
        "path. This is not an approval gate and must not be used for choices "
        "you can resolve safely from engineering convention."
    ),
    "safety": "READ",
    "parameters": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "description": (
                    "One round of 1-8 material design questions, each with a "
                    "stable id, rationale, recommendation, and answer choices."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Stable short identifier for this question.",
                        },
                        "question": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "recommended_answer": {
                            "type": "string",
                            "description": "The model's recommended answer and default.",
                        },
                        "options": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "answer": {"type": "string"},
                                },
                                "required": ["label", "answer"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "id",
                        "question",
                        "why_it_matters",
                        "recommended_answer",
                        "options",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["questions"],
        "additionalProperties": False,
    },
}

RUNNER_HANDLED = True
