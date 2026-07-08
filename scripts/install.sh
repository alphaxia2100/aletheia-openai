#!/usr/bin/env bash
# Make Aletheia's skills usable from ANY chat (not just the Aletheia repo).
#
# Cursor loads "personal" skills from ~/.cursor/skills/ across every project;
# Claude Code loads from ~/.claude/skills/. We symlink each skill there, so the
# single source of truth stays in this repo and edits show up everywhere.
#
# Scripts self-locate the repo via realpath, so your keys (.env), channels.json,
# and the atlas keep working even when a skill is reached through the symlink.
#
# Usage:  bash scripts/install.sh            # link into ~/.cursor + ~/.claude
#         bash scripts/install.sh --copy     # copy instead of symlink (if your
#                                            #   client doesn't follow symlinked skills)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/.cursor/skills"
MODE="${1:-symlink}"

for DEST in "$HOME/.cursor/skills" "$HOME/.claude/skills"; do
  mkdir -p "$DEST"
  n=0
  for skill in "$SRC"/*/; do
    name="$(basename "$skill")"
    target="$DEST/$name"
    rm -rf "$target"
    if [ "$MODE" = "--copy" ]; then
      cp -R "$skill" "$target"
    else
      ln -s "$skill" "$target"
    fi
    n=$((n + 1))
  done
  echo "$([ "$MODE" = "--copy" ] && echo copied || echo linked) $n skills -> $DEST"
done

echo
echo "Done. Aletheia is now available in any Cursor / Claude Code chat."
echo "  - Invoke it by name: \"use the aletheia skill to survey <topic>\"."
echo "  - Keys load automatically from: $REPO_ROOT/.env"
  echo "  - Utilities (global, by absolute path):"
  echo "      python3 ~/.cursor/skills/channel-retrieval/scripts/doctor.py     # what's live"
  echo "      python3 ~/.cursor/skills/channel-retrieval/scripts/channels.py list"
if [ "$MODE" = "--copy" ]; then
  echo "  - NOTE: --copy mode drifts from the repo; re-run after edits."
fi
