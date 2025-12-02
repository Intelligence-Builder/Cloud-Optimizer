"""
Data models for Cloud Optimizer NLU.

Defines the core data structures for NLU results and entities.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ib_platform.nlu.intents import Intent


@dataclass
class NLUEntities:
    """
    Extracted entities from user query.

    Attributes:
        aws_services: List of AWS service names mentioned (e.g., ['S3', 'EC2', 'IAM'])
        compliance_frameworks: List of compliance frameworks mentioned (e.g., ['SOC2', 'HIPAA'])
        finding_ids: List of security finding identifiers (e.g., ['SEC-001', 'FND-12345'])
        resource_ids: List of AWS resource identifiers (ARNs, bucket names, instance IDs, etc.)
    """

    aws_services: List[str] = field(default_factory=list)
    compliance_frameworks: List[str] = field(default_factory=list)
    finding_ids: List[str] = field(default_factory=list)
    resource_ids: List[str] = field(default_factory=list)

    def has_entities(self) -> bool:
        """
        Check if any entities were extracted.

        Returns:
            True if at least one entity was found
        """
        return bool(
            self.aws_services
            or self.compliance_frameworks
            or self.finding_ids
            or self.resource_ids
        )

    def get_all_entities(self) -> List[str]:
        """
        Get all extracted entities as a flat list.

        Returns:
            Combined list of all entities
        """
        return (
            self.aws_services
            + self.compliance_frameworks
            + self.finding_ids
            + self.resource_ids
        )


@dataclass
class NLUResult:
    """
    Result of NLU processing for a user query.

    Attributes:
        query: Original user query
        intent: Classified intent
        confidence: Confidence score for intent classification (0.0 to 1.0)
        entities: Extracted entities from the query
        requires_findings: Whether the query requires access to security findings
        requires_documents: Whether the query requires document analysis
        context_aware: Whether this is a follow-up question requiring conversation context
        metadata: Additional metadata about the NLU processing
    """

    query: str
    intent: Intent
    confidence: float
    entities: NLUEntities = field(default_factory=NLUEntities)
    requires_findings: bool = False
    requires_documents: bool = False
    context_aware: bool = False
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate NLU result after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Set flags based on intent
        if self.intent == Intent.FINDING_EXPLANATION:
            self.requires_findings = True
        elif self.intent == Intent.DOCUMENT_ANALYSIS:
            self.requires_documents = True

    @property
    def is_high_confidence(self) -> bool:
        """
        Check if intent classification has high confidence.

        Returns:
            True if confidence >= 0.8
        """
        return self.confidence >= 0.8

    @property
    def is_low_confidence(self) -> bool:
        """
        Check if intent classification has low confidence.

        Returns:
            True if confidence < 0.5
        """
        return self.confidence < 0.5

    def to_dict(self) -> dict:
        """
        Convert NLU result to dictionary.

        Returns:
            Dictionary representation of the NLU result
        """
        return {
            "query": self.query,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": {
                "aws_services": self.entities.aws_services,
                "compliance_frameworks": self.entities.compliance_frameworks,
                "finding_ids": self.entities.finding_ids,
                "resource_ids": self.entities.resource_ids,
            },
            "requires_findings": self.requires_findings,
            "requires_documents": self.requires_documents,
            "context_aware": self.context_aware,
            "metadata": self.metadata,
        }
