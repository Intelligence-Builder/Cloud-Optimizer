# 7.1 AWS Account Connection

## Parent Epic
Epic 7: MVP Phase 2 - Security & Cost Scanning

## Overview

Implement secure AWS account connection that allows trial customers to connect their AWS account for scanning. Uses IAM roles with read-only permissions to ensure customer data security and follows AWS best practices for cross-account access.

## Background

Trial customers need to connect their AWS account to Cloud Optimizer for scanning. The connection must:
- Use least-privilege IAM permissions (read-only)
- Support cross-account access via IAM roles (preferred) or access keys
- Validate credentials before storing
- Encrypt credentials at rest
- Support easy disconnection

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| AWS-001 | Account connection | Support IAM role ARN (preferred) and access keys |
| AWS-002 | Credential validation | Validate credentials via STS GetCallerIdentity before storing |
| AWS-003 | Permission verification | Verify required permissions before accepting connection |
| AWS-004 | Secure storage | Encrypt credentials with AWS KMS or Fernet, never log credentials |

## Technical Specification

### IAM Role Policy (Customer Creates)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudOptimizerReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketPolicy",
        "s3:GetBucketEncryption",
        "s3:GetBucketPublicAccessBlock",
        "s3:GetBucketVersioning",
        "s3:GetBucketLogging",
        "s3:ListAllMyBuckets",
        "ec2:Describe*",
        "rds:Describe*",
        "iam:GetAccountPasswordPolicy",
        "iam:ListUsers",
        "iam:ListRoles",
        "iam:ListPolicies",
        "iam:GetPolicy",
        "iam:GetPolicyVersion",
        "iam:ListAccessKeys",
        "iam:GetAccessKeyLastUsed",
        "cloudtrail:DescribeTrails",
        "cloudtrail:GetTrailStatus",
        "config:DescribeConfigurationRecorders",
        "kms:ListKeys",
        "kms:GetKeyPolicy",
        "kms:DescribeKey",
        "ce:GetCostAndUsage",
        "ce:GetReservationUtilization",
        "ce:GetSavingsPlansPurchaseRecommendation",
        "support:DescribeTrustedAdvisorChecks",
        "support:DescribeTrustedAdvisorCheckResult"
      ],
      "Resource": "*"
    }
  ]
}
```

### Trust Policy (for IAM Role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::CLOUD_OPTIMIZER_ACCOUNT:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "${TENANT_EXTERNAL_ID}"
        }
      }
    }
  ]
}
```

### Database Schema

```sql
-- AWS account connections
CREATE TABLE aws_accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(tenant_id),
    aws_account_id VARCHAR(12) NOT NULL,  -- 12-digit AWS account ID
    friendly_name VARCHAR(255),
    connection_type VARCHAR(20) NOT NULL,  -- 'iam_role' or 'access_keys'

    -- For IAM role connection
    role_arn VARCHAR(2048),
    external_id VARCHAR(255),  -- Per-tenant external ID for security

    -- For access key connection (encrypted)
    access_key_id_encrypted BYTEA,
    secret_access_key_encrypted BYTEA,

    -- Connection status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, active, error, disconnected
    last_validated_at TIMESTAMPTZ,
    last_error TEXT,

    -- Metadata
    region VARCHAR(20) NOT NULL DEFAULT 'us-east-1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, aws_account_id)
);

CREATE INDEX idx_aws_accounts_tenant ON aws_accounts(tenant_id);
CREATE INDEX idx_aws_accounts_status ON aws_accounts(status);
```

### AWS Connection Service

```python
# src/cloud_optimizer/services/aws_connection.py
from cryptography.fernet import Fernet
import boto3

class AWSConnectionService:
    def __init__(self, db: AsyncSession, encryption_key: str):
        self.db = db
        self.fernet = Fernet(encryption_key.encode())

    async def connect_with_role(
        self,
        tenant_id: UUID,
        role_arn: str,
        external_id: str,
        friendly_name: str = None,
    ) -> AWSAccount:
        """Connect AWS account using IAM role."""
        # Validate role ARN format
        if not self._validate_role_arn(role_arn):
            raise InvalidRoleARNException()

        # Extract AWS account ID from ARN
        aws_account_id = self._extract_account_id(role_arn)

        # Check trial limit (1 AWS account for trial)
        await self._check_account_limit(tenant_id)

        # Validate connection by assuming role
        try:
            credentials = await self._assume_role(role_arn, external_id)
            await self._verify_permissions(credentials)
        except Exception as e:
            raise AWSConnectionException(f"Failed to connect: {str(e)}")

        # Store connection
        account = AWSAccount(
            tenant_id=tenant_id,
            aws_account_id=aws_account_id,
            friendly_name=friendly_name or f"AWS {aws_account_id}",
            connection_type="iam_role",
            role_arn=role_arn,
            external_id=external_id,
            status="active",
            last_validated_at=datetime.utcnow(),
        )
        self.db.add(account)
        await self.db.commit()

        return account

    async def connect_with_keys(
        self,
        tenant_id: UUID,
        access_key_id: str,
        secret_access_key: str,
        friendly_name: str = None,
    ) -> AWSAccount:
        """Connect AWS account using access keys (less secure)."""
        # Check trial limit
        await self._check_account_limit(tenant_id)

        # Validate credentials
        try:
            session = boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            aws_account_id = identity["Account"]

            # Verify required permissions
            await self._verify_permissions_with_session(session)
        except Exception as e:
            raise AWSConnectionException(f"Invalid credentials: {str(e)}")

        # Encrypt credentials
        encrypted_key_id = self.fernet.encrypt(access_key_id.encode())
        encrypted_secret = self.fernet.encrypt(secret_access_key.encode())

        # Store connection
        account = AWSAccount(
            tenant_id=tenant_id,
            aws_account_id=aws_account_id,
            friendly_name=friendly_name or f"AWS {aws_account_id}",
            connection_type="access_keys",
            access_key_id_encrypted=encrypted_key_id,
            secret_access_key_encrypted=encrypted_secret,
            status="active",
            last_validated_at=datetime.utcnow(),
        )
        self.db.add(account)
        await self.db.commit()

        return account

    async def _assume_role(self, role_arn: str, external_id: str) -> dict:
        """Assume IAM role and return temporary credentials."""
        sts = boto3.client("sts")
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="CloudOptimizerScan",
            ExternalId=external_id,
            DurationSeconds=3600,
        )
        return response["Credentials"]

    async def _verify_permissions(self, credentials: dict) -> bool:
        """Verify the role has required permissions."""
        session = boto3.Session(
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

        required_checks = [
            ("s3", "list_buckets", {}),
            ("ec2", "describe_instances", {}),
            ("iam", "get_account_password_policy", {}),
        ]

        for service, method, params in required_checks:
            try:
                client = session.client(service)
                getattr(client, method)(**params)
            except client.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "AccessDenied":
                    raise InsufficientPermissionsException(
                        f"Missing permission for {service}:{method}"
                    )
                raise

        return True

    async def get_session(self, account_id: UUID) -> boto3.Session:
        """Get boto3 session for connected account."""
        account = await self._get_account(account_id)

        if account.connection_type == "iam_role":
            credentials = await self._assume_role(
                account.role_arn, account.external_id
            )
            return boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
        else:
            access_key_id = self.fernet.decrypt(
                account.access_key_id_encrypted
            ).decode()
            secret_key = self.fernet.decrypt(
                account.secret_access_key_encrypted
            ).decode()
            return boto3.Session(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_key,
            )

    async def disconnect(self, tenant_id: UUID, account_id: UUID):
        """Disconnect AWS account."""
        await self.db.execute(
            update(AWSAccount)
            .where(AWSAccount.account_id == account_id)
            .where(AWSAccount.tenant_id == tenant_id)
            .values(
                status="disconnected",
                access_key_id_encrypted=None,
                secret_access_key_encrypted=None,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.commit()
```

