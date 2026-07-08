---
name: deep-aletheia
description: Deep, high-scrutiny research surveyor. A RECURSIVE orchestrator-worker tree coordinated entirely through the filesystem — the lead frames a hypothesis portfolio, decomposes the question into a budget-balanced tree (equal scrutiny per leaf, equal effort per level), spawns parallel READ-ONLY worker subagents that investigate leaves and write artifacts, then synthesizes bottom-up with top-down clarification and a claim->source verification gate. Use for deep dives where surface-level answers are not enough and tokens/time are not a concern. For a quick single-pass survey, use `aletheia` instead.
---

# Deep Aletheia — recursive research tree (v0.1)

Depth does NOT come from running one loop longer. It comes from: **many parallel, well-scoped,
read-only explorations, each in its own clean context, coordinated through the filesystem, with
aggressive compression and a verification gate.** (Evidence + rationale: `docs/deep-aletheia-design.md`.)

Everything is files. Every agent is a directory. Nothing depends on one context window.

## Toolkit
```bash
AL=~/.cursor/skills                       # global install (scripts/install.sh)
DA="$AL/deep-aletheia/scripts"
python3 "$AL/channel-retrieval/scripts/doctor.py"    # confirm channels live first
```
Scripts: `treestate.py` (blackboard/tree/budget), `router.py` (channel routing),
`investigate.py` (leaf engine), `rank.py` (authority ranking), `verify.py` (citation gate),
`synthesize.py` (bottom-up merge + independence).

## The loop (do every step; none is optional)

### 1. Init + frame the portfolio (anti-anchoring — load-bearing)
```bash
RUN=$(python3 "$DA/treestate.py" init "<topic>" --slug "<slug>" \
      --budget 32 --unit 4 --max-depth 3 --max-children 5 --max-nodes 40)
```
Write **4–6 competing framings** into `$RUN/portfolio.md` BEFORE any search: the
mainstream/consensus view, ≥1 heterodox ("the experts are wrong because…"), ≥1
practitioner/field-report, ≥1 orthogonal reframe, and **name one framing as the current
"leading" one so step 5 can attack it**. Commit to none.

