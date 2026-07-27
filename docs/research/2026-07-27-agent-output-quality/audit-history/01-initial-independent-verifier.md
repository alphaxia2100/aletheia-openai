# Independent fresh-context verification report

Verifier: fresh-context Codex subagent (`/root/fresh_verifier`)  
Run: `2026-07-27-101249-aletheia-output-quality-20260727`  
Date: 2026-07-27

## Result

The current 55-row claim ledger is not ready to attest the final brief. I assigned 45 existing rows
`supported` and 10 `unsupported`; none was directly contradicted by its declared source. I found 29
additional load-bearing claims in the final brief that were absent from `claims.jsonl`: 14 are
supported and 15 are unsupported as currently worded. A reconciled 84-claim scope would therefore
contain 59 supported and 25 unsupported claims before any edits or source repairs.

The largest problem is not ordinary factual error. It is that engineering hypotheses, priority
judgments, universal absence claims, and cross-domain transfers are repeatedly described as if the
cited studies established them. The brief's central priority order is not empirically compared, and
the final recommendation gives a different immediate order.

| Scope | Supported | Contradicted | Unsupported | Total |
|---|---:|---:|---:|---:|
| Existing `claims.jsonl` | 45 | 0 | 10 | 55 |
| Omitted load-bearing claims | 14 | 0 | 15 | 29 |
| Reconciled proposal | 59 | 0 | 25 | 84 |

## Coverage method

I read all 400 lines of the final `brief.md`, all 55 exact `claims.jsonl` rows, and all 55 lexical
leads in `verify.jsonl`. I treated lexical overlap only as a locator. For each claim I mapped the
declared URL to the persisted note under `tree/root`, read the relevant full or decisive artifact,
and checked scope, polarity, magnitude, units, task population, and whether an inferential or
normative conclusion followed. This included the full/decisive captures for the agent-scaling,
equal-token, BrowseComp-Plus, ranking, FAIR-RAG, WebWeaver, long-context, GRADE, overlap, stopping,
MindSearch, Co-STORM, PROV, OpenHands, Reflexion, ExpeL, HiAgent, and judge-bias sources, plus the
complete internal operational note. I also read the cited field-dossier experiment record from its
exact Git commit to verify the fixture denominators.

I then compared every paragraph, table row, numbered recommendation, agreement/disagreement
statement, gap, rejection, and final recommendation against the 55-claim set. I added only claims
that materially support a diagnosis, architecture choice, promotion rule, priority, gap, or final
recommendation; illustrative prose and explicitly labeled brainstorms were not treated as
load-bearing. I did not run `report.py audit-claims`, and I did not modify `brief.md`, `claims.jsonl`,
or `verify.jsonl`.

## Existing-claim weaknesses

### Source-scope mismatches

- Claim 1 cites the internal run note for parallel read-only workers and centralized synthesis. The
  note proves the six-child tree but does not document those execution semantics. Cite the production
  specification or code and split the claim.
- Claim 25's exact eight-state read taxonomy goes beyond the observed mismatch, anti-bot, and
  truncation cases. The need to separate identity from readability is supported; the exact taxonomy
  is a candidate schema.
- Claim 28 cites the captured 2014 Pieper article for the proposition that double-counting magnifies
  findings. The persisted artifact's body is only an abstract and does not make that claim. The exact
  sentence appears in the declared 2025 wCCA source used by claim 29.
- Claim 34 moves from Booth's eight weakly evaluated HTA stopping approaches to a universal statement
  about what can never certify open-web recall. That inference is not established.
- Claim 44 generalizes a book-QA routing experiment and a two-agent internal diagnostic into a field-
  survey delivery policy. The July 2026 paper explicitly says routing depth is task- and scale-
  specific and reports large-corpus open-QA exceptions.
- Claim 50 combines evidence-backed cost matching and order balancing with unvalidated project design
  choices such as the exact topic count, repeats, downstream tasks, activation checks, paired
  intervals, and hidden criteria.
- Claim 51 says one mechanism per branch is *necessary*. Isolation is a defensible convention, but
  factorial and explicit ablation designs can also identify multiple mechanisms.
- Claims 52 and 53 are universal or survey-level absence claims. The run has a degraded independent
  web channel and no persisted targeted search audit for the dossier-comparison or origin-ontology
  absences. They can only be reported as sources not located in this run.
- Claim 55's seven-plane priority order is engineering judgment. The sources establish individual
  failures and mechanism effects, not their comparative expected value or urgency.

### Compound and inferential rows

Several multi-source rows are not atomic enough for one URL and one verdict. Claims 19, 26, 34, 44,
50, 53, and 55 combine empirical premises with an engineering conclusion. Claim 19 survives because
its conclusion is tightly scoped to the tested decomposable-versus-sequential distinction. Claims
34, 44, 50, 53, and 55 do not. Future ledgers should separate the empirical premise, transfer
assumption, and normative decision.

### Absence and independence language

The brief correctly warns that run-wide independence does not attach origins to claims, then later
says four branches “independently converge.” Source-separated branches are not necessarily
independent origins, and thematic recurrence is not claim-level corroboration. Likewise, “found no”
and “identified neither” are too strong without a targeted search protocol and intact channel
coverage.

## Important omitted claims

The 29 atomic additions are in `independent-verifier-additions.jsonl`. The most consequential are:

- the omitted 34-read/668-URL run counters and their identity-mismatch qualification;
- the exact field-dossier coverage denominators (51/51, 280/280, 3/3, and 7/7);
- the uncited 4.6 KB/72-line versus 950.9 KB/9,077-line compression example;
- the 1,952-character anti-bot page counted as a successful read;
- the 512-node backstop, which conflicts with the table's suggestion of literal indefinite search;
- the read-identity invariant that a strong identifier mismatch must make read success false;
- the query-format result showing why lexical and neural indexes should receive different forms;
- the unvalidated resolver, claim-graph, question-graph, event-ledger, and negative-memory schemas;
- the missing distinction between provenance lineage and truth;
- the claim-level-independence limitation;
- the unsupported branch-convergence and sampling-gap assertions;
- the unvalidated complete-architecture absence claim; and
- the final identity→ledger→retrieval priority order, which conflicts with the opening
  retrieval→coverage→identity order.

## Exact recommended brief edits

These edits are required before a final claim audit. They are proposals only; this verifier did not
apply them.

1. Replace “The evidence-supported priority order is:” with:

   > The evidence below identifies three first-plane defects but does not compare their expected
   > value. Combining those results with local risk and implementation judgment, the proposed
   > project order is:

   If the final recommendation is intended to govern, reorder the first three items to **semantic
   read identity and primary resolution; whole-answer claim coverage; retrieval/query/reranking**.
   Otherwise change the final recommendation to follow retrieval→coverage→identity. Use one order.

2. In the operational-failure table, replace the output-compression row's unsupported four-number
   example with the reproducible experiment values:

   > Narrow same-run fixture: 950,921-byte production bundle versus 28,782-byte dossier; the cited
   > record reports 51/51 manifest artifacts and 3/3 branch syntheses preserved.

3. Replace the length-only-gate observation with the supported scope:

   > A 1,952-character anti-bot page and two wrong-document bodies counted as successful reads;
   > truncation was tracked separately in one mismatch.

   Remove “paywall” and “scanned-image” unless exact persisted cases are cited.

4. Replace the unobservable-convergence consequence with:

   > Without a recall estimator, an unlimited run can stop early or consume substantial resources
   > before hitting the 512-node runaway backstop; the cap is not evidence of convergence.

5. Change the opening of the read-integrity taxonomy from “should make read success typed” to:

   > A separate read-identity branch should test the following candidate state taxonomy:

   Keep the two strong-identifier mismatch reproductions as established facts; label title thresholds,
   shell detection, image-only detection, and retry policy as hypotheses and test conditions.

6. Repair the overlap citation. Replace the sentence beginning “Review-overlap work likewise shows”
   with:

   > The 2025 wCCA paper states that double-counting primary studies can magnify findings and skew
   > conclusions, while the 2014 Pieper study establishes that overlap is common and often
   > unreported.

   Cite the wCCA URL for the first clause and Pieper for the second.

7. Replace “No one signal certifies open-web completeness” with:

   > No signal in the sources reviewed here has been validated as an open-web completeness
   > certificate. The following stop card is a proposed observability contract, not a recall proof.

8. Replace the field-dossier transfer conclusion with:

   > The book-QA study and this project's two-fixture diagnostic motivate testing one bounded map
   > with deeper artifacts on demand. They do not establish that design across field-survey domains,
   > and the book-QA appendix reports task-specific hierarchical exceptions.

9. Split the promotion protocol into evidence and policy:

   > Prior project comparisons require observed cost matching, and judge-bias studies require
   > order-balanced evaluation. The remaining hidden criteria, topic mix, repeat count, downstream
   > tasks, activation checks, paired intervals, and explicit inconclusive rule are proposed project
   > gates to validate.

10. Replace “One mechanism per branch is not bureaucracy; it is how...” with:

    > One mechanism per branch is this project's default attribution discipline. A multi-mechanism
    > branch is acceptable only with a prespecified factorial or feature-off ablation that identifies
    > each effect.

11. Replace the two survey-level absence bullets with:

    > Among sources successfully retrieved in this run, we did not locate a controlled cross-domain
    > layered-dossier-versus-flat-bundle study.

    > Among sources successfully retrieved in this run, we did not locate a validated universal
    > open-domain origin ontology or an open-web stopping policy with a demonstrated recall guarantee.

    Retain the Brave degradation immediately beside these statements.

12. Replace “Independent method, architecture, practitioner, and interface branches converge” with:

    > Several source-separated branches recur on the same design themes. This is thematic
    > convergence, not claim-level independent corroboration; origins were not attached to each
    > conclusion in this run.

13. Replace the broad sampling-gap sentence with:

    > The retrieved artifact set is academically and technically concentrated. This run did not
    > quantify language, book, newsroom, domain-specialist, or user-organization coverage.

14. Change “Many deep-research studies are author-run, small, and LLM-judged” to a counted statement
    after adding a study inventory. Until then use:

    > Several cited evaluations are author-run or LLM-judged; this brief does not quantify their
    > prevalence across the retrieved corpus.

15. Add a citation or reproduction for “The final-brief hash audit makes post-audit edits visible.”
    The current internal observation note does not establish that product behavior.

16. Preserve the final recommendation to keep `prod` pinned and the dossier experimental, but preface
    the implementation sequence with “risk-based project judgment” and make it match the single
    priority order chosen in edit 1.

## Final disposition

Do not attest or score the current brief against the current 55-row ledger. First apply the source
repair and wording changes above, add the supported omitted claims, either remove or explicitly label
the unsupported claims as hypotheses/policies/unverified absences, regenerate the complete atomic
claim ledger, rerun source verification, and then perform a new fresh-context coverage pass before
calling `report.py audit-claims`.
