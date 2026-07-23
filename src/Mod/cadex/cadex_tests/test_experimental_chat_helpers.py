# SPDX-License-Identifier: LGPL-2.1-or-later

"""Pure single-pane chat helpers: question rendering and chat-reply answers."""

from __future__ import annotations

from CadexExperimentalChat import chat_reply_answers, question_round_markdown


FULL_QUESTIONS = [
    {
        "id": "q_thread",
        "question": "Which thread standard should the holes use?",
        "why_it_matters": "It changes the tap drill diameters.",
        "recommended_answer": "M5",
        "options": [
            {"label": "M5", "answer": "M5"},
            {"label": "1/4-20 UNC", "answer": "1/4-20 UNC"},
        ],
    },
    {
        "id": "q_depth",
        "question": "How deep should the pocket be?",
    },
]


def test_question_round_markdown_is_complete() -> None:
    text = question_round_markdown(FULL_QUESTIONS)
    assert "**1. Which thread standard should the holes use?**" in text
    assert "_It changes the tap drill diameters._" in text
    assert "- M5" in text
    assert "- 1/4-20 UNC" in text
    assert "Recommended: M5" in text
    assert "**2. How deep should the pocket be?**" in text
    assert text.endswith("Reply in the chat to answer.")


def test_question_round_markdown_degrades_gracefully() -> None:
    text = question_round_markdown(
        [
            {"question": "Only a question?"},
            {"not_a_question": True},
            "not a dict",
            {"question": "", "options": ["ignored"]},
        ]
    )
    assert "**1. Only a question?**" in text
    assert "**2." not in text
    assert "Recommended:" not in text
    assert "_ " not in text


def test_question_round_markdown_accepts_cleaned_and_string_options() -> None:
    text = question_round_markdown(
        [
            {
                "question": "Pick a size?",
                "why": "Affects fit.",
                "default_answer": "8 mm",
                "options": ["5 mm", "8 mm"],
            }
        ]
    )
    assert "_Affects fit._" in text
    assert "- 5 mm" in text
    assert "Recommended: 8 mm" in text


def test_question_round_markdown_empty_round_is_empty() -> None:
    assert question_round_markdown([]) == ""
    assert question_round_markdown(None) == ""
    assert question_round_markdown([{"question": ""}]) == ""


def test_chat_reply_answers_shape_and_id_preservation() -> None:
    answers = chat_reply_answers(FULL_QUESTIONS, "  Use M5, 10 mm deep.  ")
    assert answers == [
        {
            "id": "q_thread",
            "question": "Which thread standard should the holes use?",
            "answer": "Use M5, 10 mm deep.",
            "source": "chat_reply",
        },
        {
            "id": "q_depth",
            "question": "How deep should the pocket be?",
            "answer": "Use M5, 10 mm deep.",
            "source": "chat_reply",
        },
    ]


def test_chat_reply_answers_generates_missing_ids() -> None:
    answers = chat_reply_answers([{"question": "Anonymous?"}], "yes")
    assert answers == [
        {
            "id": "question_1",
            "question": "Anonymous?",
            "answer": "yes",
            "source": "chat_reply",
        }
    ]


def test_chat_reply_answers_empty_reply_is_empty() -> None:
    assert chat_reply_answers(FULL_QUESTIONS, "") == []
    assert chat_reply_answers(FULL_QUESTIONS, "   \n  ") == []
    assert chat_reply_answers([], "hello") == []
