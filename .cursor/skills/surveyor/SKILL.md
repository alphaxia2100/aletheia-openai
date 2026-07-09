---
name: surveyor
description: DEPRECATED (2026-07-08) — superseded by the `aletheia-research` (0.3) skill; kept runnable only as an eval baseline. Prefer `aletheia-research`. Research surveyor that gives an accurate, un-anchored picture of a field or task — pulling current/diverse/real sources a bare LLM can't reach, reading them in full, judging whether support is independent or one origin echoed, attacking its own leading conclusion, and tying every claim to a primary through a verification gate. SINGLE-AGENT by default; fans out to parallel breadth-workers only at high thoroughness. Thoroughness scales to the question: pass `thoroughness: auto` (default, scales to breadth×contestedness) or set `quick | standard | deep | exhaustive`. Use when asked to research, survey, map, fact-check, or "get an accurate picture of" a topic. Callable from any session.
---

# Surveyor

> **DEPRECATED (2026-07-08).** Superseded by **`aletheia-research` 0.3**. A blind LLM-judge of fresh runs found
> the tree-based multi-perspective design produced more complete, better-grounded briefs; surveyor is
> kept only as an **eval baseline** (`scripts/eval/eval_compare.py`). For new work, use `aletheia-research`.

An accurate, un-anchored picture of a field. A bare LLM anchors on its priors, searches to confirm
them, cites nothing, and is stale. Surveyor beats it with **discipline, not machinery**, and scales
effort to the question. (Design + evidence: `docs/surveyor-design.md`; it replaces the retired
`aletheia-research`/`deep-aletheia` skills.)

**Principles (from the self-audit of the retired skills):**
- **Single-agent by default.** The best deep-research systems are single-loop; multi-agent only pays
  off for *independent breadth*. So fan-out happens ONLY at `deep`/`exhaustive`, one read-only worker
  per angle — never a recursive tree.
- **Scale effort to complexity**, via the thoroughness dial — not a uniform per-item budget.
- **Read in full, cite primaries, judge independence, attack your own conclusion, verify every claim.**
- The human owns the final call; surveyor does the breadth and the stress-testing.

## Toolkit (do this first)
Scripts are installed globally at `~/.cursor/skills/` (via the repo's `scripts/install.sh`) — call by
absolute path; they are NOT in the current workspace.
```bash
AL=~/.cursor/skills ; SV="$AL/surveyor/scripts/surveyor.py"
python3 "$AL/channel-retrieval/scripts/doctor.py"     # confirm channels live (keys auto-load from repo .env)
```
Do NOT fall back to plain web search — the point is the channels (Brave/OpenAlex/arXiv/Reddit/HN/
YouTube + real-browser reads) that reach current, diverse, authenticated sources.

## Thoroughness tiers (effort scales to the question)
| tier | angles | channels | reads/round | deepen rounds | fan-out | verify | adversary |
|---|---|---|---|---|---|---|---|
| `quick` | 1–2 | 2 | 5 | 0 | no | light | no |
| `standard` | 2–3 | 3 | 6 | 1–2 | no | full | yes |
| `deep` | 3–4 | 3–4 | 6/angle | 2 | **yes** (1 worker/angle) | full + subagent | yes |
| `exhaustive` | 4–6 | 4+ | 8/angle | 3 | yes | multi-vote | yes |
| `auto` (default) | — | — | — | — | — | — | — |

**`auto`:** in SCOPE (step 1) judge the question's **breadth** (how many distinct sub-areas) × **contestedness**
(is the consensus disputed?), pick a tier, and re-run `plan` with it. Narrow+settled → `quick`;
broad+contested → `deep`/`exhaustive`. This is the adaptive control; the human can always override.

## The loop
`plan` prints the tier, effort params, and channels — then just follow them.

### 1. SCOPE & plan
```bash
RUN=$(python3 "$SV" plan --topic "<topic>" --thoroughness auto | python3 -c "import sys,json;print(json.load(sys.stdin)['run'])")
```
Write `$RUN/angles.md`: the tier's number of **competing angles** — the mainstream view (to test, not
serve), ≥1 heterodox, ≥1 practitioner/field-report, and **one deliberately disconfirming** angle.
Commit to none; note which is "leading" (step 5 attacks it). (Don't force angles a topic doesn't have.)

### 2. GATHER (retrieve → rank → read in full)
Run one round per angle's queries (queries are `||`-separated):
```bash
python3 "$SV" gather --run "$RUN" --queries "<angle-1 query>||<angle-2 query>"
```
It covers the 3 classes, ranks by authority (primaries over content farms), reads the top-K in full
into `notes/`, and dedups at the work level. Read `$RUN/evidence.md` + the `notes/`.

### 3. DEEPEN (iterate into gaps; stop on convergence)
Reflect on what the reading exposed, then:
```bash
NEXT=$(python3 "$SV" deepen --run "$RUN" --learning "<source-backed finding>" --followup "<the top gap>" --followup "<a disconfirming angle>")
# exit 3 = STOP (converged or round cap). Else: python3 "$SV" gather --run "$RUN" --queries "$NEXT"  (repeat)
```

### 4. JUDGE INDEPENDENCE
```bash
python3 "$SV" independence --run "$RUN"    # echo/voice/domain concentration
```
If echo is high, convergence may be one origin echoed — trace claims to their primary; count echoes as one.

### 5. ATTACK the leading conclusion (adversary)
Take the leading angle and hunt the strongest disconfirming evidence (un-laundered channels). If it
survives, keep it; else revise/downgrade. Do this before you believe it.

### 6. VERIFY every load-bearing claim (must complete)
Extract the draft's claims → `$RUN/claims.jsonl` (`{"claim":"…","url":"…"}`), then:
```bash
python3 "$SV" verify --run "$RUN" --claims "$RUN/claims.jsonl"     # deterministic: relevance only, NEVER "supported"
```
Then **Fact-Check every `relevant` claim yourself** (read the cited source in a small context; watch
polarity/magnitude) and rewrite each `verify.jsonl` verdict to `supported` / `contradicted` /
`unsupported`. Only `supported` claims survive in Agreement. `python3 "$SV" score --run "$RUN"`
reports `citation_accuracy` — it must be a real number, not null.

### 7. ANSWER, grounded
Write `$RUN/brief.md`: **Agreement** (independent sources converge) · **Disagreement** (name both
sides) · **Unverified** (single-origin/unsupported). Every claim links to the primary you read; dates
on time-sensitive claims; reddit/youtube/x are **color**, never proof.

## deep / exhaustive: breadth fan-out (the only multi-agent step)
When `plan` says `fanout: true`, run steps 2–3 as **parallel READ-ONLY worker subagents, one per
angle** (Task tool). Give each the topic + its angle + `--angle <name>` so it writes to
`$RUN/angles/<name>/`; each returns a 5-line summary + its findings. Then YOU (single-threaded) do
steps 4–7 over the merged run. Workers are independent breadth — no worker depends on another.

## Rules
Channel **classes**: `evidence` citable · `lead_gen` (search/HN/Reddit) → find & cite the primary ·
`color` (X/YouTube) → never cite as fact. Independence-by-judgment, adversary, and read-in-full are
non-optional from `standard` up. Save the brief to the `consilient-atlas` so surveys compound.
