"""Unit tests for ACM Certificate CloudFormation templates.

Issue #160: SSL/TLS certificate setup (ACM)
Tests for acm-certificate.yaml template structure and validation.
"""

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


def get_cfn_loader() -> type:
    """Create a YAML loader that handles CloudFormation intrinsic functions."""

    class CloudFormationLoader(yaml.SafeLoader):
        pass

    # CloudFormation intrinsic function tags
    cfn_tags = [
        "!Ref",
        "!Sub",
        "!GetAtt",
        "!If",
        "!Not",
        "!Equals",
        "!And",
        "!Or",
        "!Condition",
        "!Select",
        "!Split",
        "!Join",
        "!FindInMap",
        "!ImportValue",
        "!GetAZs",
        "!Cidr",
        "!Base64",
    ]

    def generic_constructor(loader: yaml.Loader, tag_suffix: str, node: yaml.Node) -> Dict[str, Any]:
        """Handle CloudFormation intrinsic functions."""
        if isinstance(node, yaml.ScalarNode):
            return {f"Fn::{tag_suffix}": loader.construct_scalar(node)}
        elif isinstance(node, yaml.SequenceNode):
            return {f"Fn::{tag_suffix}": loader.construct_sequence(node)}
        elif isinstance(node, yaml.MappingNode):
            return {f"Fn::{tag_suffix}": loader.construct_mapping(node)}
        return {}

    for tag in cfn_tags:
        tag_name = tag[1:]  # Remove the '!' prefix
        CloudFormationLoader.add_constructor(
            tag,
            lambda loader, node, name=tag_name: generic_constructor(loader, name, node),
        )

    return CloudFormationLoader


def load_cfn_template(path: Path) -> Dict[str, Any]:
    """Load a CloudFormation template with intrinsic function support."""
    with open(path, "r") as f:
        return yaml.load(f, Loader=get_cfn_loader())


