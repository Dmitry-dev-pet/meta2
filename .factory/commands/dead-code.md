---
description: Scan for dead code with Vulture (fallback to Ruff for unused imports/vars)
argument-hint: [paths] [--exclude=pat1,pat2] [--min-confidence=80]
---

Use the executable command to scan:

- Run: `/deadcode-scan.sh [paths] [--exclude=…] [--min-confidence=…]`

Defaults target `data-importer/src` if no paths are provided.
