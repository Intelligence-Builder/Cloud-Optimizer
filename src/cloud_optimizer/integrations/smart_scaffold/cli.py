"""Command line entrypoints for Smart-Scaffold migration scripts."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cloud_optimizer.integrations.smart_scaffold.entity_migrator import (
    EntityMigrator,
    MigrationResult,
)
from cloud_optimizer.integrations.smart_scaffold.relationship_migrator import (
    RelationshipMigrator,
)
from cloud_optimizer.integrations.smart_scaffold.runtime import (
    StaticSSKnowledgeGraph,
    ensure_default_paths,
    ib_service_manager,
    load_json_records,
    load_mapping,
    parse_kv_pairs,
    save_mapping,
)
from cloud_optimizer.integrations.smart_scaffold.validator import (
    CutoverManager,
    MigrationValidator,
    ParallelValidator,
)

logger = logging.getLogger(__name__)

BASE_DATA_DIR = Path("smart_scaffold_data")
PATHS = ensure_default_paths(BASE_DATA_DIR)
DEFAULT_ENTITY_EXPORT = PATHS["backups"] / "entities.json"
DEFAULT_RELATIONSHIP_EXPORT = PATHS["backups"] / "relationships.json"
DEFAULT_MAPPING_PATH = PATHS["temp"] / "entity_mapping.json"


def _add_common_ib_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ib-backend",
        default="memory",
        help=(
            "IB backend to use. 'memory' for local testing, 'sdk' for the "
            "real Intelligence-Builder SDK, or module:Class for custom services."
        ),
    )
    parser.add_argument(
        "--ib-option",
        action="append",
        dest="ib_options",
        help="Additional IB backend options (KEY=VALUE). Repeat for multiple options.",
    )


def _add_ss_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ss-client",
        help="Optional Smart-Scaffold client import path (module:Class). "
        "When omitted the CLI reads JSON exports instead.",
    )
    parser.add_argument(
        "--ss-client-option",
        action="append",
        dest="ss_client_options",
        help="Options passed to the Smart-Scaffold client (KEY=VALUE).",
    )


async def _load_ss_exports(
    entity_path: Optional[Path],
    relationship_path: Optional[Path],
    client_path: Optional[str] = None,
    client_options: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load Smart-Scaffold exports from JSON file or live client."""
    if client_path:
        client_cls = _import_string(client_path)
        options = parse_kv_pairs(client_options)
        client = client_cls(**options)
        if hasattr(client, "__aenter__"):
            async with client as ctx:
                entities = await ctx.export_all_entities()
                relationships = (
                    await ctx.export_all_relationships()
                    if relationship_path is not None
                    else []
                )
        else:
            entities = await client.export_all_entities()
            relationships = (
                await client.export_all_relationships()
                if relationship_path is not None
                else []
            )
        return list(entities), list(relationships)

    entities = load_json_records(entity_path or DEFAULT_ENTITY_EXPORT)
    relationships = load_json_records(relationship_path) if relationship_path else []
    return entities, relationships


@asynccontextmanager
async def _ss_client_manager(
    entity_path: Optional[Path],
    relationship_path: Optional[Path],
    client_path: Optional[str],
    client_options: Optional[List[str]],
) -> Iterable[Any]:
    """Yield a Smart-Scaffold client (real or static)."""
    if client_path:
        client_cls = _import_string(client_path)
        options = parse_kv_pairs(client_options)
        client = client_cls(**options)
        if hasattr(client, "__aenter__"):
            async with client as ctx:
                yield ctx
        else:
            try:
                yield client
            finally:
                close_method = getattr(client, "close", None)
                if callable(close_method):
                    maybe_coro = close_method()
                    if asyncio.iscoroutine(maybe_coro):  # pragma: no cover
                        await maybe_coro
    else:
        entities = load_json_records(entity_path or DEFAULT_ENTITY_EXPORT)
        relationships = load_json_records(
            relationship_path or DEFAULT_RELATIONSHIP_EXPORT
        )
        yield StaticSSKnowledgeGraph(entities, relationships)