class TestACMCertificateStandalone:
    """Test standalone ACM certificate CloudFormation template (Issue #160)."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to ACM certificate template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that ACM certificate template file exists."""
        assert template_path.exists(), "ACM certificate template should exist"

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description with SSL/TLS and issue reference."""
        assert "Description" in template
        description = template["Description"]
        assert "SSL/TLS" in description
        assert "Issue #160" in description

    def test_template_has_metadata(self, template: Dict[str, Any]) -> None:
        """Test template has CloudFormation interface metadata."""
        assert "Metadata" in template
        assert "AWS::CloudFormation::Interface" in template["Metadata"]

    def test_required_parameters_exist(self, template: Dict[str, Any]) -> None:
        """Test all required parameters are defined."""
        params = template.get("Parameters", {})
        required_params = [
            "DomainName",
            "LoadBalancerArn",
            "TargetGroupArn",
            "AlertEmail",
            "TLSSecurityPolicy",
            "CertificateExpirationAlertDays",
        ]
        for param in required_params:
            assert param in params, f"Missing required parameter: {param}"

    def test_domain_name_parameter(self, template: Dict[str, Any]) -> None:
        """Test DomainName parameter configuration."""
        domain_param = template["Parameters"]["DomainName"]
        assert domain_param["Type"] == "String"
        assert "AllowedPattern" in domain_param
        # Pattern should validate domain format
        pattern = domain_param["AllowedPattern"]
        assert "\\." in pattern or "." in pattern

    def test_hosted_zone_optional(self, template: Dict[str, Any]) -> None:
        """Test HostedZoneId parameter is optional."""
        hosted_zone_param = template["Parameters"]["HostedZoneId"]
        assert hosted_zone_param.get("Default") == ""

    def test_tls_security_policy_defaults_to_tls12_plus(self, template: Dict[str, Any]) -> None:
        """Test TLS security policy defaults to TLS 1.2+."""
        tls_param = template["Parameters"]["TLSSecurityPolicy"]
        default = tls_param["Default"]
        # Should be TLS 1.2 or TLS 1.3 policy
        assert "TLS13" in default or "TLS-1-2" in default

    def test_tls_allowed_values_secure(self, template: Dict[str, Any]) -> None:
        """Test TLS security policy only allows secure values."""
        tls_param = template["Parameters"]["TLSSecurityPolicy"]
        allowed = tls_param["AllowedValues"]
        for policy in allowed:
            # No TLS 1.0 or 1.1
            assert "TLS-1-0" not in policy
            assert "TLS-1-1" not in policy

    def test_expiration_alert_days_configuration(self, template: Dict[str, Any]) -> None:
        """Test certificate expiration alert days parameter."""
        alert_param = template["Parameters"]["CertificateExpirationAlertDays"]
        assert alert_param["Type"] == "Number"
        assert alert_param["Default"] == 30
        assert alert_param.get("MinValue", 0) >= 7

    def test_alert_email_validation(self, template: Dict[str, Any]) -> None:
        """Test AlertEmail parameter has email validation."""
        email_param = template["Parameters"]["AlertEmail"]
        assert "AllowedPattern" in email_param
        assert "@" in email_param["AllowedPattern"]


class TestACMCertificateResources:
    """Test ACM certificate resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_certificate_resource_exists(self, template: Dict[str, Any]) -> None:
        """Test Certificate resource is defined."""
        resources = template.get("Resources", {})
        assert "Certificate" in resources
        cert = resources["Certificate"]
        assert cert["Type"] == "AWS::CertificateManager::Certificate"

    def test_certificate_uses_dns_validation(self, template: Dict[str, Any]) -> None:
        """Test Certificate uses DNS validation method."""
        cert = template["Resources"]["Certificate"]
        props = cert["Properties"]
        assert props["ValidationMethod"] == "DNS"

    def test_certificate_has_tags(self, template: Dict[str, Any]) -> None:
        """Test Certificate resource has proper tags."""
        cert = template["Resources"]["Certificate"]
        props = cert["Properties"]
        assert "Tags" in props
        tags = props["Tags"]
        tag_keys = [t["Key"] for t in tags]
        assert "Name" in tag_keys
        assert "Application" in tag_keys


class TestHTTPSListener:
    """Test HTTPS listener configuration."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_https_listener_exists(self, template: Dict[str, Any]) -> None:
        """Test HTTPS listener resource is defined."""
        resources = template.get("Resources", {})
        assert "HTTPSListener" in resources
        listener = resources["HTTPSListener"]
        assert listener["Type"] == "AWS::ElasticLoadBalancingV2::Listener"

    def test_https_listener_port_443(self, template: Dict[str, Any]) -> None:
        """Test HTTPS listener uses port 443."""
        listener = template["Resources"]["HTTPSListener"]
        props = listener["Properties"]
        assert props["Port"] == 443
        assert props["Protocol"] == "HTTPS"

    def test_https_listener_has_ssl_policy(self, template: Dict[str, Any]) -> None:
        """Test HTTPS listener has SSL policy configured."""
        listener = template["Resources"]["HTTPSListener"]
        props = listener["Properties"]
        assert "SslPolicy" in props

    def test_https_listener_has_certificate(self, template: Dict[str, Any]) -> None:
        """Test HTTPS listener references the certificate."""
        listener = template["Resources"]["HTTPSListener"]
        props = listener["Properties"]
        assert "Certificates" in props


class TestHTTPRedirect:
    """Test HTTP to HTTPS redirect configuration."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_http_redirect_listener_exists(self, template: Dict[str, Any]) -> None:
        """Test HTTP redirect listener exists."""
        resources = template.get("Resources", {})
        assert "HTTPRedirectListener" in resources
        listener = resources["HTTPRedirectListener"]
        assert listener["Type"] == "AWS::ElasticLoadBalancingV2::Listener"

    def test_http_redirect_uses_port_80(self, template: Dict[str, Any]) -> None:
        """Test HTTP redirect listener uses port 80."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        assert props["Port"] == 80
        assert props["Protocol"] == "HTTP"

    def test_http_redirect_action(self, template: Dict[str, Any]) -> None:
        """Test HTTP listener redirects to HTTPS."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        actions = props["DefaultActions"]
        assert len(actions) >= 1
        assert actions[0]["Type"] == "redirect"

    def test_http_redirect_to_https_443(self, template: Dict[str, Any]) -> None:
        """Test redirect goes to HTTPS on port 443."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        actions = props["DefaultActions"]
        redirect_config = actions[0]["RedirectConfig"]
        assert redirect_config["Protocol"] == "HTTPS"
        assert redirect_config["Port"] == "443"

    def test_http_redirect_uses_301(self, template: Dict[str, Any]) -> None:
        """Test redirect uses HTTP 301 (permanent)."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        actions = props["DefaultActions"]
        redirect_config = actions[0]["RedirectConfig"]
        assert redirect_config["StatusCode"] == "HTTP_301"


