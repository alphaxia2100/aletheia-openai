# Final claims review — source-access 2×2 operational pilot

**Reviewer:** fresh-context claims reviewer
**Review date:** 2026-07-31
**Scope:** [results.md](../results.md), [analysis.md](../analysis.md),
[decision-log.md](../decision-log.md), [results.json](../results.json),
[audit-manifest.json](../audit-manifest.json), [validate_audit.py](../validate_audit.py),
the raw receipts available locally, and the prior
[result-integrity review](result-integrity-review.md) and
[runtime review](runtime-review.md). This was an offline review; it made no
network request and changed no production artifact.

## Verdict: fail pending claim corrections

The audit's central conclusion is sound and unusually well caveated: the
recorded pilot does **not** show that current Aletheia is much better because of
specialist access, and it does show concrete operational/identity failures.
The literal primary counts, post-hoc separation, raw-file hashes, and
limitations are described consistently.

However, the bundle is not publication-ready as a claims audit until the
corrections below are incorporated or explicitly preserved as protocol
errata. The defects do not reverse the bottom line. They matter because they
otherwise overstate experimental control, make incomparable ranks sound like an
improvement, and imply a stronger identity result than the diagnostic provides.

## What passed

- `python3 validate_audit.py` passed. Its checked-in `results.json` hash is
  `sha256:5d9c0f7e37671fdaf4f8e2e77b8047967bf7a1fa8d148fed0fc67d992a1922b9`,
  and its task hash is
  `sha256:4d20bebac1bb2324c71b83ae518a68fe1318d50c2c0a42e467edc7308bd53a16`.
- The three available raw-file SHA-256 values equal the corresponding values
  checked into `results.json`: primary `931fc59b…358f54d`, replication
  `9b420b0a…776a4aa`, and diagnostic `3214acaf…cef0c83`.
- The primary raw receipts support the stated literal outcome: generic `1/3`,
  specialist `0/3`, with the generic GitHub URL at DuckDuckGo's local rank 7
  and the replay placing it at pooled rank 4. The replication has `0/3` in
  both lanes. Two primary specialist cells contain the recorded OpenAlex HTTP
  400 error.
- The separate diagnostic supports its narrow statements: Europe PMC resolves
  the expected creatine title under a PMC URL; exact arXiv ID and GitHub slug
  lookups return their targets at rank 1; the natural GitHub query returns
  zero; and OpenAlex returns the recorded 400 for the punctuation-bearing
  question.
- The reports correctly avoid claims about answer quality, end-to-end latency,
  cost, source exclusivity, full workflow performance, or a direct agent with
  the same tools. They correctly retain the PubMed/PMC matcher defect as `NE`,
  rather than changing the frozen literal result.

## Required corrections

| Priority | Finding and evidence | Precise correction |
|---|---|---|
| P1 | **The request/invocation unit is ambiguous and can be read as false.** `run_access_probe.py` loops over three tasks, two access lanes, and two adapters: it makes **two adapter invocations per task × access lane**, six per aggregate access lane, and 12 across the primary run. `results.md` and `audit-manifest.json` instead say “two adapter invocations per access lane.” Further, adapters may retry internally, so neither the protocol's “exactly two requests” nor a lane-wide request count describes physical HTTP attempts. | In the final report and manifest, replace the resource wording with: “For **each task × access lane**, the harness invoked two channel adapters (six invocations per aggregate lane; 12 across the three-task primary run), requesting at most eight records per invocation with a 20-second per-attempt timeout. Connector-internal HTTP attempts/retries were not fully logged.” Preserve the frozen protocol unchanged, but add an erratum/decision-log entry stating that its word “requests” means adapter invocations per task/lane, not exactly two physical HTTP requests. |
| P1 | **The protocol did not give all four access cells one common network snapshot.** Generic and specialist retrieval calls are sequential; the primary receipt spans about 12.6 seconds. The replay arm correctly reuses the raw records of its own access lane, but that is a paired transformation, not a simultaneous four-cell retrieval experiment. The integrity review reaches the same distinction. | Do not describe the source-access comparison as sharing an identical network snapshot. State: “Within each access lane, raw and replay use the identical retrieved records; generic and specialist requests were sequential within the recorded 12.6-second observation window.” Preserve the frozen protocol and add this as an execution erratum if its “same live snapshot window” phrase is retained. |
| P2 | **“Improved from … rank 7 to … rank 4” compares different ordinals.** The first number is DuckDuckGo's channel-local rank; the second is a rank in a deduplicated pooled list. The retained candidate was placed at pooled rank 4, but the numerical change is not a comparable rank improvement. | Replace the sentence in `results.md` with: “The generic autoresearch hit was retained in memory and placed at pooled replay rank 4 after appearing at DuckDuckGo's channel-local rank 7. These are different candidate lists, so the ordinals are not a measured rank improvement.” |
| P2 | **“Several current specialist adapters can retrieve exact known stable IDs” is too strong and slightly inaccurate.** All supporting successes are post-hoc known-identifier/slug lookups. Europe PMC returns the expected title but loses the PMID in its normalized record, and a GitHub owner/repository slug is not an immutable version identity. | Replace the first supporting bullet in `results.md` with: “In the post-hoc diagnostic, Europe PMC, arXiv, and GitHub resolved known identifiers or a repository slug to the expected record; Europe PMC's normalized result did not retain the PMID.” Keep the existing warning that this is not natural-language discovery. |
| P2 | **The letter grades in `analysis.md` look measured but have no declared rubric.** “F / D / B” is defensible as an assessor opinion, but could be mistaken for a benchmark score and the underlying-hypothesis “B” is not directly measured by this three-task pilot. | Either remove the letters and retain the prose verdict, or label them explicitly: “qualitative auditor judgments, not benchmark scores.” Define each dimension in one sentence and change “B” to “plausible but untested product hypothesis.” |
| P2 | **The claimed fresh isolation of the replication is not independently evidenced by the checked-in receipt.** The raw result records runtime commit/config metadata, but not the execution command, environment variable values, or initial cache digest. The result-integrity review already identifies this provenance gap. | In `results.md`, change “with a fresh isolated configuration/cache” to “reported as using a fresh isolated configuration/cache; the saved receipt does not independently attest the initial cache/config state.” Future runs should record nonsecret environment-mode fields and cache-state digests. |

