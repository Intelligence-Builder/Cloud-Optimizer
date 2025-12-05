"""Cross-Account Role Assumption.

Issue #148: 9.2.2 Cross-account role assumption

Implements secure cross-account role assumption to enable Cloud Optimizer to scan
resources in other AWS accounts using IAM roles with proper trust relationships.
"""

import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class AssumedRoleCredentials:
    """Cached credentials from AssumeRole.

    Attributes:
        access_key_id: Temporary access key ID
        secret_access_key: Temporary secret access key
        session_token: Session token
        expiration: Credential expiration timestamp
        role_arn: ARN of the assumed role
        assumed_at: When the role was assumed
    """

    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime
    role_arn: str
    assumed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if credentials are expired."""
        return datetime.now(timezone.utc) >= self.expiration

    @property
    def expires_soon(self) -> bool:
        """Check if credentials expire within 5 minutes."""
        now = datetime.now(timezone.utc)
        time_remaining = (self.expiration - now).total_seconds()
        return time_remaining < 300  # 5 minutes

    @property
    def time_remaining(self) -> float:
        """Get remaining time in seconds."""
        return (self.expiration - datetime.now(timezone.utc)).total_seconds()


class CredentialCache:
    """Cache for assumed role credentials.

    Provides in-memory caching with automatic expiration handling.
    """

    def __init__(self) -> None:
        """Initialize credential cache."""
        self._cache: Dict[str, AssumedRoleCredentials] = {}

    def get(self, role_arn: str) -> Optional[AssumedRoleCredentials]:
        """Get cached credentials for a role.

        Args:
            role_arn: ARN of the role

        Returns:
            Cached credentials if valid, None otherwise
        """
        creds = self._cache.get(role_arn)
        if creds and not creds.expires_soon:
            return creds
        return None

    def put(self, credentials: AssumedRoleCredentials) -> None:
        """Cache credentials.

        Args:
            credentials: Credentials to cache
        """
        self._cache[credentials.role_arn] = credentials

    def invalidate(self, role_arn: str) -> None:
        """Invalidate cached credentials for a role.

        Args:
            role_arn: ARN of the role to invalidate
        """
        self._cache.pop(role_arn, None)

    def clear(self) -> None:
        """Clear all cached credentials."""
        self._cache.clear()


class CrossAccountRoleManager:
    """Manages cross-account role assumption.

    Provides secure role assumption with caching, automatic refresh,
    and error handling.
    """

    # Default session duration (1 hour)
    DEFAULT_DURATION = 3600
    # Maximum session duration (12 hours)
    MAX_DURATION = 43200
    # Minimum session duration (15 minutes)
    MIN_DURATION = 900

    def __init__(
        self,
        source_session: Optional[boto3.Session] = None,
        credential_cache: Optional[CredentialCache] = None,
    ) -> None:
        """Initialize cross-account role manager.

        Args:
            source_session: Source boto3 session (defaults to default session)
            credential_cache: Credential cache (creates new if not provided)
        """
        self.source_session = source_session or boto3.Session()
        self.credential_cache = credential_cache or CredentialCache()
        self._sts_client = self.source_session.client(
            "sts",
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                connect_timeout=5,
                read_timeout=30,
            ),
        )

    def generate_external_id(self) -> str:
        """Generate a secure random external ID.

        Returns:
            Cryptographically secure external ID
        """
        return secrets.token_urlsafe(32)

    def assume_role(
        self,
        role_arn: str,
        session_name: Optional[str] = None,
        external_id: Optional[str] = None,
        duration_seconds: int = DEFAULT_DURATION,
        mfa_serial_number: Optional[str] = None,
        mfa_token: Optional[str] = None,
        policy: Optional[str] = None,
        use_cache: bool = True,
    ) -> AssumedRoleCredentials:
        """Assume an IAM role.

        Args:
            role_arn: ARN of the role to assume
            session_name: Optional session name (auto-generated if not provided)
            external_id: External ID for additional security
            duration_seconds: Session duration (900-43200 seconds)
            mfa_serial_number: MFA device serial number
            mfa_token: MFA token code
            policy: Session policy to apply (further restricts permissions)
            use_cache: Whether to use cached credentials

        Returns:
            Assumed role credentials

        Raises:
            ClientError: If role assumption fails
        """
        # Check cache first
        if use_cache:
            cached = self.credential_cache.get(role_arn)
            if cached:
                logger.debug(f"Using cached credentials for {role_arn}")
                return cached

        # Validate duration
        duration_seconds = max(
            self.MIN_DURATION, min(duration_seconds, self.MAX_DURATION)
        )

        # Generate session name if not provided
        if not session_name:
            session_name = f"CloudOptimizer-{int(time.time())}"

        # Build assume role parameters
        params: Dict[str, Any] = {
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": duration_seconds,
        }

        if external_id:
            params["ExternalId"] = external_id

        if mfa_serial_number and mfa_token:
            params["SerialNumber"] = mfa_serial_number
            params["TokenCode"] = mfa_token

        if policy:
            params["Policy"] = policy

        # Assume role
        logger.info(f"Assuming role {role_arn}")
        try:
            response = self._sts_client.assume_role(**params)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")

            # Provide helpful error messages
            if error_code == "AccessDenied":
                logger.error(
                    f"Access denied when assuming {role_arn}. "
                    "Check trust relationship and permissions."
                )
            elif error_code == "MalformedPolicyDocument":
                logger.error(f"Invalid session policy for {role_arn}")
            elif error_code == "InvalidIdentityToken":
                logger.error(
                    f"External ID mismatch or invalid for {role_arn}"
                )
            else:
                logger.error(f"Failed to assume {role_arn}: {error_message}")

            raise

        # Parse credentials
        creds = response["Credentials"]
        credentials = AssumedRoleCredentials(
            access_key_id=creds["AccessKeyId"],
            secret_access_key=creds["SecretAccessKey"],
            session_token=creds["SessionToken"],
            expiration=creds["Expiration"].replace(tzinfo=timezone.utc),
            role_arn=role_arn,
        )

        # Cache credentials
        if use_cache:
            self.credential_cache.put(credentials)

        logger.info(
            f"Successfully assumed {role_arn}, "
            f"expires in {credentials.time_remaining:.0f}s"
        )

        return credentials

    def get_session_for_role(
        self,
        role_arn: str,
        external_id: Optional[str] = None,
        duration_seconds: int = DEFAULT_DURATION,
        region_name: Optional[str] = None,
    ) -> boto3.Session:
        """Get a boto3 session for an assumed role.

        Args:
            role_arn: ARN of the role to assume
            external_id: External ID for additional security
            duration_seconds: Session duration
            region_name: AWS region for the session

        Returns:
            Configured boto3 session
        """
        credentials = self.assume_role(
            role_arn=role_arn,
            external_id=external_id,
            duration_seconds=duration_seconds,
        )

        return boto3.Session(
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            aws_session_token=credentials.session_token,
            region_name=region_name,
        )

    def validate_trust_relationship(
        self,
        role_arn: str,
        expected_principal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate role trust relationship configuration.

        Args:
            role_arn: ARN of the role to validate
            expected_principal: Expected trusted principal ARN

        Returns:
            Validation result with details
        """
        result: Dict[str, Any] = {
            "valid": False,
            "role_arn": role_arn,
            "issues": [],
            "trust_policy": None,
        }

        try:
            # Get caller identity to know who we are
            caller = self._sts_client.get_caller_identity()
            caller_arn = caller["Arn"]
            caller_account = caller["Account"]

            # Extract role name from ARN
            role_name = role_arn.split("/")[-1]
            role_account = role_arn.split(":")[4]

            # We need to use IAM in the target account to check trust policy
            # This requires existing access, so we try a test assume
            try:
                self.assume_role(
                    role_arn=role_arn,
                    duration_seconds=self.MIN_DURATION,
                    use_cache=False,
                )
                result["valid"] = True
                result["message"] = "Role assumption successful"
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "AccessDenied":
                    result["issues"].append(
                        "Trust relationship may not include caller principal"
                    )
                else:
                    result["issues"].append(str(e))

        except ClientError as e:
            result["issues"].append(f"Validation failed: {e}")

        return result

    def refresh_credentials(self, role_arn: str) -> Optional[AssumedRoleCredentials]:
        """Refresh credentials for a role (force refresh).

        Args:
            role_arn: ARN of the role

        Returns:
            Fresh credentials or None on failure
        """
        # Invalidate cache
        self.credential_cache.invalidate(role_arn)

        try:
            return self.assume_role(role_arn=role_arn, use_cache=True)
        except ClientError:
            return None