class TestCertificateMonitoring:
    """Test certificate monitoring resources."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_sns_topic_exists(self, template: Dict[str, Any]) -> None:
        """Test SNS topic for alerts exists."""
        resources = template.get("Resources", {})
        assert "CertificateAlertTopic" in resources
        topic = resources["CertificateAlertTopic"]
        assert topic["Type"] == "AWS::SNS::Topic"

    def test_sns_subscription_exists(self, template: Dict[str, Any]) -> None:
        """Test SNS email subscription exists."""
        resources = template.get("Resources", {})
        assert "CertificateAlertSubscription" in resources
        sub = resources["CertificateAlertSubscription"]
        assert sub["Type"] == "AWS::SNS::Subscription"
        assert sub["Properties"]["Protocol"] == "email"

    def test_expiration_alarm_exists(self, template: Dict[str, Any]) -> None:
        """Test certificate expiration CloudWatch alarm exists."""
        resources = template.get("Resources", {})
        assert "CertificateExpirationAlarm" in resources
        alarm = resources["CertificateExpirationAlarm"]
        assert alarm["Type"] == "AWS::CloudWatch::Alarm"

    def test_eventbridge_rule_exists(self, template: Dict[str, Any]) -> None:
        """Test EventBridge rule for ACM notifications exists."""
        resources = template.get("Resources", {})
        assert "CertificateExpirationRule" in resources
        rule = resources["CertificateExpirationRule"]
        assert rule["Type"] == "AWS::Events::Rule"

    def test_lambda_metrics_function_exists(self, template: Dict[str, Any]) -> None:
        """Test Lambda function for certificate metrics exists."""
        resources = template.get("Resources", {})
        assert "CertificateMetricsFunction" in resources
        func = resources["CertificateMetricsFunction"]
        assert func["Type"] == "AWS::Lambda::Function"

    def test_lambda_uses_python(self, template: Dict[str, Any]) -> None:
        """Test Lambda uses Python runtime."""
        func = template["Resources"]["CertificateMetricsFunction"]
        props = func["Properties"]
        assert props["Runtime"].startswith("python")

    def test_lambda_schedule_exists(self, template: Dict[str, Any]) -> None:
        """Test Lambda has scheduled execution."""
        resources = template.get("Resources", {})
        assert "CertificateMetricsSchedule" in resources
        schedule = resources["CertificateMetricsSchedule"]
        assert schedule["Type"] == "AWS::Events::Rule"


class TestTemplateOutputs:
    """Test CloudFormation outputs."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_certificate_arn_output(self, template: Dict[str, Any]) -> None:
        """Test CertificateArn output exists and is exported."""
        outputs = template["Outputs"]
        assert "CertificateArn" in outputs
        assert "Export" in outputs["CertificateArn"]

    def test_https_listener_arn_output(self, template: Dict[str, Any]) -> None:
        """Test HTTPSListenerArn output exists."""
        outputs = template["Outputs"]
        assert "HTTPSListenerArn" in outputs

    def test_domain_name_output(self, template: Dict[str, Any]) -> None:
        """Test DomainName output exists."""
        outputs = template["Outputs"]
        assert "DomainName" in outputs

    def test_tls_policy_output(self, template: Dict[str, Any]) -> None:
        """Test TLSPolicy output exists."""
        outputs = template["Outputs"]
        assert "TLSPolicy" in outputs

    def test_ssl_labs_url_output(self, template: Dict[str, Any]) -> None:
        """Test SSLLabsTestURL output exists."""
        outputs = template["Outputs"]
        assert "SSLLabsTestURL" in outputs


