"""
Intelligence Builder Service - Integration with IB Platform.

Provides Cloud Optimizer specific functionality built on the IB SDK.
"""

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

from cloud_optimizer.config import Settings, get_settings

logger = logging.getLogger(__name__)


# Import SDK - use try/except for graceful degradation during development
try:
    from intelligence_builder_sdk import (
        ClientConfig,
        DetectedEntity,
        DetectedRelationship,
        DomainInfo,
        Entity,
        IntelligenceBuilderClient,
        PatternDetectionResponse,
        Relationship,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    logger.warning(
        "Intelligence Builder SDK not installed. "
        "Install with: pip install intelligence-builder-sdk"
    )


class IntelligenceBuilderService:
    """
    Service for interacting with Intelligence-Builder platform.

    Provides high-level methods for:
    - Security pattern detection
    - Entity/relationship management
    - Knowledge graph operations

    Usage:
        service = IntelligenceBuilderService(settings)
        await service.connect()

        # Analyze text for security entities
        result = await service.analyze_security_text(text)

        await service.disconnect()
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize Intelligence Builder service.

        Args:
            settings: Application settings (uses default if not provided)
        """
        self._settings = settings or get_settings()
        self._client: Optional["IntelligenceBuilderClient"] = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to IB platform."""
        return self._connected

    @property
    def is_available(self) -> bool:
        """Check if SDK is available."""
        return SDK_AVAILABLE

    async def connect(self) -> None:
        """
        Connect to Intelligence-Builder platform.

        Raises:
            RuntimeError: If SDK not available
            ConnectionError: If connection fails
        """
        if not SDK_AVAILABLE:
            raise RuntimeError(
                "Intelligence Builder SDK not installed. "
                "Install with: pip install intelligence-builder-sdk"
            )

        if self._connected:
            return

        try:
            config = ClientConfig(
                base_url=self._settings.ib_platform_url,
                api_key=self._settings.ib_api_key or "",
                timeout=30,
                enable_caching=True,
                cache_ttl=300,
            )
            self._client = IntelligenceBuilderClient(config)
            await self._client.connect()
            self._connected = True

            logger.info(
                f"Connected to Intelligence-Builder at {self._settings.ib_platform_url}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Intelligence-Builder: {e}")
            raise ConnectionError(f"IB connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Intelligence-Builder platform."""
        if self._client and self._connected:
            await self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from Intelligence-Builder")

    async def __aenter__(self) -> "IntelligenceBuilderService":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if not self._connected or not self._client:
            raise RuntimeError(
                "Not connected to Intelligence-Builder. Call connect() first."
            )

    # =========================================================================
    # Security Analysis
    # =========================================================================

    async def analyze_security_text(
        self,
        text: str,
        source_type: Optional[str] = None,
    ) -> "PatternDetectionResponse":
        """
        Analyze text for security entities and relationships.

        Uses the security domain patterns to detect:
        - CVE identifiers
        - Compliance requirements
        - Threat actors
        - Security controls

        Args:
            text: Text to analyze
            source_type: Type of source (e.g., "vulnerability_report")

        Returns:
            PatternDetectionResponse with detected entities
        """
        self._ensure_connected()
        return await self._client.detect_security_patterns(text, source_type)

    async def analyze_vulnerability_report(
        self,
        report_text: str,
        report_source: str = "security_scan",
    ) -> Dict[str, Any]:
        """
        Analyze a vulnerability report and extract structured data.

        Args:
            report_text: Full text of the vulnerability report
            report_source: Source of the report

        Returns:
            Structured analysis with:
            - vulnerabilities: List of detected CVEs
            - controls: Recommended controls
            - compliance_impacts: Affected compliance requirements
            - risk_score: Calculated risk score
        """
        self._ensure_connected()

        # Detect patterns
        result = await self._client.detect_security_patterns(
            text=report_text,
            source_type=report_source,
        )

        # Structure the response
        vulnerabilities = [
            e for e in result.entities if e.entity_type == "vulnerability"
        ]
        controls = [e for e in result.entities if e.entity_type == "control"]
        compliance = [
            e for e in result.entities if e.entity_type == "compliance_requirement"
        ]
        threats = [e for e in result.entities if e.entity_type == "threat_actor"]

        # Calculate risk score based on findings
        risk_score = self._calculate_risk_score(vulnerabilities, threats)

        return {
            "vulnerabilities": [self._entity_to_dict(v) for v in vulnerabilities],
            "controls": [self._entity_to_dict(c) for c in controls],
            "compliance_impacts": [self._entity_to_dict(c) for c in compliance],
            "threat_actors": [self._entity_to_dict(t) for t in threats],
            "relationships": [
                self._relationship_to_dict(r) for r in result.relationships
            ],
            "risk_score": risk_score,
            "entity_count": result.entity_count,
            "relationship_count": result.relationship_count,
            "processing_time_ms": result.processing_time_ms,
        }

    def _calculate_risk_score(
        self,
        vulnerabilities: List["DetectedEntity"],
        threats: List["DetectedEntity"],
    ) -> float:
        """Calculate risk score from detected entities."""
        if not vulnerabilities:
            return 0.0

        # Base score from vulnerability count
        base_score = min(len(vulnerabilities) * 15, 60)

        # Add for threat actors
        threat_bonus = min(len(threats) * 10, 20)

        # Add for high confidence vulnerabilities
        high_confidence = sum(1 for v in vulnerabilities if v.confidence > 0.9)
        confidence_bonus = min(high_confidence * 5, 20)

        return min(base_score + threat_bonus + confidence_bonus, 100.0)

    def _entity_to_dict(self, entity: "DetectedEntity") -> Dict[str, Any]:
        """Convert detected entity to dictionary."""
        return {
            "type": entity.entity_type,
            "name": entity.name,
            "confidence": entity.confidence,
            "properties": entity.properties,
        }

    def _relationship_to_dict(self, rel: "DetectedRelationship") -> Dict[str, Any]:
        """Convert detected relationship to dictionary."""
        return {
            "type": rel.relationship_type,
            "source": rel.from_entity_name,
            "target": rel.to_entity_name,
            "confidence": rel.confidence,
        }

    # =========================================================================
    # Knowledge Graph Operations
    # =========================================================================

    async def persist_analysis_results(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """
        Persist analysis results to the knowledge graph.

        Args:
            analysis: Analysis result from analyze_vulnerability_report

        Returns:
            Dictionary with created entity and relationship IDs
        """
        self._ensure_connected()

        # Create entities
        entity_ids = []
        entity_name_map: Dict[str, str] = {}

        for vuln in analysis.get("vulnerabilities", []):
            entity = await self._client.create_entity(
                {
                    "entity_type": "vulnerability",
                    "name": vuln["name"],
                    "metadata": vuln["properties"],
                }
            )
            entity_ids.append(str(entity.entity_id))
            entity_name_map[vuln["name"]] = str(entity.entity_id)

        for control in analysis.get("controls", []):
            entity = await self._client.create_entity(
                {
                    "entity_type": "control",
                    "name": control["name"],
                    "metadata": control["properties"],
                }
            )
            entity_ids.append(str(entity.entity_id))
            entity_name_map[control["name"]] = str(entity.entity_id)

        # Create relationships
        relationship_ids = []
        for rel in analysis.get("relationships", []):
            source_id = entity_name_map.get(rel["source"])
            target_id = entity_name_map.get(rel["target"])

            if source_id and target_id:
                relationship = await self._client.create_relationship(
                    {
                        "from_entity_id": source_id,
                        "to_entity_id": target_id,
                        "relationship_type": rel["type"],
                        "confidence": rel["confidence"],
                    }
                )
                relationship_ids.append(str(relationship.relationship_id))

        return {
            "entity_ids": entity_ids,
            "relationship_ids": relationship_ids,
        }

    async def get_vulnerability_context(
        self,
        cve_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get context around a vulnerability from the knowledge graph.

        Args:
            cve_id: CVE identifier to look up
            depth: Traversal depth

        Returns:
            Context including related controls, assets, and threats
        """
        self._ensure_connected()

        # Search for the vulnerability entity
        entities = await self._client.search_entities(
            query_text=cve_id,
            entity_types=["vulnerability"],
            limit=1,
        )

        if not entities:
            return {"found": False, "cve_id": cve_id}

        entity = entities[0]

        # Traverse to find related entities
        traversal = await self._client.traverse_graph(
            entity_id=str(entity.entity_id),
            depth=depth,
        )

        # Categorize related entities
        controls = []
        assets = []
        threats = []
        remediations = []

        for node in traversal.nodes:
            if node.entity_type == "control":
                controls.append(node.name)
            elif node.entity_type == "asset":
                assets.append(node.name)
            elif node.entity_type == "threat_actor":
                threats.append(node.name)
            elif node.entity_type == "remediation":
                remediations.append(node.name)

        return {
            "found": True,
            "cve_id": cve_id,
            "entity_id": str(entity.entity_id),
            "name": entity.name,
            "metadata": entity.metadata,
            "related_controls": controls,
            "affected_assets": assets,
            "threat_actors": threats,
            "remediations": remediations,
            "traversal_depth": depth,
            "total_related": traversal.total_nodes,
        }

    # =========================================================================
    # Domain Information
    # =========================================================================

    async def list_available_domains(self) -> List[Dict[str, Any]]:
        """
        List domains available on the IB platform.

        Returns:
            List of domain information dictionaries
        """
        self._ensure_connected()

        response = await self._client.list_domains()
        return [
            {
                "name": d.name,
                "version": d.version,
                "description": d.description,
                "entity_types": d.entity_type_count,
                "relationship_types": d.relationship_type_count,
                "pattern_count": d.pattern_count,
                "enabled": d.enabled,
            }
            for d in response.domains
        ]

    async def get_security_schema(self) -> Dict[str, Any]:
        """
        Get the security domain schema.

        Returns:
            Schema with entity types and relationship types
        """
        self._ensure_connected()

        entity_types = await self._client.list_entity_types(domain="security")
        rel_types = await self._client.list_relationship_types(domain="security")

        return {
            "domain": "security",
            "entity_types": [
                {
                    "name": et.name,
                    "description": et.description,
                    "properties": et.property_count,
                }
                for et in entity_types
            ],
            "relationship_types": [
                {
                    "name": rt.name,
                    "description": rt.description,
                    "source_types": rt.source_entity_types,
                    "target_types": rt.target_entity_types,
                }
                for rt in rel_types
            ],
        }

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> Dict[str, Any]:
        """
        Check IB platform health status.

        Returns:
            Health status dictionary
        """
        if not self._connected or not self._client:
            return {
                "status": "disconnected",
                "platform_url": self._settings.ib_platform_url,
            }

        try:
            health = await self._client.health_check()
            return {
                "status": health.status,
                "timestamp": health.timestamp.isoformat(),
                "platform_url": self._settings.ib_platform_url,
                "components": health.components,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "platform_url": self._settings.ib_platform_url,
            }


# Singleton service instance
_ib_service: Optional[IntelligenceBuilderService] = None


def get_ib_service() -> IntelligenceBuilderService:
    """
    Get the global Intelligence Builder service instance.

    Returns:
        IntelligenceBuilderService singleton
    """
    global _ib_service
    if _ib_service is None:
        _ib_service = IntelligenceBuilderService()
    return _ib_service


async def reset_ib_service() -> None:
    """Reset the global service instance (for testing)."""
    global _ib_service
    if _ib_service and _ib_service.is_connected:
        await _ib_service.disconnect()
    _ib_service = None
