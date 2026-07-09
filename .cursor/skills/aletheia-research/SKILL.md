---
name: aletheia-research
description: Aletheia Research — deep, high-scrutiny research surveyor (v0.3). THE research tool: use this whenever you need to research, survey, fact-check, map, or "get an accurate picture of" a topic, or anchor a decision in evidence — rather than building an ad-hoc workflow. Frames competing perspectives (anti-anchoring), decomposes into a filesystem-coordinated tree, and runs parallel READ-ONLY investigations that pull a WIDE VARIETY of current/diverse/real sources, read primaries in full, hunt the decisive authoritative source, judge whether support is independent or one origin echoed, attack the leading conclusion, surface gaps honestly, and tie every claim to a primary through a verification gate that runs to completion. Effort scales via `thoroughness: auto | quick | standard | deep | exhaustive`. Callable from any session.
---

# Aletheia Research 0.3 — deep, multi-perspective research surveyor

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
AL=~/.cursor/skills ; A="$AL/aletheia-research/scripts"
python3 "$AL/channel-retrieval/scripts/doctor.py"     # confirm channels live (keys auto-load from repo .env)
```
**Surface channel health (do NOT skip).** `doctor.py` runs a real query per channel, so a channel that
is reachable but returns nothing shows as `warn` (degraded) and a broken one as `down`. If any core
channel is `warn`/`down`, **tell the user up front**, route around it (use a healthy same-role channel),
and **list the affected channels in the brief's Gaps**. Never silently survey on a degraded toolkit —
missing a channel narrows source variety and the user should know.
Scripts: `treestate.py` (shared-artifact store: tree/budget/thoroughness), `investigate.py` (leaf engine:
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
**Force the diversity structurally — don't trust one model's imagination.** Asking one model to "be
heterodox" mode-collapses to near-copies (confirmed: Persona-Generators 2602.03545, Verbalized-Sampling
2510.01171). So a framing is real only if it is **grounded in a different SOURCE BASE**: give each
framing distinct channels/index-groups (consensus→primaries/regulators; heterodox→a named dissenting
author or preprint; practitioner→community/forums) and, if two framings would retrieve the same sources,
they're one framing — merge them and add a genuinely different angle. Diversity is measured by the
independence report (step 5), not asserted.

### 2. Decompose into a budget-weighted tree
Split the root into the framings; a node **splits** if broad and budget allows, else it's a **leaf**.
```bash
python3 "$A/treestate.py" cansplit --node "$RUN/tree/root"
python3 "$A/treestate.py" split --node "$RUN/tree/root" \
  --children '[["consensus","<q>"],["heterodox","<q>"],["practitioner","<q>"],["adversary","strongest disconfirming evidence for the leading framing"]]' \
  --weights '[2,3,1,3]'
