"""
NLU Service for Cloud Optimizer chat interface.

Provides intent classification using Claude LLM and entity extraction
with conversation context tracking.
"""

import json
from typing import Optional

import anthropic
import structlog

from cloud_optimizer.config import Settings, get_settings
from ib_platform.nlu.context import ConversationContext
from ib_platform.nlu.entities import EntityExtractor
from ib_platform.nlu.intents import Intent, get_all_intent_examples
from ib_platform.nlu.models import NLUResult

logger = structlog.get_logger(__name__)


class NLUService:
    """
    Natural Language Understanding service for Cloud Optimizer.

    Provides:
    - Intent classification using Claude LLM
    - Entity extraction (AWS services, compliance frameworks, etc.)
    - Conversation context tracking
    - Follow-up question detection
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        anthropic_client: Optional[anthropic.Anthropic] = None,
    ) -> None:
        """
        Initialize NLU service.

        Args:
            settings: Application settings (uses get_settings() if not provided)
            anthropic_client: Anthropic client (creates new one if not provided)
        """
        self.settings = settings or get_settings()
        self.entity_extractor = EntityExtractor()
        self.context = ConversationContext()

        # Initialize Anthropic client
        if anthropic_client:
            self.client = anthropic_client
        else:
            if not self.settings.anthropic_api_key:
                raise ValueError(
                    "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable."
                )
            self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

        # Claude model to use
        self.model = "claude-3-5-sonnet-20241022"

    async def process_query(self, query: str) -> NLUResult:
        """
        Process a user query with full NLU pipeline.

        Args:
            query: User query text

        Returns:
            NLUResult with intent, entities, and metadata
        """
        logger.info("Processing NLU query", query_length=len(query))

        # Detect if this is a follow-up question
        is_follow_up = self.context.is_follow_up_question(query)

        # Classify intent
        intent, confidence = await self._classify_intent(query, is_follow_up)

        # Extract entities
        entities = self.entity_extractor.extract(query)

        # Add to conversation context
        self.context.add_message(
            content=query,
            role="user",
            intent=intent,
            metadata={"confidence": confidence},
        )

        # Create NLU result (after adding message to get correct count)
        result = NLUResult(
            query=query,
            intent=intent,
            confidence=confidence,
            entities=entities,
            context_aware=is_follow_up,
            metadata={
                "conversation_length": self.context.get_message_count(),
                "is_follow_up": is_follow_up,
            },
        )

        logger.info(
            "NLU processing complete",
            intent=intent.value,
            confidence=confidence,
            entity_count=len(entities.get_all_entities()),
            is_follow_up=is_follow_up,
        )

        return result

    async def _classify_intent(
        self, query: str, is_follow_up: bool
    ) -> tuple[Intent, float]:
        """
        Classify user query intent using Claude.

        Args:
            query: User query text
            is_follow_up: Whether this is a follow-up question

        Returns:
            Tuple of (intent, confidence_score)
        """
        try:
            # Build prompt with intent examples and conversation context
            prompt = self._build_classification_prompt(query, is_follow_up)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            response_text = response.content[0].text.strip()
            intent, confidence = self._parse_classification_response(response_text)

            return intent, confidence

        except Exception as e:
            logger.error("Intent classification failed", error=str(e))
            # Fallback to GENERAL_QUESTION with low confidence
            return Intent.GENERAL_QUESTION, 0.3

    def _build_classification_prompt(self, query: str, is_follow_up: bool) -> str:
        """
        Build prompt for intent classification.

        Args:
            query: User query text
            is_follow_up: Whether this is a follow-up question

        Returns:
            Formatted prompt for Claude
        """
        # Get intent examples
        examples = get_all_intent_examples()

        # Build examples section
        examples_text = []
        for intent, example_queries in examples.items():
            examples_text.append(f"\n{intent.value.upper()}:")
            for example in example_queries[:3]:  # Use first 3 examples
                examples_text.append(f"  - {example}")

        examples_section = "\n".join(examples_text)

        # Build context section
        context_section = ""
        if is_follow_up and self.context.get_message_count() > 0:
            context_section = f"""
CONVERSATION CONTEXT:
{self.context.get_context_for_llm()}

Note: This appears to be a follow-up question. Consider the conversation context.
"""

        prompt = f"""You are an intent classifier for an AWS security expert system.

Your task is to classify the user's query into one of these intents:

{examples_section}

{context_section}

USER QUERY: {query}

Respond with ONLY a JSON object in this exact format:
{{
  "intent": "intent_name",
  "confidence": 0.95
}}

The intent must be one of: security_advice, finding_explanation, compliance_question, document_analysis, cost_optimization, remediation_help, general_question, greeting, out_of_scope

Confidence should be a number between 0.0 and 1.0.
"""

        return prompt

    def _parse_classification_response(self, response: str) -> tuple[Intent, float]:
        """
        Parse Claude's classification response.

        Args:
            response: Raw response from Claude

        Returns:
            Tuple of (intent, confidence)
        """
        try:
            # Try to parse as JSON
            data = json.loads(response)
            intent_str = data.get("intent", "general_question")
            confidence = float(data.get("confidence", 0.5))

            # Map string to Intent enum
            try:
                intent = Intent(intent_str)
            except ValueError:
                logger.warning("Unknown intent returned", intent_str=intent_str)
                intent = Intent.GENERAL_QUESTION
                confidence = 0.3

            # Validate confidence
            confidence = max(0.0, min(1.0, confidence))

            return intent, confidence

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to parse classification response", error=str(e))
            return Intent.GENERAL_QUESTION, 0.3

    def add_assistant_response(self, response: str) -> None:
        """
        Add assistant response to conversation context.

        Args:
            response: Assistant response text
        """
        self.context.add_message(content=response, role="assistant")

    def get_conversation_context(self) -> ConversationContext:
        """
        Get the current conversation context.

        Returns:
            ConversationContext instance
        """
        return self.context

    def clear_context(self) -> None:
        """Clear conversation history."""
        self.context.clear()
        logger.info("Conversation context cleared")

    def get_context_summary(self) -> str:
        """
        Get a summary of the current conversation context.

        Returns:
            String summary of conversation
        """
        return self.context.get_conversation_summary()
