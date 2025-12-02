"""
Tests for conversation context tracking.
"""

from datetime import datetime, timedelta

import pytest

from ib_platform.nlu.context import ConversationContext, Message
from ib_platform.nlu.intents import Intent


class TestMessage:
    """Tests for Message dataclass."""

    def test_create_user_message(self) -> None:
        """Test creating a user message."""
        msg = Message(
            content="How do I secure S3?",
            role="user",
            intent=Intent.SECURITY_ADVICE,
        )
        assert msg.content == "How do I secure S3?"
        assert msg.role == "user"
        assert msg.intent == Intent.SECURITY_ADVICE
        assert isinstance(msg.timestamp, datetime)

    def test_create_assistant_message(self) -> None:
        """Test creating an assistant message."""
        msg = Message(content="Here's how to secure S3...", role="assistant")
        assert msg.content == "Here's how to secure S3..."
        assert msg.role == "assistant"
        assert msg.intent is None

    def test_is_user_message(self) -> None:
        """Test is_user_message method."""
        user_msg = Message(content="test", role="user")
        assistant_msg = Message(content="test", role="assistant")

        assert user_msg.is_user_message()
        assert not assistant_msg.is_user_message()

    def test_is_assistant_message(self) -> None:
        """Test is_assistant_message method."""
        user_msg = Message(content="test", role="user")
        assistant_msg = Message(content="test", role="assistant")

        assert not user_msg.is_assistant_message()
        assert assistant_msg.is_assistant_message()

    def test_message_with_metadata(self) -> None:
        """Test message with metadata."""
        msg = Message(
            content="test",
            role="user",
            metadata={"confidence": 0.95, "custom_field": "value"},
        )
        assert msg.metadata["confidence"] == 0.95
        assert msg.metadata["custom_field"] == "value"


