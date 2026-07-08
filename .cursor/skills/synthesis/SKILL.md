---
name: synthesis
description: Single-threaded writer that turns audited findings into a survey structured as agreement / disagreement / unique-claims (an audit, not a majority vote), with inline provenance and disagreement preserved. Use as the synthesis stage of an Aletheia survey, after provenance-audit and adversary have run.
disable-model-invocation: true
---

# synthesis

You are the **one writer**. Retrieval was parallel; synthesis is not. Hold the whole picture in one continuous context so decisions stay consistent (parallel writers make conflicting implicit decisions — the documented failure mode).

## Inputs

`runs/<run>/sources.jsonl`, the full texts you read (`runs/<run>/reads/`), the framing portfolio from step 1, and the adversary findings (step 7). Read all before writing. Independence verdicts come from **your own judgment while reading** (aletheia step 5 / the `provenance-audit` skill); a computed `provenance.md` exists only if you ran the optional script on an oversized source set.

## Structure the output as an audit, not a vote

Majority vote rewards the loudest echo. Instead, for the field, produce three explicit buckets:

- **Agreement** — claims multiple *independent* sources support. State the independent-source count from your reading judgment, not the raw mention count. "Supported by 4 independent sources (11 mentions)."
- **Disagreement** — where credible sources genuinely conflict. Name both sides, who holds each, and why it's unresolved. Never collapse this into a false consensus. If the adversary found a top lab or named practitioner dissenting, it goes here.
- **Unique / unreplicated** — claims resting on a single origin. Mark them as such; a single-origin claim is a lead, not a finding.

## Rules

1. **Independent sources, not mentions.** Every load-bearing statement carries its provenance verdict. If your reading found a claim single-origin or circular ("40 blogs, 1 paper"), say so inline.
2. **Class-aware citation.** Cite `evidence`-class primaries. When something rests only on `lead_gen`/`color`, label it ("per practitioner reports on Reddit — color, not evidence").
3. **Preserve disagreement.** The divergence between channels/sources is itself a finding — report it, don't smooth it.
4. **Surface the spiky POV, if one earned it.** If the evidence supports a defensible non-consensus view (especially one only the un-laundered channels revealed), state it plainly and route it to `defensibility-judge`.
5. **Widen, don't just compress.** This is DOK 3-4 territory: show the framings and the counter-evidence and the reasoning chain, not a lossy conclusion. The reader should be able to hold and defend the view unaided — that is the point.

## Output template

Write `runs/<run>/synthesis.md`:

```markdown
# Survey: <topic>

## Framings tested
<the step-1 portfolio, and which framings survived contact with evidence>

## Agreement (independent-source-backed)
- <claim> — <N independent sources (M mentions)>; <primary cites>

## Disagreement (preserved)
- <claim>: <side A, who> vs <side B, who>; unresolved because <...>

## Unique / unreplicated (leads, not findings)
- <claim> — single origin: <source>

## Spiky POV (if earned)
<statement> — routed to defensibility-judge.

## Provenance flags carried forward
<single-origin, circular-citation, echo notes from your reading judgment>

## What would change this view
<the cheapest evidence that would move the conclusion — the anti-overtraining marker>
```

## BrainLift output (optional)

When the survey feeds a BrainLift, restructure `synthesis.md` into these sections instead:

- **Purpose / scope** — the question and why it matters, bounded.
- **Sources & Experts** — the primaries and expert voices, each tagged evidence / lead-gen / color, and explicitly **where the experts might be wrong** (from the adversary pass). Sourcing only from experts cannot surface that experts are wrong — so name the un-laundered channels you checked.
- **Spiky POVs** — defensible non-consensus claims that passed `defensibility-judge` (include the verdict + the stated falsifier). A POV that merely agrees with the experts isn't spiky; one that survived disconfirmation is.
- **Knowledge tree (DOK-tagged)** — the gathered facts (DOK 1-2) organized so the user can do DOK 3-4. Keep the reasoning chain; do not pre-compress.
- **Insights / what would change this view** — the cheapest disconfirmer, so the belief stays live.

Route Spiky POVs through `defensibility-judge` and the whole doc to `consilient-atlas`. (Field names track the BrainLift frame — Purpose, Experts, SpikyPOVs, Knowledge Tree, Insights — adjust to your exact template.)
