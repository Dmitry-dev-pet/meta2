# Data Importer Service Architecture

## 📋 Обзор

**Назначение:** Импорт данных из Google Sheets в базу данных IT Mentor Community Platform

**Тип:** Full Replace (полная очистка перед каждым импортом)

**Подход:** Download-First с файловой отладкой и Telegram-фильтрацией

---

## 🎯 Ключевое требование

**Только пользователи с Telegram могут попасть в БД**, так как вся дальнейшая авторизация идет через Telegram Mini App.

---

## 📊 Структура данных (проверена через MCP)

### Источники данных:

**1. Основной spreadsheet** (`15ItyrC-p1jnuTjIaFG9GFcUYltuiRDYr_hBsl6riqrQ`)
- **Students:** лист "Telegram аккаунты студентов", диапазон `A2:C`
  ```
  A: GitHub URL
  B: Telegram ID
  C: Telegram username
  ```

- **Projects:** лист "Projects", диапазон `A2:I`
  ```
  A: Период (заголовок через строку)
  B: Название проекта
  C: Язык
  D: Имя репозитория
  E: Ссылка на репозиторий
  F: Имя автора
  G: Ссылка на автора (GitHub!)
  H: Наличие ревью
  I: Текущий период (не используется)
  ```

- **Reviews:** лист "Reviews", диапазон `A2:I`
  ```
  A: Период ревью
  B: Проект (для связи)
  C: Язык
  D: Ссылка на репозиторий
  E: Тип ревью ("Видео", "Текст")
  F: Ссылка на ревью
  G: Автор ревью (имя)
  H: Имя автора в телеграм (ключевое поле!)
  I: Ссылка на автора
  ```

**2. Spreadsheet менторов** (`1zxDrkL_OlJR-oLfT5Saphn9jEdmUxXWSTV7PvtGbaO8`)
- **Mentors:** лист "Менторы", диапазон `E5:J29`
  ```
  E: Ментор (полное имя)
  F: Контакт (Telegram username!)
  G: Языки
  H: Услуги
  I: Цена
  J: Комментарии/сайт
  ```
  ```
  **GitHub URL для менторов - НЕ ОБЯЗАТЕЛЕН!**

**3. Spreadsheet платных ревью** (`MENTORS_SPREADSHEET_ID`)
- **Sponsored Reviews:** лист "Платные ревью", диапазон `A2:M`
  ```
  A: Дата
  B: Ментор
  C: Студент (не используется)
  D: Проект
  E: Стоимость
  F: Валюта
  G: Статус оплаты
  H: Дата оплаты
  I: Спонсор
  J: Способ оплаты
  K: Заметки
  L: Ссылка на ревью (для V1)
  M: Ссылка на сообщение в Telegram (для V2)
  ```

---

## 🏗️ Схема базы данных

### Таблица Users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE,
    telegram_username VARCHAR(255) UNIQUE NOT NULL,
    github_url VARCHAR(500) UNIQUE
);
```

### Таблица Roles
```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO roles (name) VALUES ('ADMIN'), ('STUDENT'), ('MENTOR');
```

### Таблица Users_Roles (множественные роли)
```sql
CREATE TABLE users_roles (
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```

### Таблица MentorProfiles
```sql
CREATE TABLE mentor_profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    full_name VARCHAR(255),
    languages TEXT,
    services TEXT,
    price_type VARCHAR(50),
    website_url VARCHAR(500)
);
```

### Таблица Projects
```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    language VARCHAR(100),
    repository_name VARCHAR(255),
    repository_url VARCHAR(500),
    submission_date DATE,
    has_review BOOLEAN DEFAULT FALSE,
    student_id INTEGER REFERENCES users(id)
);
```

### Таблица Reviews
```sql
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    mentor_id INTEGER REFERENCES users(id),
    period_date DATE,
    review_type VARCHAR(100),
    review_url VARCHAR(500)
);
```

