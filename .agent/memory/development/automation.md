# Automation

## Droid System

**Расположение**: `.factory/droids/*.md` (инструкции) + `.factory/commands/*.sh` (скрипты)

### Available Droids

#### commit
**Назначение**: Коммит с автоматическими pre-commit проверками

**Usage**:
```bash
.factory/commands/commit-droid.sh -m "Your message"
```

**What it does**:
1. Runs preflight checks (Black, Ruff, MyPy, Mermaid validation)
2. Stages changes (`git add -A` by default)
3. Creates commit with co-author trailer

**Options**:
- `--no-preflight` - skip checks
- `--no-add-all` - only commit specified files
- `--dry-run` - show what would be committed
- `--signoff` - add Signed-off-by

---

#### pr-create
**Назначение**: Создание Pull Request (ветка → коммит → push → PR)

**Usage**:
```bash
.factory/commands/pr-create.sh \
  --title "Title" \
  --body "Description" \
  --branch "feature/name"
```

**What it does**:
1. Creates new branch
2. Commits changes (uses `commit-droid.sh`)
3. Pushes branch to origin
4. Creates PR via `gh pr create`

**Options**:
- `--base main` - target branch (default: main)
- `--message "..."` - custom commit message (defaults to title)
- `--no-preflight` - skip checks

---

#### ruff-fix
**Назначение**: Линтинг и автоматическое исправление

**Usage**:
```bash
.factory/commands/ruff-fix.sh data-importer/src
```

**What it does**:
1. Runs `ruff check --fix`
2. Verifies clean state
3. Reports summary

**Options**:
- `--check-only` - only check, don't fix

---

#### black-format
**Назначение**: Форматирование кода

**Usage**:
```bash
.factory/commands/black-fix.sh data-importer/src
```

**What it does**:
1. Formats code with Black
2. Verifies formatting
3. Reports changed files

**Options**:
- `--check-only` - only check, don't format

---

#### typecheck
**Назначение**: Проверка типов с MyPy

**Usage**:
```bash
.factory/commands/typecheck.sh data-importer/src
```

**What it does**:
1. Runs MyPy type checking
2. Reports errors with context

**Options**:
- `--strict` - enable strict mode

---

#### dead-code-scan
**Назначение**: Поиск неиспользуемого кода

**Usage**:
```bash
.factory/commands/deadcode-scan.sh data-importer/src
```

**What it does**:
1. Runs Vulture (or Ruff fallback)
2. Reports unused code candidates

**Options**:
- `--exclude=pattern` - exclude patterns
- `--min-confidence=80` - minimum confidence (0-100)

---

#### mermaid-create
**Назначение**: Генерация Mermaid диаграмм

**Usage**:
```bash
echo "users { int id PK }" | \
.factory/commands/mermaid-create.sh \
  --type erDiagram \
  --output doc/diagram.md
```

**What it does**:
1. Creates Mermaid diagram from stdin
2. Validates syntax
3. Renders SVG (optional)

**Options**:
- `--direction LR` - diagram direction
- `--theme neutral` - theme
- `--render` - generate SVG

---

## Workflow Example

**Standard Development Flow**:
```bash
# 1. Make changes to code
vim data-importer/src/...

# 2. Run verification droids
.factory/commands/ruff-fix.sh data-importer/src
.factory/commands/black-fix.sh data-importer/src
.factory/commands/typecheck.sh data-importer/src

# 3. Create PR
.factory/commands/pr-create.sh \
  --title "Fix: Update import logic" \
  --body "Detailed description" \
  --branch "fix/import-logic"
```

**Note**: `pr-create` автоматически запускает проверки через `commit-droid`, так что шаг 2 можно пропустить.
