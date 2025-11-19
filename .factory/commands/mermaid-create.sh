#!/usr/bin/env bash
set -euo pipefail

# Generate a Mermaid diagram file (Markdown with ```mermaid block),
# applying safe defaults and ER-specific normalizations, then optionally validate/render.

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

type="erDiagram"
direction="LR"
theme="neutral"
title=""
output="doc/diagram.md"
render=0
no_theme_vars=0

print_help() {
  cat <<EOF
Usage: $(basename "$0") [--type erDiagram|flowchart|classDiagram] [--direction LR|TB|BT|RL] \
       [--theme default|neutral|dark|forest|base] [--title TITLE] [--output PATH] [--render] [--no-theme-vars]

Reads Mermaid body from stdin (recommended) or env MERMAID_BODY and writes a Markdown file
with a mermaid code block and frontmatter config. For erDiagram, applies:
 - PK/FK normalization: ' PK FK' -> ' PK, FK'
 - Type mapping: INTEGER/BIGINT->int, VARCHAR/TEXT->string, NUMERIC->float, DATE->date, DATETIME->datetime
 - Preserves user casing otherwise.

Examples:
  printf '%s\n' 'users { int id PK }' | bash .factory/commands/mermaid-create.sh --output doc/db.mmd --render
  MERMAID_BODY=$'users {\n  string name\n}' bash .factory/commands/mermaid-create.sh -o doc/users.md
EOF
}

while (( "$#" )); do
  case "$1" in
    --type) type="${2:-$type}"; shift 2;;
    --direction) direction="${2:-$direction}"; shift 2;;
    --theme) theme="${2:-$theme}"; shift 2;;
    --title) title="${2:-}"; shift 2;;
    -o|--output) output="${2:-$output}"; shift 2;;
    --render) render=1; shift;;
    --no-theme-vars) no_theme_vars=1; shift;;
    -h|--help) print_help; exit 0;;
    --) shift; break;;
    -*) echo "Unknown option: $1" >&2; print_help; exit 2;;
    *) break;;
  esac
done

# Read body
body="${MERMAID_BODY:-}"
if [[ -z "$body" ]]; then
  if ! IFS= read -r -d '' body; then
    # read until EOF
    body="$(cat || true)"
  fi
fi

if [[ -z "$body" ]]; then
  echo "No Mermaid body provided on stdin or MERMAID_BODY." >&2
  exit 2
fi

# Normalize for erDiagram only
norm_body="$body"
if [[ "$type" == "erDiagram" ]]; then
  # Ensure newlines between attributes (replace multiple spaces between tokens with single space)
  norm_body="$(printf '%s\n' "$norm_body" | sed 's/[\t]\+/ /g')"
  # PK FK -> PK, FK
  norm_body="$(printf '%s\n' "$norm_body" | sed 's/ PK[ ]\+FK/ PK, FK/g')"
  # Common SQL-ish types -> Mermaid canonical
  norm_body="$(printf '%s\n' "$norm_body" \
    | sed -E 's/\bINTEGER\b/int/g; s/\bBIGINT\b/int/g; s/\bINT\b/int/g' \
    | sed -E 's/\bVARCHAR(\([^)]*\))?/string/g; s/\bTEXT\b/string/g; s/\bSTRING\b/string/g' \
    | sed -E 's/\bNUMERIC(\([^)]*\))?/float/g; s/\bDECIMAL(\([^)]*\))?/float/g; s/\bFLOAT\b/float/g' \
    | sed -E 's/\bDATE\b/date/g; s/\bDATETIME\b/datetime/g')"
fi

out_dir="$(dirname "$output")"
mkdir -p "$out_dir"

tmp_file="$(mktemp)"
{
  printf '```mermaid\n'
  printf '---\n'
  printf 'config:\n'
  printf '  theme: %s\n' "$theme"
  if [[ $no_theme_vars -eq 0 ]]; then
    cat <<THEMEVARS
  themeVariables:
    primaryColor: "#E2E8F0"
    primaryBorderColor: "#94A3B8"
    primaryTextColor: "#1F2937"
    lineColor: "#64748B"
    tertiaryColor: "#F8FAFC"
THEMEVARS
  fi
  printf '---\n'
  printf '%s\n' "$type"
  printf '    direction %s\n' "$direction"
  if [[ -n "$title" ]]; then
    printf '    %% %s\n' "$title"
  fi
  # Indent body by 4 spaces to stay within block
  printf '%s\n' "$norm_body" | sed 's/^/    /'
  printf '```\n'
} > "$tmp_file"

mv "$tmp_file" "$output"
echo "Created: $output"

# Validate / render
if [[ $render -eq 1 ]]; then
  bash "$repo_root/.factory/commands/mermaid-validate.sh" --render-dir "$out_dir" "$output"
fi

exit 0
