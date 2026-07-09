---
name: deep-aletheia
description: SUPERSEDED (2026-07-08) — this 0.2 is the ANCESTOR of the `aletheia-research` 0.3 skill (which is built from it and keeps its good parts); frozen and kept runnable only as an eval baseline. Prefer `aletheia-research`. Deep, high-scrutiny research surveyor. A DYNAMIC, question-driven tree coordinated through the filesystem — the lead frames a portfolio of competing perspectives (anti-anchoring), then GROWS a living outline FROM the evidence: each node investigates, reflects, and either deepens (drills the same question) or decomposes (spawns sub-questions) based on what it found. Findings bubble up; parents ask thin children for specifics instead of assuming; every claim is tied to a primary through a verification gate. The human owns framing sign-off and final judgment (DOK 3-4); the AI does breadth and stress-testing (DOK 1-2). Use for deep dives where surface-level answers are not enough and tokens/time are not a concern. For a quick single-pass survey, use `aletheia-research`.
---

# Deep Aletheia — a dynamic, question-driven surveyor (v0.2)

> **SUPERSEDED (2026-07-08) → this is the ANCESTOR of `aletheia-research` 0.3.** A blind LLM-judge of fresh
> runs found this design's tree/breadth produced the most complete, best-grounded briefs, so it was
> promoted (not retired): **`aletheia-research` 0.3 is built from this 0.2**, keeps its good parts (variety of
> sources, real multi-round surveying, honest gaps, adversary, independence, completed verification),
> and adds a decisive-source hunt, chase-the-primary discipline, wider channel variety, and a
> thoroughness dial. This 0.2 is frozen and kept runnable only as an eval baseline. Use `aletheia-research`.

Depth is NOT a longer loop, and NOT a bigger pre-planned tree. It is **how expert researchers and the
strongest deep-research systems actually work**: ask from many perspectives, gather evidence to disk,
**let the outline grow from what you find**, then write grounded — with the **human owning judgment**.

