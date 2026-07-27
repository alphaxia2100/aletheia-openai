# Improving Aletheia as an agent-facing field surveyor

Research date: 2026-07-27  
Production baseline: `addfaf6` / `aletheia-research 0.5.0-openai.1`  
Self-survey: six source-separated branches, 34 engine-recognized reads, 668 deduplicated retrieved
records, plus direct/manual primary recovery recorded in node artifacts

## Bottom line

Aletheia 0.5 is a strong experimental production baseline, not a finished research system. Its most
valuable design choices should remain: source-separated competing framings; a deliberately
overweighted adversary; primary-source chasing; structural origin clustering; read-only parallel
breadth with one synthesizer; durable file artifacts; explicit channel health; and whole-brief
verification with an independent coverage pass.

The user's output diagnosis is real, but the adversary is also right: **output hierarchy is not the
main epistemic bottleneck**. The evidence-supported priority order is:

1. retrieval recall, query formulation, topic-relative source selection, and primary resolution;
2. complete final-answer claim coverage, including inferential/normative/forecast claims;
3. semantic read integrity and claim-addressed context assembly;
4. task-aware orchestration rather than tree-by-default;
5. observable stopping, cost integrity, and diminishing-value control;
6. claim-specific origin independence and contradiction structure;
7. output navigation and progressive disclosure.

The first isolated output experiment nevertheless succeeded at its intended mechanism. The
production handoff jumped from a short brief to a flat raw bundle. The candidate field dossier keeps
one shallow map, embeds every branch synthesis, previews material decisions, and content-addresses
all raw artifacts. On same-run checks it reduced entry size by 96.97% and 98.45% while preserving all
51/280 artifacts and all 3/7 branch syntheses. A fresh-agent diagnostic recovered 7/7 requested facts
from the dossier tree versus 6/7 from the flat bundle; the missing flat-bundle item was an exact
rejected-path rationale because production falsely called its bundle complete while omitting
`decisions.jsonl`.

That is a useful experimental win, not a reason to promote the branch. Aletheia still accepted wrong
documents as successful reads during this self-survey, and prior high-accuracy work still allowed an
unsupported headline outside its claim ledger. Better navigation cannot repair evidence that never
arrived, arrived under the wrong identity, or escaped the verification denominator.

## 1. What production already gets right

### Anti-anchoring is structural, not rhetorical

The portfolio creates source-separated consensus, heterodox, practitioner, orthogonal, and adversary
branches before search. That is stronger than asking one model to “consider alternatives.” It should
remain, but the initial portfolio must be treated as a revisable prior rather than a permanent
taxonomy.

### Parallel breadth is constrained to its safer role

