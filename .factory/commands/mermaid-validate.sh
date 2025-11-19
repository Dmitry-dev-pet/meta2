#!/usr/bin/env bash
set -euo pipefail
SECONDS=0

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
render_dir=""
format="svg"
paths=()

while (( "$#" )); do
  case "$1" in
    --render-dir)
      render_dir="${2:-}"
      shift 2 ;;
    --format)
      format="${2:-svg}"
      shift 2 ;;
    --help|-h)
      cat <<EOF
Usage: $(basename "$0") [--render-dir DIR] [--format svg|png] [paths...]
 - Validate Mermaid files (.mmd) and Markdown with mermaid code blocks.
 - By default scans current repo for *.mmd and *.md.
 - If --render-dir is set, outputs rendered files there; otherwise renders to a temp dir and deletes after.
EOF
      exit 0 ;;
    --*) echo "Unknown option: $1" >&2; exit 2 ;;
    *) paths+=("$1"); shift ;;
  esac
done

cd "$repo_root"

tmp_dir=""
cleanup() { [[ -n "$tmp_dir" && -d "$tmp_dir" && -z "$render_dir" ]] && rm -rf "$tmp_dir" || true; }
trap cleanup EXIT

if [[ -z "$render_dir" ]]; then
  tmp_dir="$(mktemp -d)"
fi

# Collect files
if [[ ${#paths[@]} -eq 0 ]]; then
  mapfile -t files < <(find . -type f \( -name '*.mmd' -o -name '*.md' \) | sort)
else
  files=()
  for p in "${paths[@]}"; do
    if [[ -d "$p" ]]; then
      while IFS= read -r f; do files+=("$f"); done < <(find "$p" -type f \( -name '*.mmd' -o -name '*.md' \))
    elif [[ -f "$p" ]]; then
      files+=("$p")
    else
      echo "Warning: path not found or unsupported pattern: $p" >&2
    fi
  done
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No candidate files found (*.mmd, *.md)." >&2
  exit 0
fi

# Choose runner
MMDC=""
if command -v npx >/dev/null 2>&1; then
  MMDC="npx -y @mermaid-js/mermaid-cli"
elif command -v docker >/dev/null 2>&1; then
  MMDC="docker run --rm -u $(id -u):$(id -g) -v $PWD:/data minlag/mermaid-cli"
else
  echo "Neither npx nor docker available to run mermaid-cli." >&2
  exit 127
fi

ok=0; fail=0; total=0
out_dir="${render_dir:-$tmp_dir}"
mkdir -p "$out_dir"

echo "Mermaid validate: runner=${MMDC%% *}; format=$format; out=${render_dir:-(temp)}"

for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  ((total++))
  base="$(basename "$f")"
  out="$out_dir/${base%.*}.$format"
  set +e
  if [[ "$MMDC" == docker* ]]; then
    $MMDC -i "/data/${f#./}" -o "/data/${out#./}" -e "$format" >/dev/null 2>&1
  else
    $MMDC -i "$f" -o "$out" -e "$format" >/dev/null 2>&1
  fi
  status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    echo "OK  - $f"
    ((ok++))
  else
    echo "FAIL- $f" >&2
    ((fail++))
  fi
done

echo "Summary: total=$total ok=$ok fail=$fail elapsed=${SECONDS}s"
exit $(( fail>0 ? 1 : 0 ))
