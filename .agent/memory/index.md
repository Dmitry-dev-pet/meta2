---
type: index
last_updated: 2025-11-19
---

# Memory Bank Index

**Главный файл навигации** по Memory Bank проекта `meta2`.

## Быстрый старт
- 📍 [Project Status](project_status.md) - текущее состояние проекта
- 🏗️ [Architecture Overview](architecture/context.md) - обзор архитектуры
- 🛠️ [Automation](development/automation.md) - доступные droids
- 📊 [Tech Stack](development/tech_stack.md) - технологии

---

## Структура Memory Bank

### 📐 Architecture (C1-C3)
Архитектурные уровни по C4 Model:

- **[context.md](architecture/context.md)** (C1: System Context)
  - Внешние системы и пользователи
  - Границы системы
  - Ключевые требования

- **[containers.md](architecture/containers.md)** (C2: Containers)
  - High-level архитектура
  - FastAPI, Database, Google Sheets API
  - Deployment strategy

- **[components.md](architecture/components.md)** (C3: Components)
  - Внутренние компоненты
  - ImportService, DataProcessor, GoogleSheetsClient
  - Design patterns

- **[features/](architecture/features/)** (C3: Features)
  - [import_flow.md](architecture/features/import_flow.md) - основной процесс импорта
  - [data_filtering.md](architecture/features/data_filtering.md) - логика фильтрации
  - [review_linking.md](architecture/features/review_linking.md) - связывание ревью

---

### 💻 Development (C4 + Practice)

- **[code_standards.md](development/code_standards.md)** (C4: Code Level)
  - Coding patterns (async/await, type hints)
  - Verification standards
  - Error handling

- **[automation.md](development/automation.md)**
  - Droids documentation
  - Available scripts
  - Workflow examples

- **[tech_stack.md](development/tech_stack.md)**
  - Python 3.13, FastAPI, SQLAlchemy
  - Rye, Alembic, Pydantic v2
  - Technologies overview

- **[steering.md](development/steering.md)**
  - Decision-making guide for AI agents
  - When to use which droid
  - Debugging strategies

- **[inline_scripts.md](development/inline_scripts.md)**
  - Common commands
  - Quick references

---

### 📊 Status

- **[project_status.md](project_status.md)**
  - Current phase
  - Recent achievements
  - Next steps
  - Open questions

---

## How to Use This Memory Bank

### For AI Agents
1. **Start here** (`index.md`) для навигации
2. Читайте **project_status.md** для понимания текущего контекста
3. Обращайтесь к **architecture/** для архитектурных решений
4. Используйте **development/** для стандартов кодирования и автоматизации
5. Документируйте изменения в **project_status.md**

### For Developers
- Все документы в Markdown
- Используйте ссылки для быстрой навигации
- Обновляйте `last_updated` при изменениях
- Следуйте структуре при добавлении новых документов

---

## Metadata
- **Project**: Data Importer Service (meta2)
- **Repository**: https://github.com/Dmitry-dev-pet/meta2
- **Created**: 2025-11-19
- **Last Updated**: 2025-11-19
