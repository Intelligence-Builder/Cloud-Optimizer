"""
Integration tests for Security API endpoints.

Tests all 10 endpoints defined in Issue #11.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cloud_optimizer.api.routers.security import router
from cloud_optimizer.api.schemas.security import (
    ComplianceCheckRequest,
    SecurityControlCreate,
    SecurityScanRequest,
    VulnerabilityCreate,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_ib_service() -> MagicMock:
    """Create a mock Intelligence-Builder service."""
    service = MagicMock()
    service.is_connected = True

    # Mock analyze_security_text
    async def mock_analyze_security_text(text: str, source_type: str = None) -> Any:
        # Create mock entities with proper attribute access
        entity1 = MagicMock()
        entity1.entity_type = "vulnerability"
        entity1.name = "CVE-2024-1234"
        entity1.confidence = 0.95
        entity1.properties = {"severity": "high"}

        entity2 = MagicMock()
        entity2.entity_type = "threat_actor"
        entity2.name = "APT28"
        entity2.confidence = 0.88
        entity2.properties = {"motivation": "espionage"}

        # Create mock relationship
        rel = MagicMock()
        rel.relationship_type = "exploits"
        source_mock = MagicMock()
        source_mock.name = "APT28"
        target_mock = MagicMock()
        target_mock.name = "CVE-2024-1234"
        rel.source_entity = source_mock
        rel.target_entity = target_mock
        rel.confidence = 0.92

        mock_result = MagicMock()
        mock_result.entities = [entity1, entity2]
        mock_result.relationships = [rel]

        return mock_result

    service.analyze_security_text = mock_analyze_security_text

    # Mock query_entities
    async def mock_query_entities(
        entity_type: str,
        filters: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        entities = []

        if entity_type == "vulnerability":
            entities = [
                {
                    "id": str(uuid4()),
                    "name": "SQL Injection",
                    "cve_id": "CVE-2024-1234",
                    "severity": "high",
                    "cvss_score": 8.5,
                    "description": "SQL injection vulnerability",
                    "affected_systems": ["web-server-1"],
                    "remediation": "Update to latest version",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        elif entity_type == "security_control":
            entities = [
                {
                    "id": str(uuid4()),
                    "name": "Access Control",
                    "control_id": "AC-1",
                    "description": "Implement access control",
                    "category": "access_control",
                    "implementation_status": "implemented",
                    "framework": "SOC2",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        elif entity_type == "compliance_requirement":
            entities = [
                {
                    "id": str(uuid4()),
                    "framework": "soc2",
                    "requirement_code": "CC1.1",
                    "description": "Access controls implemented",
                    "status": "compliant",
                }
            ]
        elif entity_type == "security_finding":
            entities = [
                {
                    "id": str(uuid4()),
                    "finding_type": "misconfiguration",
                    "severity": "high",
                    "title": "Weak password policy",
                    "description": "Password policy does not meet requirements",
                    "affected_resources": ["auth-service"],
                    "recommendations": ["Implement stronger password policy"],
                    "confidence_score": 0.9,
                    "status": "open",
                    "created_at": now,
                }
            ]

        return {"entities": entities}

    service.query_entities = mock_query_entities

    # Mock get_entity_by_id
    async def mock_get_entity_by_id(entity_id: str) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "id": entity_id,
            "name": "SQL Injection",
            "cve_id": "CVE-2024-1234",
            "severity": "high",
            "cvss_score": 8.5,
            "description": "SQL injection vulnerability",
            "affected_systems": ["web-server-1"],
            "remediation": "Update to latest version",
            "created_at": now,
            "updated_at": now,
        }

    service.get_entity_by_id = mock_get_entity_by_id

    # Mock create_entity
    async def mock_create_entity(entity_data: Dict[str, Any]) -> Dict[str, Any]:
        return entity_data

    service.create_entity = mock_create_entity

    # Mock get_security_graph
    async def mock_get_security_graph(
        entity_types: list = None,
        max_nodes: int = 100,
    ) -> Dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": str(uuid4()),
                    "type": "vulnerability",
                    "label": "CVE-2024-1234",
                    "properties": {"severity": "high"},
                },
                {
                    "id": str(uuid4()),
                    "type": "threat_actor",
                    "label": "APT28",
                    "properties": {"motivation": "espionage"},
                },
            ],
            "edges": [
                {
                    "id": str(uuid4()),
                    "type": "exploits",
                    "source": str(uuid4()),
                    "target": str(uuid4()),
                    "properties": {},
                }
            ],
        }

    service.get_security_graph = mock_get_security_graph

    return service


@pytest.fixture
def app(mock_ib_service: MagicMock) -> FastAPI:
    """Create a FastAPI test application."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/security")

    # Add mock IB service to app state
    app.state.ib_service = mock_ib_service

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