def _import_string(path: str) -> Any:
    module_name, _, attr = path.partition(":")
    if not attr:
        raise ValueError(
            f"Invalid import path '{path}'. Expected format module:attribute."
        )
    module = __import__(module_name, fromlist=[attr])
    if (
        module_name == "smart_scaffold.knowledge_graph"
        and attr == "SSKnowledgeGraph"
        and not hasattr(module, attr)
    ):
        from cloud_optimizer.integrations.smart_scaffold.live_ss_client import (
            SSKnowledgeGraph,
        )

        setattr(module, attr, SSKnowledgeGraph)
    return getattr(module, attr)


def run_entity_migration_cli(argv: Optional[List[str]] = None) -> None:
    asyncio.run(_run_entity_migration_cli(argv))


async def _run_entity_migration_cli(argv: Optional[List[str]]) -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Smart-Scaffold entities to Intelligence-Builder."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_ENTITY_EXPORT,
        help=f"Path to Smart-Scaffold entity export (default: {DEFAULT_ENTITY_EXPORT})",
    )
    parser.add_argument(
        "--mapping-output",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help=f"Path to write entity ID mapping (default: {DEFAULT_MAPPING_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of entities to process per batch.",
    )
    _add_common_ib_args(parser)
    _add_ss_args(parser)

    args = parser.parse_args(argv)
    entities, _ = await _load_ss_exports(
        args.input, None, args.ss_client, args.ss_client_options
    )
    await _migrate_entities(
        entities=entities,
        mapping_path=args.mapping_output,
        ib_backend=args.ib_backend,
        ib_options=parse_kv_pairs(args.ib_options),
        batch_size=args.batch_size,
    )


def run_relationship_migration_cli(argv: Optional[List[str]] = None) -> None:
    asyncio.run(_run_relationship_migration_cli(argv))


async def _run_relationship_migration_cli(argv: Optional[List[str]]) -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Smart-Scaffold relationships to Intelligence-Builder."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_RELATIONSHIP_EXPORT,
        help=(
            "Path to Smart-Scaffold relationship export "
            f"(default: {DEFAULT_RELATIONSHIP_EXPORT})"
        ),
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help=f"Path to entity mapping generated by migrate_ss_entities.py (default: {DEFAULT_MAPPING_PATH})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Relationships processed per batch.",
    )
    _add_common_ib_args(parser)
    _add_ss_args(parser)

    args = parser.parse_args(argv)
    relationships_data = load_json_records(args.input)
    mapping = load_mapping(args.mapping)

    async with ib_service_manager(
        args.ib_backend, parse_kv_pairs(args.ib_options)
    ) as ib_service:
        migrator = RelationshipMigrator(
            ib_service,
            mapping,
            batch_size=args.batch_size,
        )
        result = await migrator.migrate_all(relationships_data)
        logger.info(
            "Migrated %s relationships (%s failed, %s skipped)",
            result.migrated,
            result.failed,
            result.skipped,
        )


def run_full_migration_cli(argv: Optional[List[str]] = None) -> None:
    asyncio.run(_run_full_migration_cli(argv))


