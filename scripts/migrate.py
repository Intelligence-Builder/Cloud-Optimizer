#!/usr/bin/env python
"""
Database Migration Management Script for Cloud Optimizer.

Provides safe migration operations with backup, rollback, and status checking.
Includes pre-migration health checks, automatic backup, and post-migration validation.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://cloud_optimizer:localpass@localhost:5432/cloud_optimizer",
    )


def run_alembic(args: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    """Run an Alembic command."""
    cmd = ["alembic"] + args
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

    if capture:
        return subprocess.run(cmd, capture_output=True, text=True, env=env)
    return subprocess.run(cmd, env=env)


def get_current_revision() -> str | None:
    """Get current database revision."""
    result = run_alembic(["current"], capture=True)
    if result.returncode != 0:
        return None
    # Parse output like "001 (head)" or "001"
    output = result.stdout.strip()
    if output:
        # Extract revision ID from output
        lines = output.split("\n")
        for line in lines:
            if line.strip():
                parts = line.split()
                if parts:
                    return parts[0]
    return None


def get_migration_history() -> list[dict]:
    """Get migration history with timestamps."""
    result = run_alembic(["history", "-v"], capture=True)
    if result.returncode != 0:
        return []

    history = []
    for line in result.stdout.strip().split("\n"):
        if line.strip() and "->" in line:
            # Parse lines like "001 -> 002, Add trial tables"
            parts = line.split(",", 1)
            revision_part = parts[0].strip()
            description = parts[1].strip() if len(parts) > 1 else ""

            history.append(
                {
                    "revision": revision_part,
                    "description": description,
                }
            )
    return history


def check_database_connection() -> Tuple[bool, str]:
    """
    Check if database is accessible.

    Returns:
        Tuple of (success, message)
    """
    db_url = get_database_url()
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        user = parsed.username or "cloud_optimizer"
        password = parsed.password or ""
        dbname = parsed.path.lstrip("/") or "cloud_optimizer"

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password

        # Simple connection test using psql
        cmd = [
            "psql",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", dbname,
            "-c", "SELECT 1;",
            "-t",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=10
        )

        if result.returncode == 0:
            return True, "Database connection successful"
        return False, f"Database connection failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Database connection timeout (10s)"
    except Exception as e:
        return False, f"Database connection error: {e}"


def check_disk_space() -> Tuple[bool, str]:
    """
    Check if sufficient disk space is available.

    Returns:
        Tuple of (success, message)
    """
    try:
        backup_dir = Path(__file__).parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Get disk space using df
        result = subprocess.run(
            ["df", "-h", str(backup_dir)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                fields = lines[1].split()
                if len(fields) >= 5:
                    available = fields[3]
                    use_percent = fields[4]
                    return True, f"Disk space: {available} available ({use_percent} used)"

        return True, "Disk space check completed (details unavailable)"
    except Exception as e:
        return False, f"Disk space check failed: {e}"


def check_alembic_version_table() -> Tuple[bool, str]:
    """
    Check if alembic_version table exists.

    Returns:
        Tuple of (success, message)
    """
    db_url = get_database_url()
    try:
        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        user = parsed.username or "cloud_optimizer"
        password = parsed.password or ""
        dbname = parsed.path.lstrip("/") or "cloud_optimizer"

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            "psql",
            "-h", host,
            "-p", str(port),
            "-U", user,
            "-d", dbname,
            "-c", "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version');",
            "-t",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode == 0:
            exists = result.stdout.strip() == "t"
            if exists:
                return True, "Alembic version table exists"
            return True, "Alembic version table does not exist (first migration)"
        return False, f"Failed to check alembic_version table: {result.stderr}"
    except Exception as e:
        return False, f"Error checking alembic_version table: {e}"


def run_health_checks() -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Run pre-migration health checks.

    Returns:
        Tuple of (all_passed, check_results)
    """
    print("\n" + "=" * 60)
    print("Pre-Migration Health Checks")
    print("=" * 60)

    checks = [
        ("Database Connection", check_database_connection),
        ("Disk Space", check_disk_space),
        ("Alembic Version Table", check_alembic_version_table),
    ]

    results = []
    all_passed = True

    for check_name, check_func in checks:
        print(f"\nChecking {check_name}...", end=" ")
        success, message = check_func()
        results.append({
            "check": check_name,
            "success": success,
            "message": message,
        })

        if success:
            print(f"PASS - {message}")
        else:
            print(f"FAIL - {message}")
            all_passed = False

    print("\n" + "=" * 60)

    return all_passed, results


def validate_migration(pre_revision: Optional[str], post_revision: Optional[str]) -> Tuple[bool, str]:
    """
    Validate that migration was successful.

    Args:
        pre_revision: Revision before migration
        post_revision: Revision after migration

    Returns:
        Tuple of (success, message)
    """
    if pre_revision == post_revision:
        return False, "Migration did not change database version"

    # Check that database is still accessible
    success, message = check_database_connection()
    if not success:
        return False, f"Post-migration database check failed: {message}"

    return True, f"Migration successful: {pre_revision or 'None'} -> {post_revision}"


