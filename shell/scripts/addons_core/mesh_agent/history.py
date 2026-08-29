# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Chat transcript, mirrored into ``bpy.data.texts`` so it saves with the .blend
file and survives the Simple/Pro mode toggle.

The .blend is where a conversation lives (cadex ADR-020, decision 4): the
transcript *and* the Claude Code ``session_id`` that lets a later turn
resume it. The conversation is shell state -- the engine has no notion of
a turn -- and one file the user can move, copy and mail is worth more than
a second store beside it.
"""

import json

TEXT_BLOCK_NAME = "mesh_chat.json"
SCHEMA = "mesh-chat-v1"

# Roles: "user", "assistant", "status" (tool activity / notices, greyed out).


class ChatMessage:
    __slots__ = ("role", "text")

    def __init__(self, role, text=""):
        self.role = role
        self.text = text


class ChatHistory:
    def __init__(self):
        self.messages = []
        self._streaming = None  # message receiving streamed text
        #: Claude Code session to resume, or "" for a fresh conversation.
        #: Saved with the transcript, because it belongs to this .blend's
        #: conversation and to no other.
        self.session_id = ""

    def add(self, role, text):
        self.messages.append(ChatMessage(role, text))

    def begin_assistant(self):
        self._streaming = ChatMessage("assistant", "")
        self.messages.append(self._streaming)

    def append_stream(self, text):
        if self._streaming is None:
            self.begin_assistant()
        self._streaming.text += text

    def end_assistant(self):
        # Drop the placeholder if nothing was streamed.
        if self._streaming is not None and not self._streaming.text:
            try:
                self.messages.remove(self._streaming)
            except ValueError:
                pass
        self._streaming = None

    def clear(self):
        self.messages = []
        self._streaming = None
        self.session_id = ""

    def to_json(self):
        return json.dumps(
            {
                "schema": SCHEMA,
                "session_id": self.session_id,
                "messages": [{"role": message.role, "text": message.text}
                             for message in self.messages],
            },
            ensure_ascii=False, indent=1)

    def from_json(self, text):
        self.clear()
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return
        if isinstance(data, dict):
            self.session_id = str(data.get("session_id") or "")
            items = data.get("messages") or []
        else:
            # Transcripts written before the session id was carried.
            items = data
        for item in items:
            if isinstance(item, dict) and "role" in item:
                self.add(item["role"], item.get("text", ""))

    def save_to_text_block(self):
        import bpy
        text_block = bpy.data.texts.get(TEXT_BLOCK_NAME)
        if text_block is None:
            text_block = bpy.data.texts.new(TEXT_BLOCK_NAME)
        text_block.clear()
        text_block.write(self.to_json())
        # Keep the transcript when the text datablock is otherwise unused.
        text_block.use_fake_user = True

    def load_from_text_block(self):
        import bpy
        text_block = bpy.data.texts.get(TEXT_BLOCK_NAME)
        if text_block is not None:
            self.from_json(text_block.as_string())
        else:
            self.clear()