class TestConversationContext:
    """Tests for ConversationContext class."""

    def test_initialization(self, conversation_context: ConversationContext) -> None:
        """Test context initialization."""
        assert conversation_context.max_messages == 10
        assert len(conversation_context.messages) == 0
        assert conversation_context.session_id is None

    def test_custom_max_messages(self) -> None:
        """Test custom max_messages setting."""
        context = ConversationContext(max_messages=5)
        assert context.max_messages == 5

    def test_add_user_message(self, conversation_context: ConversationContext) -> None:
        """Test adding a user message."""
        conversation_context.add_message(
            content="How do I secure S3?",
            role="user",
            intent=Intent.SECURITY_ADVICE,
        )

        assert len(conversation_context.messages) == 1
        msg = conversation_context.messages[0]
        assert msg.content == "How do I secure S3?"
        assert msg.role == "user"
        assert msg.intent == Intent.SECURITY_ADVICE

    def test_add_assistant_message(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test adding an assistant message."""
        conversation_context.add_message(
            content="Here's how to secure S3...", role="assistant"
        )

        assert len(conversation_context.messages) == 1
        msg = conversation_context.messages[0]
        assert msg.role == "assistant"
        assert msg.intent is None

    def test_add_invalid_role_raises_error(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            conversation_context.add_message(content="test", role="invalid")

    def test_max_messages_limit(self) -> None:
        """Test that messages are trimmed to max_messages."""
        context = ConversationContext(max_messages=3)

        # Add 5 messages
        for i in range(5):
            context.add_message(content=f"Message {i}", role="user")

        # Should only keep last 3
        assert len(context.messages) == 3
        assert context.messages[0].content == "Message 2"
        assert context.messages[2].content == "Message 4"

    def test_get_last_user_message(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting last user message."""
        conversation_context.add_message(content="First user", role="user")
        conversation_context.add_message(content="Assistant reply", role="assistant")
        conversation_context.add_message(content="Second user", role="user")

        last_user = conversation_context.get_last_user_message()
        assert last_user is not None
        assert last_user.content == "Second user"

    def test_get_last_user_message_none(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test get_last_user_message with no user messages."""
        conversation_context.add_message(content="Assistant only", role="assistant")

        last_user = conversation_context.get_last_user_message()
        assert last_user is None

    def test_get_last_assistant_message(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting last assistant message."""
        conversation_context.add_message(content="User query", role="user")
        conversation_context.add_message(content="First reply", role="assistant")
        conversation_context.add_message(content="Another query", role="user")
        conversation_context.add_message(content="Second reply", role="assistant")

        last_assistant = conversation_context.get_last_assistant_message()
        assert last_assistant is not None
        assert last_assistant.content == "Second reply"

    def test_get_last_assistant_message_none(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test get_last_assistant_message with no assistant messages."""
        conversation_context.add_message(content="User only", role="user")

        last_assistant = conversation_context.get_last_assistant_message()
        assert last_assistant is None

    def test_get_recent_messages(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting recent messages."""
        for i in range(8):
            conversation_context.add_message(content=f"Message {i}", role="user")

        recent = conversation_context.get_recent_messages(3)
        assert len(recent) == 3
        assert recent[0].content == "Message 5"
        assert recent[2].content == "Message 7"

    def test_get_recent_messages_more_than_available(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting recent messages when fewer available."""
        conversation_context.add_message(content="Message 1", role="user")
        conversation_context.add_message(content="Message 2", role="user")

        recent = conversation_context.get_recent_messages(5)
        assert len(recent) == 2

    def test_get_conversation_summary_empty(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test conversation summary with empty history."""
        summary = conversation_context.get_conversation_summary()
        assert "No conversation history" in summary

    def test_get_conversation_summary(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test conversation summary with messages."""
        conversation_context.add_message(content="How do I secure S3?", role="user")
        conversation_context.add_message(
            content="Here are some best practices...", role="assistant"
        )

        summary = conversation_context.get_conversation_summary()
        assert "User:" in summary
        assert "Assistant:" in summary
        assert "secure S3" in summary

    def test_get_conversation_summary_truncates_long_messages(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test that summary truncates long messages."""
        long_message = "x" * 150
        conversation_context.add_message(content=long_message, role="user")

        summary = conversation_context.get_conversation_summary()
        assert "..." in summary
        assert len(summary) < len(long_message) + 50


class TestFollowUpDetection:
    """Tests for follow-up question detection."""

    def test_no_follow_up_first_message(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test that first message is not a follow-up."""
        is_follow_up = conversation_context.is_follow_up_question("How do I secure S3?")
        assert not is_follow_up

    def test_follow_up_with_this(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test follow-up detection with 'this'."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question(
            "What about this configuration?"
        )
        assert is_follow_up

    def test_follow_up_with_that(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test follow-up detection with 'that'."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question(
            "How do I fix that?"
        )
        assert is_follow_up

    def test_follow_up_with_it(self, conversation_context: ConversationContext) -> None:
        """Test follow-up detection with 'it'."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question("Can I disable it?")
        assert is_follow_up

    def test_follow_up_with_relative_reference(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test follow-up detection with relative references."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question(
            "How do I fix the finding?"
        )
        assert is_follow_up

    def test_follow_up_with_continuation_word(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test follow-up detection with continuation words."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question(
            "Also, what about encryption?"
        )
        assert is_follow_up

    def test_follow_up_very_short_query(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test follow-up detection for very short queries."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question("And EC2")
        assert is_follow_up

    def test_not_follow_up_complete_question(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test that complete standalone questions are not follow-ups."""
        conversation_context.add_message(content="First question", role="user")
        conversation_context.add_message(content="Response", role="assistant")

        is_follow_up = conversation_context.is_follow_up_question(
            "What are the best practices for securing Lambda functions?"
        )
        assert not is_follow_up


class TestContextForLLM:
    """Tests for LLM context formatting."""

    def test_empty_context(self, conversation_context: ConversationContext) -> None:
        """Test LLM context with no messages."""
        context = conversation_context.get_context_for_llm()
        assert context == ""

    def test_context_formatting(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test LLM context formatting."""
        conversation_context.add_message(content="How do I secure S3?", role="user")
        conversation_context.add_message(
            content="Use bucket policies and encryption", role="assistant"
        )
        conversation_context.add_message(content="What about IAM?", role="user")

        context = conversation_context.get_context_for_llm()
        assert "Previous conversation:" in context
        assert "User: How do I secure S3?" in context
        assert "Assistant: Use bucket policies" in context
        assert "User: What about IAM?" in context

    def test_context_limits_to_recent(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test that LLM context only includes recent messages."""
        # Add many messages
        for i in range(10):
            conversation_context.add_message(content=f"Message {i}", role="user")

        context = conversation_context.get_context_for_llm()
        # Should only include last 5 messages
        assert "Message 9" in context
        assert "Message 5" in context
        assert "Message 0" not in context


class TestClearAndCounts:
    """Tests for clearing context and counting messages."""

    def test_clear_context(self, conversation_context: ConversationContext) -> None:
        """Test clearing conversation context."""
        conversation_context.add_message(content="Test", role="user")
        conversation_context.session_id = "test-session"
        conversation_context.metadata = {"key": "value"}

        conversation_context.clear()

        assert len(conversation_context.messages) == 0
        assert conversation_context.session_id is None
        assert len(conversation_context.metadata) == 0

    def test_get_message_count(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting total message count."""
        assert conversation_context.get_message_count() == 0

        conversation_context.add_message(content="Test 1", role="user")
        assert conversation_context.get_message_count() == 1

        conversation_context.add_message(content="Test 2", role="assistant")
        assert conversation_context.get_message_count() == 2

    def test_get_user_message_count(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting user message count."""
        assert conversation_context.get_user_message_count() == 0

        conversation_context.add_message(content="User 1", role="user")
        conversation_context.add_message(content="Assistant 1", role="assistant")
        conversation_context.add_message(content="User 2", role="user")

        assert conversation_context.get_user_message_count() == 2

    def test_get_last_n_user_queries(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting last N user queries."""
        conversation_context.add_message(content="Query 1", role="user")
        conversation_context.add_message(content="Response 1", role="assistant")
        conversation_context.add_message(content="Query 2", role="user")
        conversation_context.add_message(content="Response 2", role="assistant")
        conversation_context.add_message(content="Query 3", role="user")

        queries = conversation_context.get_last_n_user_queries(2)
        assert len(queries) == 2
        assert queries[0] == "Query 2"
        assert queries[1] == "Query 3"

    def test_get_last_n_user_queries_more_than_available(
        self, conversation_context: ConversationContext
    ) -> None:
        """Test getting more queries than available."""
        conversation_context.add_message(content="Query 1", role="user")

        queries = conversation_context.get_last_n_user_queries(5)
        assert len(queries) == 1
        assert queries[0] == "Query 1"