def create_migration_report(
    operation: str,
    pre_revision: Optional[str],
    post_revision: Optional[str],
    health_checks: List[Dict[str, Any]],
    success: bool,
    backup_file: Optional[str] = None
) -> str:
    """
    Create a migration report JSON file.

    Returns:
        Path to report file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = Path(__file__).parent.parent / "reports" / "migrations"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_file = reports_dir / f"{operation}_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "success": success,
        "pre_revision": pre_revision,
        "post_revision": post_revision,
        "health_checks": health_checks,
        "backup_file": backup_file,
        "database_url_masked": get_database_url().split("@")[1] if "@" in get_database_url() else "N/A",
    }

    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    return str(report_file)


def cmd_status(args: argparse.Namespace) -> int:
    """Show migration status."""
    print("=" * 60)
    print("Migration Status")
    print("=" * 60)

    current = get_current_revision()
    print(f"\nCurrent revision: {current or 'None (no migrations applied)'}")

    print("\nMigration history:")
    result = run_alembic(["history", "--verbose"])

    print("\nPending migrations:")
    result = run_alembic(["heads"])

    return 0


def cmd_upgrade(args: argparse.Namespace) -> int:
    """Run migrations to upgrade database with health checks and validation."""
    target = args.revision or "head"

    print("=" * 60)
    print(f"Upgrading database to: {target}")
    print("=" * 60)

    if args.dry_run:
        print("\n[DRY RUN] Would run the following SQL:")
        current = get_current_revision()
        # For SQL generation, need explicit from:to format
        from_rev = current or "base"
        result = run_alembic(["upgrade", f"{from_rev}:{target}", "--sql"])
        return result.returncode

    # Run pre-migration health checks
    if not args.skip_health_checks:
        health_passed, health_results = run_health_checks()
        if not health_passed:
            print("\nWARNING: Some health checks failed!")
            if not args.yes:
                response = input("Continue anyway? [y/N]: ")
                if response.lower() != "y":
                    print("Upgrade cancelled due to failed health checks.")
                    return 1
    else:
        health_results = []

    pre_revision = get_current_revision()
    print(f"\nCurrent revision: {pre_revision or 'None'}")
    print(f"Target revision: {target}")

    # Create backup before migration if requested
    backup_file = None
    if args.backup:
        print("\nCreating backup before migration...")
        backup_file = create_backup()
        if backup_file:
            print(f"Backup created: {backup_file}")
        else:
            print("WARNING: Backup creation failed!")
            if not args.yes:
                response = input("Continue without backup? [y/N]: ")
                if response.lower() != "y":
                    print("Upgrade cancelled.")
                    return 1

    if not args.yes:
        response = input("\nProceed with upgrade? [y/N]: ")
        if response.lower() != "y":
            print("Upgrade cancelled.")
            return 1

    # Run migration
    print("\nRunning migration...")
    result = run_alembic(["upgrade", target])

    # Get post-migration revision
    post_revision = get_current_revision()

    # Validate migration
    migration_success = result.returncode == 0
    if migration_success and not args.skip_validation:
        print("\nValidating migration...")
        validation_success, validation_message = validate_migration(pre_revision, post_revision)
        print(f"Validation: {validation_message}")
        if not validation_success:
            migration_success = False

    # Create migration report
    report_file = create_migration_report(
        operation="upgrade",
        pre_revision=pre_revision,
        post_revision=post_revision,
        health_checks=health_results,
        success=migration_success,
        backup_file=backup_file
    )

    if migration_success:
        print(f"\nUpgrade complete. Current revision: {post_revision}")
        print(f"Migration report: {report_file}")
        return 0
    else:
        print(f"\nUpgrade failed!")
        print(f"Migration report: {report_file}")
        if backup_file:
            print(f"You can restore from backup: {backup_file}")
        return 1


def cmd_downgrade(args: argparse.Namespace) -> int:
    """Rollback migrations."""
    target = args.revision or "-1"

    print("=" * 60)
    print(f"Downgrading database to: {target}")
    print("=" * 60)

    current = get_current_revision()
    print(f"\nCurrent revision: {current or 'None'}")

    if args.dry_run:
        print("\n[DRY RUN] Would run the following SQL:")
        # For SQL generation, need explicit from:to format
        if current:
            result = run_alembic(["downgrade", f"{current}:{target}", "--sql"])
        else:
            print("No current revision - nothing to downgrade")
            return 0
        return result.returncode

    # Show what will be undone
    print("\nMigrations that will be rolled back:")
    run_alembic(["history", "-r", f"{target}:current"])

    print("\n" + "!" * 60)
    print("WARNING: This will ROLLBACK database migrations!")
    print("Data may be LOST if tables/columns are dropped!")
    print("!" * 60)

    if args.backup:
        print("\nCreating backup before rollback...")
        backup_file = create_backup()
        if backup_file:
            print(f"Backup created: {backup_file}")
        else:
            print("WARNING: Backup creation failed!")
            if not args.yes:
                response = input("Continue without backup? [y/N]: ")
                if response.lower() != "y":
                    print("Rollback cancelled.")
                    return 1

    if not args.yes:
        response = input("\nProceed with rollback? [y/N]: ")
        if response.lower() != "y":
            print("Rollback cancelled.")
            return 1

    result = run_alembic(["downgrade", target])
    if result.returncode == 0:
        new_revision = get_current_revision()
        print(f"\nRollback complete. Current revision: {new_revision}")
    return result.returncode


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate a new migration."""
    if not args.message:
        print("Error: --message is required for migration generation")
        return 1

    print(f"Generating migration: {args.message}")

    if args.autogenerate:
        result = run_alembic(["revision", "--autogenerate", "-m", args.message])
    else:
        result = run_alembic(["revision", "-m", args.message])

    return result.returncode


