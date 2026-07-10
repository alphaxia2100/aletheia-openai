# OpenAI Aletheia 0.5 forward-test record

Date: 2026-07-10  
Candidate branch: `codex/openai-aletheia-v05`  
Pinned baseline: `aletheia-research-v0.4.3` (`70f7a43`)

## Research decision

A full Aletheia survey of deep-aletheia, Bilevel Autoresearch, ranking research, and recent deep-research
systems verified 12/12 load-bearing claims. It did **not** support copying Bilevel Autoresearch's runtime
self-editing: its committed Group C driver uses `simple_mode=True`, which bypasses the generated Level-2
mechanisms. The transferable ideas were experimental discipline—full traces, behavioral activation
checks, held-out gates, cost matching, and rollback—and evidence-conditioned outline evolution as a
hypothesis requiring its own test.

## Accepted: capped topic-relative source triage

### Consumer forward test

Topic: long-term reliability of countertop tank dishwashers for a renter.

- Candidate: eight reads, including exact manuals, owner repair accounts, and OEM parts catalogs.
- Baseline: seven reads, mostly unrelated plumbing threads, affiliate material, and one marketplace listing.
- Two blind judges saw reversed A/B order; both preferred the candidate at 0.98 confidence.
- A candidate warranty-extension assertion was omitted from `claims.jsonl` despite a 1.0 score. This
  defect directly motivated the final-brief scope gate; the assertion is not counted as a clean pass.

### Biomedical no-regression test

Topic: oral magnesium for idiopathic nocturnal leg cramps in nonpregnant adults.

- Baseline engine passes: three. Capped candidate: three manifests, zero requeries, six successful reads.
- The candidate recovered the current Cochrane synthesis, primary RCTs, NIH safety guidance, and a
  registry-only attribution problem: the positive 60-day product contained magnesium plus vitamins E
  and B6, although the paper described it as magnesium oxide monohydrate.
- A fresh scope verifier expanded 17 writer-selected claims to 32; all 32 received final supported
  verdicts. Citation accuracy and coverage were 1.0, and the artifact-hash audit was valid.
- Two fresh blind judges saw reversed order and both preferred the capped candidate (confidence 0.78
  and 0.77), primarily for its cleaner primary-source hierarchy and intervention attribution.

Interpretation: two topics support mechanism-level promotion and science no-regression. They do not
estimate general win rate; a larger frozen candidate benchmark remains desirable.

## Rejected for now: evidence-conditioned dynamic outlines

Topic: sodium-ion versus LFP for a U.S. four-hour utility project entering service in 2028–2030.

- Baseline: two broad leaves × four rounds = eight scrutiny rounds.
- Candidate: three parent rounds plus five evidence-earned child rounds = eight scrutiny rounds.
- Behavioral activation passed: the candidate produced two post-evidence proposals and five level-2
  questions; its budgeted split conserved only unspent budget, fixing the initial scout double-spend.
- Cost audit failed: baseline persisted 41 read artifacts (6 engine-tracked, 35 direct/manual); candidate
  persisted 97 (13 engine-tracked, 84 direct/manual). The candidate therefore used 2.37× the observed
  read artifacts despite equal configured rounds.

The dynamic mechanism may improve structure and quality, but this run cannot establish an efficient
win. It stays experimental until linked-primary reads are enforceably budgeted and a new blind,
cost-matched trial passes. The release adds artifact-level read accounting so this failure cannot hide
behind round telemetry again.

## Channel and evidence limitations

Brave was degraded throughout because no API key was configured. Healthy DuckDuckGo and Marginalia
served the same role, but losing an independent web index remains a coverage gap. The consumer and
science results are small-N and model-judged; decisive citations were separately inspected, but no
human-calibrated multi-topic benchmark yet exists.
