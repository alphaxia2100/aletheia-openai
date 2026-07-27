# Reader/caller interface: progressive disclosure without transcript spelunking

## Bottom line

Aletheia should preserve the whole research record but stop treating “agent output” as “inject the
whole bundle.” The better contract is a small, stable **research map** that routes a caller into
self-contained branch syntheses, then into atomic claim/evidence records, then into full primary
reads and process traces. Logical depth can be rich; *always-loaded routing depth* should stay
shallow. The map is a control surface for coverage, disagreement, uncertainty, and navigation—not a
shortened final answer and not a table of raw worker transcripts.

A useful artifact shape is:

```text
MAP.md / manifest.json                always read: scope, branch map, tensions, gaps, entry points
branches/<branch>/findings.md         one self-contained synthesis per question/mechanism
claims/<claim-id>.json                atomic claim, status, scope, evidence links, counterevidence
evidence/<evidence-id>.json           exact supporting span + primary/source/read provenance
decisions/<decision-id>.json          material choice, alternatives, why, revisit trigger
reads/<source-id>/{full.md,meta.json} full primary read and read-integrity metadata
traces/...                            execution/worker transcript, available but never default-loaded
```

The layers are views over linked research state, not lossy stages that replace one another. A caller
should be able to move both downward (“show evidence for C17”) and sideways (“show every branch that
depends on source S4” or “all unresolved contradictions”) without opening worker transcripts.

## Claim 1 — Use one compact routing map; do not assume that more routing hierarchy is better

The strongest direct agent evidence supports progressive disclosure as a *context-scaling* device,
but rejects a universal “deeper tree is better” rule. In a controlled long-document agent study,
one flat indexed skill helped when native navigation was weak and at larger corpus scale, while an
extra always-loaded routing layer often cost accuracy. The paper reports a Pi/gpt-5.4-mini En.MC drop
from **0.9126 flat to 0.6398 hierarchical** and, for Codex English open QA at 20 books, **0.257 raw vs
0.462 flat**. Its own appendix also complicates the headline: on some large-corpus open-QA cells the
hierarchical variant recovered or led, so depth is task-, language-, harness-, and scale-dependent.
That internal tension argues for an adaptive interface and held-out A/Bs, not a fixed three-layer
dogma.

