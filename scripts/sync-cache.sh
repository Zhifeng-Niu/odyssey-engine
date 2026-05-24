#!/usr/bin/env bash
# Sync odyssey-engine source to CC plugin cache
# Usage: bash scripts/sync-cache.sh
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="$HOME/.claude/plugins/cache/local/odyssey-engine/1.0.0"

if [[ ! -d "$CACHE" ]]; then
  echo "ERROR: Cache directory not found: $CACHE"
  echo "Run /reload-plugins in Claude Code first to populate the cache."
  exit 1
fi

echo "Syncing $SRC → $CACHE"
rsync -av --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.DS_Store' \
  "$SRC/" "$CACHE/"

echo "Done. Changes will take effect on next CC turn (no reload needed for hooks/scripts)."
echo "For skill changes, run /reload-plugins."
