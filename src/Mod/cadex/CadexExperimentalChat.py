# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure helpers for experimental mode's single-pane chat.

Experimental mode has no question panel: a model question round renders as one
chat message and the user's next chat reply answers every question in the
round. This module holds the text-shaping logic with no Qt or FreeCAD
imports so it stays unit-testable headlessly.
"""

from __future__ import annotations

from typing import Any


def _clean_questions(questions: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Normalize a question round; tolerates raw provider and cleaned shapes."""
    cleaned: list[dict[str, Any]] = []
    for item in questions or []:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        options: list[str] = []
        for option in item.get("options") or []:
            if isinstance(option, dict):
                label = str(option.get("label") or option.get("text") or "").strip()
                answer = str(option.get("answer") or option.get("value") or "").strip()
                label = label or answer
            else:
                label = str(option).strip()
            if label:
                options.append(label)
        cleaned.append(
            {
                "id": str(item.get("id") or f"question_{len(cleaned) + 1}"),
                "question": question,
                "why": str(item.get("why_it_matters") or item.get("why") or "").strip(),
                "recommended": str(
                    item.get("recommended_answer") or item.get("default_answer") or ""
                ).strip(),
                "options": options,
            }
        )
    return cleaned


def question_round_markdown(questions: list[dict[str, Any]] | None) -> str:
    """Render a question round as one chat message; "" when nothing to ask."""
    cleaned = _clean_questions(questions)
    if not cleaned:
        return ""
    parts: list[str] = ["I need your input before continuing:"]
    for index, question in enumerate(cleaned, start=1):
        lines = [f"**{index}. {question['question']}**"]
        if question["why"]:
            lines.append(f"_{question['why']}_")
        for option in question["options"]:
            lines.append(f"- {option}")
        if question["recommended"]:
            lines.append(f"Recommended: {question['recommended']}")
        parts.append("\n".join(lines))
    parts.append("Reply in the chat to answer.")
    return "\n\n".join(parts)


def chat_reply_answers(
    questions: list[dict[str, Any]] | None,
    reply: str,
) -> list[dict[str, Any]]:
    """Map one chat reply onto every question of the round; [] on empty reply."""
    clean_reply = str(reply or "").strip()
    if not clean_reply:
        return []
    return [
        {
            "id": question["id"],
            "question": question["question"],
            "answer": clean_reply,
            "source": "chat_reply",
        }
        for question in _clean_questions(questions)
    ]