# CloudFormation template for cross-account role
CROSS_ACCOUNT_ROLE_CFN_TEMPLATE = """
AWSTemplateFormatVersion: '2010-09-09'
Description: Cross-account role for Cloud Optimizer scanning

Parameters:
  TrustedAccountId:
    Type: String
    Description: AWS Account ID that will assume this role
    AllowedPattern: '^[0-9]{12}$'

  ExternalId:
    Type: String
    Description: External ID for additional security
    MinLength: 16
    MaxLength: 128

  RoleName:
    Type: String
    Default: CloudOptimizerScanner
    Description: Name for the cross-account role

Resources:
  CrossAccountRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: !Ref RoleName
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              AWS: !Sub 'arn:aws:iam::${TrustedAccountId}:root'
            Action: sts:AssumeRole
            Condition:
              StringEquals:
                sts:ExternalId: !Ref ExternalId
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/SecurityAudit
        - arn:aws:iam::aws:policy/ReadOnlyAccess
      Policies:
        - PolicyName: CloudOptimizerDeny
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Sid: DenyDestructiveActions
                Effect: Deny
                Action:
                  - 'ec2:TerminateInstances'
                  - 'ec2:DeleteVolume'
                  - 's3:DeleteBucket'
                  - 's3:DeleteObject'
                  - 'rds:DeleteDB*'
                  - 'lambda:DeleteFunction'
                  - 'iam:Delete*'
                  - 'iam:Create*'
                  - 'iam:Update*'
                  - 'iam:Put*'
                  - 'iam:Attach*'
                  - 'iam:Detach*'
                Resource: '*'
      Tags:
        - Key: Application
          Value: CloudOptimizer
        - Key: Purpose
          Value: SecurityScanning

Outputs:
  RoleArn:
    Description: ARN of the cross-account role
    Value: !GetAtt CrossAccountRole.Arn
    Export:
      Name: !Sub '${AWS::StackName}-RoleArn'

  ExternalId:
    Description: External ID (keep secure)
    Value: !Ref ExternalId
"""

