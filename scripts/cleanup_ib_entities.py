#!/usr/bin/env python3
"""Wrapper around the cleanup CLI to purge migrated IB entities."""

from cloud_optimizer.integrations.smart_scaffold.cli import run_cleanup_cli

if __name__ == "__main__":
    run_cleanup_cli()
