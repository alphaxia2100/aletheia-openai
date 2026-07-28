#!/usr/bin/env bash
# Install Aletheia without mutating unrelated skills or relying on this checkout.
#
# Default: make a self-contained, copied Codex runtime.  `--link` is a deliberate
# development convenience; it requires the source checkout to remain in place.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "install.sh requires Bash; run: bash scripts/install.sh" >&2
  exit 2
fi
set -euo pipefail
# The copied runtime, managed-target backups, and installer metadata can identify local harness
# layout. Do not let a permissive caller umask turn an otherwise verified runtime into a
# group/world-writable directory tree.
umask 077

usage() {
  cat <<'EOF'
Usage: bash scripts/install.sh [options]

Targets (Codex is the safe default):
  --codex-only, --codex   install only the public Codex entry point (default)
  --cursor                install the portable Aletheia runtime set for Cursor
  --claude                install the portable Aletheia runtime set for Claude Code
  --all                   install all three targets (explicit; never the default)

Mode and safety:
  --copy                  make a self-contained portable copy (default)
  --link                  link to this checkout (developer mode; checkout must remain)
  --allow-dirty           developer escape hatch: copy uncommitted runtime files instead of HEAD
  --force                 back up an unmanaged existing target before replacing it
  --dry-run               show changes without writing anything
  --help                  show this help

Configuration directories can be overridden for automation with ALETHEIA_CODEX_SKILLS,
ALETHEIA_CURSOR_SKILLS, and ALETHEIA_CLAUDE_SKILLS.
EOF
}

MODE="copy"
FORCE=0
DRY_RUN=0
ALLOW_DIRTY=0
DO_CODEX=0
DO_CURSOR=0
DO_CLAUDE=0

for arg in "$@"; do
  case "$arg" in
    --codex-only|--codex) DO_CODEX=1 ;;
    --cursor) DO_CURSOR=1 ;;
    --claude) DO_CLAUDE=1 ;;
    --all) DO_CODEX=1; DO_CURSOR=1; DO_CLAUDE=1 ;;
    --copy) MODE="copy" ;;
    --link) MODE="link" ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown option: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

if [ "$DO_CODEX" -eq 0 ] && [ "$DO_CURSOR" -eq 0 ] && [ "$DO_CLAUDE" -eq 0 ]; then
  DO_CODEX=1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SRC="$REPO_ROOT/.cursor/skills"
CODEX_SKILLS="${ALETHEIA_CODEX_SKILLS:-${CODEX_HOME:-$HOME/.codex}/skills}"
CURSOR_SKILLS="${ALETHEIA_CURSOR_SKILLS:-$HOME/.cursor/skills}"
CLAUDE_SKILLS="${ALETHEIA_CLAUDE_SKILLS:-$HOME/.claude/skills}"

[ -d "$SRC/aletheia-research" ] || { echo "Aletheia skill source is missing: $SRC" >&2; exit 1; }
# These are the only skills the public flagship imports at runtime. Keeping the portable install
# deliberately small avoids shipping retired/experimental tools with older configuration semantics.
PORTABLE_SKILLS=("aletheia-research" "channel-retrieval" "provenance-audit")

say() { printf '%s\n' "$*"; }
run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY-RUN: $*"
  else
    "$@"
  fi
}

timestamp() { date -u +%Y%m%dT%H%M%SZ; }

is_managed() {
  local target="$1"
  if [ -L "$target" ]; then
    local link
    link="$(readlink "$target" 2>/dev/null || true)"
    case "$link" in
      "$SRC"/*|*/.aletheia-runtime/skills/*) return 0 ;;
    esac
  fi
  [ -f "$target/.aletheia-install.json" ]
}

backup_existing() {
  local target="$1"
  local parent base backup_dir backup
  parent="$(dirname "$target")"
  base="$(basename "$target")"
  backup_dir="$parent/.aletheia-backups"
  backup="$backup_dir/$base.$(timestamp)"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY-RUN: move existing $target to $backup"
    return
  fi
  mkdir -p "$backup_dir"
  # A timestamp collision is unlikely, but never overwrite a prior recovery copy.
  while [ -e "$backup" ] || [ -L "$backup" ]; do
    backup="$backup.$RANDOM"
  done
  mv "$target" "$backup"
  say "backed up existing $(basename "$target") -> $backup"
}

prepare_target() {
  local target="$1"
  local parent
  parent="$(dirname "$target")"
  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$parent"
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    if ! is_managed "$target" && [ "$FORCE" -ne 1 ]; then
      echo "refusing to replace unmanaged target: $target" >&2
      echo "re-run with --force to move it into $parent/.aletheia-backups/" >&2
      exit 3
    fi
    backup_existing "$target"
  fi
}

install_link() {
  local source="$1" target="$2" parent temp
  parent="$(dirname "$target")"
  prepare_target "$target"
  temp="$parent/.${target##*/}.aletheia-link.$$"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY-RUN: symlink $source -> $target"
    return
  fi
  ln -s "$source" "$temp"
  mv "$temp" "$target"
  say "linked $(basename "$target") -> $source"
}

