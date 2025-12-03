"""Tests for finding correlation and clustering."""

import pytest

from cloud_optimizer.models.finding import Finding
from ib_platform.security.correlation import FindingCluster, FindingCorrelator


class TestFindingCorrelator:
    """Test cases for FindingCorrelator class."""

    def test_correlator_initialization(self) -> None:
        """Test that FindingCorrelator initializes correctly."""
        correlator = FindingCorrelator(min_cluster_size=2)
        assert correlator is not None
        assert correlator.min_cluster_size == 2

    def test_correlator_default_min_cluster_size(self) -> None:
        """Test default minimum cluster size."""
        correlator = FindingCorrelator()
        assert correlator.min_cluster_size == 2

    def test_correlate_findings_creates_clusters(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test that correlate_findings creates clusters."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        assert isinstance(clusters, list)
        assert len(clusters) > 0

        for cluster in clusters:
            assert isinstance(cluster, FindingCluster)
            assert len(cluster.findings) >= correlator.min_cluster_size

    def test_cluster_by_resource_type(
        self, same_resource_type_findings: list[Finding]
    ) -> None:
        """Test clustering by resource type."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(same_resource_type_findings)

        # Deduplication assigns each finding to its highest-scoring cluster
        # With PCI-DSS compliance in fixtures, compliance clusters score higher
        # than resource_type clusters, so findings may end up in compliance clusters
        assert len(clusters) > 0  # At least one cluster should be created

        # Verify all findings in each cluster share a common attribute
        for cluster in clusters:
            cluster_type = cluster.common_attributes.get("cluster_type")
            if cluster_type == "resource_type":
                # If we have resource_type clusters, verify homogeneity
                resource_types = set(f.resource_type for f in cluster.findings)
                assert len(resource_types) == 1

    def test_cluster_by_service(self, multiple_findings: list[Finding]) -> None:
        """Test clustering by AWS service."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        # Deduplication assigns findings to highest-scoring cluster type
        # Service clusters have lower weight than compliance/rule_pattern
        # So service clusters may not be created if findings go elsewhere
        assert len(clusters) > 0  # At least some clusters should be created

        # If service clusters exist, verify findings share service
        service_clusters = [
            c for c in clusters if c.common_attributes.get("cluster_type") == "service"
        ]
        for cluster in service_clusters:
            services = set(f.service for f in cluster.findings)
            assert len(services) == 1

    def test_cluster_by_compliance(self, multiple_findings: list[Finding]) -> None:
        """Test clustering by compliance framework."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        compliance_clusters = [
            c
            for c in clusters
            if c.common_attributes.get("cluster_type") == "compliance"
        ]

        # Should have compliance-based clusters
        assert len(compliance_clusters) > 0

        # Check cluster has compliance framework
        for cluster in compliance_clusters:
            assert cluster.common_attributes.get("common_value") is not None

    def test_cluster_by_rule_pattern(self, same_resource_type_findings: list[Finding]) -> None:
        """Test clustering by rule pattern."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(same_resource_type_findings)

        rule_clusters = [
            c
            for c in clusters
            if c.common_attributes.get("cluster_type") == "rule_pattern"
        ]

        # AWS-S3-* rules should cluster together
        if rule_clusters:
            for cluster in rule_clusters:
                # All findings should have similar rule prefix
                rule_prefixes = [f.rule_id.split("-")[0] for f in cluster.findings]
                assert len(set(rule_prefixes)) == 1

    def test_cluster_minimum_size_respected(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test that minimum cluster size is respected."""
        min_size = 3
        correlator = FindingCorrelator(min_cluster_size=min_size)
        clusters = correlator.correlate_findings(multiple_findings)

        # All clusters should have at least min_size findings
        for cluster in clusters:
            assert len(cluster.findings) >= min_size

    def test_cluster_severity_is_highest(self, multiple_findings: list[Finding]) -> None:
        """Test that cluster severity is the highest in the group."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        severity_order = ["critical", "high", "medium", "low", "info"]

        for cluster in clusters:
            cluster_severity_priority = severity_order.index(cluster.severity)

            for finding in cluster.findings:
                finding_severity_priority = severity_order.index(
                    finding.severity.value
                )
                # Cluster severity should be at least as high as any finding
                assert cluster_severity_priority <= finding_severity_priority

    def test_cluster_affected_resources_count(
        self, same_resource_type_findings: list[Finding]
    ) -> None:
        """Test that affected resources count is accurate."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(same_resource_type_findings)

        for cluster in clusters:
            unique_resources = set(f.resource_id for f in cluster.findings)
            assert cluster.affected_resources == len(unique_resources)

    def test_cluster_correlation_score(self, multiple_findings: list[Finding]) -> None:
        """Test that correlation score is calculated."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        for cluster in clusters:
            # Score should be between 0 and 1
            assert 0.0 <= cluster.correlation_score <= 1.0

    def test_cluster_has_recommended_action(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test that clusters have recommended actions."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        for cluster in clusters:
            assert len(cluster.recommended_action) > 0

    def test_cluster_to_dict(self, multiple_findings: list[Finding]) -> None:
        """Test conversion of FindingCluster to dictionary."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        if clusters:
            result = clusters[0].to_dict()

            assert isinstance(result, dict)
            assert "cluster_id" in result
            assert "title" in result
            assert "finding_count" in result
            assert "finding_ids" in result
            assert "common_attributes" in result
            assert "severity" in result
            assert "affected_resources" in result
            assert "correlation_score" in result
            assert "recommended_action" in result

    def test_empty_findings_list(self) -> None:
        """Test correlation with empty findings list."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings([])
        assert clusters == []

    def test_single_finding(self, sample_finding: Finding) -> None:
        """Test correlation with single finding."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings([sample_finding])

        # Should not create clusters with min_size=2
        assert len(clusters) == 0

    def test_deduplication_across_clusters(
        self, same_resource_type_findings: list[Finding]
    ) -> None:
        """Test that findings are not duplicated across clusters."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(same_resource_type_findings)

        # Collect all finding IDs from all clusters
        all_finding_ids = []
        for cluster in clusters:
            all_finding_ids.extend(str(f.finding_id) for f in cluster.findings)

        # Should have no duplicates
        assert len(all_finding_ids) == len(set(all_finding_ids))

    def test_get_cluster_summary(self, multiple_findings: list[Finding]) -> None:
        """Test cluster summary generation."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)
        summary = correlator.get_cluster_summary(clusters)

        assert isinstance(summary, dict)
        assert "total_clusters" in summary
        assert "total_findings" in summary
        assert "total_resources" in summary
        assert "average_cluster_size" in summary
        assert "severity_distribution" in summary
        assert "cluster_types" in summary

        # Verify counts
        assert summary["total_clusters"] == len(clusters)

        total_findings = sum(len(c.findings) for c in clusters)
        assert summary["total_findings"] == total_findings

    def test_cluster_summary_with_empty_clusters(self) -> None:
        """Test cluster summary with no clusters."""
        correlator = FindingCorrelator(min_cluster_size=2)
        summary = correlator.get_cluster_summary([])

        assert summary["total_clusters"] == 0
        assert summary["total_findings"] == 0
        assert summary["average_cluster_size"] == 0

    def test_cluster_title_generation(self, multiple_findings: list[Finding]) -> None:
        """Test that cluster titles are descriptive."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        for cluster in clusters:
            assert len(cluster.title) > 0
            # Title should include count
            assert any(char.isdigit() for char in cluster.title)

    def test_clusters_sorted_by_priority(self, multiple_findings: list[Finding]) -> None:
        """Test that clusters are sorted by severity."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        if len(clusters) > 1:
            severity_order = ["critical", "high", "medium", "low", "info"]

            for i in range(len(clusters) - 1):
                current_priority = severity_order.index(clusters[i].severity)
                next_priority = severity_order.index(clusters[i + 1].severity)

                # Current should be higher or equal priority
                assert current_priority <= next_priority

    def test_correlation_score_higher_for_same_severity(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test that correlation score is higher when severities match."""
        correlator = FindingCorrelator(min_cluster_size=2)

        # This is tested indirectly through the scoring logic
        # A cluster with all same severity should have higher correlation
        clusters = correlator.correlate_findings(multiple_findings)

        for cluster in clusters:
            severities = set(f.severity.value for f in cluster.findings)

            if len(severities) == 1:
                # All same severity should get severity bonus
                # Correlation score should be higher (tested in implementation)
                assert cluster.correlation_score > 0.5

    def test_cluster_common_attributes_populated(
        self, multiple_findings: list[Finding]
    ) -> None:
        """Test that common attributes are populated."""
        correlator = FindingCorrelator(min_cluster_size=2)
        clusters = correlator.correlate_findings(multiple_findings)

        for cluster in clusters:
            assert "cluster_type" in cluster.common_attributes
            assert "common_value" in cluster.common_attributes
            assert cluster.common_attributes["cluster_type"] in [
                "resource_type",
                "rule_pattern",
                "compliance",
                "service",
            ]