### Таблица SponsoredReviews
```sql
CREATE TABLE sponsored_reviews (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES reviews(id),
    project_id INTEGER REFERENCES projects(id),
    mentor_id INTEGER REFERENCES users(id),
    cost NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'RUB',
    payment_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    payment_date TIMESTAMP,
    review_date DATE,
    sponsor_id INTEGER REFERENCES users(id),
    payment_method VARCHAR(50),
    payment_method VARCHAR(50),
    notes TEXT,
    telegram_message_url VARCHAR(500)
);
```

---

## 🔄 Полный флоу импорта

### Этап 0: Конфигурация
```python
# ENV переменные
MAIN_SPREADSHEET_ID = "15ItyrC-p1jnuTjIaFG9GFcUYltuiRDYr_hBsl6riqrQ"
MENTORS_SPREADSHEET_ID = "1zxDrkL_OlJR-oLfT5Saphn9jEdmUxXWSTV7PvtGbaO8"
GOOGLE_SHEETS_CREDENTIALS_PATH = "/app/credentials/secret.json"
BACKUP_DIR = "/app/backups"
```

### Этап 1: Выгрузка из Google Sheets → память + `import_raw.json`
```python
# Инициализация Google Sheets API
credentials = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS_PATH)
service = build('sheets', 'v4', credentials=credentials)

# Выгрузка данных с проверенными диапазонами
students_result = service.spreadsheets().values().get(
    spreadsheetId=MAIN_SPREADSHEET_ID,
    range='Telegram аккаунты студентов!A2:C'
).execute()

projects_result = service.spreadsheets().values().get(
    spreadsheetId=MAIN_SPREADSHEET_ID,
    range='Projects!A2:J'
).execute()

reviews_result = service.spreadsheets().values().get(
    spreadsheetId=MAIN_SPREADSHEET_ID,
    range='Reviews!A2:I'
).execute()

mentors_result = service.spreadsheets().values().get(
    spreadsheetId=MENTORS_SPREADSHEET_ID,
    range='Менторы!E5:J29'
).execute()

sponsored_reviews_result = service.spreadsheets().values().get(
    spreadsheetId=MENTORS_SPREADSHEET_ID,
    range='Платные ревью!A2:M'
).execute()

# Сохранение сырых данных
raw_data = {
    'timestamp': datetime.utcnow().isoformat(),
    'students': students_result.get('values', []),
    'projects': projects_result.get('values', []),
    'reviews': reviews_result.get('values', []),
    'mentors': mentors_result.get('values', []),
    'sponsored_reviews': sponsored_reviews_result.get('values', [])
}
save_to_file('import_raw.json', raw_data)
```

### Этап 2: Telegram-фильтрация и обработка → память + `import_processed.json`

