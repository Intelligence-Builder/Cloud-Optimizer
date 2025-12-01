"""Runtime helpers for Smart-Scaffold migration tooling.

Provides lightweight implementations that allow the migration CLI to run
without depending on the live Smart-Scaffold services or Intelligence-Builder
SDK. The helpers can ingest Smart-Scaffold exports from JSON files, manage
ID mapping persistence, and offer local or SDK-backed IB service adapters.
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from importlib import import_module
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Protocol

import httpx

logger = logging.getLogger(__name__)


class IBServiceProtocol(Protocol):
    """Protocol describing the operations migration tools rely upon."""

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        ...

    async def query_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100,
        **filters: Any,
    ) -> Dict[str, Any]:
        ...

    async def query_relationships(
        self, relationship_type: Optional[str] = None, **filters: Any
    ) -> Dict[str, Any]:
        ...


class LocalIBService:
    """In-memory implementation of :class:`IBServiceProtocol`.

    Useful for unit tests, local dry-runs, or environments without the IB SDK
    installed. Entities and relationships are persisted in dictionaries and
    lists respectively so the validator and hybrid adapters can inspect
    previously created artifacts.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._relationships: List[Dict[str, Any]] = []
        self._counter = 0

    async def __aenter__(self) -> "LocalIBService":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self._entities.clear()
        self._relationships.clear()

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        self._counter += 1
        entity_id = f"ib-{self._counter:06d}"
        record = {
            "entity_id": entity_id,
            "entity_type": entity_data.get("entity_type", "entity"),
            "name": entity_data.get("name", ""),
            "properties": entity_data.get("properties", {}),
            "metadata": entity_data.get("metadata", {}),
        }
        self._entities[entity_id] = record
        return record

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        relationship_id = f"rel-{len(self._relationships) + 1:06d}"
        record = {
            "relationship_id": relationship_id,
            "source_id": rel_data.get("source_id")
            or rel_data.get("from_entity_id"),
            "target_id": rel_data.get("target_id")
            or rel_data.get("to_entity_id"),
            "relationship_type": rel_data.get("relationship_type", "").lower(),
            "metadata": rel_data.get("metadata", {}),
        }
        self._relationships.append(record)
        return record

    async def query_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100,
        **filters: Any,
    ) -> Dict[str, Any]:
        entities = list(self._entities.values())
        if entity_type:
            entities = [
                e for e in entities if e.get("entity_type") == entity_type
            ]
        if filters:
            entities = [
                e for e in entities if _matches_filters(e, filters)
            ]
        return {"total": len(entities), "entities": entities[:limit]}

    async def query_relationships(
        self, relationship_type: Optional[str] = None, **filters: Any
    ) -> Dict[str, Any]:
        relationships = list(self._relationships)
        if relationship_type:
            relationships = [
                r for r in relationships if r.get("relationship_type") == relationship_type
            ]
        filters = {k: v for k, v in filters.items() if k not in {"limit"}}
        if filters:
            relationships = [
                r for r in relationships if _matches_filters(r, filters)
            ]
        return {"total": len(relationships), "relationships": relationships}

    async def search_entities(
        self,
        query_text: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        **_: Any,
    ) -> Dict[str, Any]:
        """Basic text search implementation for hybrid workflows."""
        entities = list(self._entities.values())
        if entity_types:
            entities = [
                e for e in entities if e.get("entity_type") in entity_types
            ]
        if query_text:
            lowered = query_text.lower()
            entities = [
                e for e in entities if lowered in (e.get("name", "").lower())
            ]
        return {"total": len(entities), "entities": entities[:limit]}

    async def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Return stored entity by ID."""
        return self._entities.get(entity_id)


def _matches_filters(record: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """Check whether a record matches dotted filter expressions."""

    def resolve(data: Dict[str, Any], dotted_key: str) -> Any:
        parts = dotted_key.split(".")
        current: Any = data
        for part in parts:
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    for key, expected in filters.items():
        value = resolve(record, key)
        if value != expected:
            return False
    return True


class StaticSSKnowledgeGraph:
    """In-memory representation of Smart-Scaffold exports."""

    def __init__(
        self,
        entities: Iterable[Dict[str, Any]],
        relationships: Iterable[Dict[str, Any]],
    ) -> None:
        self._entities = list(entities)
        self._relationships = list(relationships)
        self._entity_index = {e["id"]: e for e in self._entities if "id" in e}

    async def export_all_entities(self) -> List[Dict[str, Any]]:
        return list(self._entities)

    async def export_all_relationships(self) -> List[Dict[str, Any]]:
        return list(self._relationships)

    async def count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for entity in self._entities:
            entity_type = entity.get("type", "Unknown")
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts

    async def count_relationships_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for rel in self._relationships:
            rel_type = rel.get("type", "related_to")
            counts[rel_type] = counts.get(rel_type, 0) + 1
        return counts

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        return self._entity_index.get(node_id)

    async def query(self, query_text: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Simple substring search across entity names."""
        lowered = query_text.lower()
        results = [
            entity
            for entity in self._entities
            if lowered in entity.get("name", "").lower()
        ]
        return results[:limit]


