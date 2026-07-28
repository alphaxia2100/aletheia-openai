# Portable installation, transfer, and security boundary

This document describes the unpromoted portable-runtime candidate on
`codex/exp-portable-sandbox-v06`. `prod` remains the stable GitHub default. Do
not describe this candidate as an OS sandbox or a security-certified release:
it supplies application-level guardrails and an optional reference container,
while real isolation remains a host and harness responsibility.

## Runtime closure

The default installer creates a self-contained Codex runtime. It copies the
Git-tracked runtime closure only:

- `aletheia-research` — the public entry point and orchestrator;
- `channel-retrieval` — channel clients, configuration policy, and readers;
- `provenance-audit` — the runtime provenance dependency;
- `VERSION`, `.env.example`, optional-dependency requirements, and the offline
  preflight utility.

The public Codex skill is a symlink into its adjacent copied runtime at
`${CODEX_HOME:-$HOME/.codex}/skills/.aletheia-runtime/`. After a successful
copy install, that runtime does not depend on the source checkout, Git, or a
repository-local `.env`.

Normal copying derives the closure from the committed `HEAD` tree, not from
working-tree bytes. That prevents a local run corpus, browser state, accidental
helper, or half-finished code change from silently becoming part of a release.
The installer therefore needs a Git checkout; Git is not needed to run the
already copied runtime. `--allow-dirty` is an explicit developer-only escape
hatch for forward-testing uncommitted files and must not be used for transfer.

The portable closure deliberately excludes legacy and experimental siblings,
including `survey-scope`, along with the repository MCP configuration. They
are not dependencies of the public entry point and should not be treated as
part of this release without their own portability/security review. Copying
tracked files is a containment measure, not an authenticity guarantee. The
installed runtime carries a SHA-256 manifest which detects missing, changed,
unexpected, or symlinked runtime files offline; it is self-integrity evidence,
not a signature. This candidate still does not ship a signed tag, SBOM, or
independent supply-chain attestation.

## Install on a new macOS or Linux machine

The core requires Bash and Python 3.9+. Obtain the intended branch from GitHub,
then preflight it before installing:

```bash
git clone https://github.com/alphaxia2100/aletheia-openai.git
cd aletheia-openai
git switch codex/exp-portable-sandbox-v06
python3 scripts/preflight.py
bash scripts/install.sh
```

The default installs only the public Codex entry point at
`${CODEX_HOME:-$HOME/.codex}/skills/aletheia-research` and its private sibling
runtime. Start a fresh Codex session afterward so it discovers the skill.

Use `--link` only for development from a checkout that will remain in place.
`--cursor`, `--claude`, and `--all` are explicit because they write into other
harness roots; `--all` installs the same portable runtime closure, not every
skill in this repository. Use `--dry-run` before an update. The installer sets
a private `077` umask for its copied runtime and recovery backups, then
refuses to replace an unmanaged target unless `--force` is supplied, in which
case it moves the old target into a timestamped `.aletheia-backups/` directory.

Validate the installed copy without relying on the checkout:

```bash
RUNTIME="${CODEX_HOME:-$HOME/.codex}/skills/.aletheia-runtime"
python3 "$RUNTIME/tools/preflight.py" --runtime "$RUNTIME"
```

`preflight.py` is an offline structural and Python-compilation check; for a
copied runtime it also verifies the SHA-256 closure manifest and rejects
unexpected runtime files, symlinks, and dotenv files. It does not validate a
Git signature, test third-party APIs, or prove sandboxing.

## Configuration, capabilities, and private artifacts

Keep connector keys and mutable channel choices outside both the Git checkout
and the copied runtime. The user configuration directory is
`${ALETHEIA_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/aletheia}`:

```bash
CONFIG_DIR="${ALETHEIA_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/aletheia}"
mkdir -p "$CONFIG_DIR"
cp .env.example "$CONFIG_DIR/.env"
chmod 700 "$CONFIG_DIR"
chmod 600 "$CONFIG_DIR/.env"
```

Only that explicit user-scoped `.env` is loaded; checkout, runtime, and
ancestor-directory `.env` files are ignored. Real process environment values
win, so do not hand an agent process unrelated secrets. On POSIX, the loader
refuses a `.env` that is not a regular, current-user file with no group/other
permissions.

`channels.py` writes a separate user-owned `channels.json` overlay containing
only the enabled-channel list; the bundled channel metadata remains immutable.
An unsafe, malformed, stale, or unknown-channel overlay fails closed to **no
enabled channels**, rather than restoring network access. Repair it consciously
with the CLI (for example, `channels.py reset`) after checking the file.

```bash
AL="${CODEX_HOME:-$HOME/.codex}/skills/.aletheia-runtime/skills"
python3 "$AL/channel-retrieval/scripts/channels.py" list
python3 "$AL/channel-retrieval/scripts/channels.py" enable stackexchange
python3 "$AL/channel-retrieval/scripts/channels.py" reset
```

Optional connectors, including X and YouTube, are disabled by default. An
explicit `--channels` request cannot revive a disabled connector, and direct
client CLIs enforce the same enabled-channel policy.

