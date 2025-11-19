---
level: c2
tags: [architecture, containers, high-level]
last_updated: 2025-11-19
---

# Containers (C2)

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    Google Sheets API                        │
│              (External Data Источник)                       │
└───────────────────────┬────────────────────────────────────┘
                        │ HTTPS/JSON
                        ▼
┌────────────────────────────────────────────────────────────┐
│              Data Importer Service (FastAPI)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   API Layer  │  │   Service    │  │   Models     │     │
│  │   (REST)     │─▶│    Layer     │─▶│   (ORM)      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────┬────────────────────────────────────┘
                        │ SQL
                        ▼
┌────────────────────────────────────────────────────────────┐
│                    Database                                 │
│         SQLite (dev) / PostgreSQL (prod)                    │
└────────────────────────────────────────────────────────────┘
```

## Container: Data Importer Service
- **Технология**: FastAPI (Python 3.13)
- **Ответственность**: 
  - Получение данных из Google Sheets
  - Валидация и фильтрация
  - Трансформация и запись в БД
- **API**: REST endpoints для управления импортом
- **Аутентификация**: Нет (внутренний сервис)
- **Масштабирование**: Stateless, горизонтальное

## Container: Database
- **SQLite** (разработка):
  - Файл: `data_importer_dev.db`
  - Для локального тестирования
- **PostgreSQL** (продакшн):
  - Managed service (планируется)
  - Connection pooling через SQLAlchemy

## Container: Google Sheets API
- **Версия**: Google Sheets API v4
- **Аутентификация**: Service Account (read-only)
- **Rate Limits**: Учитываются через exponential backoff
- **Data Format**: JSON responses

## Взаимодействие Контейнеров
1. **Import Trigger** → FastAPI endpoint вызывается
2. **FastAPI** → Google Sheets API (fetch данных)
3. **FastAPI** → Обработка и валидация
4. **FastAPI** → Database (транзакционная запись)
5. **FastAPI** → Return status

## Deployment Strategy
- **Development**: Local SQLite, локальный сервер
- **Staging**: PostgreSQL, Kubernetes pod
- **Production**: PostgreSQL (managed), auto-scaling pods