copy_tracked_skill() {
  local source="$1" target="$2" name path rel
  name="$(basename "$source")"
  git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "portable copy installs require a Git checkout; use --link only for local development" >&2
    exit 1
  }
  mkdir -p "$target"
  if [ "$ALLOW_DIRTY" -eq 0 ]; then
    # Archive from HEAD rather than copying working-tree bytes. A portable transfer should be
    # reconstructible from the pushed ref even when a developer happens to have other edits open.
    local copied
    copied="$(git -C "$REPO_ROOT" ls-tree -r --name-only HEAD -- ".cursor/skills/$name" | wc -l | tr -d '[:space:]')"
    [ "$copied" -gt 0 ] || { echo "no committed files found for skill: $name" >&2; exit 1; }
    git -C "$REPO_ROOT" archive --format=tar HEAD -- ".cursor/skills/$name" | \
      tar -x -C "$target" --strip-components=3
    return
  fi

  # Explicit developer-only path for forward-testing an uncommitted skill. The resulting runtime
  # manifest identifies those exact bytes, but it is not reproducible from a Git ref until commit.
  local copied=0
  while IFS= read -r -d '' path; do
    rel="${path#.cursor/skills/$name/}"
    [ "$rel" = "$path" ] && continue
    mkdir -p "$(dirname "$target/$rel")"
    cp -p "$REPO_ROOT/$path" "$target/$rel"
    copied=$((copied + 1))
  done < <(git -C "$REPO_ROOT" ls-files -z -- ".cursor/skills/$name")
  [ "$copied" -gt 0 ] || { echo "no tracked files found for skill: $name" >&2; exit 1; }
}

copy_release_file() {
  local rel="$1" target="$2"
  mkdir -p "$(dirname "$target")"
  if [ "$ALLOW_DIRTY" -eq 1 ]; then
    cp -p "$REPO_ROOT/$rel" "$target"
  else
    git -C "$REPO_ROOT" show "HEAD:$rel" > "$target"
  fi
}

copy_skill() {
  local source="$1" target="$2" parent temp
  parent="$(dirname "$target")"
  prepare_target "$target"
  temp="$parent/.${target##*/}.aletheia-copy.$$"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY-RUN: copy $source -> $target"
    return
  fi
  mkdir "$temp"
  copy_tracked_skill "$source" "$temp"
  printf '{"schema_version":1,"managed_by":"aletheia","mode":"copy"}\n' \
    > "$temp/.aletheia-install.json"
  mv "$temp" "$target"
  say "copied $(basename "$target") -> $target"
}

install_suite() {
  local destination="$1" skill name target
  for name in "${PORTABLE_SKILLS[@]}"; do
    skill="$SRC/$name"
    target="$destination/$name"
    if [ "$MODE" = "link" ]; then
      install_link "$skill" "$target"
    else
      copy_skill "$skill" "$target"
    fi
  done
}

install_codex() {
  local target="$CODEX_SKILLS/aletheia-research"
  if [ "$MODE" = "link" ]; then
    install_link "$SRC/aletheia-research" "$target"
    return
  fi

  local runtime="$CODEX_SKILLS/.aletheia-runtime"
  local runtime_parent runtime_tmp
  runtime_parent="$(dirname "$runtime")"
  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$CODEX_SKILLS"
  fi
  if [ -e "$runtime" ] || [ -L "$runtime" ]; then
    if ! is_managed "$runtime" && [ "$FORCE" -ne 1 ]; then
      echo "refusing to replace unmanaged runtime: $runtime" >&2
      echo "re-run with --force to save it under $CODEX_SKILLS/.aletheia-backups/" >&2
      exit 3
    fi
    backup_existing "$runtime"
  fi
  runtime_tmp="$CODEX_SKILLS/.aletheia-runtime.tmp.$$"
  if [ "$DRY_RUN" -eq 1 ]; then
    say "DRY-RUN: create self-contained runtime at $runtime"
  else
    mkdir -p "$runtime_tmp/skills" "$runtime_tmp/tools"
    local skill
    for skill in "${PORTABLE_SKILLS[@]}"; do
      copy_tracked_skill "$SRC/$skill" "$runtime_tmp/skills/$skill"
    done
    copy_release_file "VERSION" "$runtime_tmp/VERSION"
    copy_release_file ".env.example" "$runtime_tmp/.env.example"
    copy_release_file "requirements-optional.txt" "$runtime_tmp/requirements-optional.txt"
    copy_release_file "scripts/preflight.py" "$runtime_tmp/tools/preflight.py"
    # The copied runtime has no .git directory.  Record the exact shipped files so its offline
    # preflight can detect accidental corruption after this checkout is gone.  The marker is
    # deliberately written afterwards and is excluded from the executable-file manifest.
    python3 "$runtime_tmp/tools/preflight.py" --runtime "$runtime_tmp" --write-manifest >/dev/null
    printf '{"schema_version":1,"managed_by":"aletheia","mode":"portable-copy"}\n' \
      > "$runtime_tmp/.aletheia-install.json"
    mv "$runtime_tmp" "$runtime"
    say "created portable Aletheia runtime -> $runtime"
  fi
  install_link "$runtime/skills/aletheia-research" "$target"
}

if [ "$DO_CODEX" -eq 1 ]; then install_codex; fi
if [ "$DO_CURSOR" -eq 1 ]; then install_suite "$CURSOR_SKILLS"; fi
if [ "$DO_CLAUDE" -eq 1 ]; then install_suite "$CLAUDE_SKILLS"; fi

say
say "Aletheia installation complete."
say "  mode: $MODE"
[ "$DO_CODEX" -eq 0 ] || say "  Codex skill: $CODEX_SKILLS/aletheia-research"
[ "$DO_CURSOR" -eq 0 ] || say "  Cursor skills: $CURSOR_SKILLS"
[ "$DO_CLAUDE" -eq 0 ] || say "  Claude skills: $CLAUDE_SKILLS"
say "  Configure keys in: ${ALETHEIA_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/aletheia}/.env"
say "  Start a new harness session after installing so it discovers the skill."
