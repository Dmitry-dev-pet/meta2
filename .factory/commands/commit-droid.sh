#!/usr/bin/env bash
set -euo pipefail
SECONDS=0

# Defaults
MESSAGE=""
ADD_ALL=1
NO_PREFLIGHT=0
DRY_RUN=0
SIGNOFF=0
NO_VERIFY=0
FILES=()

print_help() {
  cat <<EOF
Usage: $(basename "$0") [options] [--] [files...]

Options:
  -m, --message TXT      Commit message (required unless --dry-run).
  --no-preflight         Skip preflight checks (ruff/black/typecheck/mermaid).
  --no-add-all           Do not stage all changes; only provided files.
  --dry-run              Show what would be committed without committing.
  --signoff              Add Signed-off-by trailer.
  --no-verify            Skip pre-commit hooks.
  -h, --help             Show this help.

Notes:
  - Runs inside data-importer git repo if present.
  - Preflight runs:
      * .factory/commands/black-check.sh
      * .factory/commands/ruff-check.sh
      * .factory/commands/typecheck.sh
      * .factory/commands/mermaid-validate.sh doc/
EOF
}

while (( "$#" )); do
  case "$1" in
    -m|--message) MESSAGE="${2:-}"; shift 2;;
    --no-preflight) NO_PREFLIGHT=1; shift;;
    --no-add-all) ADD_ALL=0; shift;;
    --dry-run) DRY_RUN=1; shift;;
    --signoff) SIGNOFF=1; shift;;
    --no-verify) NO_VERIFY=1; shift;;
    -h|--help) print_help; exit 0;;
    --) shift; while (( "$#" )); do FILES+=("$1"); shift; done;;
    -*) echo "Unknown option: $1" >&2; print_help; exit 2;;
    *) FILES+=("$1"); shift;;
  esac
done

# Resolve repo directory (prefer data-importer)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ -d "$ROOT/data-importer/.git" ]]; then
  REPO_DIR="$ROOT/data-importer"
else
  if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    REPO_DIR="$ROOT"
  else
    echo "No git repository found." >&2; exit 128
  fi
fi
cd "$REPO_DIR"

echo "Commit droid: repo=$(pwd) preflight=$((1-NO_PREFLIGHT)) add_all=$ADD_ALL dry_run=$DRY_RUN"

# Preflight checks
if [[ $NO_PREFLIGHT -eq 0 ]]; then
  echo "Preflight: Black check..."
  bash "$ROOT/.factory/commands/black-fix.sh" --check-only >/dev/null
  echo "Preflight: Ruff check..."
  bash "$ROOT/.factory/commands/ruff-check.sh" >/dev/null
  echo "Preflight: Typecheck..."
  bash "$ROOT/.factory/commands/typecheck.sh" >/dev/null
  echo "Preflight: Mermaid validate (doc/)..."
  if [[ -d "$ROOT/doc" ]]; then
    bash "$ROOT/.factory/commands/mermaid-validate.sh" "$ROOT/doc" >/dev/null || {
      echo "Mermaid validation failed." >&2; exit 1; }
  fi
  echo "Preflight OK"
fi

# Stage files
if [[ $ADD_ALL -eq 1 && ${#FILES[@]} -eq 0 ]]; then
  git add -A
else
  if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "No files specified and --no-add-all set; nothing to stage." >&2
    exit 2
  fi
  git add -- "${FILES[@]}"
fi

# Show status and ensure there is something to commit
git status --short
if git diff --cached --quiet; then
  echo "No staged changes to commit." >&2
  exit 0
fi

echo "Staged changes:" && git diff --cached --name-status

if [[ $DRY_RUN -eq 1 ]]; then
  echo "Dry-run: would commit with message:" >&2
  printf '\n%s\n' "${MESSAGE:-<no message provided>}"
  echo "Elapsed: ${SECONDS}s"
  exit 0
fi

if [[ -z "$MESSAGE" ]]; then
  echo "Commit message is required (use -m)." >&2
  exit 2
fi

COMMIT_CMD=(git commit -m "$MESSAGE

Co-authored-by: factory-droid[bot] <138933559+factory-droid[bot]@users.noreply.github.com>")
[[ $SIGNOFF -eq 1 ]] && COMMIT_CMD+=(--signoff)
[[ $NO_VERIFY -eq 1 ]] && COMMIT_CMD+=(--no-verify)

"${COMMIT_CMD[@]}"

echo "Commit created:" && git log -1 --oneline
echo "Elapsed: ${SECONDS}s"
