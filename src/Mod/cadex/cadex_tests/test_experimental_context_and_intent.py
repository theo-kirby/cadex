# SPDX-License-Identifier: LGPL-2.1-or-later

"""Track A regression coverage: cross-message context.

A1 threads the persisted transcript back into the provider so the model keeps
context across messages. These tests exercise the engine-agnostic seams that
carry that fix.
"""

from __future__ import annotations

import CadexSession as session
import CadexProvider as provider


class _ConversationService:
    """Minimal service implementing the off-thread conversation-read contract."""

    def __init__(self, conversation: list[dict]) -> None:
        self._conversation = conversation
        self.prepared_with: str | None = "unset"

    def prepare_conversation_read(self, conversation_id=None) -> dict:
        self.prepared_with = conversation_id
        return {"project_root": "/tmp/project", "conversation_id": conversation_id}

    def read_prepared_conversation(self, prepared: dict) -> list[dict]:
        assert prepared["project_root"] == "/tmp/project"
        return list(self._conversation)


def test_history_normalizer_keeps_prior_dependent_turn() -> None:
    """The second message resolves a pronoun referring to the first."""
    conversation = [
        {"role": "user", "content": "make a 20mm cube"},
        {"role": "assistant", "content": "Created a 20mm cube."},
        {"role": "user", "content": "make it 40"},
    ]
    history = session._conversation_history_for_provider(conversation, "make it 40")
    # The current message is dropped (re-sent separately); the prior pair stays.
    assert history == [
        {"role": "user", "content": "make a 20mm cube"},
        {"role": "assistant", "content": "Created a 20mm cube."},
    ]


def test_history_normalizer_enforces_alternation_and_ends_on_assistant() -> None:
    conversation = [
        {"role": "assistant", "content": "leading assistant is dropped"},
        {"role": "user", "content": "a"},
        {"role": "user", "content": "duplicate user is dropped"},
        {"role": "assistant", "content": "c"},
        {"role": "user", "content": "trailing user is dropped"},
    ]
    history = session._conversation_history_for_provider(conversation, "unrelated")
    assert [turn["role"] for turn in history] == ["user", "assistant"]
    assert history[0]["content"] == "a"
    assert history[-1]["content"] == "c"


def test_history_respects_turn_count_budget() -> None:
    conversation = []
    for index in range(session.MAX_HISTORY_TURNS * 2):
        conversation.append({"role": "user", "content": f"u{index}"})
        conversation.append({"role": "assistant", "content": f"a{index}"})
    history = session._conversation_history_for_provider(conversation, "current")
    assert len(history) <= session.MAX_HISTORY_TURNS


def test_load_conversation_history_scopes_to_turn_conversation_id() -> None:
    conversation = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
    ]
    service = _ConversationService(conversation)
    history = session._load_conversation_history_for_turn(
        service, "b" * 32, "current", None
    )
    assert service.prepared_with == "b" * 32
    assert history == conversation


def test_openai_provider_prepends_prior_turns() -> None:
    """A1: the OpenAI input carries prior user/assistant messages ahead of now."""
    context = {
        "conversation_history": [
            {"role": "user", "content": "make a 20mm cube"},
            {"role": "assistant", "content": "Created a 20mm cube."},
        ]
    }
    messages = provider._openai_history_input_messages(context)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"][0] == {
        "type": "input_text",
        "text": "make a 20mm cube",
    }
    assert messages[1]["content"][0] == {
        "type": "output_text",
        "text": "Created a 20mm cube.",
    }


def test_anthropic_history_turns_are_plain_text() -> None:
    context = {
        "conversation_history": [
            {"role": "user", "content": "cube"},
            {"role": "assistant", "content": "ok"},
        ]
    }
    turns = provider._conversation_history_turns(context)
    assert turns == [
        {"role": "user", "content": "cube"},
        {"role": "assistant", "content": "ok"},
    ]


def test_missing_history_yields_empty(monkeypatch) -> None:
    class _Bare:
        pass

    assert session._load_conversation_history_for_turn(_Bare(), None, "x", None) == []
    assert provider._openai_history_input_messages({}) == []
    assert provider._conversation_history_turns({}) == []


def test_budget_notice_level_is_debug_in_experimental_mode(monkeypatch) -> None:
    """A3: budget notices are demoted so the Report view stays quiet."""
    import logging

    monkeypatch.setattr(session, "_experimental_mode_session", lambda: True)
    assert session._budget_notice_level() == logging.DEBUG
    monkeypatch.setattr(session, "_experimental_mode_session", lambda: False)
    assert session._budget_notice_level() == logging.WARNING
