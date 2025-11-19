#!/usr/bin/env bash
set -euo pipefail

# Defaults
TITLE=""
BODY=""
BRANCH_NAME=""
BASE="main"
MESSAGE=""
NO_PREFLIGHT=0
FILES=()

print_help() {
  cat <<EOF
Usage: $(basename "$0") [options] [--] [files...]

Options:
  --title TXT            PR Title (required).
  --body TXT             PR Body (required).
  --branch TXT           New branch name (required).
  --base TXT             Base branch (default: main).
  --message TXT          Commit message (defaults to title).
  --no-preflight         Skip preflight checks.
  -h, --help             Show this help.
EOF
}

while (( "$#" )); do
  case "$1" in
    --title) TITLE="${2:-}"; shift 2;;
    --body) BODY="${2:-}"; shift 2;;
    --branch) BRANCH_NAME="${2:-}"; shift 2;;
    --base) BASE="${2:-}"; shift 2;;
    --message) MESSAGE="${2:-}"; shift 2;;
    --no-preflight) NO_PREFLIGHT=1; shift;;
    -h|--help) print_help; exit 0;;
    --) shift; while (( "$#" )); do FILES+=("$1"); shift; done;;
    -*) echo "Unknown option: $1" >&2; print_help; exit 2;;
    *) FILES+=("$1"); shift;;
  esac
done

if [[ -z "$TITLE" || -z "$BODY" || -z "$BRANCH_NAME" ]]; then
  echo "Error: --title, --body, and --branch are required." >&2
  exit 1
fi

if [[ -z "$MESSAGE" ]]; then
  MESSAGE="$TITLE"
fi

# Resolve root
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# 1. Create and checkout branch
echo "Creating branch '$BRANCH_NAME'..."
git checkout -b "$BRANCH_NAME"

# 2. Commit changes using commit-droid.sh
echo "Committing changes..."
COMMIT_ARGS=("--message" "$MESSAGE")
if [[ $NO_PREFLIGHT -eq 1 ]]; then
  COMMIT_ARGS+=("--no-preflight")
fi

# Pass files if any
if [[ ${#FILES[@]} -gt 0 ]]; then
  COMMIT_ARGS+=("--no-add-all")
  COMMIT_ARGS+=("--")
  COMMIT_ARGS+=("${FILES[@]}")
fi

bash .factory/commands/commit-droid.sh "${COMMIT_ARGS[@]}"

# 3. Push branch
echo "Pushing branch '$BRANCH_NAME'..."
git push -u origin "$BRANCH_NAME"

# 4. Create PR
echo "Creating Pull Request..."
gh pr create --title "$TITLE" --body "$BODY" --base "$BASE" --head "$BRANCH_NAME"

echo "PR creation complete."