# Terraform template for cross-account role
CROSS_ACCOUNT_ROLE_TF_TEMPLATE = """
# Cross-account role for Cloud Optimizer scanning

variable "trusted_account_id" {
  description = "AWS Account ID that will assume this role"
  type        = string
  validation {
    condition     = length(var.trusted_account_id) == 12
    error_message = "Account ID must be 12 digits."
  }
}

variable "external_id" {
  description = "External ID for additional security"
  type        = string
  sensitive   = true
}

variable "role_name" {
  description = "Name for the cross-account role"
  type        = string
  default     = "CloudOptimizerScanner"
}

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${var.trusted_account_id}:root"]
    }

    actions = ["sts:AssumeRole"]

    condition {
      test     = "StringEquals"
      variable = "sts:ExternalId"
      values   = [var.external_id]
    }
  }
}

data "aws_iam_policy_document" "deny_destructive" {
  statement {
    sid    = "DenyDestructiveActions"
    effect = "Deny"

    actions = [
      "ec2:TerminateInstances",
      "ec2:DeleteVolume",
      "s3:DeleteBucket",
      "s3:DeleteObject",
      "rds:DeleteDB*",
      "lambda:DeleteFunction",
      "iam:Delete*",
      "iam:Create*",
      "iam:Update*",
      "iam:Put*",
      "iam:Attach*",
      "iam:Detach*",
    ]

    resources = ["*"]
  }
}

resource "aws_iam_role" "scanner" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Application = "CloudOptimizer"
    Purpose     = "SecurityScanning"
  }
}

resource "aws_iam_role_policy_attachment" "security_audit" {
  role       = aws_iam_role.scanner.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}

resource "aws_iam_role_policy_attachment" "read_only" {
  role       = aws_iam_role.scanner.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_role_policy" "deny_destructive" {
  name   = "CloudOptimizerDeny"
  role   = aws_iam_role.scanner.id
  policy = data.aws_iam_policy_document.deny_destructive.json
}

output "role_arn" {
  description = "ARN of the cross-account role"
  value       = aws_iam_role.scanner.arn
}
"""


def get_cloudformation_template() -> str:
    """Get CloudFormation template for cross-account role setup.

    Returns:
        CloudFormation template YAML string
    """
    return CROSS_ACCOUNT_ROLE_CFN_TEMPLATE


def get_terraform_template() -> str:
    """Get Terraform template for cross-account role setup.

    Returns:
        Terraform template HCL string
    """
    return CROSS_ACCOUNT_ROLE_TF_TEMPLATE
