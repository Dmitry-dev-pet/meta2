#!/usr/bin/env bash
set -euo pipefail

# Wrapper: run Black in check-only mode (no modifications)
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$repo_root/.factory/commands/black-fix.sh" --check-only "$@"
