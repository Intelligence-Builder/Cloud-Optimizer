#!/usr/bin/env python3
"""CLI wrapper for migrating Smart-Scaffold relationships."""

from cloud_optimizer.integrations.smart_scaffold.cli import (
    run_relationship_migration_cli,
)

if __name__ == "__main__":
    run_relationship_migration_cli()
