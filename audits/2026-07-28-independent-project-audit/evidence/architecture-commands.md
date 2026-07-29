# Architecture-audit command and evidence log

Date: 2026-07-28. Commands were run from `/Users/daemon1/Developer/Personal/Aletheia-OpenAI` against audit HEAD `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`. The audited working tree had only audit artifacts untracked; no production file was modified by this reviewer.

| Command / inspection | Result used in the audit |
|---|---|
| `git status --short; git branch --show-current; git log --oneline --decorate -20` | Audit branch is `codex/independent-audit-2026-07-28`, based on `bd5e1a5`, which is also `codex/exp-portable-sandbox-v06`; `prod` is `7cc657b` and the immutable runtime tag dereferences to `addfaf6`. |
| `git rev-parse HEAD prod aletheia-prod-v0.5.0-openai.1^{}; git merge-base prod HEAD` | Confirmed candidate/stable separation and baseline identities stated in the note. |
| `git ls-tree -r --name-only HEAD`; `find .cursor/skills -type f`; `find .cursor/skills -type f -name '*.py'` | Current full skill suite has 61 files and 45 Python files. Portable runtime source is three skills: `aletheia-research`, `channel-retrieval`, and `provenance-audit`. |
| `git for-each-ref --format='%(refname:short)' refs/heads`; same for `refs/remotes/origin` | 31 local heads and 30 remote heads observed, including many named experiments and archive branches. |
| `python3 scripts/preflight.py` | `Aletheia preflight: PASS`; Python 3.9.6; repository skill root found; manifest not applicable to checkout. |
| `python3 -m unittest discover -s tests -v` | **186 tests passed** in **12.764s**. This included portability, browser/capability, retrieval/routing, verification, state/resume, scoring, and security regression cases. Test run only created temporary test artifacts. |
| `env ALETHEIA_CONFIG_DIR=/tmp/aletheia-audit-20260728-config ALETHEIA_CACHE_DIR=/tmp/aletheia-audit-20260728-cache python3 .cursor/skills/channel-retrieval/scripts/doctor.py` | Correct contemporaneous health snapshot: **11/13 core probes live**. Brave: `warn`, no `BRAVE_API_KEY`, so the independent Brave web index is unavailable. Reddit: `down`, HTTP 502. Other listed core probes returned OK. This is one functional probe per channel, not a load test. |
| `python3 .cursor/skills/aletheia-research/scripts/treestate.py init ... --thoroughness standard --base /tmp/...`; same without a tier | The emitted `run.json` confirmed `standard` = budget 16/depth 2/nodes 16, whereas omitted tier = `unlimited`, budget 1,000,000/depth 99/nodes 512. Scratch runs were created only under `/tmp/aletheia-audit-20260728-runs`. |
| `bash scripts/install.sh --dry-run --codex --copy` | Installer plans a copied private runtime under Codex skills, backs up a managed public entry-point if present, and symlinks the public skill to the private runtime. No filesystem write occurred because `--dry-run` was supplied. |
| `git diff --check prod...HEAD; git fsck --no-reflogs --no-dangling` | No whitespace error or Git-object integrity failure reported. |
| `find . -maxdepth 3 -type f \( -path './.github/*' -o -name '.gitlab-ci.yml' -o -name 'tox.ini' -o -name 'pytest.ini' -o -name 'setup.cfg' \)` | No repository CI/workflow or conventional Python test configuration file found in the audited tree. This is an observation about checked-in automation, not a claim that no external CI exists. |
| Source review: `nl -ba` / `rg -n` over `README.md`, `docs/BRANCHES.md`, `docs/PORTABILITY.md`, all public-skill scripts, eval scripts, tests, and research records | Produced the precise source references in `notes/architecture-audit.md`. Particularly important direct code inspections were `investigate.py:590-609`, `treestate.py:190-258`, `verify.py:8-23,105-159`, `report.py:186-287,303-504`, and `router.py:38-195`. |
| `git show fa4b26d:docs/experiments/read-identity-gate-v06/results.md` and `git diff --stat HEAD..fa4b26d` | Confirmed that semantic read identity is a distinct experimental branch, with its own test/result record, not functionality of the audited portable candidate or `prod`. |

## Important interpretation controls

- The channel health check used the public skill’s documented `$AL/channel-retrieval/scripts/doctor.py` runtime path.
- A unit-test pass establishes deterministic regression behavior, not agent judgment quality, live service reliability, factual accuracy, or comparative research performance.
- Historical self-audit and experiment records are cited as evidence of the project’s observed failures and stated limitations. They have not been independently repeated in full by this architecture reviewer.
