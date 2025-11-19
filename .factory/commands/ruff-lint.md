---
description: Run Ruff autofix or check-only on Python sources
argument-hint: [paths] [--check-only] [extra ruff args]
---

Use the executable command to lint:

- Fix + verify: `/ruff-fix.sh [paths] [extra ruff args]`
- Check-only: `/ruff-check.sh [paths] [extra ruff args]`

Defaults target `data-importer/src` if no paths are provided.
