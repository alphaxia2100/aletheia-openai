---
name: iterative-deepening
description: Turns a flat one-shot search into real research via a breadth x depth loop with reflection - search the frontier, extract learnings and follow-up questions, then recurse into the gaps with decaying breadth. Use inside an Aletheia survey when a channel or framing needs depth beyond a single query, or whenever a topic needs progressive drilling rather than one search.
disable-model-invocation: true
---

# iterative-deepening

A single query per subagent finds the surface. Research is a *loop*: search, learn, notice what you still don't know, search that. This is the mechanism behind deep-research agents (dzhng/deep-research) and it is the biggest upgrade over flat fan-out. The `deepen.py` controller owns the state (dedup, breadth decay, stop decision); you do the LLM parts (generate queries, extract learnings).

## The loop

```bash
D=~/.cursor/skills/iterative-deepening/scripts/deepen.py
STATE=runs/<run>/deepen/<framing>.json

python3 $D init "$STATE" --query "<framing-scoped question>" --breadth 4 --depth 2
while true; do
  # 1. SEARCH the current frontier across the framing's channels (channel-retrieval),
  #    appending normalized records to sources.jsonl.
  python3 $D status "$STATE"        # shows the frontier to search this round

  # 2. REFLECT: from what you just read, write dense LEARNINGS and the FOLLOW-UP
  #    questions the results exposed (the gaps), then record them:
  python3 $D record "$STATE" \
      --learning "<one specific, source-backed finding>" \
      --learning "<another>" \
      --followup "<question the results raised but did not answer>" \
      --followup "<a disconfirming angle to probe next>"

  # 3. DESCEND: get the next, deduped, breadth-decayed frontier. Exit 3 = STOP.
  NEXT=$(python3 $D next "$STATE") || break
done
```

## Rules

- **Reflection drives the next round.** Follow-ups must come from *gaps the results exposed*, not restatements of the original query. At least one follow-up per round should be a **disconfirming** angle (feeds the adversary).
- **Breadth decays with depth.** Level 1 uses full breadth; each deeper level halves it — you widen at the top, narrow as you drill. `deepen.py` enforces this.
- **Dedup is automatic.** `deepen.py` normalizes and drops already-visited queries, so the loop can't spin on the same search.
- **One tree per framing.** Run a separate deepening state per framing from `survey-scope`, so competing framings drill independently and don't collapse into one path (anti-anchoring).
- **Scope stays fixed.** Deepening changes *depth*, never the framing's scope — a subagent must not redefine what it's hunting mid-loop.

## Stop conditions (anti-overtraining)

`deepen.py next` exits non-zero (STOP) when depth is reached OR no novel follow-ups remain (convergence). Convergence is the signal from the weightlifting frame: once new searches stop moving the view, stop — more searching is procrastination dressed as rigor.

## Output

Each round appends records to `runs/<run>/sources.jsonl` and the `learnings` accumulate in the state file. Learnings become candidate claims for `provenance-audit`; the frontier history shows what was explored (and what wasn't) for the adversary's "premature termination" check.
