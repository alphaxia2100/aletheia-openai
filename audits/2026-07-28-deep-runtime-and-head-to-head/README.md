# Deep runtime review and head-to-head evaluation

This is the follow-on audit requested after the first independent project audit. It has two distinct
goals:

1. a line-level review of every executable source file in the portable Aletheia runtime closure and
   its installer/security boundary; and
2. a controlled same-question comparison between the Aletheia protocol and a bounded direct-agent
   baseline, with a predeclared rubric and an independent judge.

The comparison's initial 12–11 Aletheia score was independently corrected to an **11–11 factual tie**:
the blind judge awarded Output B a rubric point for naming two favorable forward tests when it named
only one. The raw blind judgment remains preserved; use [comparison/results.md](comparison/results.md)
and [comparison/independent-method-audit.md](comparison/independent-method-audit.md) as the
authoritative interpretation.

**Audited commit:** `cbed478c` on `codex/independent-audit-2026-07-28`, which contains the prior
audit artifacts and is based on the runtime candidate `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5`.

## Channel-health limitation

The comparison began with a live doctor probe on 2026-07-28. Brave was degraded because no API key was
configured and Reddit was down with HTTP 502. The evaluation uses healthy channels and records the
missing coverage; it does not silently present the result as a full web/community benchmark.

Raw fetched documents, generated fixtures, and full research-run state remain ignored. Compact source
inventories, line-coverage manifests, outputs, grading records, and conclusions are the committed
artifacts.

## Re-run checklist

This directory is intentionally self-validating so a future audit can preserve the frozen evidence
while adding a dated sibling rather than overwriting it.

```bash
python3 audits/2026-07-28-deep-runtime-and-head-to-head/validate_audit.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

The validator checks JSON syntax, frozen Git blob hashes, contiguous line-review coverage, comparison
packet/output hashes, and whitespace errors. It cannot re-prove qualitative findings, live channel
behavior, or blinding; those limits are documented in [report.md](report.md), the
[independent method audit](comparison/independent-method-audit.md), and the
[runtime adversarial addendum](runtime-adversarial-addendum.md).
