"""
Tests for NLU service.
"""

import json
from unittest.mock import Mock

import pytest

from ib_platform.nlu.intents import Intent
from ib_platform.nlu.models import NLUResult
from ib_platform.nlu.service import NLUService


class TestNLUServiceInitialization:
    """Tests for NLU service initialization."""

    def test_initialization_with_settings(
        self, nlu_service: NLUService, mock_settings
    ) -> None:
        """Test service initialization with settings."""
        assert nlu_service.settings == mock_settings
        assert nlu_service.entity_extractor is not None
        assert nlu_service.context is not None

    def test_initialization_without_api_key_raises_error(self, mock_settings) -> None:
        """Test that missing API key raises error."""
        mock_settings.anthropic_api_key = None

        with pytest.raises(ValueError, match="Anthropic API key not configured"):
            NLUService(settings=mock_settings)

    def test_uses_claude_model(self, nlu_service: NLUService) -> None:
        """Test that service uses correct Claude model."""
        assert "claude" in nlu_service.model.lower()


class TestProcessQuery:
    """Tests for process_query method."""

    @pytest.mark.asyncio
    async def test_process_query_returns_nlu_result(
        self, nlu_service: NLUService
    ) -> None:
        """Test that process_query returns NLUResult."""
        result = await nlu_service.process_query("How do I secure S3?")
        assert isinstance(result, NLUResult)

    @pytest.mark.asyncio
    async def test_process_query_extracts_entities(
        self, nlu_service: NLUService
    ) -> None:
        """Test that entities are extracted from query."""
        result = await nlu_service.process_query(
            "How do I fix SEC-001 for my S3 bucket to meet HIPAA compliance?"
        )

        assert "S3" in result.entities.aws_services
        assert "HIPAA" in result.entities.compliance_frameworks
        assert "SEC-001" in result.entities.finding_ids

    @pytest.mark.asyncio
    async def test_process_query_adds_to_context(self, nlu_service: NLUService) -> None:
        """Test that query is added to conversation context."""
        query = "How do I secure S3?"
        await nlu_service.process_query(query)

        assert nlu_service.context.get_message_count() == 1
        last_msg = nlu_service.context.get_last_user_message()
        assert last_msg is not None
        assert last_msg.content == query

    @pytest.mark.asyncio
    async def test_process_query_detects_follow_up(
        self, nlu_service: NLUService
    ) -> None:
        """Test that follow-up questions are detected."""
        # Add initial context
        await nlu_service.process_query("What are S3 security best practices?")
        nlu_service.add_assistant_response("Here are the best practices...")

        # Ask follow-up
        result = await nlu_service.process_query("What about this configuration?")

        assert result.context_aware is True
        assert result.metadata["is_follow_up"] is True

    @pytest.mark.asyncio
    async def test_process_query_metadata(self, nlu_service: NLUService) -> None:
        """Test that result includes metadata."""
        result = await nlu_service.process_query("How do I secure S3?")

        assert "conversation_length" in result.metadata
        assert "is_follow_up" in result.metadata
        assert result.metadata["conversation_length"] == 1


class TestIntentClassification:
    """Tests for intent classification."""

    @pytest.mark.asyncio
    async def test_classify_security_advice(self, nlu_service: NLUService) -> None:
        """Test classification of security advice query."""
        # Mock response for security advice
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "security_advice", "confidence": 0.92}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query(
            "What are the best practices for securing S3?"
        )

        assert result.intent == Intent.SECURITY_ADVICE
        assert result.confidence > 0.8

    @pytest.mark.asyncio
    async def test_classify_finding_explanation(self, nlu_service: NLUService) -> None:
        """Test classification of finding explanation query."""
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "finding_explanation", "confidence": 0.95}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query("What is finding SEC-001?")

        assert result.intent == Intent.FINDING_EXPLANATION
        assert result.requires_findings is True

    @pytest.mark.asyncio
    async def test_classify_compliance_question(self, nlu_service: NLUService) -> None:
        """Test classification of compliance query."""
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "compliance_question", "confidence": 0.88}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query("How do I achieve HIPAA compliance?")

        assert result.intent == Intent.COMPLIANCE_QUESTION

    @pytest.mark.asyncio
    async def test_classify_document_analysis(self, nlu_service: NLUService) -> None:
        """Test classification of document analysis query."""
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "document_analysis", "confidence": 0.90}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query(
            "Can you review this IAM policy for vulnerabilities?"
        )

        assert result.intent == Intent.DOCUMENT_ANALYSIS
        assert result.requires_documents is True

    @pytest.mark.asyncio
    async def test_classify_greeting(self, nlu_service: NLUService) -> None:
        """Test classification of greeting."""
        mock_content = Mock()
        mock_content.text = json.dumps({"intent": "greeting", "confidence": 0.99})
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query("Hello!")

        assert result.intent == Intent.GREETING

    @pytest.mark.asyncio
    async def test_classify_out_of_scope(self, nlu_service: NLUService) -> None:
        """Test classification of out-of-scope query."""
        mock_content = Mock()
        mock_content.text = json.dumps({"intent": "out_of_scope", "confidence": 0.85})
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query("What's the weather like?")

        assert result.intent == Intent.OUT_OF_SCOPE

    @pytest.mark.asyncio
    async def test_classification_fallback_on_error(
        self, nlu_service: NLUService
    ) -> None:
        """Test that classification falls back on API error."""
        # Mock API error
        nlu_service.client.messages.create.side_effect = Exception("API Error")

        result = await nlu_service.process_query("Some query")

        # Should fall back to GENERAL_QUESTION with low confidence
        assert result.intent == Intent.GENERAL_QUESTION
        assert result.confidence < 0.5


