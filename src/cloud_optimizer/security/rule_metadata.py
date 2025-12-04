"""Security scanner rule metadata and compliance mappings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RuleMetadata:
    """Metadata mapped to a scanner finding type."""

    rule_id: str
    service: str
    frameworks: tuple[str, ...]


RULE_METADATA: Dict[str, RuleMetadata] = {
    "overly_permissive_security_group": RuleMetadata(
        rule_id="EC2_001",
        service="ec2",
        frameworks=("CIS", "HIPAA", "SOC2"),
    ),
    "wildcard_iam_permissions": RuleMetadata(
        rule_id="IAM_001",
        service="iam",
        frameworks=("CIS", "SOC2"),
    ),
    "iam_user_no_mfa": RuleMetadata(
        rule_id="IAM_002",
        service="iam",
        frameworks=("CIS", "HIPAA", "SOC2"),
    ),
    "inactive_iam_user": RuleMetadata(
        rule_id="IAM_003",
        service="iam",
        frameworks=("CIS",),
    ),
    "unencrypted_ebs_volume": RuleMetadata(
        rule_id="EC2_005",
        service="ec2",
        frameworks=("CIS", "HIPAA"),
    ),
    "unencrypted_s3_bucket": RuleMetadata(
        rule_id="S3_002",
        service="s3",
        frameworks=("CIS", "SOC2", "HIPAA"),
    ),
    "unencrypted_rds_instance": RuleMetadata(
        rule_id="RDS_001",
        service="rds",
        frameworks=("CIS", "HIPAA"),
    ),
    "s3_public_access": RuleMetadata(
        rule_id="S3_001",
        service="s3",
        frameworks=("CIS", "SOC2", "HIPAA"),
    ),
    "s3_versioning_disabled": RuleMetadata(
        rule_id="S3_003",
        service="s3",
        frameworks=("CIS",),
    ),
    "s3_logging_disabled": RuleMetadata(
        rule_id="S3_004",
        service="s3",
        frameworks=("CIS", "SOC2"),
    ),
    "single_point_of_failure": RuleMetadata(
        rule_id="REL_001",
        service="reliability",
        frameworks=("AWS-WAF",),
    ),
}

DEFAULT_RULE = RuleMetadata(
    rule_id="GENERIC_SECURITY_RULE",
    service="security",
    frameworks=(),
)


def get_rule_metadata(finding_type: str) -> RuleMetadata:
    """Return metadata for finding type."""
    return RULE_METADATA.get(finding_type, DEFAULT_RULE)
