Scope
- Tidy `doc/db-erd.md` (Mermaid ERD), `.factory/commands/mermaid-create.sh`, and `.factory/droids/mermaid-create.md` for consistency, readability, and robustness.

Planned changes
1) ERD (`doc/db-erd.md`)
- Ensure single well‑formed ```mermaid block with frontmatter, `direction LR`, `layout: elk`, and consistent themeVariables.
- Normalize entities: lowercase types (int/string/float/date/datetime), attributes per line, flags as `PK, FK`, consistent quoting and spacing.
- Move all relationships to the end, grouped logically (users → projects/reviews → sponsored_*), and remove redundant labels.
- Validate and re‑render SVG (no content changes beyond formatting).

2) mermaid-create.sh
- Harden stdin reading (no `read -d ''`), safer temp handling, clear errors; keep `set -euo pipefail`.
- Constrain type/flag normalization to attribute tokens only (avoid touching names/comments), handle `FK, PK` order, and skip mapping inside quotes.
- Add flags: `--layout elk` (default), `--no-render`, and robust output handling for .md/.mmd; print created file(s) paths.

3) mermaid-create.md
- Update inputs/flags docs (type/direction/theme/layout/render/no_theme_vars), provide concise examples, and note normalization rules/limits.

Acceptance
- ERD renders with all attributes visible; validator passes; CLI script idempotent and safe; droid docs match script behavior.

Proceed? I’ll apply these tidy-ups and re‑validate without altering semantics.