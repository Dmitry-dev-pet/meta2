#!/usr/bin/env bash
set -euo pipefail
SECONDS=0

# Resolve repository root (parent of .factory)
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"

# Defaults
default_targets=("src")
paths=()
vulture_args=()
exclude_default="migrations,.venv,venv,logs,backups"
min_confidence_default="90"
exclude="$exclude_default"
min_confidence="$min_confidence_default"

# Parse arguments
for arg in "$@"; do
  case "$arg" in
    --exclude=*) exclude="${arg#--exclude=}" ;;
    --min-confidence=*) min_confidence="${arg#--min-confidence=}" ;;
    --*) vulture_args+=("$arg") ;;
    *) paths+=("$arg") ;;
  esac
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

cd "$repo_root/data-importer" || { echo "data-importer directory not found" >&2; exit 1; }

runner=""

run_vulture() {
  local args=("${paths[@]}")
  # Apply exclude and min-confidence unless user already provided
  local has_exclude=0 has_conf=0
  if [[ ${vulture_args+x} ]]; then
    for a in "${vulture_args[@]}"; do
      [[ "$a" == --exclude=* ]] && has_exclude=1 || true
      [[ "$a" == --min-confidence=* ]] && has_conf=1 || true
    done
  fi
  if [[ $has_exclude -eq 0 && -n "$exclude" ]]; then
    args+=("--exclude" "$exclude")
  fi
  if [[ $has_conf -eq 0 && -n "$min_confidence" ]]; then
    args+=("--min-confidence" "$min_confidence")
  fi
  # Append any extra user args (after defaults to allow overrides)
  if [[ ${vulture_args+x} ]]; then
    args+=("${vulture_args[@]}")
  fi

  # Try via rye
  if rye run vulture "${args[@]}"; then
    runner="rye run vulture"
    return 0
  fi
  # Try plain vulture
  if command -v vulture >/dev/null 2>&1; then
    if vulture "${args[@]}"; then runner="vulture"; return 0; fi
  fi
  # Try python -m vulture
  if python3 -m vulture --version >/dev/null 2>&1; then
    if python3 -m vulture "${args[@]}"; then runner="python3 -m vulture"; return 0; fi
  fi
  return 127
}

echo "DeadCode: targets=${paths[*]} (exclude=${exclude}; min-confidence=${min_confidence})"

# Capture output to summarize
set +e
output="$(run_vulture 2>&1)"
status=$?
set -e

if [[ $status -eq 127 ]]; then
  echo "Vulture not available. Fallback: Ruff unused checks (limited)." >&2
  # Limited fallback using Ruff
  if rye run ruff check "${paths[@]}" --select F401,F841; then
    echo "Fallback Ruff: no unused imports/variables found"
  else
    echo "Fallback Ruff findings (unused imports/vars):"
    rye run ruff check "${paths[@]}" --select F401,F841 || true
  fi
  exit 0
fi

issues=$(printf '%s' "$output" | grep -c ":" || true)
if [[ $issues -eq 0 ]]; then
  echo "No dead code candidates found"
else
  echo "Candidates found: $issues"
  # Show last 50 lines for brevity
  echo "--- Last findings ---"
  printf '%s' "$output" | tail -n 50 || true
fi
echo "Runner: ${runner:-unknown}; elapsed: ${SECONDS}s"