```python
def parse_period(period_str):
    """'Ноябрь, 2021' → '2021-11-01'"""
    month_map = {
        'Январь': 1, 'Февраль': 2, 'Март': 3, 'Апрель': 4,
        'Май': 5, 'Июнь': 6, 'Июль': 7, 'Август': 8,
        'Сентябрь': 9, 'Октябрь': 10, 'Ноябрь': 11, 'Декабрь': 12
    }

    try:
        parts = period_str.replace(',', '').strip().split()
        if len(parts) >= 2:
            month_name = parts[0]
            year = int(parts[1])
            month = month_map.get(month_name)
            if month:
                return f"{year}-{month:02d}-01"
    except:
        pass
    return None

# Обработка студентов (Telegram + GitHub фильтр)
students_processed = []
for row in raw_data['students']:
    github_url = normalize_github_url(row[0])
    telegram_username = row[2].strip() if len(row) > 2 and row[2] else None

    # ❌ ФИЛЬТР: нет GitHub или Telegram
    if not github_url or not telegram_username:
        continue

    students_processed.append({
        'github_url': github_url,
        'telegram_user_id': int(row[1]) if row[1] and row[1].isdigit() else None,
        'telegram_username': telegram_username,
        'role': 'STUDENT'
    })

# Обработка проектов (умная фильтрация + периоды)
projects_processed = []
current_period = None

for row in raw_data['projects']:
    # Заголовки периодов
    if len(row) <= 2 or (len(row) > 1 and not row[1].strip()):
        current_period = parse_period(row[0]) if row and row[0] else None
        continue

    project_name = row[1].strip() if len(row) > 1 and row[1] else None
    github_url = normalize_github_url(row[6].strip()) if len(row) > 6 and row[6] else None

    # ❌ ФИЛЬТР: нет имени проекта или GitHub
    if not project_name or not github_url:
        continue

    projects_processed.append({
        'name': project_name,
        'language': row[2].strip() if len(row) > 2 else None,
        'repository_url': row[4].strip() if len(row) > 4 else None,
        'author_github_url': github_url,
        'has_review': row[7].strip() in ["Есть", "Да"] if len(row) > 7 else False,
        'submission_date': current_period
    })

# Обработка менторов (Telegram только)
mentors_processed = []
for row in raw_data['mentors']:
    if len(row) < 2:
        continue

    mentor_name = row[2].strip() if row[2] else ""
    telegram_username = row[3].strip() if row[3] else ""

    # ❌ ФИЛЬТР: нет Telegram username
    if not telegram_username or not telegram_username.startswith('@'):
        continue

    mentors_processed.append({
        'telegram_username': telegram_username,
        'github_url': None,  # НЕ ОБЯЗАТЕЛЬНО!
        'role': 'MENTOR',
        'profile': {
            'full_name': mentor_name,
            'languages': row[4].strip() if len(row) > 4 else '',
            'services': row[5].strip() if len(row) > 5 else '',
            'price_type': row[6].strip() if len(row) > 6 else '',
            'website_url': row[7].strip() if len(row) > 7 else ''
        }
    })

# Обработка ревью (умная фильтрация)
reviews_processed = []
for row in raw_data['reviews']:
    project_name = row[1].strip() if len(row) > 1 and row[1] else None
    mentor_telegram = row[7].strip() if len(row) > 7 and row[7] else None

    # ❌ ФИЛЬТР: нет проекта или ментора
    if not project_name or not mentor_telegram:
        continue

    reviews_processed.append({
        'project_name': project_name,
        'mentor_telegram': mentor_telegram,
        'period_date': parse_period(row[0]) if row and row[0] else None,
        'review_type': row[4].strip() if len(row) > 4 else None,
        'review_url': row[5].strip() if len(row) > 5 else None
    })

# Сохранение обработанных данных
processed_data = {
    'students': students_processed,
    'mentors': mentors_processed,
    'projects': projects_processed,
    'reviews': reviews_processed
}
save_to_file('import_processed.json', processed_data)
```

### Этап 3: Очистка БД
```python
# В правильном порядке зависимости
await db.execute("DELETE FROM sponsored_reviews")
await db.execute("DELETE FROM reviews")
await db.execute("DELETE FROM mentor_profiles")
await db.execute("DELETE FROM projects")
await db.execute("DELETE FROM users_roles")
await db.execute("DELETE FROM users")
```

