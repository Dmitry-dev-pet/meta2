---
level: c3
component: ImportService
tags: [feature, import, data-flow]
last_updated: 2025-11-19
---

# Feature: Import Flow

## What
Основной процесс импорта данных из Google Sheets в базу данных.

## Why
- **Качество данных**: Гарантирует, что только валидные данные попадают в БД
- **Консистентность**: Full replace strategy обеспечивает актуальность
- **Прослеживаемость**: Детальная статистика и логи каждого импорта

## How

### High-Level Flow
```
1. Trigger Import (API call)
   ↓
2. Fetch Data from Google Sheets
   ↓
3. Process & Validate (DataProcessor)
   ↓
4. Clear Database (transactional)
   ↓
5. Import Entities in Order
   ↓
6. Generate Statistics
```

### Step-by-Step
1. **Start Import**
   - Endpoint: `POST /api/v1/import/start`
   - Background task создается
   - Возвращается import_id

2. **Fetch Data**
   - GoogleSheetsClient получает данные
   - Ranges: Students, Projects, Reviews, Mentors, Sponsored Reviews

3. **Process**
   - DataProcessor фильтрует студентов (Telegram OR GitHub)
   - DataProcessor фильтрует менторов (Telegram required)
   - Projects связываются со студентами по GitHub URL
   - Reviews связываются с менторами и проектами

4. **Clear Database**
   ```python
   # В правильном порядке (foreign keys)
   await session.execute(delete(SponsoredReview))
   await session.execute(delete(Review))
   await session.execute(delete(MentorProfile))
   await session.execute(delete(Project))
   await session.execute(delete(user_roles))
   await session.execute(delete(Role))
   await session.execute(delete(User))
   ```

5. **Import**
   - Порядок: Users → Roles → UserRoles → MentorProfiles → Projects → Reviews → SponsoredReviews
   - Все в одной транзакции
   - Откат при ошибке

6. **Report**
   - Генерируется статистика
   - Сохраняется в `backups/database_statistics_*.json`

## Related Components
- [ImportService](../components.md#importservice) - оркестратор
- [DataProcessor](../components.md#dataprocessor) - обработка
- [GoogleSheetsClient](../components.md#googlesheetsClient) - fetch
- [DatabaseAdapter](../components.md#databaseadapter) - БД

## Code References
- `src/data_importer/services/import_service.py:run_import()`
- `src/data_importer/services/data_processor.py`
- `src/data_importer/api/endpoints/import_.py`
