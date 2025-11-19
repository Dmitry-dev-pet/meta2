#!/usr/bin/env bash
set -euo pipefail

# Watch for creation/changes of Mermaid files and validate/render them.
# Requires: node+npm; uses npx chokidar-cli.

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

render_dir=${RENDER_DIR:-doc}
format=${FORMAT:-svg}
watch_globs=("doc/**/*.mmd" "doc/**/*.md")

while (( "$#" )); do
  case "$1" in
    --render-dir) render_dir="$2"; shift 2;;
    --format) format="$2"; shift 2;;
    --glob) watch_globs+=("$2"); shift 2;;
    --help|-h)
      echo "Usage: $(basename "$0") [--render-dir DIR] [--format svg|png] [--glob GLOB]...";
      exit 0;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found; install Node.js/npm to use the watcher" >&2
  exit 127
fi

echo "Mermaid watch: globs=${watch_globs[*]} out=$render_dir format=$format"

exec npx -y chokidar-cli \
  "${watch_globs[@]}" \
  -i "**/node_modules/**" -i "**/.git/**" -i "**/.venv/**" \
  --initial \
  -c "bash .factory/commands/mermaid-validate.sh --render-dir '$render_dir' --format '$format' {path}"
