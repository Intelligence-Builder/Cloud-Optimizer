# LLM Analysis Code Samples

## 1. Document Analysis Example

### Basic Usage
```python
from ib_platform.document.analysis import DocumentAnalyzer
from cloud_optimizer.config import get_settings

# Initialize analyzer
settings = get_settings()
analyzer = DocumentAnalyzer(api_key=settings.anthropic_api_key)

# Analyze a document
document_text = """
Our AWS infrastructure uses S3 for data storage and Lambda for processing.
All data must comply with HIPAA and PCI-DSS requirements.
Current security concern: S3 buckets are publicly accessible.
"""

result = await analyzer.analyze_document(document_text)

print(f"AWS Resources: {result.aws_resources}")
# Output: AWS Resources: ['Lambda', 'S3']

print(f"Compliance: {result.compliance_frameworks}")
# Output: Compliance: ['HIPAA', 'PCI-DSS']

print(f"Security Concerns: {result.security_concerns}")
# Output: Security Concerns: ['S3 buckets are publicly accessible']

print(f"Summary: {result.summary}")
# Output: Summary: This document describes an AWS infrastructure...
```

### With Error Handling
```python
from ib_platform.document.analysis import DocumentAnalyzer, AnalysisError

try:
    analyzer = DocumentAnalyzer()  # Will use ANTHROPIC_API_KEY from env
    result = await analyzer.analyze_document(text)
except AnalysisError as e:
    print(f"Analysis failed: {e}")
    # Fallback to keyword extraction
    entities = analyzer.extract_entities(text, "aws_resources")
```

## 2. Security Finding Explanation Example

### Basic Usage
```python
from ib_platform.security.explanation import FindingExplainer
from cloud_optimizer.models.finding import Finding, FindingSeverity

# Initialize explainer
explainer = FindingExplainer(api_key="sk-ant-...")

# Create a finding
finding = Finding(
    finding_id=uuid4(),
    title="Public S3 Bucket",
    severity=FindingSeverity.HIGH,
    resource_type="s3_bucket",
    resource_id="my-data-bucket",
    service="s3",
    description="S3 bucket allows public read access",
    recommendation="Enable bucket versioning and remove public access",
    compliance_frameworks=["HIPAA", "PCI-DSS"],
)

# Generate explanation for general audience
explanation = await explainer.explain_finding(
    finding=finding,
    target_audience="general",
    include_technical_details=False
)

print(explanation["what_it_means"])
# "Your S3 bucket 'my-data-bucket' is configured to allow anyone on
#  the internet to view and download files stored in it..."

print(explanation["why_it_matters"])
# "This creates a significant data exposure risk that could lead to
#  data breaches, regulatory violations, and unauthorized access..."
```

### Multi-Audience Example
```python
# For technical team
tech_explanation = await explainer.explain_finding(
    finding=finding,
    target_audience="technical",
    include_technical_details=True
)

# For executives
exec_explanation = await explainer.explain_finding(
    finding=finding,
    target_audience="executive",
    include_technical_details=False
)

print(exec_explanation["why_it_matters"])
# "This high-priority issue creates immediate business risk of data
#  breaches and could result in HIPAA and PCI-DSS compliance violations..."
```

### Batch Processing
```python
# Explain multiple findings at once
findings = [finding1, finding2, finding3]
explanations = await explainer.explain_findings_batch(
    findings=findings,
    target_audience="general"
)

for exp in explanations:
    print(f"Finding {exp['finding_id']}: {exp['what_it_means']}")
```

### Fallback Mode (No API Key)
```python
# Initialize without API key - uses template-based explanations
explainer = FindingExplainer()  # No API key

if not explainer.is_available():
    print("LLM not available - using fallback mode")

# Still works, but with template-based explanations
explanation = await explainer.explain_finding(finding)
# Returns structured explanation using severity-based templates
```

## 3. Entity Extraction Example

### AWS Service Extraction
```python
from ib_platform.nlu.entities import EntityExtractor

extractor = EntityExtractor()

query = "How do I secure my S3 buckets and Lambda functions?"
entities = extractor.extract(query)

print(entities.aws_services)
# ['Lambda', 'S3']

print(entities.has_entities())
# True

print(entities.get_all_entities())
# ['Lambda', 'S3']
```

