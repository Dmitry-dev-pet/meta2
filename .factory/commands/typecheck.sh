#!/usr/bin/env bash
set -euo pipefail
SECONDS=0

# Resolve repo root
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

# Defaults
default_targets=("src")
paths=()
extra_args=()
strict=0

# Args parsing
for arg in "$@"; do
  case "$arg" in
    --strict) strict=1 ;;
    --*) extra_args+=("$arg") ;;
    *) paths+=("$arg") ;;
  esac
done

if [[ ${#paths[@]} -eq 0 ]]; then
  paths=("${default_targets[@]}")
fi

# Normalize possible workspace-relative path
for i in "${!paths[@]}"; do
  case "${paths[$i]}" in
    data-importer/*) paths[$i]="${paths[$i]#data-importer/}" ;;
  esac
done

cd "$repo_root/data-importer" || { echo "data-importer directory not found" >&2; exit 1; }

config_detected=0
if grep -q "^\[tool.mypy\]" pyproject.toml 2>/dev/null; then
  config_detected=1
fi

MYPY_RUNNER=""
# Detect runner once, then execute while preserving exit code
if rye run mypy --version >/dev/null 2>&1; then
  MYPY_RUNNER="rye run mypy"
elif command -v mypy >/dev/null 2>&1; then
  MYPY_RUNNER="mypy"
elif python3 -m mypy --version >/dev/null 2>&1; then
  MYPY_RUNNER="python3 -m mypy"
else
  echo "Mypy is not available. Install it in dev dependencies to enable type checking." >&2
  exit 127
fi

# Build argument list
args=()
if [[ $config_detected -eq 0 ]]; then
  # No config; keep noise low by default
  args+=("--ignore-missing-imports")
fi
if [[ $strict -eq 1 ]]; then
  args+=("--strict")
fi

if (( ${#extra_args[@]} )); then args+=("${extra_args[@]}"); fi
args+=("${paths[@]}")

echo "Typecheck: targets=${paths[*]}; strict=${strict}; config=${config_detected}" 

set +e
output="$( ${MYPY_RUNNER} "${args[@]}" 2>&1 )"
status=$?
set -e

if [[ $status -eq 0 ]]; then
  echo "All type checks passed"
  echo "Runner: ${MYPY_RUNNER}; elapsed: ${SECONDS}s"
  exit 0
fi

# Summarize errors
echo "--- Last 40 lines ---"
printf '%s' "$output" | tail -n 40 || true
summary_line=$(printf '%s' "$output" | grep -E "^Found [0-9]+ errors? in [0-9]+ files?" | tail -n 1 || true)
if [[ -n "$summary_line" ]]; then echo "$summary_line"; fi
echo "Runner: ${MYPY_RUNNER}; elapsed: ${SECONDS}s"
exit 1
