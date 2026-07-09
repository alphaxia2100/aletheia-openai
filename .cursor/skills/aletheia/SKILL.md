---
name: aletheia
description: Deep, high-scrutiny research surveyor (v0.3) — gives an accurate, un-anchored picture of a field by framing competing perspectives, decomposing into a filesystem-coordinated tree, and running parallel READ-ONLY investigations that pull a WIDE VARIETY of current/diverse/real sources, read primaries in full, hunt the decisive authoritative source, judge whether support is independent or one origin echoed, attack the leading conclusion, surface gaps honestly, and tie every claim to a primary through a verification gate that runs to completion. Effort scales via `thoroughness: auto | quick | standard | deep | exhaustive`. Use to research, survey, map, fact-check, or "get an accurate picture of" a topic. Callable from any session.
---

# Aletheia 0.3 — deep, multi-perspective research surveyor

An accurate, un-anchored picture of a field. A bare LLM anchors on its priors, searches to confirm
them, cites nothing, and is stale. Aletheia beats it by **surveying widely and for real**: competing
perspectives, a **variety of distinct sources**, primaries read in full, the **decisive** source
hunted down, independence judged, the leading conclusion attacked, and **gaps stated honestly** —
every claim tied to a primary through a verification gate.

**Lineage:** 0.3 is built on **deep-aletheia 0.2**, which won a blind LLM-judge over a single-agent
design on *completeness*, *source variety*, and *groundedness to distinct primaries*. 0.3 keeps all of
that and adds four things it was missing (see **What's new** below). Everything is files; every node
is a directory; nothing depends on one context window.

## Toolkit (do this first)
Installed globally at `~/.cursor/skills/` (via `scripts/install.sh`) — call by absolute path.
```bash
AL=~/.cursor/skills ; A="$AL/aletheia/scripts"
python3 "$AL/channel-retrieval/scripts/doctor.py"     # confirm channels live (keys auto-load from repo .env)
```
Scripts: `treestate.py` (blackboard/tree/budget/thoroughness), `investigate.py` (leaf engine:
route→retrieve→rank→read-in-full, multi-round), `router.py` (channel routing), `rank.py` (authority
ranking), `synthesize.py` (bottom-up merge + independence + `--gate`), `verify.py` (citation gate).
Do NOT fall back to plain web search — the point is the channels (Brave/OpenAlex/arXiv/Reddit/HN/
Stack Exchange/GitHub/YouTube + real-browser reads) that reach current, diverse, authenticated sources.

## Thoroughness (scales effort to the question — pass it or judge it in SCOPE)
| tier | budget | max_depth | max_children | ≈ leaves | when |
|---|---|---|---|---|---|
| `quick` | 8 | 1 | 3 | ~3 | narrow, settled |
| `standard` | 16 | 2 | 3 | ~4–6 | the default workhorse |
| `deep` | 32 | 3 | 4 | ~10+ | broad / contested (fan-out) |
| `exhaustive` | 64 | 3 | 5 | ~15+ | maximal (fan-out) |
`auto` = judge breadth×contestedness in SCOPE, then init with the chosen tier.

## What's new in 0.3 (the good parts of deep-aletheia 0.2, plus these)
1. **Hunt the DECISIVE source.** Don't just pool many primaries — actively find the *authoritative /
   settling* source (a regulator/agency opinion, a landmark systematic review/meta-analysis, an
   official standard, the largest RCT). This is the one thing the single-agent design beat 0.2 on.
2. **Chase the primary, never cite the secondary.** If a load-bearing claim rests on a blog/summary
   (Examine/Healthline/press), find and read the primary before citing; if you can't, mark it Unverified.
3. **Wide source variety by design.** `doctor.py` first and **health-check the channels** (route
   around dead ones); cover the 3 classes AND multiple index-groups per framing (academic ·
   independent web · community · code/QA · video where relevant) so distinct origins surface — and
   **filter for relevance BEFORE spending the read budget** (rank first; don't read off-topic hits —
   over-retrieval injects noise). Note any channels that returned nothing as a gap.
4. **Verification runs to completion** — every load-bearing claim gets a final supported/contradicted/
   unsupported verdict and a real `citation_accuracy` (never left null). Callable via `thoroughness`.

## The loop (do every step)

### 1. Frame the portfolio + init (anti-anchoring — load-bearing)
```bash
RUN=$(python3 "$A/treestate.py" init "<topic>" --slug "<slug>" --thoroughness auto)   # or quick|standard|deep|exhaustive
```
For `auto`, pick the tier by breadth×contestedness, then re-init with it. Write **4–6 competing
framings** into `$RUN/portfolio.md` BEFORE searching: mainstream/consensus (to test, not serve),
≥1 heterodox, ≥1 practitioner/field-report, ≥1 orthogonal reframe, and name one **leading** framing
for the adversary. Commit to none.

### 2. Decompose into a budget-balanced tree
Split the root into the framings; a node **splits** if broad and budget allows, else it's a **leaf**.
```bash
python3 "$A/treestate.py" cansplit --node "$RUN/tree/root"
python3 "$A/treestate.py" split --node "$RUN/tree/root" \
  --children '[["consensus","<q>"],["heterodox","<q>"],["practitioner","<q>"],["adversary","strongest disconfirming evidence for the leading framing"]]'
```
Give contested/broad framings more scope; always include an **adversary** child. Log decisions
(`treestate.py decide --node <n> --actor orchestrator --why "…" "<decision>"`).

### 3. Investigate leaves — multi-round, WIDE, primary-first
Process **level by level**. For each pending leaf (`treestate.py frontier --run "$RUN" --state pending --depth <d>`),
run the leaf engine, which reads primaries in full and **accumulates across rounds**:
```bash
python3 "$A/investigate.py" --node "<NODE_DIR>"     # round 1; repeat with --query "<gap>" to deepen
```
At `deep`/`exhaustive`, spawn one **READ-ONLY worker subagent per leaf, in parallel** (Task tool),
each given the topic + its framing + why it exists. Each worker: reads `evidence.md`+`notes/`;
**pulls a variety of distinct sources**; **hunts the decisive source** for its sub-question; **chases
primaries** (no secondhand citations); writes `<NODE_DIR>/findings.md` (3–8 claims, each with the
**primary URL** + one-line quote + class; corroborated vs single-origin; disconfirming evidence; and
**what's missing** — the gaps). Workers are independent; they write artifacts, not big blobs back.

### 4. Synthesize bottom-up, with enforced back-and-forth
Deepest nodes first. `python3 "$A/synthesize.py" --node "<NODE_DIR>" --gate` — if it exits 3, a child
is thin/unanswered: **ask it** (`treestate.py ask …`) and let it **answer from its already-gathered
sources** (`treestate.py answer …`) before you author. Then write `<NODE_DIR>/findings.md` yourself
(single-threaded), honoring the independence report (high echo ⇒ don't treat convergence as truth).

### 5. Judge independence + attack the leading conclusion
`synthesize.py` reports echo/voice/domain concentration ("40 sources or 1 origin echoed 40×?").
Take the **adversary** branch + un-laundered channels and try to break the leading framing. Survive → keep; else downgrade. Log it.

### 6. Verify every load-bearing claim (must complete)
Extract the draft's claims → `$RUN/claims.jsonl` (`{"claim":"…","url":"…"}`):
```bash
python3 "$A/verify.py" --claims "$RUN/claims.jsonl" --node "$RUN/tree/root" --out "$RUN/verify.jsonl"
```
Layer 1 (lexical) certifies **relevance only**, never support. Then **Fact-Check EVERY `relevant`
claim** (read the cited primary in a small context; watch polarity + magnitude) and rewrite each
verdict to `supported`/`contradicted`/`unsupported`. Only `supported` survives in Agreement;
`contradicted` → cut/flip; `unsupported` → downgrade to Unverified. Report a real `citation_accuracy`.

### 7. Answer, grounded — with gaps
Write `$RUN/brief.md`: **Bottom line** · **Agreement** (independent sources converge) ·
**Disagreement** (name both sides; do not smooth over) · **Unverified / single-origin** ·
**Gaps** (what couldn't be reached: paywalled primaries, missing large RCTs, empty channels — state
them). Every claim links to the **primary you read**; dates on time-sensitive claims; reddit/youtube/x
are **color**, never proof. Accrete into the `consilient-atlas` so surveys compound.

## Observability & resume
`treestate.py tree --run "$RUN"` shows the whole tree (state/budget/findings). Every node has
`decisions.jsonl`, `questions.jsonl`/`answers.jsonl`, `sources.jsonl`, `notes/`, `evidence.md`,
`findings.md`. Fully resumable — re-run `frontier`.

## Rules
Channel **classes**: `evidence` citable · `lead_gen` (search/HN/Reddit) → **find & cite the primary** ·
`color` (X/YouTube) → never cite as fact. Variety, decisive-source hunt, chase-the-primary,
independence-by-judgment, adversary, read-in-full, honest gaps, and completed verification are
non-optional from `standard` up.
