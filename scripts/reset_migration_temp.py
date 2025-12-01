#!/usr/bin/env python3
"""Remove migration temp files under smart_scaffold_data/temp."""

from cloud_optimizer.integrations.smart_scaffold.cli import run_cleanup_cli

if __name__ == "__main__":
    run_cleanup_cli(["temp-files", "--pattern", "*.json"])
