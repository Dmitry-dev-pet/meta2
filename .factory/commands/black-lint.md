---
description: Run Black formatting (fix) or check-only on Python sources
argument-hint: [paths] [--check-only] [extra black args]
---

Use the executable commands to format or validate formatting:

- Fix + verify: `/black-fix.sh [paths] [extra black args]`
- Check-only: `/black-check.sh [paths] [extra black args]`

Defaults target `data-importer/src` if no paths are provided.
