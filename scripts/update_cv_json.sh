#!/usr/bin/env bash
#
# Regenerate _data/cv.json from the repository's own content.
#
# _data/cv.json is a DERIVED artifact — never hand-edit it. Edit _pages/cv.md,
# _config.yml, or the collections, then run this script. CI also runs the
# generator on every deploy (.github/workflows/pages-deploy.yml), so the JSON CV
# served at /cv-json/ cannot drift from the Markdown CV at /cv/.
#
# Usage:
#   scripts/update_cv_json.sh            # regenerate
#   scripts/update_cv_json.sh --check    # exit 1 if the committed file is stale
#   scripts/update_cv_json.sh --serve    # regenerate, then serve the site
#
# Nix users: `nix run .#cv-json` does the same thing without a Python in PATH.

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CV_MARKDOWN="$BASE_DIR/_pages/cv.md"
CV_JSON="$BASE_DIR/_data/cv.json"
CONFIG_FILE="$BASE_DIR/_config.yml"
PYTHON_SCRIPT="$BASE_DIR/scripts/cv_markdown_to_json.py"

for f in "$PYTHON_SCRIPT" "$CV_MARKDOWN" "$CONFIG_FILE"; do
  [ -f "$f" ] || { echo "Error: missing $f" >&2; exit 1; }
done

mode="${1:-}"

if [ "$mode" = "--check" ]; then
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  python3 "$PYTHON_SCRIPT" --input "$CV_MARKDOWN" --output "$tmp" --config "$CONFIG_FILE" >/dev/null
  if diff -u "$CV_JSON" "$tmp"; then
    echo "_data/cv.json is up to date."
  else
    echo "" >&2
    echo "_data/cv.json is STALE. Run: scripts/update_cv_json.sh" >&2
    exit 1
  fi
  exit 0
fi

python3 "$PYTHON_SCRIPT" --input "$CV_MARKDOWN" --output "$CV_JSON" --config "$CONFIG_FILE"

if [ "$mode" = "--serve" ]; then
  echo "Building Jekyll site..."
  cd "$BASE_DIR" && bundle exec jekyll serve
fi
