"""
Unit tests for SystemsManagerScanner - Pure logic tests only.

These tests verify scanner logic WITHOUT mocking AWS services.
AWS interaction tests are in tests/integration/ using LocalStack.

Testing Strategy:
- Unit tests: Test internal logic (finding creation, severity calculation)
- Integration tests: Test actual AWS API interactions via LocalStack
"""

import pytest

from cloud_optimizer.integrations.aws.operations import SystemsManagerScanner


class TestSystemsManagerScannerInitialization:
    """Tests for SystemsManagerScanner initialization and configuration."""

    def test_scanner_name(self):
        """Test scanner returns correct name."""
        scanner = SystemsManagerScanner()
        assert scanner.get_scanner_name() == "SystemsManagerScanner"

    def test_scanner_default_region(self):
        """Test scanner uses default region."""
        scanner = SystemsManagerScanner()
        assert scanner.region == "us-east-1"

    def test_scanner_custom_region(self):
        """Test scanner accepts custom region."""
        scanner = SystemsManagerScanner(region="eu-west-1")
        assert scanner.region == "eu-west-1"

    def test_required_tags_defined(self):
        """Test required tags are properly defined."""
        assert "Name" in SystemsManagerScanner.REQUIRED_TAGS
        assert "Environment" in SystemsManagerScanner.REQUIRED_TAGS
        assert "Owner" in SystemsManagerScanner.REQUIRED_TAGS

    def test_critical_metrics_defined(self):
        """Test critical metrics are properly defined."""
        assert "CPUUtilization" in SystemsManagerScanner.CRITICAL_METRICS
        assert "StatusCheckFailed" in SystemsManagerScanner.CRITICAL_METRICS


class TestMonitoringGapFinding:
    """Tests for monitoring gap finding creation."""

    def test_create_monitoring_gap_with_all_metrics_missing(self):
        """Test monitoring gap finding with all critical metrics missing."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-0123456789abcdef0",
            "InstanceType": "t3.medium",
            "Tags": [{"Key": "Name", "Value": "web-server-01"}],
        }
        missing_metrics = ["CPUUtilization", "StatusCheckFailed"]

        finding = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=missing_metrics,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "monitoring_gap"
        assert finding["severity"] == "high"
        assert "web-server-01" in finding["title"]
        assert "CPUUtilization" in finding["description"]
        assert "StatusCheckFailed" in finding["description"]
        assert finding["resource_id"] == "i-0123456789abcdef0"
        assert finding["resource_name"] == "web-server-01"
        assert finding["metadata"]["instance_type"] == "t3.medium"
        assert finding["metadata"]["missing_metrics"] == missing_metrics

    def test_create_monitoring_gap_with_one_metric_missing(self):
        """Test monitoring gap finding with one critical metric missing."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test123",
            "InstanceType": "m5.large",
            "Tags": [{"Key": "Name", "Value": "app-server"}],
        }
        missing_metrics = ["CPUUtilization"]

        finding = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=missing_metrics,
            account_id="123456789012",
        )

        assert finding["severity"] == "medium"
        assert len(finding["metadata"]["missing_metrics"]) == 1

    def test_monitoring_gap_includes_remediation(self):
        """Test monitoring gap finding includes remediation steps."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test456",
            "InstanceType": "t2.micro",
            "Tags": [],
        }

        finding = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=["CPUUtilization"],
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "CloudWatch" in finding["remediation"]
        assert "alarms" in finding["remediation"].lower()

    def test_monitoring_gap_without_name_tag(self):
        """Test monitoring gap finding when instance has no Name tag."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-unnamed",
            "InstanceType": "t3.small",
            "Tags": [],
        }

        finding = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=["CPUUtilization"],
            account_id="123456789012",
        )

        # Should fall back to instance ID as name
        assert finding["resource_name"] == "i-unnamed"


