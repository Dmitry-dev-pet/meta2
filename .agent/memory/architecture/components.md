---
level: c3
tags: [architecture, components, services]
last_updated: 2025-11-19
---

# Components (C3)

## Layered Architecture

### API Layer (`src/data_importer/api/`)
**Ответственность**: Обработка HTTP запросов и ответов

#### Components:
- **endpoints/import_.py**: REST endpoints для импорта
  - `POST /api/v1/import/start` - запуск полного импорта
  - `POST /api/v1/import/dry-run` - тестовый импорт
  - `GET /api/v1/import/status/{id}` - проверка статуса
- **deps.py**: Dependency injection для FastAPI

### Service Layer (`src/data_importer/services/`)
**Ответственность**: Бизнес-логика

#### ImportService
- **Роль**: Оркестратор процесса импорта
- **Зависимости**: GoogleSheetsClient, DataProcessor, DatabaseAdapter
- **Методы**:
  - `run_import()` - основной флоу импорта
  - `_clear_database()` - очистка БД перед импортом
  - `_import_users()`, `_import_projects()`, `_import_reviews()` - импорт сущностей

#### GoogleSheetsClient
- **Роль**: Интеграция с Google Sheets API
- **Паттерн**: Singleton
- **Методы**:
  - `fetch_range()` - получение данных из указанного range
  - `get_all_data()` - fetch всех таблиц

#### DataProcessor
- **Роль**: Обработка, фильтрация, валидация
- **Методы**:
  - `process_students()` - фильтр студентов (Telegram OR GitHub)
  - `process_mentors()` - фильтр менторов (Telegram required)
  - `filter_projects_by_students()` - связь проектов со студентами
  - `link_reviews()` - связь ревью с менторами и проектами

### Data Access Layer (`src/data_importer/models/`)
**Ответственность**: ORM и схемы

#### Models (SQLAlchemy):
- **User**: Пользователи (студенты + менторы)
- **Role**: Роли пользователей
- **MentorProfile**: Расширенная информация о менторах
- **Project**: Проекты студентов
- **Review**: Ревью менторов
- **SponsoredReview**: Платные ревью

#### Schemas (Pydantic):
- **UserCreate**, **ProjectCreate**, etc. - валидация входных данных
- **ImportStatus** - статус импорта

### Infrastructure Layer

#### DatabaseAdapter (`config/database.py`)
- **Роль**: Абстракция над SQLite/PostgreSQL
- **Паттерн**: Adapter
- **Методы**: `get_session()`, `create_tables()`

#### Settings (`config/settings.py`)
- **Роль**: Конфигурация через переменные окружения
- **Паттерн**: Singleton (Pydantic BaseSettings)

## Component Interactions

```
API Endpoints
    ↓
ImportService → GoogleSheetsClient → Google Sheets API
    ↓
DataProcessor (validate + filter)
    ↓
DatabaseAdapter → Database
```

## Design Patterns
- **Dependency Injection**: Сервисы внедряются через FastAPI deps
- **Singleton**: GoogleSheetsClient, Settings
- **Adapter**: DatabaseAdapter (SQLite/PostgreSQL)
- **Repository** (неявный): Операции с БД инкапсулированы в ImportService
