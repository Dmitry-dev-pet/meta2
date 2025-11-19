---
level: development
tags: [steering, decision-making, ai-agents]
last_updated: 2025-11-19
---

# Steering Guide

**Гайд для AI агентов** по принятию решений в проекте meta2.

## When to Use Which Droid

### Code Changes
**If**: Внесение изменений в код
**Then**: 
1. Сначала запустить `ruff-fix`, `black-format`, `typecheck`
2. Коммитить через `commit-droid.sh`

**Rationale**: Проверки обязательны перед коммитом (стандарты верификации).

### Creating Pull Request
**If**: Нужно создать PR
**Then**: Использовать `pr-create.sh` (включает все проверки автоматически)

**Rationale**: Один шаг вместо нескольких, меньше ошибок.

### Documentation Changes
**If**: Изменения только в markdown файлах (.md)
**Then**: Можно коммитить напрямую через `commit-droid.sh --no-preflight`

**Rationale**: Ruff/Black/MyPy не применимы к markdown.

## Debugging Strategies

### Import Fails
1. **Check dry-run first**: `POST /api/v1/import/dry-run`
2. **Review logs**: `data-importer/logs/`
3. **Verify Google Sheets access**: Credentials valid?
4. **Database state**: Check if DB is locked

### Type Check Errors
1. **Read error context**: MyPy дает точное место
2. **Check imports**: Часто проблема в циклических импортах
3. **Verify models**: SQLAlchemy модели корректны?

### Tests Fail
1. **Run specific test**: `pytest path/to/test.py::test_name`
2. **Check fixtures**: Database fixtures актуальны?
3. **Verify mocks**: Mock'и соответствуют реальным данным?

## Conflict Resolution

### Breaking Changes
**Priority**: Сначала обновить документацию → потом код

**Rationale**: Документация - source of truth.

### Code Style Conflicts
**Priority**: Black > Ruff > Manual

**Rationale**: Автоматизация важнее субъективности.

### Architectural Decisions
**Priority**: C4 структура > Ad-hoc решения

**Rationale**: Консистентность архитектуры.

## Code Style Preferences

### Naming
- **Functions**: `snake_case`, глаголы (`fetch_data`, `process_students`)
- **Classes**: `PascalCase`, существительные (`ImportService`, `DataProcessor`)
- **Constants**: `UPPER_SNAKE_CASE` (`DATABASE_URL`, `MAX_RETRIES`)

### Imports
Порядок:
1. Standard library
2. Third-party
3. Local (`from src.data_importer...`)

Группировка с пустыми строками.

### Async Patterns
**Prefer**: `async def` + `await`
**Avoid**: Mixing sync/async без явной причины

### Error Handling
**Prefer**: Specific exceptions с контекстом
```python
raise ValueError(f"Student {student_id} not found")
```

**Avoid**: Generic exceptions
```python
raise Exception("Error")  # BAD
```

## Feature Implementation Strategy

### New Feature Checklist
1. [ ] Document в `architecture/features/`
2. [ ] Update `components.md` if new component
3. [ ] Implement code
4. [ ] Add tests
5. [ ] Update `project_status.md`
6. [ ] Run verification droids
7. [ ] Create PR via `pr-create.sh`

### Refactoring Strategy
1. **Document current state** (код + тесты)
2. **Plan changes** (design doc)
3. **Refactor incrementally** (small commits)
4. **Verify each step** (тесты не ломаются)

## Memory Bank Updates

### When to Update
- **After significant feature**: Add to `features/`
- **Architectural change**: Update `architecture/`
- **New tools/droids**: Update `development/`
- **Project milestone**: Update `project_status.md`

### Frontmatter Maintenance
Always update `last_updated` field when editing.

## Decision Matrix

| Situation | Action | Rationale |
|-----------|--------|-----------|
| Multiple small changes | One commit | Atomic changes |
| Big refactor | Multiple commits | Easier review |
| Fast iteration | Dry-run first | Catch errors early |
| Production deploy | Full test suite | Zero downtime |
| Emergency fix | Hotfix branch + fast PR | Minimize risk |

## Best Practices Reminders

1. **Always use droids** for commits/PRs
2. **Document before code** for new features
3. **Test dry-run** before real import
4. **Update Memory Bank** after milestones
5. **Follow C4 structure** for architecture docs
