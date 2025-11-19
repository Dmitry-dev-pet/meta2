Предлагаю добавить управляемые стили типов + легенду:

Опции (в скрипте mermaid-create.sh)
- --type-style raw|upper|abbr|rename
  - raw: int,string,float,date,datetime (как сейчас)
  - upper: INT,STRING,FLOAT,DATE,DATETIME
  - abbr: I,S,F,D,DT (добавим Legend c расшифровкой)
  - rename: оставить тип нейтральным (например, any) и перенести тип в имя атрибута суффиксом (_i,_s,_f,_d,_dt) — парсер валиден, визуально заметно; Legend включена
- --legend none|short|full — генерировать таблицу Legend (без кастомной class/style, чтобы не ломать парсер)

Реализация
1) Доработать .factory/commands/mermaid-create.sh: маппинг типов и режим rename (переименование атрибутов).
2) Обновить три диаграммы (axis/symmetric/minpull) выбранным стилем (например, abbr+legend=short) и перерендерить.
3) Оставить последнюю версию mermaid-cli для рендера (как вы просили), валидатор уже поддерживает latest.

Выберите стиль (raw/upper/abbr/rename) и вид легенды (none/short/full), после чего применю к трём файлам и перегенерирую SVG.