Workers investigate independent branches and write artifacts; one orchestrator reconciles provenance
and authors the synthesis. This matches the conditional external evidence. A controlled study across
260 configurations found multi-agent performance from **+80.8%** on decomposable financial reasoning
to **−70.0%** on sequential planning, with independent teams amplifying trace errors more than
centralized coordination ([Google/MIT study](https://arxiv.org/abs/2512.08296)). An equal-token study
found a single agent best or tied at usable budgets on two multi-hop tasks
([Tran and Kiela 2026](https://arxiv.org/abs/2604.02460)). Anthropic's internal research system is the
important positive boundary: it reports a 90.2% breadth-oriented win, but about 15× chat-token use and
poor fit for dependent/shared-context work
([Anthropic engineering report](https://www.anthropic.com/engineering/multi-agent-research-system)).

The supported rule is: parallelize high-entropy independent discovery; centralize dependent reasoning,
verification, and final synthesis.

### Durable artifacts and verification are real foundations

Runs survive context windows because questions, evidence, notes, findings, decisions, claims, and
verdicts persist on disk. The final-brief hash audit makes post-audit edits visible. Structural
origin clustering is stronger than domain counts. These are important invariants even though they do
not by themselves prove truth or claim completeness.

## 2. What the self-audit actually broke

| Failure | Direct observation | Consequence |
|---|---|---|
| Output compression cliff | 4.6 KB/72-line brief paired with a 950.9 KB/9,077-line bundle | Caller must trust a compressed answer or ingest raw evidence without a map |
| False “complete bundle” | Production `bundle()` omitted decisions, questions, answers, specs, status, and proposals | Ideas considered/rejected and stop rationales disappear from the handoff |
| Wrong-document read success | Two ACM DOI candidates persisted unrelated GRADE articles while `_read_ok=true` | A citation can point to a named paper the system never actually read |
| Length-only read gate | anti-bot, paywall, scanned-image, and wrong-page bodies could count as reads | Read counts and evidence availability are inflated |
| Router/category error | meta-research routed as a consumer-product topic | Relevant primary indexes can be silently omitted |
| Query-anchor pollution | focused named-method queries were prefixed with generic root terms | Exact retrieval degraded and irrelevant “agent/survey” material entered pools |
| Discovery/evidence conflation | primary papers found through web search inherited `lead_gen` class | Discovery path was confused with document epistemic role |
| Unobservable convergence | `unlimited` relies on agent-declared saturation without a recall estimator or true resource ceiling | Long runs can stop early or search indefinitely while claiming convergence |
| Claim-scope escape | prior auditors expanded 17→32 and 16→33 claims; one accuracy run's positive headline was outside the ledger | Perfect row-level precision can coexist with a wrong load-bearing conclusion |
| Run-level independence | headline origins are not attached to each claim | A survey may look diverse while its conclusion remains single-origin |

These are direct operational cases, not prevalence estimates. They are more useful than generic
benchmark scores because each identifies an executable failure path and a testable invariant.

## 3. Retrieval and evidence must be the first improvement plane

Changing retrieval alone can materially change final accuracy. On BrowseComp-Plus, switching GPT-5
from BM25 to Qwen3-Embedding-8B raised accuracy from **55.90% to 70.12%** while reducing mean search
calls from 23.23 to 21.74; reranking also produced large gains for GPT-4.1
([ACL 2026 paper](https://aclanthology.org/2026.acl-long.1023/)). A separate ranking study reports
passage BM25 at 0.572 accuracy and BM25→monoT5-3B at 0.689, with higher recall and fewer calls
([SIGIR 2026 paper](https://arxiv.org/abs/2602.21456)). FAIR-RAG's 200-case analysis assigned 32.5%
of failures to retrieval, 31.0% to generation after correct evidence, and 24.5% to its sufficiency
controller ([FAIR-RAG](https://arxiv.org/abs/2510.22344)). Retrieval is first, not sufficient.

The next retrieval line should isolate these mechanisms one at a time:

1. a small query portfolio by intent: direct answer, named entities/synonyms, decisive authority,
   dissent/contradiction, current status/version, and primary/citation-chain resolution;
2. query form matched to lexical versus dense indexes instead of one globally “improved” query;
3. passage-level reranking with the agent choosing sources from a persisted manifest;
4. backward/forward citation and author/dataset expansion after a generative source;
5. a resolver chain that records requested URL, resolved URL, expected identity, observed identity,
   method, completeness, and content hash;
6. source role separated from discovery channel (`document_type`, `epistemic_role`, `primary_of`,
   `discovered_via`).

Complex-review methodology supports adaptive expansion but warns against universalizing it. In one
495-source audit, only 30% of included sources came from the predefined protocol, while 51% came from
snowballing and 24% from contacts/personal knowledge
([Greenhalgh and Peacock 2005](https://doi.org/10.1136/bmj.38636.593461.68)). This is strong evidence
for recording productive discovery paths on complex topics, not a command to snowball every narrow
question.

## 4. Semantic read identity is the next clean engineering branch

The current gate effectively asks whether a fetched body is long enough. It does not prove that the
body is the candidate. In the interface branch, the candidate for `10.1145/3772318.3791101`
(`PaperTrail`) saved a 2011 GRADE inconsistency article with DOI `10.1016/j.jclinepi.2011.03.017`;
the candidate for `10.1145/3742413.3789079` saved a different 2023 GRADE article. Both were marked
successful and one was truncated. The worker caught the mismatch by reading the bodies; the runtime
did not.

A separate `codex/exp-read-identity-gate-v06` should make read success typed:

- `verified_identifier`: expected DOI/arXiv/PMID/registry ID occurs in trusted page metadata/body;
- `verified_title`: no strong ID, but normalized expected/observed titles match above a tested bound;
- `unverified_identity`: readable body with insufficient identity evidence; usable only with warning;
- `mismatch`: conflicting strong ID or decisive title mismatch; never counts as a successful read;
- `blocked|shell|image_only|truncated`: content-quality states distinct from identity.

The wrong body should remain persisted as an audit artifact, but `_read_ok` must be false, telemetry
must record the mismatch, and the resolver should try DOI/PMC/repository/HTML/PDF/OCR alternatives.
The branch needs exact reproductions of both observed mismatches plus false-positive controls for
pages with abbreviated titles, no metadata, and multiple cited DOIs. This mechanism should not be
combined with the dossier branch.

## 5. The epistemic state should be a typed claim/evidence graph

A URL appended to prose cannot express which span supports which part of a claim, whether the source
supports or contradicts, or whether several URLs share one underlying origin. The target intermediate
representation is:

```text
final sentence / headline
  → atomic factual | inferential | normative | forecast claim IDs
  → support / contradiction / qualification verdicts
  → exact immutable evidence spans
  → source snapshots and origin/derivation clusters
```

Each claim needs scope (population, time, place, intervention/exposure, outcome), polarity,
magnitude/units, uncertainty basis, supporting and disconfirming evidence, origin requirements,
dependencies, verifier, and supersession history. Inferential conclusions require supported premises
plus an explicit argument verdict; premise truth does not automatically validate the conclusion.

Evidence-synthesis methods support typed, context-relative disagreement rather than vote counting.
GRADE's inconsistency guidance distinguishes direction, magnitude, precision, and context and warns
that fixed heterogeneity thresholds are not interpretation
([2011 guidance](https://doi.org/10.1016/j.jclinepi.2011.03.017);
[2023 update](https://doi.org/10.1016/j.jclinepi.2023.03.003)). Review-overlap work likewise shows
why documents cannot be counted as independent information: double-counting primary studies can
magnify findings, and low overall overlap can hide concentrated duplication
([Pieper et al. 2014](https://doi.org/10.1016/j.jclinepi.2013.11.007);
[weighted CCA 2025](https://doi.org/10.1017/rsm.2025.19)).

The existing high-accuracy claim-ledger branch is therefore directionally right. Its first real run
also proved that a ledger is useless unless final prose is exactly reconciled to it. This should be
hardened and evaluated before inventing a second incompatible schema.

## 6. Research control should be a revision-capable graph with observable stop cards

The directory tree is a good navigation projection but a poor sole semantic model. Evidence creates
cross-branch dependencies, duplicate questions, merges, contradictions, refutations, and reopening
conditions. MindSearch represents search as a dynamically extended question DAG
([ICLR 2025](https://arxiv.org/abs/2407.20183)); Co-STORM updates a question-linked mind map as
information arrives ([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.554.pdf)). Both improve
organization/breadth but also retain factuality and source-quality limits.

The cautious target is a typed question graph projected back into legible directories. Allowed
actions include `refine`, `depends_on`, `contradicts`, `duplicate_of`, `merge`, `defer`, `refute`,
`reopen_if`, and `motivated_by_evidence`. A worker proposes changes; one orchestrator accepts/rejects
them under a monotonic resource ledger.

Stopping must be multi-signal and honestly uncertain. Booth identified eight plausible systematic-
search stopping approaches but found little comparative validation
([Booth 2010](https://doi.org/10.1017/S0266462310000966)). Aletheia should expose a stop card rather
than a bare `saturated` label:

- marginal new atomic claims;
- marginal new independent origins attached to important claims;
- conclusion stability under query/channel perturbation;
- a deliberately sought disconfirming case;
- known-landmark retrieval where applicable;
- unresolved high-value questions and next-round expected value;
- fresh alternate-channel probe followed by a later confirmation pass;
- elapsed/search/read/token caps and whether a cap, rather than convergence, stopped the branch.

No one signal certifies open-web completeness. The card records why the agent stopped and what could
reopen the branch.

## 7. Durable state and negative memory need typed provenance

The canonical control substrate should become an append-only event/evidence ledger, with current
Markdown/JSON files retained as projections. W3C PROV supplies a domain-neutral model of entities,
activities, agents, use, generation, and derivation ([PROV-DM](https://www.w3.org/TR/prov-dm/)).
OpenHands reports an immutable event-sourcing core with low persistence/replay overhead and materially
fewer system-attributable failures in a broader redesign
([MLSys 2026 paper](https://arxiv.org/abs/2511.03690)). Provenance explains lineage, not truth, so
claim verification remains separate.

Rejected paths should be structured negative-memory cards, not free-form lessons. Reflexion and ExpeL
show that retained experience can improve later performance, but ExpeL also reports that adding
plausible reflections hurt one HotPotQA setting, likely because reflections hallucinated
([Reflexion](https://arxiv.org/abs/2303.11366);
[ExpeL](https://arxiv.org/abs/2308.10144)). A negative card needs the attempted path, failure class,
evidence then available, confidence, raw trace, and explicit reopening trigger. A tool failure or
empty index result must never become a scientific null result.

## 8. Output should be progressive disclosure, not progressive amnesia

The field dossier experiment implements the narrower output claim that survives the adversary:

```text
L0  verified brief
L1  one shallow survey map + self-contained branch syntheses
L2  claims, contradictions, decisions, rejected paths
L3  evidence packs, source indexes, full reads, telemetry, execution state
```

Every summary is a view over retained evidence, not a replacement. HiAgent doubled average success
from 21% to 42% while reducing context tokens by 35.02%; removing on-demand trajectory retrieval
reduced success by 10%, direct evidence that summary-only memory is insufficient
([ACL 2025](https://aclanthology.org/2025.acl-long.1575.pdf)). WebWeaver's section-scoped writer raised
citation accuracy from 86.73% to 93.37% and support from 90.95% to 98.73% versus a whole-memory writer
([WebWeaver](https://arxiv.org/abs/2509.13312)). The mechanism is focused, addressable evidence—not
hierarchy for its own sake.

The strongest direct caution is a July 2026 long-context-agent study: a flat prepared index helped at
larger corpus scale, but a second always-loaded routing level often reduced accuracy, with some
large-corpus open-QA exceptions ([He et al. 2026](https://arxiv.org/pdf/2607.17598v1)). Therefore
Aletheia should keep one bounded map and make deeper material available on demand; it should not
preload a recursive routing tree into every caller.

## 9. Evaluation must test a field model, not a pleasant essay

The production evaluation history already contains two warnings: retrieval luck dominated a one-topic
bakeoff, and a dynamic-outline candidate preferred by judges used 97 persisted reads versus 41. A
scope auditor expanded 17 writer claims to 32. Generic preference, configured rounds, and perfect
precision on a self-selected denominator are not release gates.

The serious promotion protocol should use hidden, atomic criteria and downstream use:

1. 12 held-out topics across science, policy/legal, consumer, software, economics, and
   history/current events;
2. three isolated generator trials per arm/topic, interleaved in time;
3. same model/harness and hard observed envelope for tokens, searches, read attempts/artifacts,
   manual rereads, wall time, and output bytes;
4. expert-authored must-cover, nuance, provenance, and harmful-omission criteria frozen before runs;
5. fresh-agent QA, decision, counterfactual-update, contradiction, and exact-evidence-location tasks;
6. criterion-level binary graders with quoted evidence; human-calibrated judges;
7. exact AB+BA holistic judging only as a secondary diagnostic because order, verbosity, and
   self-preference biases are documented
   ([position-bias study](https://arxiv.org/abs/2305.17926);
   [MT-Bench](https://arxiv.org/abs/2306.05685);
   [self-preference study](https://arxiv.org/abs/2410.21819));
8. feature activation plus a feature-off ablation before crediting the mechanism;
9. topic-level paired intervals and an explicit `inconclusive` outcome.

The field-dossier diagnostic is intentionally smaller. It establishes that the artifact contract is
mechanically lossless-by-reference and recovered one omitted trace answer. It does not meet the
promotion protocol above.

## 10. Branch and experiment strategy

| Line | Base | Status | Promotion question |
|---|---|---|---|
| `prod` / `aletheia-prod-v0.5.0-openai.1` | `addfaf6` | stable baseline | unchanged until a candidate clears its gate |
| `codex/exp-field-dossier-v06` | prod | implemented; diagnostic passed; not promoted | does progressive disclosure improve repeated downstream use without evidence-use regression? |
| `codex/exp-read-identity-gate-v06` | prod | next isolated branch | does typed identity catch wrong bodies without rejecting valid difficult pages? |
| `codex/exp-claim-evidence-ledger-v06` | prod lineage | implemented invariant candidate | does it improve claim recall/support at matched reads? |
| `codex/accuracy-observability-v06` | accuracy line | implemented hardening; not prod | can complete real runs replay and reconcile every final claim? |
| adaptive query/reranking line | prod | proposed | decisive-primary/must-cover gain at equal retrieval/read cost? |
| adaptive question-DAG line | best evidence plane | proposed later | finds evidence-created questions without uncontrolled read amplification? |
| stop-card controller line | best evidence plane | proposed later | lower cost/tail failures without missing rare decisive evidence? |

One mechanism per branch is not bureaucracy; it is how the project avoids attributing a longer run or
unrelated fix to the latest architectural idea. Failed and inconclusive branches remain as provenance,
not clutter to rewrite.

## 11. Experimental ideas worth preserving

### Epistemic compiler

Treat research artifacts as a typed intermediate representation. Retrieval produces source
snapshots; extraction produces evidence spans; synthesis compiles spans into atomic claims; a type
checker rejects missing scope/polarity/units/time/origin; a linker resolves every final sentence to
claim IDs; the dossier is one materialized view. This makes prose the output of epistemic state,
instead of prose being the state.

### Claim influence and echo maps

Measure not only how many origins exist, but how much of the final decision depends on each origin,
dataset, author group, institution, or press-release lineage. A single regulator can legitimately be
decisive; the map should show that concentration rather than calling it hidden “agreement.”

### Counterfactual dossier queries

Let a caller ask: “If source S is withdrawn, which claims and recommendation change?”, “Which gaps
block a stronger conclusion?”, or “What new evidence would reopen this branch?” This tests whether
provenance is operational rather than archival.

### Compression-loss audits

After each branch/root summary, a fresh verifier compares its claim IDs with inputs and flags omitted
minority evidence, changed polarity, missing numeric qualifiers, and lost reopening conditions.
Summary coverage becomes observable without making raw context permanent.

### Calibrated exploration portfolios

Allocate some search effort to exploitation (highest-value known gap), some to challenge (strongest
disconfirmation), and a small, explicit fraction to alternate-channel novelty. Measure marginal
verified-claim/origin yield rather than asking the agent for an unexplained confidence scalar.

## 12. Ideas rejected or explicitly downgraded

- **More hierarchy as the main fix:** rejected. Hierarchy helps breadth and navigation only when task
  structure and focused context warrant it.
- **More sources or longer reports as quality:** rejected. More retrieval can degrade output, and
  repeated reviews/URLs can be one origin.
- **Full bundle as the agent default:** rejected. Preserve everything; inject selectively.
- **One run-wide independence score as corroboration:** downgraded. Independence must attach to claims.
- **Unbounded “saturation” as completeness:** rejected as a guarantee. It remains a judgment recorded
  alongside residual gaps and hard caps.
- **Free-form confidence as a stop gate:** rejected. Confidence cannot convert unsupported evidence
  into support.
- **Autonomous self-editing against a visible evaluator:** rejected for production. Keep human-gated,
  one-change, hidden-set experiments because reward hacking and topic leakage are predictable.
- **Dumping private chain-of-thought for transparency:** rejected. Persist observable decisions,
  alternatives, evidence, actions, and outcomes; do not require hidden reasoning traces.

## Agreement, disagreement, unverified, and gaps

### Agreement

Independent method, architecture, practitioner, and interface branches converge on the same core:
durable typed evidence; exact provenance; selective context; primary resolution; explicit failure and
gap state; centralized reconciliation; and layered output. The dossier is a useful view over that
state, not the state itself.

### Disagreement

The hierarchy-positive case (Anthropic, MindSearch, STORM/Co-STORM, WebWeaver, HiAgent) is real but
conditional. The strongest negative/matched-compute evidence shows architecture-task alignment and
focused context matter more than agent/tree count. The synthesis is not “single agent always” or
“tree always”; it is **parallelize independent discovery, keep dependent reasoning coherent, and
make expansion earn its cost**.

### Unverified

- No controlled primary study directly tests an agent consuming a layered field-survey dossier
  versus a flat bundle across domains.
- No validated ontology resolves every open-domain document to an underlying independent origin.
- No open-web stopping policy has a reliable recall guarantee.
- No integrated experiment validates the complete proposed evidence/control/delivery architecture.
- The exact dossier schema and read-identity thresholds remain engineering hypotheses.

### Gaps

Brave was degraded for the entire survey, removing one independent web index. GitHub was live but
unauthenticated and intermittently rate-limited; arXiv also entered transient cooldowns. The methods
branches relied heavily on academic/technical sources and under-sampled non-English evidence, books,
newsrooms, domain specialists, and user organizations. Many deep-research studies are author-run,
small, and LLM-judged. Several design transfers come from biomedical systematic review or software
agents rather than direct open-domain field-survey trials. Those limitations are reasons to run the
specified experiments, not reasons to hide the uncertainty.

## Final recommendation

Keep `prod` pinned. Preserve the field dossier on its own branch as a successful first mechanism
diagnostic, not a release. Build and test the semantic read-identity gate next. Then harden and
evaluate the existing claim/evidence ledger, followed by retrieval/reranking and only later an
adaptive question graph and stop controller. Every branch should ship its hypothesis, activation
trace, exact observed cost, result, falsifier, and reason for promotion/rejection.

That path gives Aletheia wider reach without mistaking breadth for truth, richer output without
forcing the caller to ingest everything, and memory without rewriting failures into mythology.
