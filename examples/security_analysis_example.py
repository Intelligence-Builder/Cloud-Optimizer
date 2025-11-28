"""
Security Analysis Example - Cloud Optimizer + Intelligence-Builder Integration.

This example demonstrates how to use Cloud Optimizer's security analysis
capabilities powered by Intelligence-Builder's pattern detection engine.

Prerequisites:
    1. Intelligence-Builder platform running at http://localhost:8000
    2. Valid IB_API_KEY environment variable
    3. Security domain registered in IB

Usage:
    python examples/security_analysis_example.py
"""

import asyncio
import os
from typing import Any, Dict

# Example vulnerability report text
SAMPLE_VULNERABILITY_REPORT = """
Security Assessment Report - Q4 2025
=====================================

Critical Findings:

1. CVE-2023-44487 (HTTP/2 Rapid Reset Attack)
   Severity: HIGH
   CVSS Score: 7.5
   Affected Systems: All web servers using HTTP/2

   The HTTP/2 protocol vulnerability allows attackers to perform denial
   of service attacks. APT29 has been observed exploiting this vulnerability
   in recent campaigns.

   Recommended Controls:
   - Enable rate limiting on HTTP/2 connections
   - Update web server software to patched versions
   - Implement WAF rules to detect rapid reset patterns

2. CVE-2024-21762 (FortiOS SSL VPN Vulnerability)
   Severity: CRITICAL
   CVSS Score: 9.6

   Critical out-of-bound write vulnerability in FortiOS SSL VPN.
   Allows remote code execution without authentication.

   Compliance Impact: This affects HIPAA and SOC 2 compliance requirements
   for access control and network security.

   Remediation:
   - Upgrade FortiOS to version 7.4.3 or later
   - Enable multi-factor authentication
   - Review VPN access logs for suspicious activity

3. Missing Encryption at Rest
   Severity: MEDIUM

   Several database instances are not using encryption at rest,
   which violates PCI-DSS Requirement 3.4.

   Required Control: Enable TDE (Transparent Data Encryption) on all
   database instances containing sensitive data.

Summary:
- 2 Critical/High CVEs requiring immediate attention
- SOC 2, HIPAA, and PCI-DSS compliance impacts identified
- APT29 threat actor association detected
"""


async def analyze_with_cloud_optimizer():
    """
    Demonstrate security analysis using Cloud Optimizer API.

    This example shows the API-based approach using HTTP requests.
    """
    import httpx

    # Configuration
    co_base_url = os.getenv("CO_BASE_URL", "http://localhost:8080")

    print("=" * 60)
    print("Cloud Optimizer Security Analysis Example")
    print("=" * 60)
    print(f"\nConnecting to Cloud Optimizer at: {co_base_url}")

    async with httpx.AsyncClient(base_url=co_base_url, timeout=30) as client:
        # Check health
        print("\n1. Checking service health...")
        try:
            health = await client.get("/api/v1/security/health")
            print(f"   Health status: {health.json()}")
        except Exception as e:
            print(f"   Could not connect: {e}")
            print("\n   Note: Make sure Cloud Optimizer is running!")
            return

        # Analyze text
        print("\n2. Analyzing security text...")
        response = await client.post(
            "/api/v1/security/analyze",
            json={
                "text": "We found CVE-2023-44487 affecting our web servers. "
                       "This impacts SOC 2 compliance.",
                "source_type": "quick_scan",
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   Detected {result['entity_count']} entities")
            print(f"   Detected {result['relationship_count']} relationships")
            for entity in result["entities"]:
                print(f"   - {entity['type']}: {entity['name']} "
                      f"(confidence: {entity['confidence']:.2f})")
        else:
            print(f"   Error: {response.status_code} - {response.text}")

        # Analyze full vulnerability report
        print("\n3. Analyzing vulnerability report...")
        response = await client.post(
            "/api/v1/security/vulnerability-report",
            json={
                "report_text": SAMPLE_VULNERABILITY_REPORT,
                "report_source": "security_assessment",
            },
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n   Analysis Results:")
            print(f"   - Vulnerabilities found: {len(result['vulnerabilities'])}")
            print(f"   - Controls identified: {len(result['controls'])}")
            print(f"   - Compliance impacts: {len(result['compliance_impacts'])}")
            print(f"   - Threat actors: {len(result['threat_actors'])}")
            print(f"   - Risk Score: {result['risk_score']:.1f}/100")
            print(f"   - Processing time: {result['processing_time_ms']:.1f}ms")

            print("\n   Detected Vulnerabilities:")
            for vuln in result["vulnerabilities"]:
                print(f"   - {vuln['name']} ({vuln['type']})")

            if result["compliance_impacts"]:
                print("\n   Compliance Impacts:")
                for comp in result["compliance_impacts"]:
                    print(f"   - {comp['name']}")

            if result["threat_actors"]:
                print("\n   Associated Threat Actors:")
                for ta in result["threat_actors"]:
                    print(f"   - {ta['name']}")
        else:
            print(f"   Error: {response.status_code} - {response.text}")

        # Get security schema
        print("\n4. Fetching security domain schema...")
        response = await client.get("/api/v1/security/schema")

        if response.status_code == 200:
            schema = response.json()
            print(f"\n   Entity Types ({len(schema['entity_types'])}):")
            for et in schema["entity_types"][:5]:  # Show first 5
                print(f"   - {et['name']}: {et['description'][:50]}...")

            print(f"\n   Relationship Types ({len(schema['relationship_types'])}):")
            for rt in schema["relationship_types"][:5]:
                print(f"   - {rt['name']}: {rt['source_types']} -> {rt['target_types']}")
        else:
            print(f"   Error: {response.status_code} - {response.text}")

    print("\n" + "=" * 60)
    print("Example completed!")
    print("=" * 60)


async def analyze_with_service_directly():
    """
    Demonstrate security analysis using the service directly.

    This example shows the programmatic approach for internal use.
    """
    from cloud_optimizer.services.intelligence_builder import IntelligenceBuilderService

    print("=" * 60)
    print("Direct Service Usage Example")
    print("=" * 60)

    service = IntelligenceBuilderService()

    if not service.is_available:
        print("\nIntelligence Builder SDK not installed.")
        print("Install with: pip install intelligence-builder-sdk")
        return

    try:
        async with service:
            print("\n1. Connected to Intelligence-Builder")

            # Analyze text
            print("\n2. Analyzing sample text...")
            result = await service.analyze_security_text(
                "CVE-2024-21762 is a critical vulnerability affecting FortiOS. "
                "Organizations must update immediately to maintain SOC 2 compliance."
            )

            print(f"   Found {result.entity_count} entities")
            for entity in result.entities:
                print(f"   - {entity.entity_type}: {entity.name}")

            # Get vulnerability context (if entity exists in graph)
            print("\n3. Looking up vulnerability context...")
            context = await service.get_vulnerability_context("CVE-2024-21762")
            if context["found"]:
                print(f"   Found: {context['name']}")
                print(f"   Related controls: {len(context['related_controls'])}")
            else:
                print("   Vulnerability not yet in knowledge graph")

    except ConnectionError as e:
        print(f"\nConnection failed: {e}")
        print("Make sure Intelligence-Builder platform is running.")


if __name__ == "__main__":
    print("\nRunning Security Analysis Examples\n")

    # Run API-based example
    asyncio.run(analyze_with_cloud_optimizer())

    print("\n")

    # Uncomment to run direct service example
    # asyncio.run(analyze_with_service_directly())