class TestParseClassificationResponse:
    """Tests for parsing classification responses."""

    def test_parse_valid_json(self, nlu_service: NLUService) -> None:
        """Test parsing valid JSON response."""
        response = '{"intent": "security_advice", "confidence": 0.92}'
        intent, confidence = nlu_service._parse_classification_response(response)

        assert intent == Intent.SECURITY_ADVICE
        assert confidence == 0.92

    def test_parse_invalid_json(self, nlu_service: NLUService) -> None:
        """Test parsing invalid JSON."""
        response = "Not valid JSON"
        intent, confidence = nlu_service._parse_classification_response(response)

        # Should fall back to defaults
        assert intent == Intent.GENERAL_QUESTION
        assert confidence == 0.3

    def test_parse_unknown_intent(self, nlu_service: NLUService) -> None:
        """Test parsing with unknown intent."""
        response = '{"intent": "unknown_intent", "confidence": 0.95}'
        intent, confidence = nlu_service._parse_classification_response(response)

        # Should fall back to GENERAL_QUESTION
        assert intent == Intent.GENERAL_QUESTION
        assert confidence == 0.3

    def test_parse_confidence_bounds(self, nlu_service: NLUService) -> None:
        """Test that confidence is bounded between 0 and 1."""
        # Test confidence > 1
        response = '{"intent": "greeting", "confidence": 1.5}'
        intent, confidence = nlu_service._parse_classification_response(response)
        assert confidence == 1.0

        # Test confidence < 0
        response = '{"intent": "greeting", "confidence": -0.5}'
        intent, confidence = nlu_service._parse_classification_response(response)
        assert confidence == 0.0


class TestBuildClassificationPrompt:
    """Tests for building classification prompts."""

    def test_prompt_includes_query(self, nlu_service: NLUService) -> None:
        """Test that prompt includes the user query."""
        query = "How do I secure S3?"
        prompt = nlu_service._build_classification_prompt(query, False)

        assert query in prompt

    def test_prompt_includes_intent_examples(self, nlu_service: NLUService) -> None:
        """Test that prompt includes intent examples."""
        prompt = nlu_service._build_classification_prompt("test", False)

        # Should include all intent types
        assert "security_advice" in prompt.lower()
        assert "finding_explanation" in prompt.lower()
        assert "compliance_question" in prompt.lower()

    def test_prompt_includes_context_for_follow_up(
        self, nlu_service: NLUService
    ) -> None:
        """Test that prompt includes context for follow-up questions."""
        nlu_service.context.add_message(content="First question", role="user")
        nlu_service.context.add_message(content="Response", role="assistant")

        prompt = nlu_service._build_classification_prompt("Follow-up", True)

        assert "CONVERSATION CONTEXT" in prompt
        assert "First question" in prompt


class TestAssistantResponse:
    """Tests for adding assistant responses."""

    def test_add_assistant_response(self, nlu_service: NLUService) -> None:
        """Test adding assistant response to context."""
        response = "Here are the best practices for securing S3..."
        nlu_service.add_assistant_response(response)

        assert nlu_service.context.get_message_count() == 1
        last_msg = nlu_service.context.get_last_assistant_message()
        assert last_msg is not None
        assert last_msg.content == response


