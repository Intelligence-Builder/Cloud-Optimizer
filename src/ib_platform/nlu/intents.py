"""
Intent definitions for Cloud Optimizer NLU.

Defines 9 intent types for the AWS security expert system chat interface.
"""

from enum import Enum
from typing import Dict, List


class Intent(str, Enum):
    """Intent types for user queries handled by the expert system."""

    SECURITY_ADVICE = "security_advice"
    FINDING_EXPLANATION = "finding_explanation"
    COMPLIANCE_QUESTION = "compliance_question"
    DOCUMENT_ANALYSIS = "document_analysis"
    COST_OPTIMIZATION = "cost_optimization"
    REMEDIATION_HELP = "remediation_help"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    OUT_OF_SCOPE = "out_of_scope"


INTENT_DESCRIPTIONS: Dict[Intent, str] = {
    Intent.SECURITY_ADVICE: "User is asking for AWS security recommendations or best practices.",
    Intent.FINDING_EXPLANATION: "User wants an explanation of a scanner/security finding.",
    Intent.COMPLIANCE_QUESTION: "User is mapping controls to frameworks like HIPAA, SOC 2, PCI, or CIS.",
    Intent.DOCUMENT_ANALYSIS: "User needs an uploaded architecture or policy document analyzed for risk.",
    Intent.COST_OPTIMIZATION: "User is looking for AWS cost savings opportunities or forecasting.",
    Intent.REMEDIATION_HELP: "User needs concrete remediation steps or code to fix a finding.",
    Intent.GENERAL_QUESTION: "User has a general AWS/cloud security question not tied to a specific finding.",
    Intent.GREETING: "Conversation openers such as hello, hi, or good morning.",
    Intent.OUT_OF_SCOPE: "Requests unrelated to AWS, cloud, or security topics.",
}

# Intent examples for training and classification
INTENT_EXAMPLES: Dict[Intent, List[str]] = {
    Intent.SECURITY_ADVICE: [
        "What security concerns should I have with S3 to Glue to Redshift?",
        "How should I secure my API Gateway before it calls Lambda?",
        "Is my Redshift cluster configured securely by default?",
        "What security controls should I enable on S3 buckets used for analytics?",
    ],
    Intent.FINDING_EXPLANATION: [
        "Explain this finding about public S3 buckets.",
        "What does the IAM_002 finding mean?",
        "Why is SEC-001 marked as critical?",
        "Can you break down why this finding flagged my CloudTrail logs?",
    ],
    Intent.COMPLIANCE_QUESTION: [
        "What do I need for HIPAA compliance?",
        "How does this finding relate to SOC 2?",
        "Is this configuration a PCI-DSS violation?",
        "Which CIS controls cover this AWS Config rule?",
    ],
    Intent.DOCUMENT_ANALYSIS: [
        "Review this architecture PDF and tell me the security gaps.",
        "What security issues do you see in this VPC diagram?",
        "Analyze this IAM policy document for risk.",
        "Can you inspect my Terraform plan for vulnerabilities?",
    ],
    Intent.COST_OPTIMIZATION: [
        "How can I reduce my AWS costs this quarter?",
        "Are there unused EC2 instances I can shut down?",
        "Should I migrate this workload to reserved instances?",
        "Do I have idle RDS clusters burning money?",
    ],
    Intent.REMEDIATION_HELP: [
        "How do I fix SEC-001 in my account?",
        "Show me the Terraform to remediate this S3 bucket finding.",
        "What steps fix this IAM_002 critical issue?",
        "Walk me through resolving this GuardDuty alert.",
    ],
    Intent.GENERAL_QUESTION: [
        "What is AWS Config and when should I use it?",
        "How does AWS Security Hub aggregate findings?",
        "Explain AWS GuardDuty to me.",
        "What's the difference between KMS and CloudHSM?",
    ],
    Intent.GREETING: [
        "Hello there!",
        "Hi, can you help me?",
        "Good morning Cloud Optimizer.",
        "Hey team!",
    ],
    Intent.OUT_OF_SCOPE: [
        "What's the weather like in Seattle?",
        "Can you book a flight for me?",
        "How do I bake sourdough bread?",
        "Tell me a joke about penguins.",
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
    return INTENT_DESCRIPTIONS.get(intent, "Unknown intent")
