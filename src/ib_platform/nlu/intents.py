"""
Intent definitions for Cloud Optimizer NLU.

Defines 9 intent types for the AWS security expert system chat interface.
"""

from enum import Enum
from typing import Dict, List


class Intent(str, Enum):
    """Intent types for user queries."""

    SECURITY_ADVICE = "security_advice"
    FINDING_EXPLANATION = "finding_explanation"
    COMPLIANCE_QUESTION = "compliance_question"
    DOCUMENT_ANALYSIS = "document_analysis"
    COST_OPTIMIZATION = "cost_optimization"
    REMEDIATION_HELP = "remediation_help"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"


# Intent examples for training and classification
INTENT_EXAMPLES: Dict[Intent, List[str]] = {
    Intent.SECURITY_ADVICE: [
        "What are the best practices for securing my S3 buckets?",
        "How can I improve my IAM security posture?",
        "What security controls should I implement for EC2 instances?",
        "How do I protect my RDS databases from unauthorized access?",
    ],
    Intent.FINDING_EXPLANATION: [
        "Why is finding SEC-001 marked as critical?",
        "Can you explain what this security finding means?",
        "What does the 'publicly accessible S3 bucket' finding indicate?",
        "Tell me more about finding FND-12345",
    ],
    Intent.COMPLIANCE_QUESTION: [
        "How do I achieve SOC2 compliance in AWS?",
        "What are the HIPAA requirements for storing PHI in the cloud?",
        "Does my current setup meet PCI-DSS standards?",
        "What GDPR controls do I need for EU data?",
    ],
    Intent.DOCUMENT_ANALYSIS: [
        "Can you analyze this CloudFormation template for security issues?",
        "Review this IAM policy document for vulnerabilities",
        "What security risks are in my terraform configuration?",
        "Check this security group configuration",
    ],
    Intent.COST_OPTIMIZATION: [
        "How can I reduce my AWS costs?",
        "What are the most expensive resources in my account?",
        "Suggest cost optimizations for my EC2 fleet",
        "How much can I save by using Reserved Instances?",
    ],
    Intent.REMEDIATION_HELP: [
        "How do I fix this security finding?",
        "What steps should I take to remediate SEC-001?",
        "Can you help me resolve this vulnerability?",
        "Walk me through fixing this compliance issue",
    ],
    Intent.GENERAL_QUESTION: [
        "What is AWS Config?",
        "How does AWS Security Hub work?",
        "What's the difference between KMS and CloudHSM?",
        "Explain AWS GuardDuty to me",
    ],
    Intent.GREETING: [
        "Hello",
        "Hi there",
        "Good morning",
        "Hey, can you help me?",
    ],
    Intent.OUT_OF_SCOPE: [
        "What's the weather like today?",
        "Can you book a flight for me?",
        "How do I cook pasta?",
        "Tell me a joke",
    ],
}


def get_intent_examples(intent: Intent) -> List[str]:
    """
    Get example queries for a specific intent.

    Args:
        intent: The intent type

    Returns:
        List of example queries for the intent
    """
    return INTENT_EXAMPLES.get(intent, [])


def get_all_intent_examples() -> Dict[Intent, List[str]]:
    """
    Get all intent examples for training.

    Returns:
        Dictionary mapping intents to their example queries
    """
    return INTENT_EXAMPLES.copy()


def get_intent_description(intent: Intent) -> str:
    """
    Get a human-readable description of an intent.

    Args:
        intent: The intent type

    Returns:
        Description of what the intent represents
    """
    descriptions = {
        Intent.SECURITY_ADVICE: "User is asking for security best practices or recommendations",
        Intent.FINDING_EXPLANATION: "User wants to understand a specific security finding",
        Intent.COMPLIANCE_QUESTION: "User is asking about compliance frameworks or requirements",
        Intent.DOCUMENT_ANALYSIS: "User wants to analyze a document or configuration for security issues",
        Intent.COST_OPTIMIZATION: "User is asking about reducing AWS costs",
        Intent.REMEDIATION_HELP: "User needs help fixing a security issue or vulnerability",
        Intent.GENERAL_QUESTION: "User has a general question about AWS services or concepts",
        Intent.GREETING: "User is greeting the system or starting a conversation",
        Intent.OUT_OF_SCOPE: "User's query is not related to AWS security or cloud optimization",
    }
    return descriptions.get(intent, "Unknown intent")