class TestSSMAgentMissingFinding:
    """Tests for SSM agent missing finding creation."""

    def test_create_ssm_agent_missing_finding(self):
        """Test SSM agent missing finding has correct structure."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-0123456789abcdef0",
            "InstanceType": "t3.medium",
            "Platform": "linux",
            "Tags": [{"Key": "Name", "Value": "database-server"}],
        }

        finding = scanner._create_ssm_agent_missing_finding(
            instance=instance,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "automation_opportunity"
        assert finding["severity"] == "medium"
        assert "database-server" in finding["title"]
        assert "Systems Manager agent" in finding["description"]
        assert finding["resource_id"] == "i-0123456789abcdef0"
        assert finding["metadata"]["instance_type"] == "t3.medium"
        assert finding["metadata"]["platform"] == "linux"

    def test_ssm_agent_finding_includes_remediation(self):
        """Test SSM agent finding includes remediation steps."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test789",
            "InstanceType": "m5.xlarge",
            "Tags": [{"Key": "Name", "Value": "app-01"}],
        }

        finding = scanner._create_ssm_agent_missing_finding(
            instance=instance,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Install" in finding["remediation"]
        assert "IAM role" in finding["remediation"]
        assert "AmazonSSMManagedInstanceCore" in finding["remediation"]

    def test_ssm_agent_finding_with_platform(self):
        """Test SSM agent finding captures platform information."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-windows",
            "InstanceType": "t3.large",
            "Platform": "windows",
            "Tags": [],
        }

        finding = scanner._create_ssm_agent_missing_finding(
            instance=instance,
            account_id="123456789012",
        )

        assert finding["metadata"]["platform"] == "windows"


class TestAutomationOpportunityFinding:
    """Tests for automation opportunity finding creation."""

    def test_create_automation_opportunity_finding(self):
        """Test automation opportunity finding has correct structure."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-0123456789abcdef0",
            "InstanceType": "r5.large",
            "Tags": [{"Key": "Name", "Value": "cache-server"}],
        }

        finding = scanner._create_automation_opportunity_finding(
            instance=instance,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "automation_opportunity"
        assert finding["severity"] == "low"
        assert "cache-server" in finding["title"]
        assert "automation" in finding["description"].lower()
        assert finding["resource_id"] == "i-0123456789abcdef0"
        assert finding["metadata"]["instance_type"] == "r5.large"

    def test_automation_finding_includes_remediation(self):
        """Test automation finding includes remediation steps."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test",
            "InstanceType": "t3.nano",
            "Tags": [],
        }

        finding = scanner._create_automation_opportunity_finding(
            instance=instance,
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "maintenance windows" in finding["remediation"].lower()
        assert "automation documents" in finding["remediation"].lower()


class TestTaggingIssueFinding:
    """Tests for tagging issue finding creation."""

    def test_create_tagging_issue_all_tags_missing(self):
        """Test tagging issue finding with all required tags missing."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-0123456789abcdef0",
            "InstanceType": "t3.medium",
            "Tags": [],
        }
        missing_tags = ["Name", "Environment", "Owner"]

        finding = scanner._create_tagging_issue_finding(
            instance=instance,
            missing_tags=missing_tags,
            account_id="123456789012",
        )

        assert finding["finding_type"] == "documentation_issue"
        assert finding["severity"] == "medium"
        assert "Name" in finding["description"]
        assert "Environment" in finding["description"]
        assert "Owner" in finding["description"]
        assert finding["metadata"]["missing_tags"] == missing_tags
        assert finding["metadata"]["existing_tags"] == []

    def test_create_tagging_issue_some_tags_missing(self):
        """Test tagging issue finding with some tags missing."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-partial-tags",
            "InstanceType": "m5.large",
            "Tags": [
                {"Key": "Name", "Value": "web-server"},
                {"Key": "Project", "Value": "CloudOpt"},
            ],
        }
        missing_tags = ["Environment", "Owner"]

        finding = scanner._create_tagging_issue_finding(
            instance=instance,
            missing_tags=missing_tags,
            account_id="123456789012",
        )

        assert finding["severity"] == "low"
        assert finding["resource_name"] == "web-server"
        assert "Name" in finding["metadata"]["existing_tags"]
        assert "Project" in finding["metadata"]["existing_tags"]
        assert len(finding["metadata"]["missing_tags"]) == 2

    def test_tagging_issue_includes_remediation(self):
        """Test tagging issue finding includes remediation steps."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test",
            "InstanceType": "t2.small",
            "Tags": [],
        }

        finding = scanner._create_tagging_issue_finding(
            instance=instance,
            missing_tags=["Owner"],
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "tags" in finding["remediation"].lower()
        assert "Owner" in finding["remediation"]


class TestMissingRunbooksFinding:
    """Tests for missing runbooks finding creation."""

    def test_create_missing_runbooks_finding(self):
        """Test missing runbooks finding has correct structure."""
        scanner = SystemsManagerScanner()

        finding = scanner._create_missing_runbooks_finding(
            account_id="123456789012",
        )

        assert finding["finding_type"] == "documentation_issue"
        assert finding["severity"] == "low"
        assert "runbooks" in finding["title"].lower()
        assert "automation documents" in finding["description"]
        assert finding["resource_type"] == "ssm_document"
        assert finding["metadata"]["document_type"] == "Automation"

    def test_missing_runbooks_includes_remediation(self):
        """Test missing runbooks finding includes remediation steps."""
        scanner = SystemsManagerScanner()

        finding = scanner._create_missing_runbooks_finding(
            account_id="123456789012",
        )

        assert "remediation" in finding
        assert "Create custom SSM automation documents" in finding["remediation"]
        assert "Examples:" in finding["remediation"]


class TestSeverityCalculation:
    """Tests for severity calculation logic."""

    def test_monitoring_severity_high_all_critical_missing(self):
        """Test high severity when all critical metrics missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_monitoring_severity(
            ["CPUUtilization", "StatusCheckFailed"]
        )
        assert severity == "high"

    def test_monitoring_severity_medium_one_critical_missing(self):
        """Test medium severity when one critical metric missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_monitoring_severity(["CPUUtilization"])
        assert severity == "medium"

    def test_monitoring_severity_low_non_critical(self):
        """Test low severity when only non-critical metrics missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_monitoring_severity(["NetworkIn"])
        assert severity == "low"

    def test_tagging_severity_medium_all_tags_missing(self):
        """Test medium severity when all required tags missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_tagging_severity(["Name", "Environment", "Owner"])
        assert severity == "medium"

    def test_tagging_severity_low_some_tags_missing(self):
        """Test low severity when some tags missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_tagging_severity(["Environment", "Owner"])
        assert severity == "low"

    def test_tagging_severity_low_one_tag_missing(self):
        """Test low severity when one tag missing."""
        scanner = SystemsManagerScanner()
        severity = scanner._calculate_tagging_severity(["Owner"])
        assert severity == "low"


class TestFindingStructure:
    """Tests for finding structure consistency."""

    def test_all_findings_have_required_fields(self):
        """Test that all finding types have required fields."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test",
            "InstanceType": "t3.micro",
            "Tags": [],
        }

        # Test monitoring gap finding
        finding1 = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=["CPUUtilization"],
            account_id="123456789012",
        )

        # Test SSM agent finding
        finding2 = scanner._create_ssm_agent_missing_finding(
            instance=instance,
            account_id="123456789012",
        )

        # Test automation finding
        finding3 = scanner._create_automation_opportunity_finding(
            instance=instance,
            account_id="123456789012",
        )

        # Test tagging finding
        finding4 = scanner._create_tagging_issue_finding(
            instance=instance,
            missing_tags=["Name"],
            account_id="123456789012",
        )

        # Test runbooks finding
        finding5 = scanner._create_missing_runbooks_finding(
            account_id="123456789012",
        )

        required_fields = [
            "finding_type",
            "severity",
            "title",
            "description",
            "resource_arn",
            "resource_id",
            "resource_name",
            "resource_type",
            "aws_account_id",
            "region",
            "remediation",
            "metadata",
        ]

        for finding in [finding1, finding2, finding3, finding4, finding5]:
            for field in required_fields:
                assert field in finding, f"Missing field '{field}' in finding"

    def test_finding_types_are_correct(self):
        """Test that finding types match expected values."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test",
            "InstanceType": "t3.micro",
            "Tags": [],
        }

        monitoring_finding = scanner._create_monitoring_gap_finding(
            instance=instance,
            missing_metrics=["CPUUtilization"],
            account_id="123456789012",
        )
        assert monitoring_finding["finding_type"] == "monitoring_gap"

        ssm_finding = scanner._create_ssm_agent_missing_finding(
            instance=instance,
            account_id="123456789012",
        )
        assert ssm_finding["finding_type"] == "automation_opportunity"

        automation_finding = scanner._create_automation_opportunity_finding(
            instance=instance,
            account_id="123456789012",
        )
        assert automation_finding["finding_type"] == "automation_opportunity"

        tagging_finding = scanner._create_tagging_issue_finding(
            instance=instance,
            missing_tags=["Name"],
            account_id="123456789012",
        )
        assert tagging_finding["finding_type"] == "documentation_issue"

        runbooks_finding = scanner._create_missing_runbooks_finding(
            account_id="123456789012",
        )
        assert runbooks_finding["finding_type"] == "documentation_issue"

    def test_severity_values_are_valid(self):
        """Test that severity values are from allowed set."""
        scanner = SystemsManagerScanner()
        instance = {
            "InstanceId": "i-test",
            "InstanceType": "t3.micro",
            "Tags": [],
        }

        valid_severities = {"low", "medium", "high", "critical"}

        # Test various findings
        findings = [
            scanner._create_monitoring_gap_finding(
                instance=instance,
                missing_metrics=["CPUUtilization", "StatusCheckFailed"],
                account_id="123456789012",
            ),
            scanner._create_ssm_agent_missing_finding(
                instance=instance,
                account_id="123456789012",
            ),
            scanner._create_tagging_issue_finding(
                instance=instance,
                missing_tags=["Name", "Environment", "Owner"],
                account_id="123456789012",
            ),
        ]

        for finding in findings:
            assert finding["severity"] in valid_severities