async def _run_full_migration_cli(argv: Optional[List[str]]) -> None:
    parser = argparse.ArgumentParser(
        description="Run full Smart-Scaffold migration (entities + relationships)."
    )
    parser.add_argument(
        "--entities",
        type=Path,
        default=DEFAULT_ENTITY_EXPORT,
        help=f"Entity export path (default: {DEFAULT_ENTITY_EXPORT})",
    )
    parser.add_argument(
        "--relationships",
        type=Path,
        default=DEFAULT_RELATIONSHIP_EXPORT,
        help=f"Relationship export path (default: {DEFAULT_RELATIONSHIP_EXPORT})",
    )
    parser.add_argument(
        "--mapping-output",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help="Where to store the entity ID mapping.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for both entities and relationships.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run MigrationValidator after the migration completes.",
    )
    parser.add_argument(
        "--skip-relationships",
        action="store_true",
        help="Only migrate entities when set.",
    )
    _add_common_ib_args(parser)
    _add_ss_args(parser)

    args = parser.parse_args(argv)
    entities, relationships = await _load_ss_exports(
        args.entities,
        args.relationships if not args.skip_relationships else None,
        args.ss_client,
        args.ss_client_options,
    )
    ss_graph = StaticSSKnowledgeGraph(entities, relationships)

    validation_summary: Optional[Dict[str, Any]] = None
    async with ib_service_manager(
        args.ib_backend, parse_kv_pairs(args.ib_options)
    ) as ib_service:
        entity_result = await _migrate_entities(
            entities,
            args.mapping_output,
            args.ib_backend,
            parse_kv_pairs(args.ib_options),
            args.batch_size,
            ib_service_override=ib_service,
        )

        if not args.skip_relationships and relationships:
            mapping = entity_result.id_mapping
            migrator = RelationshipMigrator(
                ib_service,
                mapping,
                batch_size=args.batch_size,
            )
            rel_result = await migrator.migrate_all(relationships)
            logger.info(
                "Migrated %s relationships (%s failed, %s skipped)",
                rel_result.migrated,
                rel_result.failed,
                rel_result.skipped,
            )

        if args.validate:
            validator = MigrationValidator(
                ss_graph,
                ib_service,
                entity_result.id_mapping,
            )
            validation = await validator.validate_all()
            validation_summary = validation.to_dict()
            logger.info(
                "Validation result: %s", json.dumps(validation_summary, indent=2)
            )

    if validation_summary:
        print(json.dumps(validation_summary, indent=2))


async def _migrate_entities(
    entities: List[Dict[str, Any]],
    mapping_path: Path,
    ib_backend: str,
    ib_options: Dict[str, Any],
    batch_size: int,
    ib_service_override: Optional[Any] = None,
) -> MigrationResult:
    """Helper that migrates entities and persists mapping."""
    if ib_service_override:
        ib_service = ib_service_override
        migrator = EntityMigrator(ib_service, batch_size=batch_size)
        result = await migrator.migrate_all(entities)
        save_mapping(result.id_mapping, mapping_path)
        logger.info(
            "Migrated %s entities (%s failed)",
            result.migrated,
            result.failed,
        )
        return result

    async with ib_service_manager(ib_backend, ib_options) as ib_service:
        migrator = EntityMigrator(ib_service, batch_size=batch_size)
        result = await migrator.migrate_all(entities)
        save_mapping(result.id_mapping, mapping_path)
        logger.info(
            "Migrated %s entities (%s failed)",
            result.migrated,
            result.failed,
        )
        return result


def run_parallel_validator_cli(argv: Optional[List[str]] = None) -> None:
    asyncio.run(_run_parallel_validator_cli(argv))