def cmd_heads(args: argparse.Namespace) -> int:
    """Show current migration heads."""
    print("Current migration heads:")
    return run_alembic(["heads", "-v"]).returncode


def cmd_check(args: argparse.Namespace) -> int:
    """Check if database is up-to-date."""
    result = run_alembic(["check"], capture=True)

    if result.returncode == 0:
        print("Database is up-to-date with migrations.")
        return 0

    print("Database is NOT up-to-date!")
    print(result.stdout)
    print(result.stderr)
    return 1


def cmd_health(args: argparse.Namespace) -> int:
    """Run health checks on database and migration system."""
    health_passed, health_results = run_health_checks()

    if args.json:
        print(json.dumps(health_results, indent=2))

    return 0 if health_passed else 1


def create_backup() -> str | None:
    """Create a database backup before rollback."""
    db_url = get_database_url()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(__file__).parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"pre_rollback_{timestamp}.sql"

    # Parse database URL for pg_dump
    # Format: postgresql://user:pass@host:port/dbname
    try:
        from urllib.parse import urlparse

        parsed = urlparse(db_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        user = parsed.username or "cloud_optimizer"
        password = parsed.password or ""
        dbname = parsed.path.lstrip("/") or "cloud_optimizer"

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password

        cmd = [
            "pg_dump",
            "-h",
            host,
            "-p",
            str(port),
            "-U",
            user,
            "-d",
            dbname,
            "-f",
            str(backup_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode == 0:
            return str(backup_file)
        print(f"Backup failed: {result.stderr}")
        return None
    except Exception as e:
        print(f"Backup error: {e}")
        return None


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cloud Optimizer Database Migration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check migration status
  python scripts/migrate.py status

  # Upgrade to latest
  python scripts/migrate.py upgrade

  # Upgrade to specific revision
  python scripts/migrate.py upgrade --revision 001

  # Preview upgrade SQL
  python scripts/migrate.py upgrade --dry-run

  # Rollback one migration with backup
  python scripts/migrate.py downgrade --backup

  # Rollback to specific revision
  python scripts/migrate.py downgrade --revision 001

  # Generate new migration
  python scripts/migrate.py generate -m "Add new table"

  # Autogenerate migration from models
  python scripts/migrate.py generate -m "Add new table" --autogenerate
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Migration command")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show migration status")
    status_parser.set_defaults(func=cmd_status)

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument(
        "--revision", "-r", help="Target revision (default: head)"
    )
    upgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show SQL without executing"
    )
    upgrade_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )
    upgrade_parser.add_argument(
        "--backup", "-b", action="store_true", help="Create backup before migration"
    )
    upgrade_parser.add_argument(
        "--skip-health-checks", action="store_true", help="Skip pre-migration health checks"
    )
    upgrade_parser.add_argument(
        "--skip-validation", action="store_true", help="Skip post-migration validation"
    )
    upgrade_parser.set_defaults(func=cmd_upgrade)

    # Downgrade command
    downgrade_parser = subparsers.add_parser(
        "downgrade", help="Rollback migrations (DANGEROUS)"
    )
    downgrade_parser.add_argument(
        "--revision",
        "-r",
        help="Target revision (default: -1, rolls back one migration)",
    )
    downgrade_parser.add_argument(
        "--backup", "-b", action="store_true", help="Create backup before rollback"
    )
    downgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show SQL without executing"
    )
    downgrade_parser.add_argument(
        "--yes", "-y", action="store_true", help="Skip confirmation prompt"
    )
    downgrade_parser.set_defaults(func=cmd_downgrade)

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate new migration")
    gen_parser.add_argument("--message", "-m", required=True, help="Migration message")
    gen_parser.add_argument(
        "--autogenerate",
        "-a",
        action="store_true",
        help="Autogenerate from model changes",
    )
    gen_parser.set_defaults(func=cmd_generate)

    # Heads command
    heads_parser = subparsers.add_parser("heads", help="Show migration heads")
    heads_parser.set_defaults(func=cmd_heads)

    # Check command
    check_parser = subparsers.add_parser("check", help="Check if database is current")
    check_parser.set_defaults(func=cmd_check)

    # Health command
    health_parser = subparsers.add_parser("health", help="Run health checks")
    health_parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    health_parser.set_defaults(func=cmd_health)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
