#!/usr/bin/env bash
# Compatibility wrapper. Prefer `bash scripts/install.sh --claude`.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ "$#" -gt 1 ]; then
  echo "usage: bash scripts/install_claude.sh [destination]" >&2
  exit 2
fi
if [ "$#" -eq 1 ]; then
  ALETHEIA_CLAUDE_SKILLS="$1" exec bash "$SCRIPT_DIR/install.sh" --claude
fi
exec bash "$SCRIPT_DIR/install.sh" --claude