class TestContextManagement:
    """Tests for context management methods."""

    def test_get_conversation_context(self, nlu_service: NLUService) -> None:
        """Test getting conversation context."""
        context = nlu_service.get_conversation_context()
        assert context == nlu_service.context

    def test_clear_context(self, nlu_service: NLUService) -> None:
        """Test clearing context."""
        nlu_service.context.add_message(content="Test", role="user")
        assert nlu_service.context.get_message_count() > 0

        nlu_service.clear_context()
        assert nlu_service.context.get_message_count() == 0

    def test_get_context_summary(self, nlu_service: NLUService) -> None:
        """Test getting context summary."""
        nlu_service.context.add_message(content="How do I secure S3?", role="user")
        nlu_service.context.add_message(
            content="Here are some tips...", role="assistant"
        )

        summary = nlu_service.get_context_summary()
        assert "User:" in summary
        assert "Assistant:" in summary


class TestNLUResultProperties:
    """Tests for NLUResult properties and methods."""

    def test_is_high_confidence(self) -> None:
        """Test is_high_confidence property."""
        result = NLUResult(
            query="test",
            intent=Intent.GREETING,
            confidence=0.85,
        )
        assert result.is_high_confidence

        result.confidence = 0.75
        assert not result.is_high_confidence

    def test_is_low_confidence(self) -> None:
        """Test is_low_confidence property."""
        result = NLUResult(
            query="test",
            intent=Intent.GENERAL_QUESTION,
            confidence=0.4,
        )
        assert result.is_low_confidence

        result.confidence = 0.6
        assert not result.is_low_confidence

    def test_to_dict(self) -> None:
        """Test converting NLUResult to dictionary."""
        result = NLUResult(
            query="How do I secure S3?",
            intent=Intent.SECURITY_ADVICE,
            confidence=0.92,
        )
        result.entities.aws_services = ["S3"]

        result_dict = result.to_dict()

        assert result_dict["query"] == "How do I secure S3?"
        assert result_dict["intent"] == "security_advice"
        assert result_dict["confidence"] == 0.92
        assert result_dict["entities"]["aws_services"] == ["S3"]

    def test_requires_findings_set_for_finding_explanation(self) -> None:
        """Test that requires_findings is set for FINDING_EXPLANATION."""
        result = NLUResult(
            query="What is SEC-001?",
            intent=Intent.FINDING_EXPLANATION,
            confidence=0.9,
        )
        assert result.requires_findings is True

    def test_requires_documents_set_for_document_analysis(self) -> None:
        """Test that requires_documents is set for DOCUMENT_ANALYSIS."""
        result = NLUResult(
            query="Analyze this policy",
            intent=Intent.DOCUMENT_ANALYSIS,
            confidence=0.9,
        )
        assert result.requires_documents is True

    def test_confidence_validation(self) -> None:
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            NLUResult(
                query="test",
                intent=Intent.GREETING,
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="Confidence must be between"):
            NLUResult(
                query="test",
                intent=Intent.GREETING,
                confidence=-0.1,
            )


class TestIntegrationScenarios:
    """Integration tests for complete NLU scenarios."""

    @pytest.mark.asyncio
    async def test_complete_security_query_flow(self, nlu_service: NLUService) -> None:
        """Test complete flow for security query."""
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "security_advice", "confidence": 0.92}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        result = await nlu_service.process_query(
            "What are the best practices for securing my S3 buckets?"
        )

        # Check intent
        assert result.intent == Intent.SECURITY_ADVICE
        assert result.confidence > 0.8

        # Check entities
        assert "S3" in result.entities.aws_services

        # Check context
        assert nlu_service.context.get_message_count() == 1

    @pytest.mark.asyncio
    async def test_complete_follow_up_flow(self, nlu_service: NLUService) -> None:
        """Test complete flow with follow-up question."""
        # Set up mock for first query
        mock_content = Mock()
        mock_content.text = json.dumps(
            {"intent": "security_advice", "confidence": 0.90}
        )
        mock_response = Mock()
        mock_response.content = [mock_content]
        nlu_service.client.messages.create.return_value = mock_response

        # First query
        result1 = await nlu_service.process_query("How do I secure S3?")
        assert not result1.context_aware

        # Add assistant response
        nlu_service.add_assistant_response("Here are the best practices...")

        # Follow-up query
        result2 = await nlu_service.process_query("What about this for EC2?")
        assert result2.context_aware
        assert nlu_service.context.get_message_count() == 3  # 2 user + 1 assistant
