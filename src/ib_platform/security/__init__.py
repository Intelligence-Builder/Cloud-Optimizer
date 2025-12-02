"""Security Analysis Module for Intelligence-Builder Platform.

This module provides comprehensive security analysis capabilities including:
- Risk scoring and finding prioritization
- Finding explanation generation using LLM
- Remediation plan generation with code examples
- Finding correlation and clustering

Components:
    - RiskScorer: Score and prioritize security findings
    - FindingExplainer: Generate human-readable explanations
    - RemediationGenerator: Create step-by-step remediation plans
    - FindingCorrelator: Cluster and correlate related findings
    - SecurityAnalysisService: Unified facade for all security analysis
"""

from .correlation import FindingCluster, FindingCorrelator
from .explanation import FindingExplainer
from .remediation import RemediationGenerator, RemediationPlan, RemediationStep
from .scoring import PrioritizedFinding, RiskScorer
from .service import SecurityAnalysisService

__all__ = [
    "RiskScorer",
    "PrioritizedFinding",
    "FindingExplainer",
    "RemediationGenerator",
    "RemediationPlan",
    "RemediationStep",
    "FindingCorrelator",
    "FindingCluster",
    "SecurityAnalysisService",
]

__version__ = "1.0.0"