class TestSSLSecurityBestPractices:
    """Test SSL/TLS security best practices."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_no_http_forward(self, template: Dict[str, Any]) -> None:
        """Test HTTP never forwards traffic (always redirects)."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        actions = props["DefaultActions"]
        for action in actions:
            assert action["Type"] != "forward"

    def test_permanent_redirect(self, template: Dict[str, Any]) -> None:
        """Test 301 permanent redirect is used."""
        listener = template["Resources"]["HTTPRedirectListener"]
        props = listener["Properties"]
        actions = props["DefaultActions"]
        redirect_config = actions[0]["RedirectConfig"]
        # 301 is permanent, 302 is temporary
        assert redirect_config["StatusCode"] == "HTTP_301"

    def test_certificate_auto_renewal(self, template: Dict[str, Any]) -> None:
        """Test certificate uses DNS validation (enables auto-renewal)."""
        cert = template["Resources"]["Certificate"]
        props = cert["Properties"]
        # DNS validation enables automatic renewal
        assert props["ValidationMethod"] == "DNS"

    def test_expiration_monitoring(self, template: Dict[str, Any]) -> None:
        """Test certificate expiration monitoring is configured."""
        resources = template["Resources"]
        # Should have monitoring alarm
        assert "CertificateExpirationAlarm" in resources
        # Should have EventBridge rule for ACM notifications
        assert "CertificateExpirationRule" in resources


class TestConditions:
    """Test CloudFormation conditions."""

    @pytest.fixture
    def template(self) -> Dict[str, Any]:
        """Load the standalone ACM certificate template."""
        path = (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "acm-certificate.yaml"
        )
        return load_cfn_template(path)

    def test_has_hosted_zone_condition(self, template: Dict[str, Any]) -> None:
        """Test HasHostedZone condition exists."""
        conditions = template.get("Conditions", {})
        assert "HasHostedZone" in conditions

    def test_has_sans_condition(self, template: Dict[str, Any]) -> None:
        """Test HasSANs condition exists."""
        conditions = template.get("Conditions", {})
        assert "HasSANs" in conditions


# Keep legacy tests for nested template if it exists
class TestACMCertificateTemplateNested:
    """Test nested ACM certificate CloudFormation template (legacy)."""

    @pytest.fixture
    def template_path(self) -> Path:
        """Get path to nested ACM certificate template."""
        return (
            Path(__file__).parent.parent.parent.parent
            / "cloudformation"
            / "nested"
            / "acm-certificate.yaml"
        )

    @pytest.fixture
    def template(self, template_path: Path) -> Dict[str, Any]:
        """Load and parse the CloudFormation template."""
        if not template_path.exists():
            pytest.skip("Nested ACM certificate template does not exist")
        return load_cfn_template(template_path)

    def test_template_file_exists(self, template_path: Path) -> None:
        """Test that nested ACM certificate template file exists."""
        if not template_path.exists():
            pytest.skip("Nested ACM certificate template does not exist")
        assert template_path.exists()

    def test_template_version(self, template: Dict[str, Any]) -> None:
        """Test template has valid AWSTemplateFormatVersion."""
        assert template["AWSTemplateFormatVersion"] == "2010-09-09"

    def test_template_has_description(self, template: Dict[str, Any]) -> None:
        """Test template has description."""
        assert "Description" in template
        assert "ACM" in template["Description"]