async def _run_parallel_validator_cli(argv: Optional[List[str]]) -> None:
    parser = argparse.ArgumentParser(
        description="Compare SS and IB query results during parallel operation."
    )
    parser.add_argument(
        "--entities",
        type=Path,
        default=DEFAULT_ENTITY_EXPORT,
        help=f"Entity export path for static mode (default: {DEFAULT_ENTITY_EXPORT})",
    )
    parser.add_argument(
        "--relationships",
        type=Path,
        default=DEFAULT_RELATIONSHIP_EXPORT,
        help="Relationship export path for static mode.",
    )
    parser.add_argument(
        "--query",
        dest="queries",
        action="append",
        help="Query text to execute (repeat for multiple queries).",
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        help="Optional file with one query per line.",
    )
    parser.add_argument(
        "--entity-type",
        help="Optional entity type filter to apply for all queries.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum results per query.",
    )
    parser.add_argument(
        "--prime-from-entities",
        action="store_true",
        help="Load the provided entity export into the IB backend before validation.",
    )
    _add_common_ib_args(parser)
    _add_ss_args(parser)

    args = parser.parse_args(argv)
    if args.prime_from_entities and args.ss_client:
        parser.error("--prime-from-entities cannot be used with --ss-client")

    queries = _collect_queries(args.queries, args.queries_file)
    if not queries:
        parser.error("Provide at least one --query or --queries-file.")

    prime_entities: List[Dict[str, Any]] = []
    if args.prime_from_entities:
        prime_entities, _ = await _load_ss_exports(
            args.entities,
            None,
            None,
            None,
        )

    async with _ss_client_manager(
        args.entities,
        args.relationships,
        args.ss_client,
        args.ss_client_options,
    ) as ss_client:
        async with ib_service_manager(
            args.ib_backend, parse_kv_pairs(args.ib_options)
        ) as ib_service:
            if args.prime_from_entities and prime_entities:
                migrator = EntityMigrator(ib_service)
                await migrator.migrate_all(prime_entities)

            manager = CutoverManager(ss_client, ib_service)
            validator = ParallelValidator(
                ss_client,
                ib_service,
                manager,
            )
            results = []
            for query in queries:
                result = await validator.validate_query(
                    query=query,
                    entity_type=args.entity_type,
                    limit=args.limit,
                )
                results.append(result)

            summary = {
                "results": results,
                "discrepancies": manager.get_discrepancies(),
            }
            print(json.dumps(summary, indent=2))


def _collect_queries(
    inline_queries: Optional[List[str]],
    file_path: Optional[Path],
) -> List[str]:
    queries = [q for q in inline_queries or [] if q]
    if file_path and file_path.exists():
        for line in file_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                queries.append(line)
    return queries


def run_cleanup_cli(argv: Optional[List[str]] = None) -> None:
    asyncio.run(_run_cleanup_cli(argv))


async def _run_cleanup_cli(argv: Optional[List[str]]) -> None:
    parser = argparse.ArgumentParser(
        description="Cleanup or reset migration artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    clean_ib = subparsers.add_parser(
        "ib-entities", help="Delete migrated entities/relationships via IB API."
    )
    clean_ib.add_argument(
        "--entity-ids",
        type=Path,
        help="Optional path to JSON file containing entity IDs to delete (defaults to mapping file).",
    )
    _add_common_ib_args(clean_ib)

    clean_temp = subparsers.add_parser(
        "temp-files", help="Clear migration evidence (mapping, validation outputs)."
    )
    clean_temp.add_argument(
        "--pattern",
        default="*.json",
        help="Glob for temp files to delete (default: *.json).",
    )

    args = parser.parse_args(argv)
    if args.command == "temp-files":
        _cleanup_temp_files(pattern=args.pattern)
    elif args.command == "ib-entities":
        await _cleanup_ib_entities(args)


def _cleanup_temp_files(pattern: str) -> None:
    files = list(PATHS["temp"].glob(pattern))
    if not files:
        logger.info("No temp files matching %s", pattern)
        return
    for file_path in files:
        try:
            file_path.unlink()
            logger.info("Deleted %s", file_path)
        except OSError as exc:
            logger.warning("Failed to delete %s: %s", file_path, exc)


async def _cleanup_ib_entities(args: argparse.Namespace) -> None:
    mapping_path = args.entity_ids or PATHS["temp"] / "entity_mapping.live.json"
    if not mapping_path.exists():
        raise SystemExit(
            f"No mapping file found at {mapping_path}. Provide --entity-ids explicitly."
        )

    mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
    entity_ids = list(mapping_data.values())
    if not entity_ids:
        logger.info("Mapping file %s contains no entity IDs.", mapping_path)
        return

    async with ib_service_manager(
        args.ib_backend,
        parse_kv_pairs(args.ib_options),
    ) as ib_service:
        delete_count = 0
        for entity_id in entity_ids:
            try:
                await ib_service.delete_entity(entity_id)
                delete_count += 1
            except Exception as exc:  # pragma: no cover - best effort cleanup
                logger.warning("Failed to delete entity %s: %s", entity_id, exc)
        logger.info("Deleted %s entities from IB.", delete_count)
