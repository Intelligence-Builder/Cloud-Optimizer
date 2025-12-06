"""
Tests for intent definitions and intent-related functions.
"""

import pytest

from ib_platform.nlu.intents import (
    Intent,
    get_all_intent_examples,
    get_intent_description,
    get_intent_examples,
)


class TestIntentEnum:
    """Tests for Intent enum."""

    def test_intent_enum_values(self) -> None:
        """Test that all intent enum values are defined."""
        expected_intents = {
            "security_advice",
            "finding_explanation",
            "compliance_question",
            "document_analysis",
            "cost_optimization",
            "remediation_help",
            "general_question",
            "greeting",
            "out_of_scope",
        }

        actual_intents = {intent.value for intent in Intent}
        assert actual_intents == expected_intents

    def test_intent_enum_count(self) -> None:
        """Test that we have exactly 9 intent types."""
        assert len(Intent) == 9

    def test_intent_string_conversion(self) -> None:
        """Test that intents can be converted to/from strings."""
        intent = Intent.SECURITY_ADVICE
        assert intent.value == "security_advice"
        assert Intent(intent.value) == intent


class TestIntentExamples:
    """Tests for intent example functions."""

    def test_get_intent_examples_returns_list(self) -> None:
        """Test that get_intent_examples returns a list."""
        examples = get_intent_examples(Intent.SECURITY_ADVICE)
        assert isinstance(examples, list)
        assert len(examples) > 0

    def test_all_intents_have_examples(self) -> None:
        """Test that all intents have at least 3 examples."""
        for intent in Intent:
            examples = get_intent_examples(intent)
            assert (
                len(examples) >= 3
            ), f"{intent.value} has fewer than 3 examples: {len(examples)}"

    def test_security_advice_examples(self) -> None:
        """Test security advice intent examples."""
        examples = get_intent_examples(Intent.SECURITY_ADVICE)
        assert len(examples) >= 3

        # Check that examples contain relevant keywords
        combined = " ".join(examples).lower()
        assert any(
            keyword in combined
            for keyword in ["security", "secure", "protect", "best practices"]
        )

    def test_finding_explanation_examples(self) -> None:
        """Test finding explanation intent examples."""
        examples = get_intent_examples(Intent.FINDING_EXPLANATION)
        assert len(examples) >= 3

        # Check that examples reference findings
        combined = " ".join(examples).lower()
        assert any(keyword in combined for keyword in ["finding", "explain", "what"])

    def test_compliance_question_examples(self) -> None:
        """Test compliance question intent examples."""
        examples = get_intent_examples(Intent.COMPLIANCE_QUESTION)
        assert len(examples) >= 3

        # Check that examples mention compliance frameworks
        combined = " ".join(examples).lower()
        assert any(
            keyword in combined
            for keyword in ["soc2", "hipaa", "pci", "gdpr", "compliance"]
        )

    def test_document_analysis_examples(self) -> None:
        """Test document analysis intent examples."""
        examples = get_intent_examples(Intent.DOCUMENT_ANALYSIS)
        assert len(examples) >= 3

        # Check that examples mention document analysis
        combined = " ".join(examples).lower()
        assert any(keyword in combined for keyword in ["analyze", "review", "check"])

    def test_cost_optimization_examples(self) -> None:
        """Test cost optimization intent examples."""
        examples = get_intent_examples(Intent.COST_OPTIMIZATION)
        assert len(examples) >= 3

        # Check that examples mention costs
        combined = " ".join(examples).lower()
        assert any(keyword in combined for keyword in ["cost", "save", "expensive"])

    def test_remediation_help_examples(self) -> None:
        """Test remediation help intent examples."""
        examples = get_intent_examples(Intent.REMEDIATION_HELP)
        assert len(examples) >= 3

        # Check that examples mention fixing issues
        combined = " ".join(examples).lower()
        assert any(
            keyword in combined for keyword in ["fix", "remediate", "resolve", "help"]
        )

    def test_general_question_examples(self) -> None:
        """Test general question intent examples."""
        examples = get_intent_examples(Intent.GENERAL_QUESTION)
        assert len(examples) >= 3

        # Check that examples are about AWS services
        combined = " ".join(examples).lower()
        assert any(keyword in combined for keyword in ["what", "how", "aws"])

    def test_greeting_examples(self) -> None:
        """Test greeting intent examples."""
        examples = get_intent_examples(Intent.GREETING)
        assert len(examples) >= 3

        # Check that examples are greetings
        combined = " ".join(examples).lower()
        assert any(keyword in combined for keyword in ["hello", "hi", "hey", "good"])

    def test_out_of_scope_examples(self) -> None:
        """Test out of scope intent examples."""
        examples = get_intent_examples(Intent.OUT_OF_SCOPE)
        assert len(examples) >= 3

        # These should be clearly unrelated to AWS/cloud/security
        combined = " ".join(examples).lower()
        assert not any(keyword in combined for keyword in ["aws", "cloud", "security"])


class TestGetAllIntentExamples:
    """Tests for get_all_intent_examples function."""

    def test_returns_dict(self) -> None:
        """Test that get_all_intent_examples returns a dictionary."""
        examples = get_all_intent_examples()
        assert isinstance(examples, dict)

    def test_contains_all_intents(self) -> None:
        """Test that all intents are included."""
        examples = get_all_intent_examples()
        assert len(examples) == 9

        for intent in Intent:
            assert intent in examples

    def test_returns_copy(self) -> None:
        """Test that get_all_intent_examples returns a copy."""
        examples1 = get_all_intent_examples()
        examples2 = get_all_intent_examples()

        # Modifying one shouldn't affect the other
        examples1[Intent.GREETING] = []
        assert len(examples2[Intent.GREETING]) > 0


class TestGetIntentDescription:
    """Tests for get_intent_description function."""

    def test_returns_string(self) -> None:
        """Test that descriptions are strings."""
        for intent in Intent:
            description = get_intent_description(intent)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_all_intents_have_descriptions(self) -> None:
        """Test that all intents have descriptions."""
        for intent in Intent:
            description = get_intent_description(intent)
            assert description != "Unknown intent"

    def test_descriptions_are_meaningful(self) -> None:
        """Test that descriptions contain relevant keywords."""
        description = get_intent_description(Intent.SECURITY_ADVICE)
        assert (
            "security" in description.lower() or "recommendation" in description.lower()
        )

        description = get_intent_description(Intent.COMPLIANCE_QUESTION)
        assert "compliance" in description.lower() or "framework" in description.lower()

        description = get_intent_description(Intent.GREETING)
        assert "greet" in description.lower() or "conversation" in description.lower()
