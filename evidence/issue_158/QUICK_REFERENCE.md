# Database Migration Automation - Quick Reference Guide

## Common Commands

### Check Migration Status
```bash
python scripts/migrate.py status
```

### Run Health Checks
```bash
# Human-readable output
python scripts/migrate.py health

# JSON output (for scripts/CI)
python scripts/migrate.py health --json
```

### Upgrade Database (Recommended)
```bash
# Interactive with all safety features
python scripts/migrate.py upgrade --backup

# Preview SQL first (recommended)
python scripts/migrate.py upgrade --dry-run
python scripts/migrate.py upgrade --backup

# Automated (CI/CD)
python scripts/migrate.py upgrade --backup --yes
```

### Rollback Migration
```bash
# Rollback one migration (with backup)
python scripts/migrate.py downgrade --backup

# Rollback to specific revision
python scripts/migrate.py downgrade --revision abc123 --backup
```

### Generate New Migration
```bash
# Manual migration
python scripts/migrate.py generate -m "Add user table"

# Auto-generate from models
python scripts/migrate.py generate -m "Add user table" --autogenerate
```

## GitHub Actions Usage

### Manual Migration
1. Go to: **Actions** → **Database Migration**
2. Click **Run workflow**
3. Select:
   - Environment: `development` / `staging` / `production`
   - Target revision: `head` (or specific revision)
   - Skip backup: `false` (recommended: keep backups enabled)
4. Click **Run workflow**

### Required Secrets (per environment)
```
DB_HOST=your-database-host
DB_PORT=5432
DB_NAME=cloud_optimizer
DB_USER=cloud_optimizer
DB_PASSWORD=your-secure-password
```

## Migration Workflow

### Development
```bash
1. python scripts/migrate.py health
2. python scripts/migrate.py upgrade --dry-run
3. python scripts/migrate.py upgrade --backup
4. python scripts/migrate.py check
```

### Staging
```bash
# Use GitHub Actions workflow
# Environment: staging
# Enable backups
```

### Production
```bash
# ALWAYS use GitHub Actions workflow
# Environment: production
# NEVER skip backups
# Schedule during low-traffic window
```

## Emergency Rollback

### Automatic (Non-Production Only)
- GitHub Actions handles automatically on failure

### Manual Rollback
```bash
# Step 1: Check current status
python scripts/migrate.py status

# Step 2: Rollback with backup
python scripts/migrate.py downgrade --backup

# Step 3: Verify
python scripts/migrate.py status
python scripts/migrate.py check
```

### Restore from Backup
```bash
# Find backup file
ls -lh backups/

# Restore (CAREFUL!)
psql -U cloud_optimizer -d cloud_optimizer < backups/pre_rollback_TIMESTAMP.sql
```

## File Locations

```
scripts/migrate.py                      # Migration automation script
.github/workflows/db-migrate.yml        # GitHub Actions workflow
alembic/versions/                       # Migration files
backups/                                # Database backups
reports/migrations/                     # Migration reports (JSON)
```

## Exit Codes

- `0` - Success
- `1` - Failure or user cancelled

## Flags Quick Reference

### Health Command
- `--json` - Output as JSON

### Upgrade Command
- `--backup` / `-b` - Create backup before migration
- `--yes` / `-y` - Skip confirmation (automation)
- `--dry-run` - Preview SQL only
- `--skip-health-checks` - Skip health checks (not recommended)
- `--skip-validation` - Skip validation (not recommended)
- `--revision` / `-r` - Target specific revision

### Downgrade Command
- `--backup` / `-b` - Create backup before rollback
- `--yes` / `-y` - Skip confirmation
- `--dry-run` - Preview SQL only
- `--revision` / `-r` - Target specific revision (default: -1)

## Best Practices

1. **Always run health checks first**
   ```bash
   python scripts/migrate.py health
   ```

2. **Always preview migrations**
   ```bash
   python scripts/migrate.py upgrade --dry-run
   ```

3. **Always create backups for important migrations**
   ```bash
   python scripts/migrate.py upgrade --backup
   ```

4. **Check migration status after completion**
   ```bash
   python scripts/migrate.py check
   ```

5. **Keep migration reports for audit trail**
   - Located in: `reports/migrations/`
   - Retention: 90 days (GitHub Actions)

## Troubleshooting

### "Database connection failed"
```bash
# Check database is running
docker ps | grep postgres

# Check DATABASE_URL
echo $DATABASE_URL

# Verify credentials
psql -U cloud_optimizer -d cloud_optimizer -c "SELECT 1;"
```

### "Health checks failed"
```bash
# See detailed output
python scripts/migrate.py health

# Skip if needed (NOT recommended)
python scripts/migrate.py upgrade --skip-health-checks
```

### "Migration failed"
```bash
# Check migration report
cat reports/migrations/upgrade_*.json

# Review Alembic logs
# Check database logs

# Rollback if needed
python scripts/migrate.py downgrade --backup
```

## Support

- Documentation: `evidence/issue_158/IMPLEMENTATION_SUMMARY.md`
- Test Results: `evidence/issue_158/TEST_DEMONSTRATION.md`
- Alembic Docs: https://alembic.sqlalchemy.org/
- GitHub Actions Logs: Actions tab in repository

---
**Issue**: #158
**Last Updated**: 2025-12-06
**Status**: Production Ready