# ============================================================================
# Test Cases
# ============================================================================


def test_scan_endpoint(client: TestClient) -> None:
    """Test POST /api/v1/security/scan endpoint."""
    request_data = {
        "text": "CVE-2024-1234 is a critical vulnerability exploited by APT28",
        "document_id": "doc-123",
        "min_confidence": 0.7,
        "include_relationships": True,
    }

    response = client.post("/api/v1/security/scan", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "scan_id" in data
    assert data["document_id"] == "doc-123"
    assert data["entity_count"] == 2
    assert data["relationship_count"] == 1
    assert len(data["entities_found"]) == 2
    assert len(data["relationships_found"]) == 1


def test_list_vulnerabilities_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/vulnerabilities endpoint."""
    response = client.get("/api/v1/security/vulnerabilities")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "vulnerability_id" in data[0]
    assert "name" in data[0]
    assert "severity" in data[0]


def test_list_vulnerabilities_with_filter(client: TestClient) -> None:
    """Test GET /api/v1/security/vulnerabilities with severity filter."""
    response = client.get("/api/v1/security/vulnerabilities?severity=high")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_vulnerability_by_id_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/vulnerabilities/{id} endpoint."""
    vuln_id = str(uuid4())
    response = client.get(f"/api/v1/security/vulnerabilities/{vuln_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["vulnerability_id"] == vuln_id
    assert "name" in data
    assert "severity" in data


def test_create_vulnerability_endpoint(client: TestClient) -> None:
    """Test POST /api/v1/security/vulnerabilities endpoint."""
    request_data = {
        "name": "XSS Vulnerability",
        "cve_id": "CVE-2024-5678",
        "severity": "medium",
        "cvss_score": 6.5,
        "description": "Cross-site scripting vulnerability in web application",
        "affected_systems": ["web-app-1", "web-app-2"],
        "remediation": "Sanitize user input",
    }

    response = client.post("/api/v1/security/vulnerabilities", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert "vulnerability_id" in data
    assert data["name"] == "XSS Vulnerability"
    assert data["cve_id"] == "CVE-2024-5678"
    assert data["severity"] == "medium"


def test_list_controls_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/controls endpoint."""
    response = client.get("/api/v1/security/controls")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "control_uuid" in data[0]
    assert "name" in data[0]


def test_create_control_endpoint(client: TestClient) -> None:
    """Test POST /api/v1/security/controls endpoint."""
    request_data = {
        "name": "Multi-Factor Authentication",
        "control_id": "AC-2",
        "description": "Require MFA for all users",
        "category": "authentication",
        "implementation_status": "implemented",
        "framework": "SOC2",
    }

    response = client.post("/api/v1/security/controls", json=request_data)

    assert response.status_code == 201
    data = response.json()
    assert "control_uuid" in data
    assert data["name"] == "Multi-Factor Authentication"
    assert data["implementation_status"] == "implemented"


def test_list_compliance_requirements_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/compliance endpoint."""
    response = client.get("/api/v1/security/compliance")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_compliance_requirements_with_filters(client: TestClient) -> None:
    """Test GET /api/v1/security/compliance with filters."""
    response = client.get("/api/v1/security/compliance?framework=soc2&status=compliant")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_check_compliance_endpoint(client: TestClient) -> None:
    """Test POST /api/v1/security/compliance/check endpoint."""
    request_data = {
        "tenant_id": "tenant-123",
        "framework": "soc2",
        "scope": [],
    }

    response = client.post("/api/v1/security/compliance/check", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert "check_id" in data
    assert data["tenant_id"] == "tenant-123"
    assert data["framework"] == "soc2"
    assert "total_requirements" in data
    assert "implemented" in data
    assert "gaps" in data
    assert "coverage_percentage" in data
    assert "recommendations" in data


def test_list_findings_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/findings endpoint."""
    response = client.get("/api/v1/security/findings")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "finding_id" in data[0]
    assert "severity" in data[0]


def test_list_findings_with_filters(client: TestClient) -> None:
    """Test GET /api/v1/security/findings with filters."""
    response = client.get("/api/v1/security/findings?severity=high&status=open")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_security_graph_endpoint(client: TestClient) -> None:
    """Test GET /api/v1/security/graph endpoint."""
    response = client.get("/api/v1/security/graph")

    assert response.status_code == 200
    data = response.json()
    assert "graph_id" in data
    assert "nodes" in data
    assert "edges" in data
    assert "node_count" in data
    assert "edge_count" in data
    assert "metadata" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_get_security_graph_with_filters(client: TestClient) -> None:
    """Test GET /api/v1/security/graph with filters."""
    response = client.get("/api/v1/security/graph?max_nodes=50")

    assert response.status_code == 200
    data = response.json()
    assert "graph_id" in data
    assert data["metadata"]["max_nodes_requested"] == 50


# ============================================================================
# Error Case Tests
# ============================================================================


def test_scan_endpoint_invalid_request(client: TestClient) -> None:
    """Test POST /api/v1/security/scan with invalid request."""
    request_data = {
        "text": "short",  # Too short
    }

    response = client.post("/api/v1/security/scan", json=request_data)
    assert response.status_code == 422  # Validation error


def test_create_vulnerability_invalid_cve(client: TestClient) -> None:
    """Test POST /api/v1/security/vulnerabilities with invalid CVE format."""
    request_data = {
        "name": "Test Vuln",
        "cve_id": "INVALID-FORMAT",  # Invalid CVE format
        "severity": "high",
        "description": "Test description",
    }

    response = client.post("/api/v1/security/vulnerabilities", json=request_data)
    assert response.status_code == 422  # Validation error


def test_create_vulnerability_invalid_severity(client: TestClient) -> None:
    """Test POST /api/v1/security/vulnerabilities with invalid severity."""
    request_data = {
        "name": "Test Vuln",
        "severity": "super-critical",  # Invalid severity
        "description": "Test description",
    }

    response = client.post("/api/v1/security/vulnerabilities", json=request_data)
    assert response.status_code == 422  # Validation error


def test_check_compliance_invalid_framework(client: TestClient) -> None:
    """Test POST /api/v1/security/compliance/check with invalid framework."""
    request_data = {
        "tenant_id": "tenant-123",
        "framework": "invalid-framework",  # Invalid framework
    }

    response = client.post("/api/v1/security/compliance/check", json=request_data)
    assert response.status_code == 422  # Validation error


# ============================================================================
# Service Unavailable Tests
# ============================================================================


def test_endpoints_when_service_unavailable() -> None:
    """Test that endpoints return 503 when IB service is unavailable."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/security")
    # No IB service in app state
    client = TestClient(app)

    # Test scan endpoint
    response = client.post(
        "/api/v1/security/scan",
        json={
            "text": "Test text for scanning security entities",
            "min_confidence": 0.7,
        },
    )
    assert response.status_code == 503

    # Test vulnerabilities endpoint
    response = client.get("/api/v1/security/vulnerabilities")
    assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
