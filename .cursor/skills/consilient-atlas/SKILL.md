---
name: consilient-atlas
description: Appends a completed survey to a growing markdown knowledge base so each survey compounds the next instead of restarting from blank (the agentic-Obsidian / LLM-wiki pattern). Use at the end of an Aletheia survey to persist it, or when the user wants to record or look up a prior survey.
disable-model-invocation: true
---

# consilient-atlas

A survey should not die as a one-off. Each defensible survey accretes into the Atlas (`atlas/`) so future surveys start from what you already established — compounding, not restarting.

## Before appending

- Only persist surveys whose load-bearing beliefs passed `defensibility-judge`. Demote failed beliefs to "lead / unresolved" in the body; do not record them as findings.
- Check `atlas/index.md` first — if a related survey exists, **update/extend** it rather than starting a blank one (progressive overload: harder questions build on the prior view).

## Append

```bash
python3 ~/.cursor/skills/consilient-atlas/scripts/atlas_add.py --title "State of <topic>" \
  --spiky-pov "<one-line spiky POV, if one earned it>" \
  --defensibility "defensible (3.5/4)" \
  --synthesis runs/<run>/synthesis.md \
  --defensibility-file runs/<run>/defensibility.md
```

This writes `atlas/surveys/<date>-<slug>.md` (embedding the synthesis + defensibility) and inserts a row into `atlas/index.md`. Re-running with the same slug/date won't duplicate the index row.

## What to store

- The survey body (from `synthesis.md`): framings tested, agreement / disagreement / unique claims, provenance flags, and "what would change this view."
- The spiky POV, if one was earned and survived the judge.
- The defensibility verdict, so a future reader knows how load-bearing the belief is.
- Provenance verdicts on key claims (independent-source counts), so you don't re-litigate them next time.

## Compounding

On the next survey, `survey-scope` should read the Atlas index for adjacent prior work and seed the framing portfolio from it — including revisiting any belief whose "what would change this view" trigger has since been met. The Atlas is the memory that turns a series of surveys into accumulating expertise.
