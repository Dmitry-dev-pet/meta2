---
level: c3
component: DataProcessor
tags: [feature, filtering, validation]
last_updated: 2025-11-19
---

# Feature: Data Filtering

## What
Интеллектуальная фильтрация данных перед импортом для обеспечения качества.

## Why
- **Telegram Integration**: Только пользователи с Telegram username могут аутентифицироваться
- **Data Quality**: Некорректные данные не попадают в БД
- **Flexible Rules**: Разные правила для разных типов пользователей

## How

### Student Filtering
**Rule**: Telegram username **OR** GitHub URL

```python
def process_students(data: List[Dict]) -> List[User]:
    filtered = []
    for student in data:
        telegram_username = student.get('telegram_username')
        github_url = student.get('github_url')
        
        # Accept if has Telegram OR GitHub
        if telegram_username or github_url:
            filtered.append(student)
    
    return filtered
```

**Rationale**: 
- Telegram для аутентификации (приоритет)
- GitHub для связи с проектами (fallback)
- Оба не требуются одновременно

### Mentor Filtering
**Rule**: Telegram username **REQUIRED**

```python
def process_mentors(data: List[Dict]) -> List[User]:
    filtered = []
    for mentor in data:
        telegram_username = mentor.get('telegram_username')
        
        # Telegram is mandatory
        if telegram_username:
            filtered.append(mentor)
    
    return filtered
```

**Rationale**:
- Менторы обязательно взаимодействуют через Telegram
- Нет Telegram = нет смысла импортировать

### Project Filtering
**Rule**: Принадлежность студенту (GitHub URL match)

```python
def filter_projects_by_students(
    projects: List[Dict],
    students: List[User]
) -> List[Project]:
    student_github_urls = {s.github_url for s in students if s.github_url}
    
    filtered = []
    for project in projects:
        repo_url = project.get('repository_url')
        
        # Extract author from URL
        author_url = extract_author_url(repo_url)
        
        if author_url in student_github_urls:
            filtered.append(project)
    
    return filtered
```

**Rationale**:
- Проекты без студента = данные-сироты
- Связь через GitHub URL автора

### Review Linking
**Rule**: Ментор и проект должны существовать

```python
def link_reviews(
    reviews: List[Dict],
    mentors: List[User],
    projects: List[Project]
) -> List[Review]:
    mentor_map = {m.telegram_username: m.id for m in mentors}
    project_map = {p.id: p for p in projects}
    
    linked = []
    for review in reviews:
        mentor_id = mentor_map.get(review['mentor_telegram'])
        project_id = review.get('project_id')
        
        if mentor_id and project_id in project_map:
            review['mentor_id'] = mentor_id
            review['project_id'] = project_id
            linked.append(review)
    
    return linked
```

## Statistics
После импорта генерируется статистика:
- Total fetched vs filtered
- Фильтрация по каждой категории
- Linking errors

Example:
```json
{
  "students": {
    "fetched": 600,
    "filtered": 544,
    "reason": "No Telegram or GitHub"
  },
  "projects": {
    "fetched": 1500,
    "filtered": 1222,
    "reason": "Author не найден в студентах"
  }
}
```

## Related Components
- [DataProcessor](../components.md#dataprocessor)
- [Import Flow](import_flow.md)

## Code References
- `src/data_importer/services/data_processor.py`