### Compliance Framework Extraction
```python
query = "What are the SOC2 and HIPAA requirements for RDS?"
entities = extractor.extract(query)

print(entities.aws_services)
# ['RDS']

print(entities.compliance_frameworks)
# ['HIPAA', 'SOC2']
```

### Resource ID Extraction
```python
query = "Check security group sg-1234567890abcdef0 in vpc-abcd1234"
entities = extractor.extract(query)

print(entities.resource_ids)
# ['sg-1234567890abcdef0', 'vpc-abcd1234']

# ARN extraction
query = "Analyze bucket arn:aws:s3:::my-bucket"
entities = extractor.extract(query)

print(entities.resource_ids)
# ['arn:aws:s3:::my-bucket']
```

### Finding ID Extraction
```python
query = "Explain finding SEC-001 and CVE-2023-12345"
entities = extractor.extract(query)

print(entities.finding_ids)
# ['CVE-2023-12345', 'SEC-001']
```

### Complex Query
```python
query = """
How do I fix finding SEC-001 for S3 bucket my-data-bucket
to meet HIPAA compliance requirements for instance i-1234567890abcdef0?
"""

entities = extractor.extract(query)

print(f"Services: {entities.aws_services}")
# Services: ['S3']

print(f"Compliance: {entities.compliance_frameworks}")
# Compliance: ['HIPAA']

print(f"Findings: {entities.finding_ids}")
# Findings: ['SEC-001']

print(f"Resources: {entities.resource_ids}")
# Resources: ['i-1234567890abcdef0', 'my-data-bucket']
```

## 4. Answer Service Example

### Streaming Response
```python
from anthropic import AsyncAnthropic
from ib_platform.answer.service import AnswerService
from ib_platform.kb.service import get_kb_service
from ib_platform.nlu.service import NLUService

# Initialize services
client = AsyncAnthropic(api_key="sk-ant-...")
kb_service = get_kb_service()
answer_service = AnswerService(
    anthropic_client=client,
    kb_service=kb_service,
)

# Process question with NLU
nlu_service = NLUService(anthropic_client=client)
question = "How do I secure my S3 buckets?"
nlu_result = await nlu_service.process(question)

# Generate streaming answer
async for chunk in answer_service.generate_streaming(
    question=question,
    nlu_result=nlu_result,
    aws_account_id=account_id,
):
    print(chunk, end="", flush=True)
```

### Non-Streaming Response
```python
# Generate complete answer at once
answer = await answer_service.generate(
    question="How do I enable MFA for IAM users?",
    nlu_result=nlu_result,
)

print(answer)
# "To enable MFA for IAM users, follow these steps: ..."
```

### With Conversation History
```python
history = [
    {"role": "user", "content": "What is MFA?"},
    {"role": "assistant", "content": "MFA (Multi-Factor Authentication) is..."},
]

answer = await answer_service.generate(
    question="How do I enable it for IAM?",
    nlu_result=nlu_result,
    conversation_history=history,
)
# Answer will reference previous context about MFA
```

## 5. Unified Security Analysis Example

### Comprehensive Analysis
```python
from ib_platform.security import SecurityAnalysisService

# Initialize service
service = SecurityAnalysisService(
    anthropic_api_key="sk-ant-...",
    min_cluster_size=2,
)

# Perform comprehensive analysis
analysis = await service.analyze_findings(
    findings=all_findings,
    include_explanations=True,
    include_remediation=True,
    include_clusters=True,
    target_audience="general",
    prefer_terraform=True,
)

# Access results
print(f"Total findings: {analysis['finding_count']}")
print(f"Critical issues: {analysis['summary']['priority_distribution']['critical']}")

# Get prioritized findings
for pf in analysis['prioritized_findings']:
    print(f"{pf['priority_rank']}: {pf['finding']['title']}")
    print(f"  Risk score: {pf['risk_score']}")

# Get explanations
for exp in analysis['explanations']:
    print(f"\n{exp['finding_id']}:")
    print(f"  {exp['what_it_means']}")
    print(f"  {exp['why_it_matters']}")

# Get remediation plans
for plan in analysis['remediation_plans']:
    print(f"\nFinding: {plan['finding_id']}")
    print(f"Estimated time: {plan['total_estimated_time_minutes']} minutes")
    for step in plan['steps']:
        print(f"  - {step['description']}")

# Get clusters
for cluster in analysis['clusters']:
    print(f"\nCluster: {cluster['pattern']}")
    print(f"  Affected resources: {cluster['affected_resource_count']}")
    print(f"  Root cause: {cluster['root_cause']}")
```