- Primary preprint, engine class `lead_gen`: [He et al., *Is Progressive Disclosure All You Need for
  Long-Context Agents?*](https://arxiv.org/pdf/2607.17598v1). Short quote: “Progressive disclosure
  buys context, not intelligence.” Main-text quote: “A second, deeper routing level never helps and
  sometimes breaks accuracy”; appendix counterexample: “Where the corpus is large and the questions
  are open, the extra routing level ... recovers.”
- Primary conference paper, author-hosted PDF, engine class `lead_gen`: [Shneiderman, *The Eyes Have
  It*](https://www.cs.umd.edu/~ben/papers/Shneiderman1996eyes.pdf). Short quote: “Overview, zoom,
  filter, details-on-demand, relate, history, and extract.”
- Primary ACM paper, abstract read, engine class `lead_gen`: [Suh et al.,
  *Sensecape*](https://dl.acm.org/doi/10.1145/3586183.3606756). Short quote: the system lets users
  “manage the complexity of information through multilevel abstraction”; its within-subject study
  reports that users explored more topics and structured knowledge hierarchically.

**Corroboration:** three independent origins agree that overview-to-detail navigation is useful.
Only He et al. directly tests agent file/package depth, and it is a July 2026 preprint with a narrow
book-QA setting. Sensecape is human-facing and only its abstract was readable here.

**Design consequence:** make `MAP.md` one bounded index whose entries contain discriminating routing
metadata and direct links. It may link to arbitrarily deep evidence, but it should not preload every
child description. Keep raw reads grep-able so a strong navigator can bypass the prepared route.

## Claim 2 — The map must expose coverage and relationships, not merely compress prose

Foundational sensemaking work separates raw sources, selected material, extracted evidence, schemas,
hypotheses, and presentation. Those are different epistemic objects. Collapsing them into one summary
destroys the caller's ability to see what was searched, what was omitted, how evidence was organized,
and where a conclusion came from. HINTs supplies a modern working-system analogue: in its comparative
study, a linear chatbot caused participants to lose track of subtopics, whereas a hierarchical corpus
representation provided persistent anchors and next actions.

- Primary cognitive-task-analysis paper (mirror of the conference paper), engine class `lead_gen`:
  [Pirolli & Card, *The Sensemaking Process and Leverage Points for Analyst
  Technology*](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf).
  Short quote: “Information → Schema → Insight → Product.” More specifically, their data flow is
  “external data sources” → “shoebox” → “evidence file” → “schemas” → “hypotheses” → presentation.
- Primary arXiv/visual-analytics paper, engine class `lead_gen`: [Chen et al.,
  *HINTs*](https://arxiv.org/html/2403.02752v2). Short quote: “sensemaking is not linear, but
  hierarchical”; the baseline's “linear conversation ... diverges from the participants' mental
  model,” while the graphical representation helped them keep track of current status and expected
  next actions.

**Corroboration:** the sources are independent and span cognitive task analysis and a working LLM
corpus-analysis system. HINTs used only 12 visualization graduate students (six per condition), and
expert-rated breadth and accuracy did **not** significantly differ; its strongest evidence is about
orientation, behavior, and calibration rather than superior answer accuracy.

**Design consequence:** each map entry should minimally expose: branch question; scope; state
(`unsearched|active|saturated|blocked`); one-sentence contribution; decisive source; evidence-origin
count; strongest counterclaim; open gap; and links to the branch synthesis. The root should also show
cross-branch dependencies and overlap, not just a folder tree. Branch syntheses should be
self-contained intermediate representations—mechanism, agreement, disagreement, boundary
conditions, unknowns—so opening one branch does not require reconstructing worker context.

## Claim 3 — Claims and evidence need a first-class, bidirectional data model

A citation URL at the end of a paragraph is too weak for an agent-facing research object. The caller
needs to ask which exact span supports a claim, which claims depend on a source, whether the evidence
supports or disconfirms, and what scope or conditions limit the inference. Pirolli and Card explicitly
describe an evidence file as extracted nuggets used to support or disconfirm hypotheses. HINTs
participants requested the same affordance in modern form: referenced documents should be shown in
the agent response and linked back to the corpus view.

- Primary cognitive-task-analysis paper, engine class `lead_gen`: [Pirolli & Card
  2005](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf).
  Short quote: the evidence file contains “snippets extracted from items in the shoebox”; read and
  extract produces nuggets “used to draw inferences, or support or disconfirm theory.”
- Primary arXiv/visual-analytics paper, engine class `lead_gen`: [HINTs](https://arxiv.org/html/2403.02752v2).
  Short quote from participant-derived requirements: “show the referenced documents in the agent's
  response and link them back to the visualizations.”

**Corroboration:** two independent sources support linked evidence objects, but this run did not
secure a valid read of the most directly relevant 2026 `PaperTrail` claim-evidence study (see Claim
7). Quantitative benefits of a specific JSON schema therefore remain unverified.

**Design consequence:** a claim record should include `claim_id`, normalized claim text, scope and
date, `status` (`supported|contradicted|mixed|single_origin|unverified`), confidence basis (not an
unexplained scalar), supporting and disconfirming evidence IDs, independent-origin count, branch
dependencies, verifier verdict, and supersession history. An evidence record should contain the
primary URL, exact quote/span locator, source class, origin/derivation cluster, requested and resolved
URL, read completeness, and content hash. Synthesis files should be generated or audited against this
graph rather than becoming the sole source of truth.

## Claim 4 — Surface disagreement and uncertainty selectively; never use visible consensus as a proxy for truth

Disagreement, critique, and consensus are valuable navigation signals, but they are also persuasive
interface cues that can miscalibrate trust. A qualitative multi-agent interface study found that
participants used agent count and consensus as reliability heuristics even when those cues need not
track actual accuracy. Participants wanted “contextually sufficient” transparency: enough dissent or
rationale for the current task, with deeper process available on request, not all deliberation shown
by default. HINTs adds a useful counterpoint: the plain-chatbot group felt more successful even though
expert-rated breadth/accuracy did not differ; the visual group saw more unexplored material and thus
felt less complete and more time pressure. A good interface may initially lower confidence because it
reveals uncertainty that fluent prose hides.

- Primary ACM paper, partial full-text read, engine class `lead_gen`: [*Sensemaking in Multi-Agent LLM
  Interfaces*](https://dl.acm.org/doi/10.1145/3772318.3791157). Short quote: users “appreciate signals
  of internal system deliberation ... but do not want to sift through all the deliberation.” The
  authors recast transparency as “sufficiency, not volume.”
- Primary arXiv paper, engine class `lead_gen`: [HINTs](https://arxiv.org/html/2403.02752v2). Short
  quote: the baseline group showed “over-confidence”; HINTs participants' lower confidence reflected
  “awareness of the incompleteness of the outline.”

**Corroboration:** two independent qualitative studies converge on the difference between apparent
fluency/consensus and epistemic calibration. The multi-agent paper is exploratory Comparative
Structured Observation, not an effect-size study; the local read was truncated during its methods.
HINTs is small and domain-specialized.

**Design consequence:** the root map should show only the few load-bearing unresolved tensions and
their decision relevance. Branch pages should preserve both sides, conditions under which each may
hold, and links to evidence matrices. Atomic claims carry `mixed`/`contradicted`/`single_origin`
states. Raw debate belongs lower in the tree. Never label multi-agent agreement as corroboration
unless the cited evidence traces to independent origins.

## Claim 5 — Keep an epistemic decision ledger distinct from the execution transcript

Research is iterative and reversible. The caller needs the *material* history—why a branch was
opened, why a source or interpretation was rejected, what alternative was considered, and what new
evidence would reopen it—not every tool call or token. Both classic interface guidance and the
sensemaking model identify history and backtracking as core, not optional, because new hypotheses
send analysts back to prior evidence and searches.

- Primary conference paper, engine class `lead_gen`: [Shneiderman
  1996](https://www.cs.umd.edu/~ben/papers/Shneiderman1996eyes.pdf). Short quote: “Keep a history of
  actions to support undo, replay, and progressive refinement”; “information exploration is
  inherently a process with many steps.”
- Primary cognitive-task-analysis paper, engine class `lead_gen`: [Pirolli & Card
  2005](https://andymatuschak.org/files/papers/Pirolli,%20Card%20-%202005%20-%20The%20sensemaking%20process%20and%20leverage%20points%20for%20analyst%20technology%20as.pdf).
  Short quote: the process has “lots of back loops”; re-evaluation may require alternative theories,
  additional evidence, and renewed search.

**Corroboration:** independent foundational sources agree on history/reversibility. Neither directly
tests an LLM-agent decision-ledger schema; the field-to-agent transfer is a design inference.

**Design consequence:** keep two linked traces. `decisions/` contains concise epistemic events:
decision, alternatives, selected/rejected status, rationale, evidence IDs, actor/time, downstream
effect, and revisit trigger. `traces/` contains reproducibility telemetry and worker execution. Root
and branch syntheses expose a short “key decisions / rejected paths” digest with links; they do not
inline transcripts. This prevents repeated dead ends while keeping prompt-injection-tainted or
low-level trace text out of the default context.

## Claim 6 — Make disclosure adaptive to the downstream task and harness

A fixed `verbosity: agent => full bundle` policy ignores that calling agents also have finite context
and heterogeneous navigation ability. The direct benchmark finds that a strong Codex navigator gains
little from a prepared index on one book but benefits when the corpus grows; weaker harnesses benefit
earlier. The multi-agent interface study likewise finds that desired transparency changes with task
complexity, expertise, and current information need. Therefore, preservation and delivery must be
separate: always persist everything, but hand back an entry point plus queryable depth.

- Primary preprint, engine class `lead_gen`: [He et al.
  2026](https://arxiv.org/pdf/2607.17598v1). Short quote: the gain is “harness-dependent”; under the
  strong harness the raw agent “reconstructs on the fly the locate-then-read capability.”
- Primary qualitative ACM paper, engine class `lead_gen`: [*Sensemaking in Multi-Agent LLM
  Interfaces*](https://dl.acm.org/doi/10.1145/3772318.3791157). Short quote: ideal transparency was
  “dynamic and context-sensitive,” and participants wanted collapsible deeper transparency “when
  needed.”
- Practitioner implementation, engine class `lead_gen`: [Groktopus, *The Artifact
  Pyramid*](https://www.groktop.us/artifact-pyramid-progressive-disclosure/). Short quote: “A
  single-page summary ... analysis files ... supporting dossiers”; each layer links to the next.

**Corroboration:** direct agent benchmark + human HCI study + working implementation align on
selective loading. The practitioner system reports no controlled outcome evaluation, and the direct
benchmark's fixed book-chunk recipe may not transfer to field surveys.

**Design consequence:** the return contract should provide the map plus operations such as `open
branch`, `show claims --status mixed`, `why <decision>`, `sources <claim>`, and `open full-read`. A
caller may request a complete archive, but “bundle” should mean a persisted addressable artifact, not
automatic context injection. Evaluate the policy on downstream research/decision tasks at equal read
and token cost; stratify by harness and corpus scale.

## Claim 7 — Read integrity and completeness must be visible at every layer

This leaf exposed a concrete provenance failure. Candidate metadata and `sources.jsonl` labeled two
records as the directly relevant papers `PaperTrail: A Claim-Evidence Interface...` and `From Toil to
Thought...`, and the runtime marked their reads successful. The persisted bodies were unrelated GRADE
articles about inconsistency in clinical evidence. They were excluded from Claims 1–6. A title/URL
shown in a synthesis therefore cannot be treated as proof that the cited work was actually read.

- Direct run trace, single-origin operational evidence: `sources.jsonl` records
  `https://doi.org/10.1145/3772318.3791101` as PaperTrail, but `notes/f399bd6717.md` begins “This article
  deals with inconsistency of relative ... treatment effects.”
- Direct run trace, single-origin operational evidence: `sources.jsonl` records
  `https://doi.org/10.1145/3742413.3789079` as From Toil to Thought, but
  `notes/857a85841e.md` contains updated GRADE guidance and clinical subgroup-analysis text.
- Several otherwise useful sources were marked `TRUNCATED`; uncapped rereads recovered the full
  HINTs and progressive-disclosure papers, but the ACM multi-agent read still stopped during methods.

**Corroboration:** observed twice in one runtime/run, so it is a reproduced local failure pattern but
not yet a measured prevalence estimate. The exact cause (resolver, browser state, redirect, or parser)
was not established.

**Design consequence:** every source and claim view must expose `read_status`, expected vs observed
title/identifier, requested vs resolved URL, retrieval method, byte/character count, truncation,
content hash, and an identity-verification verdict. A mismatch is `failed`, not a successful read. The
root map's Gaps/Warnings section should count broken, mismatched, abstract-only, paywalled, and
truncated primaries so compression cannot hide a weak evidence base.

## What was rejected or remains unresolved

- **Rejected:** a universal three-tier or recursive-tree prescription. The best direct agent study is
  conditional and contains task-specific counterexamples to its own broad headline.
- **Rejected:** exposing complete worker deliberation as “transparency.” The HCI evidence points to
  sufficient, task-sensitive process visibility; full reasoning can inflate cognitive cost and create
  false trust cues.
- **Rejected:** using the retrieved PaperTrail and From Toil to Thought records as evidence. Their
  stored content did not match their metadata.
- **Unresolved:** the optimal size and fields of the root map for an *agent* caller; no source here
  directly compares map schemas on downstream field-survey tasks.
- **Unresolved:** whether a claim graph materially improves downstream correctness over disciplined
  Markdown links at equal cost. This needs an activated A/B, not a style judge.
- **Unresolved:** how often to regenerate syntheses after evidence/claim updates without creating
  stale links or hiding superseded conclusions.
- **Unresolved:** accessibility and nonvisual representations. The retrieved HCI work is heavily
  visual; Aletheia's canonical interface should remain filesystem/Markdown/JSON-native, with visuals
  as optional views.

## Local saturation and source limitations

Four gap-driven rounds covered the locally decisive roles: overview/detail/history; empirical
sensemaking process; multilevel human information exploration; direct agent progressive-disclosure
evaluation; disagreement/transparency; and a working layered-artifact implementation. Later candidate
sets were increasingly derivative or off-topic. Retrieval stopped at conceptual saturation rather
than padding the read budget. Channel coverage was constrained by the run-level Brave outage and an
arXiv 429 cooldown; DuckDuckGo and OpenAlex supplied discovery, followed by direct full reads where
possible. The most important remaining work is controlled A/B evaluation of the proposed contract,
not another generic literature query.