## Claim language that is approved after those corrections

The following is the strongest accurate one-paragraph conclusion supported by
the bundle:

> In this three-task, time-bounded operational retrieval pilot, a literal
> URL-substring fixture recorded one generic-lane hit and zero specialist-lane
> hits. That count is not a semantic access-rate estimate: Europe PMC exposes a
> demonstrated alias/identity mismatch, OpenAlex failed on two punctuation
> queries, and native-query behavior was not endpoint-equivalent. Separately,
> post-hoc known-identifier diagnostics show that several public specialist
> endpoints can resolve their target when given the identifier or repository
> slug. The current path therefore has not demonstrated reliable
> natural-language conversion of specialist access into discovery, and the
> pilot supplies no evidence for an answer-quality, cost, latency, workflow, or
> exclusivity advantage over an equal-tools direct lead.

## Non-findings and boundaries confirmed by this review

- Do not translate generic `1/3` versus specialist `0/3` into a general
  performance comparison, a source-absence claim, or evidence that generic
  web is superior.
- Do not treat the post-hoc exact-ID/slug successes as wins in the primary
  endpoint or as proof of unique Aletheia access.
- Do not call the replay a full Aletheia workflow or a factorial
  workflow-by-access interaction result. It is an in-memory dedupe/rank
  transformation of the same lane's records.
- Do not claim a cost, total-request, physical-HTTP, end-to-end latency, or
  reliability rate from this run. The recorded 20-second setting is an
  adapter-attempt timeout, not a global deadline, and retry counts are absent.

After the listed wording and execution-erratum changes, I would mark the
claims layer **pass with material limitations**. The core recommendation—fix
query rendering, typed identity, immutable receipts, and then run a sealed
equal-tools 2×2—is supported by the recorded evidence.

## Post-correction verification

**Verification verdict: fail — one residual editorial inconsistency remains.**

I re-read the corrected reports and reran the offline validator. The first,
second, third, fourth, and sixth required corrections are now present:

- execution units are correctly stated as two adapter invocations per task ×
  access lane (six per aggregate lane; 12 overall), not physical HTTP requests;
- the execution erratum correctly says generic and specialist calls were
  sequential, while raw/replay share records only inside an access lane;
- the two rank ordinals are no longer presented as a rank improvement;
- post-hoc success is described as identifier/slug resolution, with the Europe
  PMC PMID-loss caveat; and
- the replication's claimed fresh configuration/cache isolation is explicitly
  marked as not independently attested by the saved receipt.

`results.json` was regenerated with the new validity fields and its self-hash
verifies; `python3 validate_audit.py` passes with result hash
`sha256:0d04a025bbb3695ff125c597c4879018c01a476999458ff6bb85b665e3a135b6`.

The fifth correction removed the unsupported F/D/B grade labels, but
[analysis.md](../analysis.md) still begins the next paragraph with “Those
grades are deliberately not a claim that generic web is better.” The sentence
now has no antecedent and falsely suggests grades remain. Replace it with
“These caveats do not imply that generic web is better,” or delete it. Once
that one residual sentence is fixed, the corrected claims layer passes with the
material limitations stated above.

## Final verification: PASS with material limitations

The residual “Those grades” sentence was corrected to “These caveats,” and no
F/D/B grade labels remain in [analysis.md](../analysis.md). I reran
`python3 validate_audit.py`; it passes with the corrected
`results.json` hash. The claims layer now passes, subject to the material
limitations and future-study requirements recorded throughout this audit.
