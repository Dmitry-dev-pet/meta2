#!/usr/bin/env bash
set -euo pipefail

# Generate a Mermaid diagram file (Markdown with ```mermaid block),
# applying safe defaults and ER-specific normalizations, then optionally validate/render.

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

type="erDiagram"
direction="LR"
direction_set=0
theme="neutral"
title=""
output="doc/diagram.md"
render=0
no_theme_vars=0
layout="elk"
type_style="raw"   # raw|upper|abbr|rename
legend="none"      # none|short|full
orientation=""
orientation_set=0
background=""

print_help() {
  cat <<EOF
Usage: $(basename "$0") [--type erDiagram|flowchart|classDiagram] [--direction LR|TB|BT|RL] \
       [--theme default|neutral|dark|forest|base] [--title TITLE] [--output PATH] [--render] [--no-theme-vars] [--layout elk|dagre] \
       [--type-style raw|upper|abbr|rename] [--legend none|short|full] [--orientation horizontal|vertical] [--background CSS_COLOR]

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
    --direction) direction="${2:-$direction}"; direction_set=1; shift 2;;
    --theme) theme="${2:-$theme}"; shift 2;;
    --title) title="${2:-}"; shift 2;;
    -o|--output) output="${2:-$output}"; shift 2;;
    --render) render=1; shift;;
    --no-theme-vars) no_theme_vars=1; shift;;
    --layout) layout="${2:-$layout}"; shift 2;;
    --type-style) type_style="${2:-$type_style}"; shift 2;;
    --legend) legend="${2:-$legend}"; shift 2;;
    --orientation) orientation="${2:-}"; orientation_set=1; shift 2;;
    --background) background="${2:-}"; shift 2;;
    -h|--help) print_help; exit 0;;
    --) shift; break;;
    -*) echo "Unknown option: $1" >&2; print_help; exit 2;;
    *) break;;
  esac
done

# Map orientation to direction if direction not explicitly set
if [[ $direction_set -eq 0 && $orientation_set -eq 1 ]]; then
  case "$orientation" in
    horizontal|Horizontal|H|h) direction="LR";;
    vertical|Vertical|V|v) direction="TB";;
  esac
fi

# Read body
body="${MERMAID_BODY:-}"
if [[ -z "$body" ]]; then
  # Read entire stdin into body (non-interactive safe)
  body="$(cat || true)"
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
  # Common SQL-ish types -> Mermaid canonical (lower) for a stable base
  norm_body="$(printf '%s\n' "$norm_body" \
    | sed -E 's/\bINTEGER\b/int/g; s/\bBIGINT\b/int/g; s/\bINT\b/int/g' \
    | sed -E 's/\bVARCHAR(\([^)]*\))?/string/g; s/\bTEXT\b/string/g; s/\bSTRING\b/string/g' \
    | sed -E 's/\bNUMERIC(\([^)]*\))?/float/g; s/\bDECIMAL(\([^)]*\))?/float/g; s/\bFLOAT\b/float/g' \
    | sed -E 's/\bDATE\b/date/g; s/\bDATETIME\b/datetime/g')"

  # Apply type styling or renaming via python for robust parsing
  if [[ "$type_style" != "raw" ]]; then
    norm_body="$(printf '%s\n' "$norm_body" | python3 - "$type_style" <<'PY'
import sys,re
style=sys.argv[1]
text=sys.stdin.read().splitlines()
out=[]
in_entity=False
brace_level=0
# Match attribute lines: indent, type, name, rest
attr_re=re.compile(r'^(\s+)([A-Za-z][A-Za-z0-9_]*)\s+([A-Za-z][A-Za-z0-9_]*)(.*)$')
typemap={
    'int': ('INT','I','_i'),
    'integer': ('INT','I','_i'),
    'bigint': ('INT','I','_i'),
    'string': ('STRING','S','_s'),
    'text': ('STRING','S','_s'),
    'float': ('FLOAT','F','_f'),
    'numeric': ('FLOAT','F','_f'),
    'decimal': ('FLOAT','F','_f'),
    'date': ('DATE','D','_d'),
    'datetime': ('DATETIME','DT','_dt'),
}
for line in text:
    stripped=line.strip()
    # Enter/exit entity block based on single-line braces
    if stripped.endswith('{'):
        in_entity=True
        out.append(line)
        continue
    if in_entity and stripped=='}':
        in_entity=False
        out.append(line)
        continue
    if in_entity:
        m=attr_re.match(line)
        if m:
            indent, typ, name, rest = m.groups()
            key=typ.lower()
            if key in typemap:
                up, abbr, suf = typemap[key]
                if style=='upper':
                    typ=up
                elif style=='abbr':
                    typ=abbr
                elif style=='rename':
                    typ='string'
                    if not name.endswith(suf):
                        name=f"{name}{suf}"
            out.append(f"{indent}{typ} {name}{rest}")
            continue
    out.append(line)
print('\n'.join(out))
PY
)"
  fi

  # Append Legend if requested
  if [[ "$legend" != "none" ]]; then
    legend_block=""
    case "$type_style" in
      raw|upper)
        # Use style-aware tokens
        if [[ "$type_style" == "upper" ]]; then
          t_int=INT; t_str=STRING; t_flt=FLOAT; t_date=DATE; t_dt=DATETIME
        else
          t_int=int; t_str=string; t_flt=float; t_date=date; t_dt=datetime
        fi
        legend_block=$(cat <<LEG

    Legend {
      $t_int integer_number
      $t_str text_value
      $t_flt decimal_number
      $t_date yyyy_mm_dd
      $t_dt timestamp
    }
LEG
)
        ;;
      abbr)
        legend_block=$(cat <<'LEG'

    Legend {
      I int
      S string
      F float
      D date
      DT datetime
    }
LEG
)
        ;;
      rename)
        legend_block=$(cat <<'LEG'

    Legend {
      _i int
      _s string
      _f float
      _d date
      _dt datetime
    }
LEG
)
        ;;
    esac
    norm_body="$norm_body$legend_block"
  fi
fi

out_dir="$(dirname "$output")"
mkdir -p "$out_dir"

tmp_file="$(mktemp)"
{
  printf '```mermaid\n'
  printf -- '---\n'
  printf 'config:\n'
  printf '  theme: %s\n' "$theme"
  printf '  layout: %s\n' "$layout"
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
  printf -- '---\n'
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
  bg_arg=()
  if [[ -n "$background" ]]; then
    bg_arg+=( --background "$background" )
  elif [[ "$theme" == "dark" ]]; then
    bg_arg+=( --background "#0F172A" )
  fi
  bash "$repo_root/.factory/commands/mermaid-validate.sh" --render-dir "$out_dir" "${bg_arg[@]}" "$output"
fi

exit 0
