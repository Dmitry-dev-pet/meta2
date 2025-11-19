Цель
- Перестроить ERD в три уровня сверху вниз: 1) users, 2) projects, 3) reviews (и sponsored_reviews).

Что сделаю
1) Обновлю `doc/db-erd-3levels.md`: direction TB, layout elk; сгруппирую сущности по уровням:
   - Уровень 1: users, mentor_profiles, users_roles, roles (привязки к users остаются в этом слое)
   - Уровень 2: projects
   - Уровень 3: reviews, sponsored_reviews
2) Переупорядочу связи для якорения уровней (осевой путь users→projects→reviews→sponsored_reviews; остальные связи после оси).
3) Срендерю SVG на последней версии mermaid-cli и проверю, что визуально три уровня соблюдены.
4) По вашему желанию заменю основной `doc/db-erd.md` на 3‑уровневый или оставлю оба варианта.