### Этап 4: Импорт в БД из памяти
```python
# Создаем маппинги для связывания
github_to_user_id = {}
telegram_to_mentor_id = {}
project_name_to_id = {}

# Импорт студентов
for student in processed_data['students']:
    user_id = await db.insert_and_get_id('users', {
        'telegram_user_id': student['telegram_user_id'],
        'telegram_username': student['telegram_username'],
        'github_url': student['github_url']
    })

    role_id = await get_role_id('STUDENT')
    await db.insert('users_roles', {'user_id': user_id, 'role_id': role_id})

    github_to_user_id[student['github_url']] = user_id

# Импорт менторов
for mentor in processed_data['mentors']:
    user_id = await db.insert_and_get_id('users', {
        'telegram_username': mentor['telegram_username'],
        'github_url': mentor['github_url']  # Может быть NULL
    })

    role_id = await get_role_id('MENTOR')
    await db.insert('users_roles', {'user_id': user_id, 'role_id': role_id})

    await db.insert('mentor_profiles', {
        'user_id': user_id,
        **mentor['profile']
    })

    telegram_to_mentor_id[mentor['telegram_username']] = user_id

# Импорт проектов
for project in processed_data['projects']:
    student_id = github_to_user_id.get(project['author_github_url'])
    if not student_id:
        continue  # Пропускаем если студент не найден

    project_id = await db.insert_and_get_id('projects', {
        'name': project['name'],
        'language': project['language'],
        'repository_url': project['repository_url'],
        'submission_date': project['submission_date'],
        'has_review': project['has_review'],
        'student_id': student_id
    })

    project_name_to_id[project['name']] = project_id

# Импорт ревью
for review in processed_data['reviews']:
    project_id = project_name_to_id.get(review['project_name'])
    mentor_id = telegram_to_mentor_id.get(review['mentor_telegram'])

    if not project_id or not mentor_id:
        continue  # Пропускаем если связи не найдены

    await db.insert('reviews', {
        'project_id': project_id,
        'mentor_id': mentor_id,
        'period_date': review['period_date'],
        'review_type': review['review_type'],
        'review_url': review['review_url']
    })

# Импорт платных ревью (упрощенно)
for s_review in processed_data['sponsored_reviews']:
    # Логика связывания через URL ревью или URL сообщения Telegram
    # ...
    await db.insert('sponsored_reviews', {
        # ... поля ...
    })
```

### Этап 5: Отчет → `import_report.json`
```json
{
  "timestamp": "2025-01-12T14:35:00Z",
  "status": "completed",
  "statistics": {
    "students": {
      "total_in_google": 150,
      "passed_telegram_filter": 145,
      "imported_to_db": 145
    },
    "mentors": {
      "total_in_google": 29,
      "passed_telegram_filter": 29,
      "imported_to_db": 29
    },
    "projects": {
      "total_in_google": 200,
      "imported_to_db": 190,
      "linking_errors": 10
    },
    "reviews": {
      "total_in_google": 180,
      "imported_to_db": 175,
      "linking_errors": 5
    }
  }
}
```

---

## 🎯 Фильтрация по Telegram

**Студенты:**
- ✅ GitHub URL + Telegram username → импорт
- ❌ Без GitHub URL → пропуск
- ❌ Без Telegram username → пропуск

**Менторы:**
- ✅ Telegram username → импорт (GitHub НЕ обязателен)
- ❌ Без Telegram username → пропуск

**Проекты:**
- ✅ Имя проекта + GitHub URL автора → импорт
- ❌ Без имени проекта → пропуск
- ❌ Без GitHub URL автора → пропуск (нет связки со студентом)

**Ревью:**
- ✅ Имя проекта + Telegram ментора → импорт
- ❌ Без проекта → пропуск
- ❌ Без ментора → пропуск

---

## 🔗 Логика связывания

### Проект ↔ Студент
```python
# Через GitHub URL автора проекта
student_id = github_to_user_id.get(project['author_github_url'])
```

### Ревью ↔ Проект + Ментор
```python
# Двойная связь
project_id = project_name_to_id.get(review['project_name'])
mentor_id = telegram_to_mentor_id.get(review['mentor_telegram'])
```

---

## 📁 Файловая структура

```
/app/backups/
├── import_raw.json       # Сырые данные из Google Sheets
├── import_processed.json # Фильтрованные данные
└── import_report.json    # Отчет о результатах
```

---

## ✅ Результат

- **100% пользователей в БД смогут авторизоваться через Telegram**
- **Надежное связывание** проектов со студентами через GitHub
- **Чистая база** без бесполезных записей
- **Полная отладка** через сохраненные файлы
- **Масштабируемая архитектура** для будущих расширений

---

## 📞 Следующие шаги

1. Создать файл конфигурации с ENV переменными
2. Реализовать обработчики Google Sheets API
3. Создать миграции Alembic для таблиц БД
4. Реализовать Data Importer Service с FastAPI
5. Добавить эндпоинты для запуска импорта и проверки статуса

**Команда для продолжения:**
```bash
# Сбросить контекст и начать новый сеанс
# Файл документации готов: /Users/dmitry/Project/meta2/doc/data-importer-architecture.md
```