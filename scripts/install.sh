#!/usr/bin/env bash
# Make Aletheia's skills usable from ANY chat (not just the Aletheia repo).
#
# Cursor loads "personal" skills from ~/.cursor/skills/ across every project;
# Claude Code loads from ~/.claude/skills/; Codex loads from $CODEX_HOME/skills
# (default ~/.codex/skills). Cursor/Claude receive the suite; Codex receives the validated
# `aletheia-research` entry point. Symlinks keep this repo as the single source of truth.
#
# Scripts self-locate the repo via realpath, so your keys (.env), channels.json,
# and the atlas keep working even when a skill is reached through the symlink.
#
# Usage:  bash scripts/install.sh            # link into ~/.cursor + ~/.claude + ~/.codex
#         bash scripts/install.sh --copy     # copy Cursor/Claude skills; Codex stays symlinked
if [ -z "${BASH_VERSION:-}" ]; then
  echo "install.sh requires Bash; run: bash scripts/install.sh [--copy]" >&2
  exit 2
fi
set -euo pipefail

if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--copy" ]; }; then
  echo "usage: bash scripts/install.sh [--copy]" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/.cursor/skills"
MODE="${1:-symlink}"

CODEX_SKILLS="${CODEX_HOME:-$HOME/.codex}/skills"

for DEST in "$HOME/.cursor/skills" "$HOME/.claude/skills"; do
  mkdir -p "$DEST"
  n=0
  for skill in "$SRC"/*/; do
    name="$(basename "$skill")"
    target="$DEST/$name"
    rm -rf "$target"
    if [ "$MODE" = "--copy" ]; then
      cp -R "$skill" "$target"
      if [ "$name" = "channel-retrieval" ]; then
        printf '%s\n' "$REPO_ROOT" > "$target/.aletheia-root"
      fi
    else
      ln -s "$skill" "$target"
    fi
    n=$((n + 1))
  done
  echo "$([ "$MODE" = "--copy" ] && echo copied || echo linked) $n skills -> $DEST"
done

# Codex gets the validated public entry point only. Supporting skills contain Cursor-specific
# frontmatter and are runtime siblings, not separate Codex invocation surfaces. Because the target
# is a symlink, Aletheia's realpath-based imports still resolve every sibling from this repository.
mkdir -p "$CODEX_SKILLS"
target="$CODEX_SKILLS/aletheia-research"
rm -rf "$target"
# Keep Codex symlinked even in --copy mode: the flagship imports sibling runtime skills by realpath,
# while linking only the validated public entry point avoids exposing Cursor-only frontmatter.
ln -s "$SRC/aletheia-research" "$target"
echo "linked 1 Codex skill -> $CODEX_SKILLS"

echo
echo "Done. Aletheia is now available in Cursor, Claude Code, and Codex."
echo "  - Invoke it by name: \"use the aletheia-research skill to survey <topic>\"."
echo "  - Keys load automatically from: $REPO_ROOT/.env"
echo "  - Codex discovers skills from: $CODEX_SKILLS (start a new session after installing)"
  echo "  - Utilities (global, by absolute path):"
  echo "      python3 ~/.cursor/skills/channel-retrieval/scripts/doctor.py     # what's live"
  echo "      python3 ~/.cursor/skills/channel-retrieval/scripts/channels.py list"
if [ "$MODE" = "--copy" ]; then
  echo "  - NOTE: --copy mode drifts from the repo; re-run after edits."
fi