## API Endpoints

```
POST /api/v1/aws/connect/role        # Connect with IAM role
POST /api/v1/aws/connect/keys        # Connect with access keys
GET  /api/v1/aws/accounts            # List connected accounts
GET  /api/v1/aws/accounts/:id        # Get account details
POST /api/v1/aws/accounts/:id/validate  # Re-validate connection
DELETE /api/v1/aws/accounts/:id      # Disconnect account
GET  /api/v1/aws/setup-instructions  # Get IAM policy/trust policy templates
```

## Files to Create

```
src/cloud_optimizer/services/
└── aws_connection.py            # AWS connection service

src/cloud_optimizer/models/
└── aws_account.py               # AWSAccount model

src/cloud_optimizer/api/routers/
└── aws.py                       # AWS connection endpoints

alembic/versions/
└── xxx_create_aws_accounts.py   # Migration

data/iam/
├── policy.json                  # IAM policy template
└── trust-policy.json            # Trust policy template

tests/services/
└── test_aws_connection.py       # Connection service tests
```

## Testing Requirements

### Unit Tests
- [ ] `test_role_arn_validation.py` - ARN format validation
- [ ] `test_credential_encryption.py` - Fernet encryption/decryption
- [ ] `test_permission_verification.py` - Permission check logic

### Integration Tests
- [ ] `test_aws_connection_role.py` - Full role connection flow (LocalStack)
- [ ] `test_aws_connection_keys.py` - Access key flow (LocalStack)
- [ ] `test_session_creation.py` - Session creation for scanning

### Mocking Strategy

```python
# tests/services/conftest.py
@pytest.fixture
def mock_sts_client():
    with patch("boto3.client") as mock:
        client = MagicMock()
        client.assume_role.return_value = {
            "Credentials": {
                "AccessKeyId": "ASIA...",
                "SecretAccessKey": "secret",
                "SessionToken": "token",
                "Expiration": datetime.utcnow() + timedelta(hours=1),
            }
        }
        client.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test",
        }
        mock.return_value = client
        yield client
```

## Acceptance Criteria Checklist

- [ ] User can connect AWS account with IAM role ARN
- [ ] User can connect AWS account with access keys
- [ ] Credentials validated via STS before storing
- [ ] Required permissions verified before accepting connection
- [ ] Access keys encrypted at rest (Fernet)
- [ ] Role ARN stored (not encrypted, not sensitive)
- [ ] External ID generated per-tenant
- [ ] Trial limit enforced (1 account)
- [ ] User can disconnect account
- [ ] Disconnection clears encrypted credentials
- [ ] Setup instructions provided via API
- [ ] 80%+ test coverage

## Security Considerations

1. **Credential Storage**:
   - Access keys encrypted with Fernet (AES-128-CBC)
   - Encryption key stored in AWS Secrets Manager (not in env vars)
   - Role ARNs not encrypted (not sensitive)

2. **Least Privilege**:
   - Read-only permissions only
   - No write/delete permissions on customer resources
   - External ID prevents confused deputy attacks

3. **Audit Logging**:
   - Log all connection/disconnection events
   - Log scan initiations (not results)
   - Never log credentials or decrypted values

## Dependencies

- 6.4 Basic Authentication (user context)
- 6.3 Trial Management (account limit check)

## Blocked By

- 6.4 Basic Authentication

## Blocks

- 7.2 Security Scanner (needs AWS session)
- 7.3 Cost Scanner (needs AWS session)

## Estimated Effort

1 week

## Labels

`aws`, `security`, `connection`, `mvp`, `phase-2`, `P0`