`doctor.py` probes enabled channels only by default. `doctor.py --all` is an
intentional diagnostic capability escalation: it actively contacts disabled
connectors too, rather than merely listing them.

Browser/session use has two separate conditions:

1. The caller must explicitly request browser use (for example, `--browser`)
   and enable any relevant optional channel.
2. The harness must grant the destination host through
   `ALETHEIA_BROWSER_CAPABILITY`, for example
   `ALETHEIA_BROWSER_CAPABILITY=reddit.com,x.com`.

A failed Jina read, a paywall, or an archive miss is never an authorization to
open a logged-in browser. The environment gate prevents accidental use, but is
not proof of consent when an agent can change its own environment; use a
host-level broker or policy for genuine authorization.

On POSIX, the runtime requests an `077` umask and creates its configuration
and cache directories with private permissions. Choose a private run root as
well, because run artifacts can contain full page text, transcripts, and
browser-derived material:

```bash
RUNS="$HOME/.local/share/aletheia-runs"
mkdir -p "$RUNS"
chmod 700 "$RUNS"
```

Pass that directory as `treestate.py init --base "$RUNS"`, or run from an
equally private working directory.

These defaults do not override filesystem ACLs, shared backup policies, or
permissions chosen for externally supplied output paths. Never commit run
artifacts merely to preserve them.

## What “sandboxed” means here

Application safeguards in this candidate include non-destructive installation,
private configuration/artifact defaults, disabled-channel enforcement,
public-URL validation and bounded reads, a scrubbed environment for external
adapter CLIs, and no automatic authenticated-browser fallback. They reduce
accidental exposure; they do not confine the Codex/Cursor/Claude host process.

For a meaningful deployment boundary, run the host or worker under a dedicated
unprivileged identity with a dedicated workspace, mount only that workspace,
avoid browser profiles and Docker sockets, and apply an outbound network policy
outside the skill. Browser profiles, credentials, and network egress require
separate approval and auditing. The standard-library research clients need
public network access when researching; this is not an offline tool.

### Optional reference container

`containers/run-sandbox.sh` is a reference wrapper for utility execution. Its
default is offline and runs as the invoking unprivileged host UID (it refuses
to run as root), with a read-only root,
capabilities dropped, `no-new-privileges`, resource limits, a `tmpfs` `/tmp`,
and one writable work mount:

```bash
bash containers/run-sandbox.sh --build
bash containers/run-sandbox.sh --work "$RUNS" -- \
  python3 /opt/aletheia/skills/aletheia-research/scripts/treestate.py \
    init "example topic" --thoroughness quick
```

`--build` intentionally requires a clean Git checkout and sends a `git archive
HEAD` context to the container engine, so untracked local artifacts never reach
the Docker daemon. A direct `docker build` does not get that guarantee; use the
wrapper for the reference path.

Online runs require an explicitly named `ALETHEIA_EGRESS_NETWORK`:

```bash
ALETHEIA_EGRESS_NETWORK=restricted-egress \
  bash containers/run-sandbox.sh --online --config "$CONFIG_DIR" --work "$RUNS" -- \
  python3 /opt/aletheia/skills/channel-retrieval/scripts/doctor.py
```

The wrapper merely refuses Docker's implicit default network; it cannot verify
that the named network is actually restricted. An operator must create and
enforce that network's proxy, DNS, and egress allowlist. Do not expose a Docker
socket, privileged mode, host network, or sensitive host mounts to an
untrusted agent. The container does not sandbox the host agent that launches
it, and the base image is not yet pinned by digest or independently attested.

## Transfer ledger and release provenance

GitHub is the transfer mechanism for source, tests, documentation, named
experiments, and release/recovery refs. It is intentionally **not** the backup
location for `.env`, browser profiles/cookies, raw transcripts, or `runs/`
corpora. Those can contain credentials, private prompts, downloaded third-party
content, or session-derived material; copy them only to an approved private,
access-controlled backup after reviewing them.

Before retiring a development machine, review the public payload, then push and
verify refs from a clean working tree:

```bash
git status --short
git diff --check
git push origin --all
git push origin --tags
git ls-remote --heads --tags origin
```

Do not use `git add -f` or a broad archive command to make private data “fit”
into the public repository. Verify the clone on another machine, rerun the
preflight and copied-runtime smoke check, and retain the original only until
that independent check succeeds.

The current organization is documented in [`BRANCHES.md`](BRANCHES.md): `prod`
is stable, `codex/exp-portable-sandbox-v06` is the unpromoted transfer
candidate, and recovery refs retain otherwise easy-to-lose work in progress.

This candidate was informed by a bounded Aletheia portability/sandbox review,
implementation inspection, and clean-copy smoke testing. That work is useful
provenance for design decisions, not an external security audit or a guarantee
that every host, connector, browser, DNS resolver, or container engine behaves
securely. Promotion should require a repeat on a fresh host plus an explicit
release-integrity decision (for example, signed tag and SBOM/CI provenance).
