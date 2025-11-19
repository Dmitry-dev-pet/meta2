---
level: development
tags: [scripts, commands, quick-reference]
last_updated: 2025-11-19
---

# Inline Scripts

**Quick reference** для частых команд разработки.

## Development Server

### Start dev server
```bash
cd /Users/dmitry/Project/meta2/data-importer
rye run uvicorn src.data_importer.main:app --reload
```

**Result**: Server at http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Stop server
```bash
# Find process
lsof -i :8000

# Kill
kill -9 <PID>
```

## Import Operations

### Quick test after code changes
```bash
# 1. Start dev server (if not running)
cd /Users/dmitry/Project/meta2/data-importer
rye run uvicorn src.data_importer.main:app --reload &

# 2. Wait for startup
sleep 3

# 3. Run dry-run test
curl -X POST "http://localhost:8000/api/v1/import/dry-run" \
  -H "Content-Type: application/json" | jq .

# 4. Check statistics
# Expected: students=544, projects=1222, reviews=593
```

**IMPORTANT**: Запускайте этот тест ПОСЛЕ каждого рефакторинга!

### Dry-run import
```bash
curl -X POST "http://localhost:8000/api/v1/import/dry-run" \
  -H "Content-Type: application/json"
```

**Result**: Statistics without DB changes

### Real import
```bash
curl -X POST "http://localhost:8000/api/v1/import/start" \
  -H "Content-Type: application/json"
```

**Result**: `{"import_id": "import_...", "status": "started"}`

### Check import status
```bash
curl "http://localhost:8000/api/v1/import/status/<IMPORT_ID>"
```

## Database Operations

### Create migration
```bash
cd data-importer
rye run alembic revision --autogenerate -m "Description"
```

### Apply migrations
```bash
rye run alembic upgrade head
```

### Rollback migration
```bash
rye run alembic downgrade -1
```

### View migration history
```bash
rye run alembic history
```

### Reset database (SQLite)
```bash
rm data-importer/data_importer_dev.db
rye run alembic upgrade head
```

## Code Quality

### Run all checks
```bash
# From project root
bash .factory/commands/ruff-fix.sh data-importer/src
bash .factory/commands/black-fix.sh data-importer/src
bash .factory/commands/typecheck.sh data-importer/src
```

### Fix code style
```bash
cd data-importer
rye run black src/
rye run ruff check --fix src/
```

### Type check
```bash
rye run mypy src/
```

## Testing

### Run all tests
```bash
cd data-importer
rye run pytest
```

### Run specific test file
```bash
rye run pytest tests/test_import_service.py
```

### Run with coverage
```bash
rye run pytest --cov=src/data_importer --cov-report=html
```

### View coverage report
```bash
open htmlcov/index.html
```

## Git & PR

### Commit with checks
```bash
bash .factory/commands/commit-droid.sh -m "Your message"
```

### Create PR
```bash
bash .factory/commands/pr-create.sh \
  --title "Title" \
  --body "Description" \
  --branch "feature/name"
```

### Push to GitHub
```bash
git push origin <branch-name>
```

## Dependencies

### Add dependency
```bash
cd data-importer
rye add package_name
```

### Add dev dependency
```bash
rye add --dev package_name
```

### Update dependencies
```bash
rye sync
```

## Logs & Debugging

### View logs
```bash
tail -f data-importer/logs/app.log
```

### View import statistics
```bash
ls -lh data-importer/backups/
cat data-importer/backups/database_statistics_*.json | jq .
```

### Check database content
```bash
sqlite3 data-importer/data_importer_dev.db

# Inside sqlite3
.tables
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM projects;
.quit
```

## Environment

### Activate virtual env (if needed)
```bash
cd data-importer
source .venv/bin/activate
```

### Check Python version
```bash
python --version  # Should be 3.13+
```

### Verify Google Sheets credentials
```bash
cat /Users/dmitry/Project/meta2/secret.json | jq .type
# Should output: "service_account"
```

## Quick Fixes

### Port already in use
```bash
lsof -ti:8000 | xargs kill -9
```

### Permission denied on scripts
```bash
chmod +x .factory/commands/*.sh
```

### Import hangs
```bash
# Check if database is locked
lsof data-importer/data_importer_dev.db
```

## Memory Bank

### Update Memory Bank
```bash
# Edit relevant files in .agent/memory/
# Update `last_updated` in frontmatter
```

### View index
```bash
cat .agent/memory/index.md
```
