#!/usr/bin/env bash
set -euo pipefail
SECONDS=0

# Resolve repository root (parent of .factory)
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

# Defaults
default_targets=("src")
check_only=0
paths=()
extra_args=()

# Parse arguments: paths (no leading --), flags (leading --)
for arg in "$@"; do
  if [[ "$arg" == "--check-only" ]]; then
    check_only=1
  elif [[ "$arg" == --* ]]; then
    extra_args+=("$arg")
  else
    paths+=("$arg")
  fi
done

if [[ ${#paths[@]} -eq 0 ]]; then
  paths=("${default_targets[@]}")
fi
# Normalize paths if user passed workspace-relative like data-importer/src
for i in "${!paths[@]}"; do
  case "${paths[$i]}" in
    data-importer/*) paths[$i]="${paths[$i]#data-importer/}" ;;
  esac
done

# Enter service directory
cd "$repo_root/data-importer" || { echo "data-importer directory not found" >&2; exit 1; }

# Compose fix flag
fix_flag=("--fix")
if [[ $check_only -eq 1 ]]; then
  fix_flag=()
fi

RUFF_RUNNER=""
do_ruff() {
  # Usage: do_ruff <with_fix:0|1> [paths and extra args...]
  local with_fix="$1"; shift || true
  local args=(check)
  # Append remaining args
  while (( "$#" )); do args+=("$1"); shift; done
  if [[ "$with_fix" -eq 1 ]]; then args+=("--fix"); fi

  # Try via rye
  if rye run ruff "${args[@]}"; then
    RUFF_RUNNER="rye run ruff"
    return 0
  fi
  # Try plain ruff
  if command -v ruff >/dev/null 2>&1; then
    if ruff "${args[@]}"; then RUFF_RUNNER="ruff"; return 0; fi
  fi
  # Try python -m ruff
  if python3 -m ruff --version >/dev/null 2>&1; then
    if python3 -m ruff "${args[@]}"; then RUFF_RUNNER="python3 -m ruff"; return 0; fi
  fi
  echo "Ruff not available or failed to run" >&2
  return 127
}

# 1) Fix (unless check-only)
mode="check-only"
if [[ $check_only -eq 0 ]]; then mode="fix+verify"; fi

target_list="${paths[*]}"
echo "Ruff: mode=${mode}; targets=${target_list}"

if [[ $check_only -eq 0 ]]; then
  # Build arg list safely (avoid unbound array expansion)
  all_args=()
  if (( ${#paths[@]} )); then all_args+=("${paths[@]}"); fi
  if (( ${#extra_args[@]} )); then all_args+=("${extra_args[@]}"); fi
  echo "→ Fix phase..."
  if ! do_ruff 1 "${all_args[@]}" >/dev/null; then
    echo "Fix phase: FAILED" >&2
    exit 1
  fi
  echo "Fix phase: OK"
fi

# 2) Verify clean
all_args=()
if (( ${#paths[@]} )); then all_args+=("${paths[@]}"); fi
if (( ${#extra_args[@]} )); then all_args+=("${extra_args[@]}"); fi
echo "→ Verify phase..."
if ! do_ruff 0 "${all_args[@]}" >/dev/null; then
  echo "Verify phase: FAILED" >&2
  exit 1
fi
echo "Verify phase: All checks passed"
echo "Runner: ${RUFF_RUNNER}; elapsed: ${SECONDS}s"
