#!/usr/bin/env bash
# Run a portable Aletheia utility in the reference least-privilege container.
# This is an execution wrapper, not a substitute for an egress proxy or host-agent sandbox.
set -euo pipefail
# Newly created host work directories hold raw source text and traces; keep them private unless
# the caller deliberately adjusts the resulting directory after the run.
umask 077

usage() {
  cat <<'EOF'
Usage: bash containers/run-sandbox.sh [--build] [--online] [--work DIR] [--config DIR] [--] [COMMAND ...]

Defaults to an offline preflight with a read-only root filesystem, non-root user, all Linux
capabilities dropped, no-new-privileges, bounded processes/memory/CPU, a tmpfs /tmp, and one
writable work mount. `--online` requires ALETHEIA_EGRESS_NETWORK to name an externally restricted
container network; it deliberately refuses Docker's unrestricted default network.

Examples:
  bash containers/run-sandbox.sh --build
  bash containers/run-sandbox.sh --work "$PWD/runs" -- \
    python3 /opt/aletheia/skills/aletheia-research/scripts/treestate.py init "topic" --thoroughness quick
  ALETHEIA_EGRESS_NETWORK=restricted-egress bash containers/run-sandbox.sh --online --config "$HOME/.config/aletheia" -- \
    python3 /opt/aletheia/skills/channel-retrieval/scripts/doctor.py
EOF
}

ENGINE="${ALETHEIA_CONTAINER_ENGINE:-docker}"
IMAGE="${ALETHEIA_SANDBOX_IMAGE:-aletheia-runtime:local}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK=""
CONFIG=""
ONLINE=0
BUILD=0
COMMAND=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --build) BUILD=1 ;;
    --online) ONLINE=1 ;;
    --work) shift; [ "$#" -gt 0 ] || { usage >&2; exit 2; }; WORK="$1" ;;
    --config) shift; [ "$#" -gt 0 ] || { usage >&2; exit 2; }; CONFIG="$1" ;;
    --help|-h) usage; exit 0 ;;
    --) shift; COMMAND=("$@"); break ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

command -v "$ENGINE" >/dev/null 2>&1 || { echo "container engine not found: $ENGINE" >&2; exit 1; }
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
[ "$HOST_UID" -ne 0 ] || {
  echo "refusing to run the sandbox wrapper as root; use an unprivileged host account" >&2
  exit 2
}
[ -n "$WORK" ] || WORK="$PWD/runs"
mkdir -p "$WORK"
WORK="$(cd "$WORK" && pwd -P)"

if [ "$ONLINE" -eq 1 ]; then
  : "${ALETHEIA_EGRESS_NETWORK:?--online requires an externally restricted ALETHEIA_EGRESS_NETWORK}"
  NETWORK=(--network "$ALETHEIA_EGRESS_NETWORK")
else
  NETWORK=(--network none)
fi

if [ -n "$CONFIG" ]; then
  [ -d "$CONFIG" ] || { echo "config directory does not exist: $CONFIG" >&2; exit 2; }
  CONFIG="$(cd "$CONFIG" && pwd -P)"
  # Mount secrets at a neutral path.  The process runs as the invoking host user so a 0700/0600
  # config stays readable without making it world-readable just for the image's fixed UID.
  CONFIG_MOUNT=(--mount "type=bind,src=$CONFIG,dst=/config,readonly")
  CONFIG_ENV=(--env ALETHEIA_CONFIG_DIR=/config)
else
  CONFIG_MOUNT=()
  CONFIG_ENV=()
fi

if [ "$BUILD" -eq 1 ]; then
  # A normal Docker build context can include untracked local material even when the Dockerfile
  # only copies a few folders. Build from the committed Git tree instead, so a nearby .env, run
  # transcript, or browser artifact never reaches the daemon. Refuse a dirty tree rather than
  # silently building an image whose source cannot be recovered on the next machine.
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "--build requires a Git checkout" >&2
    exit 2
  }
  if [ -n "$(git -C "$ROOT" status --porcelain --untracked-files=normal)" ]; then
    echo "refusing --build from a dirty checkout; commit or stash the candidate first" >&2
    exit 2
  fi
  git -C "$ROOT" archive --format=tar HEAD | \
    "$ENGINE" build --pull --tag "$IMAGE" --file containers/Dockerfile -
fi

if [ "${#COMMAND[@]}" -eq 0 ]; then
  COMMAND=(python3 /opt/aletheia/tools/preflight.py --runtime /opt/aletheia)
fi

RUN_ARGS=(
  --rm --init
  --user "$HOST_UID:$HOST_GID"
  --read-only
  --cap-drop=ALL
  --security-opt=no-new-privileges:true
  --pids-limit=256
  --memory=1g
  --cpus=2
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=128m
  --env HOME=/tmp/aletheia-home
  --env XDG_CACHE_HOME=/tmp/aletheia-cache
  --env XDG_CONFIG_HOME=/tmp/aletheia-config
  "${NETWORK[@]}"
)
if [ -n "$CONFIG" ]; then
  # Bash 3.2 treats an empty array as unset under `set -u`, so expand these only when populated.
  RUN_ARGS+=("${CONFIG_MOUNT[@]}" "${CONFIG_ENV[@]}")
fi
RUN_ARGS+=(--mount "type=bind,src=$WORK,dst=/work")

exec "$ENGINE" run "${RUN_ARGS[@]}" "$IMAGE" "${COMMAND[@]}"
