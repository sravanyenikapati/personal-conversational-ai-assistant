"""
Tests for conversation history management.
These are pure unit tests — no API calls, no audio.
"""

from assistant.core.conversation import ConversationHistory, Role

SYSTEM_PROMPT = "You are a helpful assistant."


class TestConversationHistory:
    def test_initial_state(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        assert len(history) == 0

    def test_add_user_message(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("Hello!")
        assert len(history) == 1

    def test_add_assistant_message(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("Hi")
        history.add_assistant_message("Hello there!")
        assert len(history) == 2

    def test_get_messages_includes_system(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("Hello")
        messages = history.get_messages(include_system=True)
        assert messages[0]["role"] == Role.SYSTEM
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert len(messages) == 2  # system + user

    def test_get_messages_excludes_system(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("Hello")
        messages = history.get_messages(include_system=False)
        assert all(m["role"] != Role.SYSTEM for m in messages)
        assert len(messages) == 1

    def test_clear_resets_messages(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("Hello")
        history.add_assistant_message("Hi!")
        history.clear()
        assert len(history) == 0

    def test_rolling_window_trims_old_messages(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT, max_messages=4)
        for i in range(6):
            history.add_user_message(f"Message {i}")
            history.add_assistant_message(f"Reply {i}")
        # max_messages=4 means only 4 messages kept
        assert len(history) <= 4

    def test_message_order_preserved(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        history.add_user_message("First")
        history.add_assistant_message("Second")
        history.add_user_message("Third")
        messages = history.get_messages(include_system=False)
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    def test_repr_contains_useful_info(self):
        history = ConversationHistory(system_prompt=SYSTEM_PROMPT)
        r = repr(history)
        assert "messages=" in r
        assert "max=" in r
