#!/usr/bin/env bash
# Mirror Aletheia's skills into Claude Code's skill directory.
# Skills are harness-agnostic SKILL.md bundles; Cursor reads .cursor/skills/,
# Claude Code reads ~/.claude/skills/ (or a repo-local .claude/skills/).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/.cursor/skills"
DEST="${1:-$HOME/.claude/skills}"

mkdir -p "$DEST"
for skill in "$SRC"/*/; do
  name="$(basename "$skill")"
  target="$DEST/$name"
  rm -rf "$target"
  ln -s "$skill" "$target"
  echo "linked $name -> $target"
done

echo
echo "Done. $(ls -1 "$SRC" | wc -l | tr -d ' ') skills linked into $DEST"
echo "MCP servers: copy blocks from .cursor/mcp.json / .cursor/mcp.reference.md into your Claude Code mcp config."
