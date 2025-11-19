# Code Standards (C4)

## Coding Patterns

### Async/Await
- **Правило**: Все операции I/O (БД, сеть) асинхронны
- **Пример**: `async def run_import(...)`, `await session.execute(...)`

### Type Hinting
- **Правило**: Полное использование аннотаций типов
- **Пример**: `def process_students(data: List[Dict[str, Any]]) -> List[User]`
- **Проверка**: MyPy в CI/CD

### Configuration
- **Паттерн**: Pydantic BaseSettings
- **Источник**: Переменные окружения (.env)
- **Пример**:
  ```python
  class Settings(BaseSettings):
      DATABASE_URL: str
      GOOGLE_SHEETS_CREDENTIALS_PATH: str
  ```

### Logging
- **Библиотека**: structlog (структурированное логирование)
- **Формат**: JSON для продакшена, консольный для dev
- **Контекст**: Все логи содержат operation_id, timestamp, level

## Data Flow Pattern

1. **Fetch**: GoogleSheetsClient скачивает сырые данные
2. **Process**: DataProcessor очищает, валидирует, фильтрует
3. **Import**: ImportService записывает в БД в транзакции
4. **Report**: Генерируется статистика импорта

## Import Strategy

**Full Replace Pattern**:
- Очистка всех таблиц перед импортом
- Минимизация конфликтов
- Гарантия консистентности

**Transaction Boundary**:
- Один импорт = одна транзакция
- Откат при любой ошибке
- Atomic updates

## Verification Standards

**Pre-commit Checks** (обязательные):
1. **Ruff**: Линтинг и авто-исправление
   ```bash
   rye run ruff check --fix src/
   ```

2. **Black**: Форматирование кода
   ```bash
   rye run black src/
   ```

3. **MyPy**: Проверка типов
   ```bash
   rye run mypy src/
   ```

**How to Run**:
- Автоматически: через `commit-droid.sh` (см. `development/automation.md`)
- Вручную: команды выше

## Error Handling

**Graceful Degradation**:
- Ошибки логируются с полным контекстом
- Background tasks не падают весь сервер
- Детальные сообщения об ошибках в API responses

**Validation Strategy**:
- Pydantic для входных данных
- Бизнес-валидация в DataProcessor
- Database constraints как последняя линия защиты
