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

BLACK_RUNNER=""
do_black() {
  # Usage: do_black <with_fix:0|1> [paths and extra args...]
  local with_fix="$1"; shift || true
  local args=()
  # Append remaining args
  while (( "$#" )); do args+=("$1"); shift; done
  if [[ "$with_fix" -eq 0 ]]; then args+=("--check"); fi

  # Try via rye
  if rye run black "${args[@]}"; then
    BLACK_RUNNER="rye run black"
    return 0
  fi
  # Try plain black
  if command -v black >/dev/null 2>&1; then
    if black "${args[@]}"; then BLACK_RUNNER="black"; return 0; fi
  fi
  # Try python -m black
  if python3 -m black --version >/dev/null 2>&1; then
    if python3 -m black "${args[@]}"; then BLACK_RUNNER="python3 -m black"; return 0; fi
  fi
  echo "Black not available or failed to run" >&2
  return 127
}

mode="check-only"
if [[ $check_only -eq 0 ]]; then mode="fix+verify"; fi

target_list="${paths[*]}"
echo "Black: mode=${mode}; targets=${target_list}"

# Build arg list safely
all_args=()
if (( ${#paths[@]} )); then all_args+=("${paths[@]}"); fi
if (( ${#extra_args[@]} )); then all_args+=("${extra_args[@]}"); fi

if [[ $check_only -eq 0 ]]; then
  echo "→ Format (fix) phase..."
  if ! do_black 1 "${all_args[@]}" >/dev/null; then
    echo "Format phase: FAILED" >&2
    exit 1
  fi
  echo "Format phase: OK"
fi

echo "→ Verify phase (check)..."
if ! do_black 0 "${all_args[@]}" >/dev/null; then
  echo "Verify phase: FAILED" >&2
  exit 1
fi
echo "Verify phase: All files well formatted"
echo "Runner: ${BLACK_RUNNER}; elapsed: ${SECONDS}s"
