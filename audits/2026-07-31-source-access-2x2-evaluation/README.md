# Aletheia source-access 2×2 evaluation — 2026-07-31

**Status:** completed operational pilot; not an answer-quality benchmark.
**Question:** Does Aletheia's source surface retrieve useful landmarks beyond a
defined generic-web lane, and does the current candidate pipeline retain them?

This is the empirical follow-up to the v2 design investigation. It directly
tests the distinction the prior fixed-source comparison could not test: access
to specialist sources versus the value of workflow ceremony after sources are
already equal.

Start with [results.md](results.md): the first live observation's literal
URL-substring score was generic web 1/3 and specialist 0/3, but independent
review finds that this is not a semantic source-access verdict. The current path
has query-sanitization, identity, receipt, and live-index-stability failures.
It does **not** support claiming that Aletheia is already much better because
it has specialist channels.

The originally stated [protocol](protocol.md), [tasks](tasks.json), and
[run_access_probe.py](run_access_probe.py) are preserved. Their current hashes
verify against the first raw observation, but they were untracked at review time;
the audit cannot independently prove a pre-run freeze. A separate
[post-hoc adapter diagnostic](posthoc_adapter_diagnostics.py) distinguishes
known-ID endpoint reachability from natural-language discovery. The derived
[results.json](results.json), [analysis](analysis.md), [decision log](decision-log.md),
and [integrity review](research/result-integrity-review.md) state the limits.
Raw public retrieval metadata remains intentionally ignored.

The prior architecture conclusion remains in
[the v2 design dossier](../2026-07-29-v2-ground-up-design/v2-design.md). This
pilot identifies current operational failures and can motivate a stronger
sealed source-access study. It cannot show end-to-end answer superiority,
evidence identity, claim correctness, cost, latency, or the value of
multi-agent orchestration.