```
**Scale scrutiny to contestedness, not uniformly** (the audited fix: uniform "equal scrutiny per leaf"
is suboptimal — Snell 2408.03314 / UAB 2605.26849). Pass `--weights` (one per child) so contested /
uncertain / adversary branches get more budget; budget is still conserved and every child is floored at
the scrutiny unit (no starvation). Omit `--weights` only when the children are genuinely equal effort.
Always include an **adversary** child, weighted high. Log decisions
(`treestate.py decide --node <n> --actor orchestrator --why "…" "<decision>"`).

### 3. Investigate leaves — multi-round, WIDE, primary-first
Process **breadth-first (level by level)** — this is a scheduling order, not an equal-time promise;
scrutiny is set by each node's budget (step 2). For each pending leaf
(`treestate.py frontier --run "$RUN" --state pending --depth <d>`; after a crash/interrupt use
`frontier --run "$RUN" --resumable` so mid-round `active` nodes are re-picked, not skipped),
run the leaf engine, which reads primaries in full and **accumulates across rounds**:
```bash
python3 "$A/investigate.py" --node "<NODE_DIR>"     # round 1; repeat with --query "<gap>" to deepen
```
**Scoped channels (each run fires only what the question needs).** `investigate.py` calls `router.py`
to pick a SMALL, domain-appropriate set — biomed→europepmc/openalex (not arXiv), CS→arxiv/semanticscholar/
github, history→wikipedia/googlebooks, products/current→community+web — always covering web·primary·
community and **excluding off-topic indexes**. Preview it: `python3 "$A/router.py" "<q>" --framing "<angle>" --json`.
The classifier is keyword-based, so if it mis-scopes (e.g. a title with no domain word), **override**:
`investigate.py --node <N> --channels europepmc,openalex,brave,reddit`. Different framings warrant
different channels (practitioner→community/forums; consensus→primaries).
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
`synthesize.py` reports two independence signals: identity `echo_ratio` (voice_key) AND the stronger
structural `origin_echo_ratio` / `independent_origins` (shared-origin clusters — it catches "40 domains
but 1 origin echoed 40×", which voice_key alone scores as independent). **Low echo does NOT license
"Agreement" — high `origin_echo_ratio` means trace claims to their independent origins first.** Take the
**adversary** branch + un-laundered channels and try to break the leading framing. Survive → keep; else downgrade. Log it.

### 6. Verify every load-bearing claim (must complete)
Extract the draft's claims → `$RUN/claims.jsonl` (`{"claim":"…","url":"…"}`):
```bash
python3 "$A/verify.py" --claims "$RUN/claims.jsonl" --node "$RUN/tree/root" --out "$RUN/verify.jsonl"
```
Layer 1 (lexical) certifies **relevance only**, never support — it emits `relevant` (on-topic),
`borderline` (readable but low overlap: a likely paraphrase — must still be checked, never dropped),
`off_topic` (readable but unrelated), or `broken`. Then **Fact-Check EVERY `relevant` AND `borderline`
claim** (read the cited primary in a small context; watch polarity + magnitude) and rewrite each
verdict to `supported`/`contradicted`/`unsupported`. Only `supported` survives in Agreement;
`contradicted` → cut/flip; `unsupported` → downgrade to Unverified.
**Use a DIFFERENT model for the Fact-Check than wrote the draft** (self-preference/verbosity bias is
real — the writer grades its own work too kindly; at `deep`/`exhaustive` spawn the verifier as a
subagent on another model). The score is **code-gated, not honor-system**: `score_run.py` reports
`citation_accuracy` (= precision) as **null until `citation_complete` is true** — i.e. every on-topic
claim has a final verdict (`citation_coverage` = 1.0) — alongside the stated `citation_denominator`
(claims judged). A run with claims still `awaiting_llm_check` has NO headline accuracy: finish the pass.

### 7. Answer, grounded — with gaps
Write `$RUN/brief.md`: **Bottom line** · **Agreement** (independent sources converge) ·
**Disagreement** (name both sides; do not smooth over) · **Unverified / single-origin** ·
**Gaps** (what couldn't be reached: paywalled primaries, missing large RCTs, empty channels — state
them). Every claim links to the **primary you read**; dates on time-sensitive claims. **X/YouTube are
`color`** (never cite as fact); **Reddit/HN are `lead_gen`** — mine them for the primary they point to
and cite THAT, not the thread. Accrete into the `consilient-atlas` so surveys compound.

## Observability & resume
`treestate.py tree --run "$RUN"` shows the whole tree (state/budget/findings). Every node has
`decisions.jsonl`, `questions.jsonl`/`answers.jsonl`, `sources.jsonl`, `notes/`, `evidence.md`,
`findings.md`. Fully resumable — after a crash/interrupt re-run `frontier --run "$RUN" --resumable`
(re-picks pending + mid-round `active` + unanswered nodes, so nothing in flight is silently skipped).

## Rules
Channel **classes**: `evidence` citable · `lead_gen` (search/HN/Reddit) → **find & cite the primary** ·
`color` (X/YouTube) → never cite as fact. Variety, decisive-source hunt, chase-the-primary,
independence-by-judgment, adversary, read-in-full, honest gaps, and completed verification are
non-optional from `standard` up.