### Executive Summary
```python
# Generate executive-focused summary for top 10 findings
exec_analysis = await service.analyze_top_findings(
    findings=all_findings,
    top_n=10,
    target_audience="executive",
)

summary = exec_analysis['executive_summary']
print(f"Critical issues: {summary['critical_issues']}")
print(f"High priority: {summary['high_priority_issues']}")
print(f"Recommendation: {summary['recommendation']}")

# Key risks for executives
for risk in summary['key_risks']:
    print(f"  - {risk}")
```

### Single Finding Analysis
```python
# Just explain one finding
explanation = await service.explain_finding(
    finding=critical_finding,
    target_audience="executive",
)

# Just get remediation
plan = await service.generate_remediation_plan(
    finding=critical_finding,
    prefer_terraform=True,
)

# Just score and prioritize
prioritized = await service.score_and_prioritize(findings)
```

## 6. API Integration Example

### Document Upload & Analysis
```python
# POST /api/v1/documents/upload
files = {'file': open('architecture.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/v1/documents/upload',
    files=files,
    headers={'Authorization': f'Bearer {token}'}
)

document_id = response.json()['document_id']

# POST /api/v1/documents/{document_id}/analyze
response = requests.post(
    f'http://localhost:8000/api/v1/documents/{document_id}/analyze',
    headers={'Authorization': f'Bearer {token}'}
)

analysis = response.json()
print(analysis['aws_resources'])
print(analysis['security_concerns'])
```

### Chat with Streaming
```python
import requests

# POST /api/v1/chat/stream
response = requests.post(
    'http://localhost:8000/api/v1/chat/stream',
    json={
        'question': 'How do I secure my S3 buckets?',
        'aws_account_id': str(account_id),
    },
    headers={'Authorization': f'Bearer {token}'},
    stream=True,
)

# Stream chunks
for chunk in response.iter_content(chunk_size=None):
    if chunk:
        print(chunk.decode(), end='', flush=True)
```

## Error Handling Patterns

### Graceful Degradation
```python
from ib_platform.security.explanation import FindingExplainer

explainer = FindingExplainer()

if explainer.is_available():
    # Use LLM
    explanation = await explainer.explain_finding(finding)
else:
    # Use fallback
    explanation = explainer._generate_fallback_explanation(finding)

# Either way, user gets an explanation
print(explanation['what_it_means'])
```

### Retry Logic (Custom)
```python
import asyncio
from anthropic import APIError

async def analyze_with_retry(analyzer, text, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await analyzer.analyze_document(text)
        except APIError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Timeout Handling
```python
import asyncio

try:
    result = await asyncio.wait_for(
        analyzer.analyze_document(text),
        timeout=30.0  # 30 second timeout
    )
except asyncio.TimeoutError:
    print("Analysis timed out - document may be too large")
```

## Performance Optimization

### Batch Processing
```python
# Instead of:
for finding in findings:
    explanation = await explainer.explain_finding(finding)

# Use batch processing:
explanations = await explainer.explain_findings_batch(findings)
```

### Concurrent Processing
```python
import asyncio

# Process multiple documents concurrently
tasks = [
    analyzer.analyze_document(doc1_text),
    analyzer.analyze_document(doc2_text),
    analyzer.analyze_document(doc3_text),
]

results = await asyncio.gather(*tasks, return_exceptions=True)

for i, result in enumerate(results):
    if isinstance(result, Exception):
        print(f"Document {i} failed: {result}")
    else:
        print(f"Document {i} analyzed: {result.summary}")
```
