# Runbook: Critical Security Finding

## Alert Details
- **Alarm Name**: `cloud-optimizer-*-security-finding-critical`
- **Severity**: Critical (P1)
- **Threshold**: Any critical security finding detected
- **Escalation Policy**: security

## Overview
This runbook addresses critical security findings detected by Cloud Optimizer's security scanning.

## Impact
- Potential data breach exposure
- Compliance violation
- Customer data at risk
- Regulatory notification requirements

## Immediate Response

### 1. Acknowledge and Assess (First 5 minutes)
1. Acknowledge the alert in PagerDuty/OpsGenie
2. Join the security incident bridge
3. Review the finding details

### 2. Initial Triage
```bash
# View the security finding details
curl -H "Authorization: Bearer $TOKEN" \
  https://api.cloud-optimizer.com/api/v1/findings/{finding_id}

# Check affected resources
aws securityhub get-findings --filters '{"Id": [{"Value": "{finding_id}", "Comparison": "EQUALS"}]}'
```

## Security Finding Categories

### Exposed Credentials
**Severity**: Critical
**Response Time**: Immediate

1. **Rotate Credentials Immediately**
   ```bash
   # Rotate AWS access keys
   aws iam update-access-key --access-key-id $OLD_KEY --status Inactive
   aws iam create-access-key --user-name $USER

   # Rotate database passwords
   kubectl create secret generic db-credentials \
     --from-literal=password=$NEW_PASSWORD -n cloud-optimizer --dry-run=client -o yaml | \
     kubectl apply -f -
   ```

2. **Audit Credential Usage**
   ```bash
   # Check CloudTrail for unauthorized access
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=$EXPOSED_KEY \
     --start-time $(date -u -d "7 days ago" +%Y-%m-%dT%H:%M:%SZ)
   ```

### Publicly Accessible Resources
**Severity**: Critical
**Response Time**: 15 minutes

1. **Remove Public Access**
   ```bash
   # S3 bucket
   aws s3api put-public-access-block --bucket $BUCKET \
     --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

   # Security group
   aws ec2 revoke-security-group-ingress --group-id $SG_ID \
     --protocol tcp --port 22 --cidr 0.0.0.0/0
   ```

### Unencrypted Data
**Severity**: High to Critical
**Response Time**: 30 minutes

1. **Enable Encryption**
   ```bash
   # Enable S3 encryption
   aws s3api put-bucket-encryption --bucket $BUCKET \
     --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

   # Enable RDS encryption (requires snapshot restore)
   # Document and plan migration
   ```

### IAM Policy Violations
**Severity**: High
**Response Time**: 30 minutes

1. **Review and Remediate Policy**
   ```bash
   # Get current policy
   aws iam get-role-policy --role-name $ROLE --policy-name $POLICY

   # Apply least privilege policy
   aws iam put-role-policy --role-name $ROLE --policy-name $POLICY \
     --policy-document file://remediated-policy.json
   ```

## Containment Steps

1. **Isolate Affected Resources**
   ```bash
   # Apply restrictive security group
   aws ec2 modify-instance-attribute --instance-id $INSTANCE \
     --groups $QUARANTINE_SG_ID
   ```

2. **Preserve Evidence**
   ```bash
   # Create forensic snapshot
   aws ec2 create-snapshot --volume-id $VOLUME \
     --description "Forensic snapshot - Incident $INCIDENT_ID"

   # Export CloudTrail logs
   aws s3 cp s3://cloudtrail-logs/ ./evidence/ --recursive \
     --include "*$(date +%Y-%m-%d)*"
   ```

3. **Enable Enhanced Monitoring**
   ```bash
   # Enable GuardDuty if not enabled
   aws guardduty create-detector --enable
   ```

## Communication Requirements

### Internal Notification
- Security team (immediate)
- Engineering leadership (within 15 minutes)
- Legal/Compliance (within 30 minutes if data breach suspected)

### External Notification
- Customer notification (as per DPA requirements)
- Regulatory bodies (per compliance requirements)
- Legal counsel review required

## Post-Incident Actions

1. **Root Cause Analysis**
   - Document timeline of events
   - Identify how the vulnerability was introduced
   - Review similar resources for same issue

2. **Preventive Measures**
   - Update security policies
   - Implement additional scanning
   - Update training materials

3. **Documentation**
   - Complete incident report
   - Update runbooks
   - Share lessons learned

## Escalation

This is a security incident requiring immediate escalation:
1. Page Security On-Call
2. Page Engineering Lead
3. Notify CISO within 15 minutes
4. Create security incident bridge

## Communication Template

```
[SECURITY INCIDENT] Cloud Optimizer - Critical Security Finding

Classification: [CONFIDENTIAL/INTERNAL]
Status: Investigating | Contained | Remediated
Impact: [Describe potential impact]
Detected: [TIMESTAMP]

Summary:
[Brief description of finding]

Current Actions:
- Security team engaged
- [Specific containment actions taken]

Next Update: [TIME]

Do not discuss this incident outside of secure channels.
```

## Related Alarms
- `cloud-optimizer-*-guardduty-finding`
- `cloud-optimizer-*-iam-policy-change`
- `cloud-optimizer-*-unusual-api-activity`
