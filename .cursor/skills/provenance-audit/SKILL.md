---
name: provenance-audit
description: Judge whether a claim's support is genuinely independent or just one origin echoed by many — by reading and understanding what is cited, not by computing a graph. Use during synthesis of an Aletheia survey, or whenever you need to decide if a "consensus" is real corroboration or an echo.
disable-model-invocation: true
---

# provenance-audit (judgment, not a graph)

The point is simple and it is **your judgment from reading**: don't treat every retrieved source as an equally-independent data point. Understand *what is actually cited* and *where it traces back to*.

## How to judge (do this while reading, step 5 of the survey)

For each load-bearing claim, look at its support and ask:

1. **Trace each source to its origin.** Does this source present original evidence, or is it summarizing/citing someone else? A blog citing a paper is not independent of that paper.
2. **Count origins, not mentions.** If ten articles all trace back to one study or one press release, that is **one** independent source, not ten. "40 blogs, 1 paper" = 1.
3. **Prefer the primary.** Cite the study/dataset/official doc/first-hand report, not the aggregator that repeated it. Follow citations back until you hit the origin.
4. **Watch for circular citation.** A cites B, B cites A, or a cluster that all cite each other with no external grounding — treat the whole cluster as one weak claim.
5. **Flag single-origin.** If everything rests on one source (or one lab/author self-citing), say so: it's a lead, not an established finding.
6. **Independent ≠ same outlet/lab.** Different reporters at one publisher, or different papers from one lab, are correlated — discount accordingly. Different, unaffiliated authors reaching the same conclusion is real corroboration.
7. **Measurable vs. non-measurable attributes.** Agreement on a **measurable** attribute backed by cross-lab instrumentation is strong (e.g. a camera's dynamic range corroborated across Photons-to-Photos / DXOMARK / CineD / RTINGS). Agreement on a **non-measurable / subjective** attribute — "ergonomics," "travel-friendly," "best value," "great for beginners" — is **weak by default**, because that is exactly where SEO/AI content-farms echo each other with no underlying measurement. Down-weight consensus on non-measurable claims; treat it as sentiment, not evidence, unless it traces to genuine first-hand experience.

Report this inline in synthesis: e.g. "supported by 3 independent groups" or "widely repeated but all tracing to a single 2024 paper (treat as one source)."

## Why judgment, not a script

You are reading the sources anyway. Knowing "these five links are really one origin echoed" is an act of *understanding what's cited*, which you do better than a metadata heuristic — a script can't tell that two differently-worded posts are the same claim, but you can. Do it by judgment.

## Optional: the computed helper (only for oversized source sets)

If a survey pulls too many sources to hold in your head, `python3 ~/.cursor/skills/provenance-audit/scripts/provenance_graph.py audit --sources sources.jsonl --claims claims.json` will *approximate* this (collapse echoes by domain/author/near-duplicate text, flag single-origin/circular). It is a convenience, not the mechanism — and it's only as good as its heuristics. Prefer your own judgment for anything load-bearing.