def load_json_records(path: Path) -> List[Dict[str, Any]]:
    """Load JSON data from *path* if it exists, returning a list."""
    if not path.exists():
        logger.warning("JSON export not found: %s", path)
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        # Allow {"entities": [...]} style exports
        if "entities" in data:
            return list(data["entities"])
        if "relationships" in data:
            return list(data["relationships"])
    return list(data)


def save_mapping(mapping: Dict[str, str], output_path: Path) -> None:
    """Persist entity ID mapping to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def load_mapping(path: Path) -> Dict[str, str]:
    """Load entity ID mapping from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Entity mapping file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_kv_pairs(pairs: Optional[List[str]]) -> Dict[str, Any]:
    """Parse ``KEY=VALUE`` pairs supplied on the CLI."""
    if not pairs:
        return {}
    result: Dict[str, Any] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Invalid setting '{pair}'. Expected KEY=VALUE.")
        key, value = pair.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def import_string(path: str) -> Any:
    """Import ``module:object`` references."""
    module_name, _, attr = path.partition(":")
    if not attr:
        raise ValueError(
            f"Invalid import path '{path}'. Expected format 'module:attribute'."
        )
    module = import_module(module_name)
    return getattr(module, attr)


@asynccontextmanager
async def ib_service_manager(
    backend: str,
    options: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[IBServiceProtocol]:
    """Context manager providing the requested IB service implementation."""

    if backend == "memory":
        service = LocalIBService()
        yield service
        return

    if backend == "sdk":
        service = await _create_sdk_service(options or {})
        try:
            yield service
        finally:
            await service.__aexit__(None, None, None)
        return

    factory = import_string(backend)
    maybe_service = factory(**(options or {}))
    if hasattr(maybe_service, "__aenter__"):
        async with maybe_service as ctx:
            yield ctx
    else:
        yield maybe_service


async def _create_sdk_service(options: Dict[str, Any]) -> "IBSDKService":
    """Create the SDK-backed service adapter, with HTTP fallback."""
    base_url = options.get("base_url") or os.getenv("IB_PLATFORM_URL", "http://localhost:8000")
    api_key = options.get("api_key") or os.getenv("IB_API_KEY")
    tenant_id = options.get("tenant_id")
    timeout = int(options.get("timeout", 30))

    if not api_key:
        raise RuntimeError("IB API key required for sdk backend. Provide --ib-option api_key=... or set IB_API_KEY.")

    service = IBSDKService(
        base_url=base_url,
        api_key=api_key,
        tenant_id=tenant_id,
        timeout=timeout,
    )
    try:
        await service.__aenter__()
        return service
    except Exception as exc:
        logger.warning(
            "SDK backend unavailable (%s). Falling back to HTTP client using API key.",
            exc,
        )
        fallback = IBHTTPService(base_url=base_url, api_key=api_key, timeout=timeout)
        await fallback.__aenter__()
        return fallback


class IBSDKService:
    """Adapter around ``IntelligenceBuilderClient`` for migration tooling."""

    def __init__(
        self,
        base_url: Optional[str],
        api_key: Optional[str],
        tenant_id: Optional[str],
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._tenant_id = tenant_id
        self._timeout = timeout
        self._client: Any = None

    async def __aenter__(self) -> "IBSDKService":
        try:  # pragma: no cover - runtime dependency
            from intelligence_builder_sdk import ClientConfig, IntelligenceBuilderClient
        except ImportError as exc:
            raise RuntimeError(
                "intelligence-builder-sdk is required for backend 'sdk'. "
                "Install it with `pip install intelligence-builder-sdk`."
            ) from exc

        config = ClientConfig(
            base_url=self._base_url or "",
            api_key=self._api_key or "",
            tenant_id=self._tenant_id,
            timeout=self._timeout,
        )
        self._client = IntelligenceBuilderClient(config)
        await self._client.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        entity = await self._client.create_entity(entity_data)
        return _serialize_entity(entity)

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        relationship = await self._client.create_relationship(rel_data)
        return _serialize_relationship(relationship)

    async def query_entities(
        self, entity_type: Optional[str] = None, limit: int = 100, **filters: Any
    ) -> Dict[str, Any]:
        result = await self._client.search_entities(
            query_text=filters.get("query_text"),
            entity_types=[entity_type] if entity_type else None,
            limit=limit,
            filters=filters.get("filters"),
        )
        # SDK returns either list or dict depending on version
        if isinstance(result, dict):
            entities = result.get("entities", [])
            total = result.get("total", len(entities))
        else:
            entities = result
            total = len(result)
        return {"entities": [_serialize_entity(e) for e in entities], "total": total}

    async def query_relationships(
        self, relationship_type: Optional[str] = None, **filters: Any
    ) -> Dict[str, Any]:
        result = await self._client.query_relationships(
            relationship_type=relationship_type,
            filters=filters or None,
        )
        relationships = result.get("relationships", [])
        return {
            "relationships": [
                _serialize_relationship(rel) for rel in relationships
            ],
            "total": result.get("total", len(relationships)),
        }

    async def search_entities(
        self,
        query_text: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        **_: Any,
    ) -> Dict[str, Any]:
        """Proxy search_entities to the underlying client."""
        result = await self._client.search_entities(
            query_text=query_text,
            entity_types=entity_types,
            limit=limit,
        )
        if isinstance(result, dict):
            entities = result.get("entities", [])
            total = result.get("total", len(entities))
        else:
            entities = result
            total = len(result)
        return {"entities": [_serialize_entity(e) for e in entities], "total": total}


def _serialize_entity(entity: Any) -> Dict[str, Any]:
    """Best-effort serialization of SDK entities."""
    if isinstance(entity, dict):
        return entity
    return {
        "entity_id": str(
            getattr(entity, "entity_id", getattr(entity, "id", ""))
        ),
        "entity_type": getattr(entity, "entity_type", ""),
        "name": getattr(entity, "name", ""),
        "properties": getattr(entity, "properties", {}),
        "metadata": getattr(entity, "metadata", {}),
    }


def _serialize_relationship(relationship: Any) -> Dict[str, Any]:
    """Best-effort serialization of SDK relationships."""
    if isinstance(relationship, dict):
        return relationship
    return {
        "relationship_id": str(
            getattr(relationship, "relationship_id", getattr(relationship, "id", ""))
        ),
        "source_id": getattr(relationship, "source_id", None)
        or getattr(relationship, "from_entity_id", None),
        "target_id": getattr(relationship, "target_id", None)
        or getattr(relationship, "to_entity_id", None),
        "relationship_type": getattr(relationship, "relationship_type", ""),
        "metadata": getattr(relationship, "metadata", {}),
    }


def ensure_default_paths(base_dir: Path) -> Dict[str, Path]:
    """Ensure default Smart-Scaffold data directories exist."""
    backups = base_dir / "backups"
    temp = base_dir / "temp"
    backups.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    return {"backups": backups, "temp": temp}


class IBHTTPService:
    """Fallback HTTP client that talks directly to IB API using API keys."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "IBHTTPService":
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _headers(self) -> Dict[str, str]:
        return {"X-API-Key": self._api_key}

    async def create_entity(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_entity_payload(entity_data)
        response = await self._client.post("/v1/knowledge/entities/", json=payload, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        return {
            "entity_id": str(data.get("entity_id")),
            "name": data.get("name"),
            "entity_type": data.get("entity_type"),
        }

    async def create_relationship(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_relationship_payload(rel_data)
        response = await self._client.post("/v1/knowledge/relationships/", json=payload, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        return {
            "relationship_id": str(data.get("relationship_id")),
            "relationship_type": data.get("relationship_type"),
        }

    async def query_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100,
        **_: Any,
    ) -> Dict[str, Any]:
        limit = max(1, limit or 1)
        params = {"limit": limit, "offset": 0}
        if entity_type:
            params["entity_type"] = entity_type
        response = await self._client.get("/v1/knowledge/entities/", headers=self._headers(), params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "entities": data.get("items", []),
            "total": data.get("total", 0),
        }

    async def search_entities(
        self,
        query_text: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        **_: Any,
    ) -> Dict[str, Any]:
        entity_type = entity_types[0] if entity_types else None
        return await self.query_entities(entity_type=entity_type, limit=limit, query_text=query_text)

    async def query_relationships(
        self,
        relationship_type: Optional[str] = None,
        limit: int = 100,
        **_: Any,
    ) -> Dict[str, Any]:
        relationships = await self._fetch_all_relationships()
        if relationship_type:
            filtered = [rel for rel in relationships if rel.get("relationship_type") == relationship_type]
        else:
            filtered = relationships
        return {
            "relationships": filtered[:limit],
            "total": len(filtered),
        }

    async def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        response = await self._client.get(
            f"/v1/knowledge/entities/{entity_id}",
            headers=self._headers(),
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def delete_entity(self, entity_id: str) -> None:
        response = await self._client.delete(
            f"/v1/knowledge/entities/{entity_id}",
            headers=self._headers(),
        )
        if response.status_code not in (200, 202, 204, 404):
            response.raise_for_status()

    def _build_entity_payload(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = dict(entity_data.get("metadata") or {})
        properties = entity_data.get("properties") or {}
        for key, value in properties.items():
            metadata.setdefault(key, value)
        name = entity_data.get("name") or properties.get("name") or entity_data.get("id", "Unnamed Entity")
        tags = properties.get("tags") if isinstance(properties.get("tags"), list) else []
        return {
            "entity_type": entity_data.get("entity_type", "entity"),
            "name": name,
            "description": properties.get("description"),
            "metadata": metadata,
            "tags": tags,
            "external_id": metadata.get("original_id") or entity_data.get("id"),
        }

    def _build_relationship_payload(self, rel_data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = dict(rel_data.get("metadata") or {})
        source_id = rel_data.get("source_id") or rel_data.get("from_entity_id")
        target_id = rel_data.get("target_id") or rel_data.get("to_entity_id")
        if not source_id or not target_id:
            raise ValueError("Relationship requires source_id and target_id")
        payload = {
            "relationship_type": rel_data.get("relationship_type") or rel_data.get("type") or "relates_to",
            "from_entity_id": source_id,
            "to_entity_id": target_id,
            "metadata": metadata,
        }
        if metadata.get("description"):
            payload["description"] = metadata["description"]
        if "confidence" in metadata:
            payload["confidence"] = metadata["confidence"]
        return payload

    async def _fetch_all_relationships(self) -> List[Dict[str, Any]]:
        relationships: List[Dict[str, Any]] = []
        offset = 0
        limit = 100
        while True:
            params = {"limit": limit, "offset": offset}
            response = await self._client.get(
                "/v1/knowledge/relationships/",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            relationships.extend(items)
            has_more = data.get("has_more")
            if not has_more or not items:
                break
            offset += limit
        return relationships
