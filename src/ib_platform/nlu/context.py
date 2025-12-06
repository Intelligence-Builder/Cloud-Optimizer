"""
Conversation context tracking for Cloud Optimizer NLU.

Maintains conversation history and detects follow-up questions that require
context from previous messages.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from ib_platform.nlu.intents import Intent


@dataclass
class Message:
    """
    A single message in the conversation.

    Attributes:
        content: Message text
        role: Message role (user or assistant)
        intent: Intent of the message (for user messages)
        timestamp: When the message was created
        metadata: Additional metadata about the message
    """

    content: str
    role: str  # "user" or "assistant"
    intent: Optional[Intent] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def is_user_message(self) -> bool:
        """Check if this is a user message."""
        return self.role == "user"

    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message."""
        return self.role == "assistant"


class ConversationContext:
    """
    Tracks conversation context for follow-up question detection.

    Maintains a rolling window of the last N messages to provide context
    for intent classification and entity extraction.
    """

    def __init__(self, max_messages: int = 10) -> None:
        """
        Initialize conversation context.

        Args:
            max_messages: Maximum number of messages to keep in history (default: 10)
        """
        self.max_messages = max_messages
        self.messages: List[Message] = []
        self.session_id: Optional[str] = None
        self.metadata: dict = {}

    def add_message(
        self,
        content: str,
        role: str,
        intent: Optional[Intent] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Add a message to the conversation history.

        Args:
            content: Message text
            role: Message role ("user" or "assistant")
            intent: Intent of the message (for user messages)
            metadata: Additional metadata about the message
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        message = Message(
            content=content,
            role=role,
            intent=intent,
            metadata=metadata or {},
        )

        self.messages.append(message)

        # Trim history to max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def get_last_user_message(self) -> Optional[Message]:
        """
        Get the most recent user message.

        Returns:
            Last user message or None if no user messages exist
        """
        for message in reversed(self.messages):
            if message.is_user_message():
                return message
        return None

    def get_last_assistant_message(self) -> Optional[Message]:
        """
        Get the most recent assistant message.

        Returns:
            Last assistant message or None if no assistant messages exist
        """
        for message in reversed(self.messages):
            if message.is_assistant_message():
                return message
        return None

    def get_recent_messages(self, count: int = 5) -> List[Message]:
        """
        Get the N most recent messages.

        Args:
            count: Number of recent messages to return

        Returns:
            List of recent messages (newest last)
        """
        return self.messages[-count:]

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation for context.

        Returns:
            String summary of recent conversation
        """
        if not self.messages:
            return "No conversation history."

        recent = self.get_recent_messages(5)
        lines = []
        for msg in recent:
            role_prefix = "User" if msg.is_user_message() else "Assistant"
            content_preview = (
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            )
            lines.append(f"{role_prefix}: {content_preview}")

        return "\n".join(lines)

    def is_follow_up_question(self, query: str) -> bool:
        """
        Detect if the current query is a follow-up question.

        A query is likely a follow-up if it:
        - Uses pronouns (this, that, it, etc.)
        - Uses relative references (the finding, the bucket, etc.)
        - Is very short (suggesting it relies on context)
        - Uses continuation words (also, additionally, furthermore, etc.)

        Args:
            query: Current user query

        Returns:
            True if the query appears to be a follow-up question
        """
        if not self.messages or len(self.messages) < 2:
            return False

        query_lower = query.lower()

        # Check for pronoun references
        # Use word boundaries to catch pronouns at start, end, or middle of sentences
        pronouns = ["this", "that", "it", "its", "these", "those", "them"]
        for pronoun in pronouns:
            # Check if pronoun appears with word boundaries (start, middle, or end)
            if (
                query_lower.startswith(f"{pronoun} ")
                or query_lower.endswith(f" {pronoun}")
                or f" {pronoun} " in query_lower
                or f" {pronoun}?" in query_lower
            ):
                return True

        # Check for relative references
        relative_refs = [
            "the finding",
            "the bucket",
            "the instance",
            "the resource",
            "the issue",
            "the vulnerability",
            "the configuration",
            "the policy",
            "same",
        ]
        if any(ref in query_lower for ref in relative_refs):
            return True

        # Check for continuation words
        continuation_words = [
            "also",
            "additionally",
            "furthermore",
            "moreover",
            "besides",
            "what about",
            "how about",
        ]
        if any(query_lower.startswith(word) for word in continuation_words):
            return True

        # Very short queries often need context
        if len(query.split()) <= 3 and not query.endswith("?"):
            return True

        return False

    def get_context_for_llm(self) -> str:
        """
        Get formatted context for LLM prompt.

        Returns:
            Formatted conversation context for LLM
        """
        if not self.messages:
            return ""

        recent = self.get_recent_messages(5)
        lines = ["Previous conversation:"]
        for msg in recent:
            role_prefix = "User" if msg.is_user_message() else "Assistant"
            lines.append(f"{role_prefix}: {msg.content}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.session_id = None
        self.metadata = {}

    def get_message_count(self) -> int:
        """
        Get total number of messages in history.

        Returns:
            Number of messages
        """
        return len(self.messages)

    def get_user_message_count(self) -> int:
        """
        Get number of user messages in history.

        Returns:
            Number of user messages
        """
        return sum(1 for msg in self.messages if msg.is_user_message())

    def get_last_n_user_queries(self, n: int = 3) -> List[str]:
        """
        Get the last N user queries.

        Args:
            n: Number of queries to return

        Returns:
            List of recent user query texts
        """
        user_messages = [msg for msg in self.messages if msg.is_user_message()]
        return [msg.content for msg in user_messages[-n:]]
