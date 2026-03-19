#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <project-path>"
  exit 1
fi

TARGET="$1"
TEMPLATE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$TARGET"
cp -r "$TEMPLATE_DIR"/md "$TARGET"/
cp -r "$TEMPLATE_DIR"/config "$TARGET"/
cp "$TEMPLATE_DIR"/README.md "$TARGET"/

echo "QMD project initialized at: $TARGET"
echo "Next: cd $TARGET && follow README.md"