### 2. Decompose into a budget-balanced tree
Split the root into the framings, then recurse: a node **splits** if its question is broad and
budget allows; otherwise it's a **leaf** to investigate.
```bash
python3 "$DA/treestate.py" cansplit --node "$RUN/tree/root"          # budget/cap check
python3 "$DA/treestate.py" split --node "$RUN/tree/root" \
  --children '[["consensus","<q>"],["heterodox","<q>"],["practitioner","<q>"],["adversary","disconfirming evidence for the leading framing"]]'
```
- **Budget is conserved**: K children each get `budget/K`. Recurse while `cansplit` allows
  (`budget/K ≥ unit`). This makes **every tree level cost ≈ the same** (your "equal time per
  level") and **every leaf get ≈ one scrutiny unit** (equal depth of scrutiny).
- Keep it **balanced**: give sibling sub-questions comparable scope. Don't over-split one branch.
- **Always include an adversary child** whose job is disconfirming evidence.
- Log why you split/stopped: `treestate.py decide --node <n> --actor orchestrator --why "…" "<decision>"`.

### 3. Investigate leaves with parallel READ-ONLY worker subagents
Process **level by level** (equal scrutiny). List the frontier and spawn one subagent per leaf,
**in parallel** (multiple Task calls in one message):
```bash
python3 "$DA/treestate.py" frontier --run "$RUN" --state pending
```
Spawn each worker with the **Task tool** (`subagent_type: generalPurpose` — workers WRITE
artifacts, so not read-only `explore`), giving it the **full shared context** (topic + this
node's framing + why it exists — Cognition: share context, not one-liners).
Worker prompt template:
> You are a READ-ONLY Deep Aletheia worker for node `<NODE_DIR>`.
> Topic: `<topic>`. Your framing/sub-question: `<question>`. Why you exist: `<role in the portfolio>`.
> 1. Run: `python3 ~/.cursor/skills/deep-aletheia/scripts/investigate.py --node <NODE_DIR> --reads <round(budget)>`
> 2. Read `<NODE_DIR>/evidence.md` and the full reads in `<NODE_DIR>/notes/`.
> 3. Write `<NODE_DIR>/findings.md`: 3–8 **claims**, each with the **primary URL** it rests on and
>    a one-line quote/paraphrase; mark class (evidence/lead_gen/color); separate what's
>    corroborated vs single-origin; note disconfirming evidence you found. Cite primaries, not aggregators.
> 4. Log key choices: `treestate.py decide --node <NODE_DIR> --actor worker --why "…" "<decision>"`.
> Do NOT make decisions that depend on sibling workers. Return a 5-line summary + the findings path.

Workers are read-only and independent (Cognition-safe). They write artifacts; they don't pass
big blobs back through you (Anthropic anti-"telephone").

### 4. Synthesize bottom-up, with top-down clarification
Deepest internal nodes first, up to the root. For each:
```bash
python3 "$DA/synthesize.py" --node "<NODE_DIR>"        # writes synthesis_input.md + independence
```
Read `synthesis_input.md`. If a child's findings are **thin or ambiguous**, don't assume — ask it
(back-and-forth, hierarchical, via the filesystem):
```bash
QID=$(python3 "$DA/treestate.py" ask --node "<CHILD_DIR>" --from "<PARENT_qid>" --q "specific question")
# re-spawn a subagent on <CHILD_DIR> to answer from its ALREADY-gathered sources (no re-retrieval),
# writing the answer: treestate.py answer --node <CHILD_DIR> --qid $QID --a "…"
```
Then author `<NODE_DIR>/findings.md` yourself (single-threaded synthesis — one context sees all):
Agreement / Disagreement / Unverified, honoring the independence report (high echo_ratio or
top_domain_share ⇒ don't treat convergence as truth; trace to independent origins).

### 5. Attack the leading conclusion (adversary)
Before believing the root's leading framing, take the adversary branch's findings and the
un-laundered channels and try to break it. If it survives, keep it; else revise/downgrade. Log it.

### 6. Verify citations (two-layer gate)
Extract the root draft's claims into `claims.jsonl` (`{"claim":"…","url":"…"}`), then run the
**deterministic layer** — it only certifies *relevance*, never *support*:
```bash
python3 "$DA/verify.py" --claims "$RUN/claims.jsonl" --node "$RUN/tree/root" --out "$RUN/verify.jsonl"
```
It emits `broken` (unreadable source → fix/drop the citation), `off_topic` (source doesn't discuss
the claim → find the real primary), or `relevant` (on-topic — but **support is still UNKNOWN**).
Every result carries `needs_llm_check=True`.

**Then the LLM verifier pass (this is the actual gate — do NOT skip it).** Lexical overlap cannot
see polarity/negation or magnitude — "IF is superior" vs "IF is *not* superior" share nearly all
words, and "doubles fat loss" looks identical to a small effect. So a verifier **subagent must
Fact-Check EVERY `relevant` claim**, not just the weak-looking ones. Spawn read-only verifier
subagents (parallel, one per claim; adversarial — tell them to hunt for a mismatch); each reads
the cited source in full and returns a final verdict, written back into `verify.jsonl`:
- **`supported`** — the source's own findings entail the claim *as stated* (direction + magnitude).
- **`contradicted`** — the source states the opposite direction, or a magnitude it refutes → the
  claim is wrong: cut it or flip it.
- **`unsupported`** — on-topic but doesn't establish the claim as stated (overstated magnitude,
  missing result, mixed/weaker evidence) → **downgrade to Unverified** or fix the citation.

Target: only `supported` claims survive in **Agreement**. `score_run.py` reads `verify.jsonl` and
reports `citation_accuracy = supported/total` (plus contradicted/unsupported counts).

### 7. Answer, grounded
Write `$RUN/brief.md`: **Agreement** (independent sources converge), **Disagreement** (name both
sides; never smooth over), **Unverified** (single-origin/unsupported). Every claim links to the
**primary you read**; dates on time-sensitive claims; reddit/youtube/x are **color**, never proof.
Then accrete into the Atlas so runs compound:
`python3 "$AL/consilient-atlas/scripts/atlas_add.py" …` (see the `consilient-atlas` skill).

## Observability & resume
`treestate.py tree --run "$RUN"` shows the whole tree with state/budget/findings. Every node has
`decisions.jsonl` (why), `questions.jsonl`/`answers.jsonl` (parent↔child), `sources.jsonl`,
`notes/`, `findings.md`. A run is fully resumable from disk — re-run `frontier` to find unfinished work.

## Caps (anti-explosion)
`max-depth`, `max-children`, `max-nodes`, and the `unit` floor bound the tree (Anthropic saw
agents spawn 50 subagents). Raise `--budget`/`--max-nodes` for deeper runs — scrutiny scales with
budget, and budget is conserved down the tree, so cost stays predictable per level.

## Rules kept from v1
Channel **classes** (evidence citable · lead_gen → find+cite the primary · color never cited),
independence-by-judgment, adversary, and "read in full." Deep Aletheia adds the tree, routing,
authority ranking, verification, and memory — it does not replace the epistemics.
