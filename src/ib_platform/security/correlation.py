"""Finding correlation and clustering module.

This module identifies relationships between security findings and groups
related findings into clusters for better analysis and remediation planning.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from cloud_optimizer.models.finding import Finding

logger = logging.getLogger(__name__)


@dataclass
class FindingCluster:
    """A cluster of related security findings.

    Attributes:
        cluster_id: Unique cluster identifier
        title: Descriptive title for the cluster
        findings: List of findings in this cluster
        common_attributes: Attributes shared by all findings
        severity: Highest severity in the cluster
        affected_resources: Count of affected resources
        correlation_score: Strength of correlation (0-1)
        recommended_action: Suggested remediation approach
    """

    cluster_id: str
    title: str
    findings: List[Finding] = field(default_factory=list)
    common_attributes: Dict[str, Any] = field(default_factory=dict)
    severity: str = "low"
    affected_resources: int = 0
    correlation_score: float = 0.0
    recommended_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with cluster details
        """
        return {
            "cluster_id": self.cluster_id,
            "title": self.title,
            "finding_count": len(self.findings),
            "finding_ids": [str(f.finding_id) for f in self.findings],
            "common_attributes": self.common_attributes,
            "severity": self.severity,
            "affected_resources": self.affected_resources,
            "correlation_score": self.correlation_score,
            "recommended_action": self.recommended_action,
        }