Why this method (read in full; independent origins — the point of Aletheia):
- **STORM** (Stanford OVAL, NAACL'24): survey quality is decided in the *pre-writing* stage —
  discover diverse **perspectives**, ask **multi-perspective questions** to retrieval-grounded
  experts, curate an **outline**. Guards *source-bias transfer* and *over-association*.
- **WebWeaver** (SOTA 2025): the killer flaw is *"static pipelines that decouple planning from
  evidence."* Fix = a **dynamic cycle interleaving evidence acquisition with outline optimization**,
  a filesystem **memory bank**, and **section-by-section grounded writing**.
- **AgentCPM-Report** (2026): plan-then-write hinges on an initial outline you *can't* get right up
  front — so **revise the outline during research** (alternate drafting and deepening).

**The rule:** never fix the decomposition before the evidence. **Look, then decide.** Everything is
files (the memory bank). Every node is a directory. The tree is a **living outline**. The human signs
off framings and makes the final call (DOK 3-4); the AI does breadth + stress-test (DOK 1-2).

## Toolkit
```bash
AL=~/.cursor/skills                       # global install (scripts/install.sh)
DA="$AL/deep-aletheia/scripts"
DEEPEN="$AL/iterative-deepening/scripts/deepen.py"    # the per-node drilling controller (now wired in)
python3 "$AL/channel-retrieval/scripts/doctor.py"    # confirm channels live first
```
`treestate.py` (blackboard/tree/budget/ask-answer), `investigate.py` (one deepening round — call it
repeatedly; evidence accumulates), `deepen.py` (reflection/dedup/stop controller), `rank.py`
(authority ranking), `synthesize.py` (bottom-up merge + independence + `--gate`), `verify.py`
(two-layer citation gate).

## The loop — five steps, processed LEVEL BY LEVEL (so "time per level" is equal)

### 1. FRAME — perspectives → questions (anti-anchoring; STORM + portfolio)
```bash
RUN=$(python3 "$DA/treestate.py" init "<topic>" --slug "<slug>" \
      --budget 32 --unit 4 --max-depth 3 --max-children 5 --max-nodes 40)
```
In `$RUN/portfolio.md`, BEFORE any search, write **4–6 competing framings** — the mainstream view, ≥1
heterodox ("the experts are wrong because…"), ≥1 practitioner/field-report, ≥1 orthogonal reframe —
and **seed each with 1–3 concrete sub-questions** (STORM: the outline is made of questions, not
labels). Name one framing the current **"leading"** one for the adversary. Then **seed the root's
level-1 children** (the framings) and get the **human's sign-off** on scope (their DOK-3/4 entry):
```bash
python3 "$DA/treestate.py" split --node "$RUN/tree/root" \
  --children '[["consensus","<q>"],["heterodox","<q>"],["practitioner","<q>"],["adversary","strongest disconfirming evidence for the leading framing"]]'
```
Commit to none. (These top framings are the one *a-priori* decomposition; everything below grows from evidence.)

### 2. GROW THE OUTLINE FROM EVIDENCE (the core — dynamic, not guessed)
Process the tree **one level at a time** (equal time per level). List the level's frontier and spawn
**one READ-ONLY worker subagent per node, in parallel** (multiple Task calls in one message):
```bash
python3 "$DA/treestate.py" frontier --run "$RUN" --state pending --depth <d>
```
Spawn each worker with the **Task tool** (`subagent_type: generalPurpose` — workers WRITE artifacts),
giving it the **full shared context** (topic + this node's question + why it exists — share context,
not one-liners). Worker prompt template:

> You are a READ-ONLY Deep Aletheia worker for node `<NODE_DIR>` (budget B, unit U from `run.json`).
> Topic: `<topic>`. Your question: `<question>`. Why you exist: `<role in the portfolio>`.
> Run the **node loop** — investigate a round, reflect, then deepen / decompose / stop:
> 1. `python3 ~/.cursor/skills/deep-aletheia/scripts/investigate.py --node <NODE_DIR>` (round 1;
>    reads ≈ one unit into `notes/`). Then READ `<NODE_DIR>/evidence.md` and the full `notes/`.
> 2. On round 1 also: `python3 <DEEPEN> init <NODE_DIR>/deepen.json --query "<question>" --breadth 1 --depth <⌊B/U⌋−1, cap 3>`
> 3. **REFLECT** (your own words): source-backed learnings; open gaps; and *"is this ONE atomic
>    question, or several distinct sub-questions?"* Record it:
>    `python3 <DEEPEN> record <NODE_DIR>/deepen.json --learning "…" --followup "<top gap>" --followup "<a disconfirming angle>"`
> 4. **DECIDE** (strict priority; log each with `treestate.py decide --node <NODE_DIR> --actor worker --why "…"`):
>    - **DECOMPOSE** — if the evidence shows *separable* sub-questions and budget allows: propose them
>      and STOP: `python3 ~/.cursor/skills/deep-aletheia/scripts/treestate.py propose --node <NODE_DIR> --children '[["s1","q1"],["s2","q2"]]' --why "<what in the evidence>"`.
>    - **DEEPEN** — else get the next gap and drill again: `NEXT=$(python3 <DEEPEN> next <NODE_DIR>/deepen.json)`; if it exits 0, `investigate.py --node <NODE_DIR> --query "$NEXT"` (accumulates), then back to step 3.
>    - **STOP** — when `deepen.py next` exits 3 (converged / depth reached) or budget is spent, write
>      `<NODE_DIR>/findings.md`: 3–8 **claims**, each with the **primary URL** it rests on + a one-line
>      quote; mark class (evidence/lead_gen/color); separate corroborated vs single-origin; note
>      disconfirming evidence. Cite primaries, not aggregators.
> Do NOT make decisions that depend on sibling workers. Return a 5-line summary + the findings path.

Workers are read-only and independent (safe to parallelize). **Depth comes from both**: leaf rounds
(deepen) AND evidence-driven decomposition (propose). Then **materialize** the approved proposals and
process the next level:
```bash
for n in $(python3 "$DA/treestate.py" frontier --run "$RUN" --state proposes_split --depth <d>); do
  python3 "$DA/treestate.py" materialize --node "$n"      # split_node enforces the budget/cap floor
done
# repeat step 2 for depth d+1 until no pending/proposes_split nodes remain
```
Budget is **conserved** across a split (K children each get B/K) → every level costs ≈ the same
(equal time per level) and every leaf bottoms out at ≈ one scrutiny **unit** (equal scrutiny). Keep
siblings comparable in scope. Caps (`max-depth/children/nodes`, unit floor) bound fan-out.

### 3. BACK-AND-FORTH — ask thin children, don't assume (enforced)
Synthesize **bottom-up** (deepest internal nodes first). For each node:
```bash
python3 "$DA/synthesize.py" --node "<NODE_DIR>" --gate     # writes synthesis_input.md; exit 3 = BLOCKED
```
If it exits **3**, a child is **thin AND unanswered** — do NOT author findings. Ask it, and let it
answer **from its already-gathered sources** (no re-retrieval):
```bash
QID=$(python3 "$DA/treestate.py" ask --node "<CHILD_DIR>" --from "<parent qid>" --q "specific question")
# re-spawn a read-only subagent on <CHILD_DIR> to answer from its notes/, then:
python3 "$DA/treestate.py" answer --node "<CHILD_DIR>" --qid $QID --a "…"
```
Re-run with `--gate` until it passes, then author `<NODE_DIR>/findings.md` yourself (single-threaded —
one context sees all): **Agreement / Disagreement / Unverified**, honoring the independence report
(high `echo_ratio`/`top_domain_share` ⇒ don't treat convergence as truth).

### 4. JUDGE INDEPENDENCE + ADVERSARY (the differentiator)
`synthesize.py` computes independence over the subtree ("40 sources, or 1 origin echoed 40×?"). Before
believing the root's leading framing, take the **adversary** branch + un-laundered channels and try to
break it. If it survives, keep it; else revise/downgrade. Log it. (This guards STORM's named
*source-bias transfer* and *over-association*.)

### 5. WRITE GROUNDED + VERIFY (section by section)
Author `$RUN/brief.md` section by section, pulling only each section's evidence from the memory bank
(WebWeaver): **Agreement** (independent sources converge) · **Disagreement** (name both sides; never
smooth over) · **Unverified** (single-origin/unsupported). Then the **two-layer citation gate**:
```bash
python3 "$DA/verify.py" --claims "$RUN/claims.jsonl" --node "$RUN/tree/root" --out "$RUN/verify.jsonl"
```
Layer 1 (lexical) only certifies **relevance** (`broken`/`off_topic`/`borderline`/`relevant`; a
`borderline` low-overlap source is a likely paraphrase and must NOT be dropped). Then a **verifier
subagent must Fact-Check EVERY `relevant` AND `borderline` claim** (it can't see polarity/magnitude) →
final verdict `supported`/`contradicted`/`unsupported`, written back to `verify.jsonl`. Only `supported` claims
survive in **Agreement**; `contradicted` → cut/flip; `unsupported` → downgrade to Unverified. Every
claim links to the **primary you read**; reddit/youtube/x are **color**, never proof. Accrete into the
Atlas so runs compound (`consilient-atlas`). **The human makes the final DOK 3-4 judgment.**

## Observability & resume
`treestate.py tree --run "$RUN"` shows the whole living outline (state/budget/findings). Every node
has `decisions.jsonl` (why), `questions.jsonl`/`answers.jsonl` (parent↔child), `sources.jsonl`,
`notes/`, `evidence.md` (per-round), `findings.md`, and `deepen.json`. Fully resumable — re-run
`frontier` to find unfinished work; `score_run.py <RUN>` reports depth (rounds/leaf, evidence-driven
vs a-priori children, clarification coverage, reads-by-depth).

## Caps (anti-explosion)
`max-depth`, `max-children`, `max-nodes`, and the `unit` floor bound the tree. Raise `--budget` at a
fixed `--unit` to buy **leaf depth** (more rounds), not just more branching — budget is conserved down
the tree, so cost stays predictable per level.

## Rules kept from v1
Channel **classes** (evidence citable · lead_gen → find+cite the primary · color never cited),
independence-by-judgment, adversary, and "read in full." v0.2 makes the tree a **living outline grown
from evidence** and wires in per-node iterative deepening + enforced back-and-forth — it does not
replace the epistemics.