class FindingCorrelator:
    """Correlate and cluster related security findings.

    This service analyzes findings to identify patterns and relationships,
    grouping related findings into clusters for more effective remediation.

    Correlation methods:
    - Same resource type
    - Same AWS service
    - Same compliance framework
    - Similar rule patterns
    - Related resources (same VPC, account, etc.)
    """

    def __init__(self, min_cluster_size: int = 2) -> None:
        """Initialize the finding correlator.

        Args:
            min_cluster_size: Minimum number of findings to form a cluster
        """
        self.min_cluster_size = min_cluster_size
        logger.info(
            f"Initialized FindingCorrelator (min_cluster_size={min_cluster_size})"
        )

    def correlate_findings(self, findings: List[Finding]) -> List[FindingCluster]:
        """Correlate findings and create clusters.

        Args:
            findings: List of findings to correlate

        Returns:
            List of finding clusters, sorted by severity and size
        """
        logger.info(f"Correlating {len(findings)} findings")

        # Create multiple types of clusters
        clusters = []

        # Cluster by resource type
        resource_type_clusters = self._cluster_by_resource_type(findings)
        clusters.extend(resource_type_clusters)

        # Cluster by rule pattern
        rule_pattern_clusters = self._cluster_by_rule_pattern(findings)
        clusters.extend(rule_pattern_clusters)

        # Cluster by compliance framework
        compliance_clusters = self._cluster_by_compliance(findings)
        clusters.extend(compliance_clusters)

        # Cluster by service
        service_clusters = self._cluster_by_service(findings)
        clusters.extend(service_clusters)

        # Remove duplicate findings across clusters
        clusters = self._deduplicate_clusters(clusters)

        # Sort by severity and size
        clusters.sort(
            key=lambda c: (
                self._severity_priority(c.severity),
                len(c.findings),
            )
        )

        logger.info(f"Created {len(clusters)} clusters from {len(findings)} findings")

        return clusters

    def _cluster_by_resource_type(
        self, findings: List[Finding]
    ) -> List[FindingCluster]:
        """Cluster findings by resource type.

        Args:
            findings: List of findings

        Returns:
            List of clusters grouped by resource type
        """
        type_groups: Dict[str, List[Finding]] = defaultdict(list)

        for finding in findings:
            type_groups[finding.resource_type].append(finding)

        clusters = []
        for resource_type, group_findings in type_groups.items():
            if len(group_findings) >= self.min_cluster_size:
                cluster = self._create_cluster(
                    findings=group_findings,
                    cluster_type="resource_type",
                    common_attribute=resource_type,
                )
                clusters.append(cluster)

        logger.debug(f"Created {len(clusters)} resource type clusters")
        return clusters

    def _cluster_by_rule_pattern(self, findings: List[Finding]) -> List[FindingCluster]:
        """Cluster findings by rule ID pattern.

        Groups findings with similar rule IDs (e.g., CIS-*, AWS-*)

        Args:
            findings: List of findings

        Returns:
            List of clusters grouped by rule pattern
        """
        pattern_groups: Dict[str, List[Finding]] = defaultdict(list)

        for finding in findings:
            # Extract rule pattern (prefix before hyphen or underscore)
            rule_id = finding.rule_id
            if "-" in rule_id:
                pattern = rule_id.split("-")[0]
            elif "_" in rule_id:
                pattern = rule_id.split("_")[0]
            else:
                pattern = "other"

            pattern_groups[pattern].append(finding)

        clusters = []
        for pattern, group_findings in pattern_groups.items():
            if len(group_findings) >= self.min_cluster_size:
                cluster = self._create_cluster(
                    findings=group_findings,
                    cluster_type="rule_pattern",
                    common_attribute=pattern,
                )
                clusters.append(cluster)

        logger.debug(f"Created {len(clusters)} rule pattern clusters")
        return clusters

    def _cluster_by_compliance(self, findings: List[Finding]) -> List[FindingCluster]:
        """Cluster findings by compliance framework.

        Args:
            findings: List of findings

        Returns:
            List of clusters grouped by compliance framework
        """
        compliance_groups: Dict[str, List[Finding]] = defaultdict(list)

        for finding in findings:
            if finding.compliance_frameworks:
                for framework in finding.compliance_frameworks:
                    compliance_groups[framework].append(finding)

        clusters = []
        for framework, group_findings in compliance_groups.items():
            if len(group_findings) >= self.min_cluster_size:
                cluster = self._create_cluster(
                    findings=group_findings,
                    cluster_type="compliance",
                    common_attribute=framework,
                )
                clusters.append(cluster)

        logger.debug(f"Created {len(clusters)} compliance framework clusters")
        return clusters

    def _cluster_by_service(self, findings: List[Finding]) -> List[FindingCluster]:
        """Cluster findings by AWS service.

        Args:
            findings: List of findings

        Returns:
            List of clusters grouped by service
        """
        service_groups: Dict[str, List[Finding]] = defaultdict(list)

        for finding in findings:
            service_groups[finding.service].append(finding)

        clusters = []
        for service, group_findings in service_groups.items():
            if len(group_findings) >= self.min_cluster_size:
                cluster = self._create_cluster(
                    findings=group_findings,
                    cluster_type="service",
                    common_attribute=service,
                )
                clusters.append(cluster)

        logger.debug(f"Created {len(clusters)} service clusters")
        return clusters

    def _create_cluster(
        self,
        findings: List[Finding],
        cluster_type: str,
        common_attribute: str,
    ) -> FindingCluster:
        """Create a finding cluster.

        Args:
            findings: Findings in the cluster
            cluster_type: Type of clustering (resource_type, rule_pattern, etc.)
            common_attribute: The common attribute value

        Returns:
            Created cluster
        """
        # Generate cluster ID
        cluster_id = f"{cluster_type}_{common_attribute}_{len(findings)}"

        # Determine title
        title = self._generate_cluster_title(
            cluster_type, common_attribute, len(findings)
        )

        # Find highest severity
        severity_order = ["critical", "high", "medium", "low", "info"]
        severities = [f.severity.value for f in findings]
        highest_severity = min(severities, key=lambda s: severity_order.index(s))

        # Count unique resources
        unique_resources = len(set(f.resource_id for f in findings))

        # Calculate correlation score (0-1)
        correlation_score = self._calculate_correlation_score(findings, cluster_type)

        # Generate recommended action
        recommended_action = self._generate_cluster_action(
            cluster_type, common_attribute, len(findings)
        )

        # Common attributes
        common_attributes = {
            "cluster_type": cluster_type,
            "common_value": common_attribute,
        }

        return FindingCluster(
            cluster_id=cluster_id,
            title=title,
            findings=findings,
            common_attributes=common_attributes,
            severity=highest_severity,
            affected_resources=unique_resources,
            correlation_score=correlation_score,
            recommended_action=recommended_action,
        )

    def _generate_cluster_title(
        self,
        cluster_type: str,
        common_attribute: str,
        count: int,
    ) -> str:
        """Generate a descriptive title for the cluster.

        Args:
            cluster_type: Type of clustering
            common_attribute: Common attribute value
            count: Number of findings

        Returns:
            Cluster title
        """
        title_templates = {
            "resource_type": f"{count} findings in {common_attribute} resources",
            "rule_pattern": f"{count} {common_attribute} rule violations",
            "compliance": f"{count} {common_attribute} compliance issues",
            "service": f"{count} issues in {common_attribute} service",
        }

        return title_templates.get(
            cluster_type,
            f"{count} related findings ({common_attribute})",
        )

    def _calculate_correlation_score(
        self,
        findings: List[Finding],
        cluster_type: str,
    ) -> float:
        """Calculate correlation strength score (0-1).

        Args:
            findings: Findings in the cluster
            cluster_type: Type of clustering

        Returns:
            Correlation score between 0 and 1
        """
        # Base score from cluster type
        type_weights = {
            "resource_type": 0.7,
            "rule_pattern": 0.8,
            "compliance": 0.9,
            "service": 0.6,
        }

        base_score = type_weights.get(cluster_type, 0.5)

        # Adjust for cluster size (larger clusters = stronger correlation)
        size_bonus = min(0.2, len(findings) * 0.02)

        # Adjust for severity consistency
        severities = set(f.severity.value for f in findings)
        if len(severities) == 1:
            severity_bonus = 0.1
        else:
            severity_bonus = 0.0

        total_score = min(1.0, base_score + size_bonus + severity_bonus)

        return round(total_score, 2)

    def _generate_cluster_action(
        self,
        cluster_type: str,
        common_attribute: str,
        count: int,
    ) -> str:
        """Generate recommended action for the cluster.

        Args:
            cluster_type: Type of clustering
            common_attribute: Common attribute value
            count: Number of findings

        Returns:
            Recommended action
        """
        actions = {
            "resource_type": f"Review and remediate all {common_attribute} resources together to ensure consistent security configuration",
            "rule_pattern": f"Address all {common_attribute} rule violations as part of a comprehensive policy review",
            "compliance": f"Implement controls to address {count} {common_attribute} compliance requirements",
            "service": f"Conduct security review of {common_attribute} service configuration and apply fixes systematically",
        }

        return actions.get(
            cluster_type,
            f"Group remediation of {count} related findings for efficiency",
        )

    def _deduplicate_clusters(
        self,
        clusters: List[FindingCluster],
    ) -> List[FindingCluster]:
        """Remove duplicate findings across clusters.

        Keep each finding in its most relevant cluster only.

        Args:
            clusters: List of clusters potentially containing duplicates

        Returns:
            List of clusters with unique findings
        """
        # Track which findings have been assigned
        assigned_findings: Set[str] = set()
        deduplicated_clusters = []

        # Sort clusters by correlation score (highest first)
        sorted_clusters = sorted(
            clusters,
            key=lambda c: c.correlation_score,
            reverse=True,
        )

        for cluster in sorted_clusters:
            # Keep only findings not yet assigned
            unique_findings = [
                f
                for f in cluster.findings
                if str(f.finding_id) not in assigned_findings
            ]

            # Only keep cluster if it still has enough findings
            if len(unique_findings) >= self.min_cluster_size:
                cluster.findings = unique_findings
                cluster.affected_resources = len(
                    set(f.resource_id for f in unique_findings)
                )
                deduplicated_clusters.append(cluster)

                # Mark these findings as assigned
                assigned_findings.update(str(f.finding_id) for f in unique_findings)

        logger.debug(
            f"Deduplicated {len(clusters)} clusters to {len(deduplicated_clusters)}"
        )

        return deduplicated_clusters

    def _severity_priority(self, severity: str) -> int:
        """Convert severity to priority number (lower = higher priority).

        Args:
            severity: Severity string

        Returns:
            Priority number
        """
        priorities = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        return priorities.get(severity, 5)

    def get_cluster_summary(
        self,
        clusters: List[FindingCluster],
    ) -> Dict[str, Any]:
        """Get summary statistics for clusters.

        Args:
            clusters: List of clusters

        Returns:
            Summary statistics dictionary
        """
        total_findings = sum(len(c.findings) for c in clusters)
        total_resources = sum(c.affected_resources for c in clusters)

        severity_counts = defaultdict(int)
        for cluster in clusters:
            severity_counts[cluster.severity] += 1

        cluster_types = defaultdict(int)
        for cluster in clusters:
            cluster_types[cluster.common_attributes.get("cluster_type", "unknown")] += 1

        return {
            "total_clusters": len(clusters),
            "total_findings": total_findings,
            "total_resources": total_resources,
            "average_cluster_size": round(total_findings / len(clusters), 1)
            if clusters
            else 0,
            "severity_distribution": dict(severity_counts),
            "cluster_types": dict(cluster_types),
        }
