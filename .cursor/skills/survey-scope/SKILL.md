---
name: survey-scope
description: Turns a research topic into a portfolio of competing framings (never one hypothesis) plus tightly-scoped, non-overlapping subagent specs, and resolves the topic to concrete entities (people, subreddits, repos, papers, channels) BEFORE searching. Use as the first stage of an Aletheia survey, or whenever scoping a research question to avoid anchoring.
disable-model-invocation: true
---

# survey-scope

Specification is the #1 failure category in multi-agent systems, and the framing you pick here silently determines every downstream query. So this stage is deliberate and, ideally, done *with* the user.

## Step 1 — Entity resolution BEFORE searching

Do not search raw keywords first — you will anchor on whatever the SEO layer surfaces. First resolve the topic to concrete entities so subagents query the right handles/subreddits/repos/authors, and switch to author-scoped queries for people.

```bash
python3 ~/.cursor/skills/survey-scope/scripts/entity_resolve.py "<topic>" > runs/<run>/entities.json
# offline / no-network fallback (still emits a usable template):
python3 ~/.cursor/skills/survey-scope/scripts/entity_resolve.py "<topic>" --offline
```

The script hits only free, no-auth endpoints (Wikipedia, HN Algolia, arXiv, GitHub, optionally OpenAlex) and degrades gracefully. It returns `canonical_terms`, `people`, `github_repos`, `arxiv_authors`, `key_papers`, `subreddits`, `suggested_queries`, and `framing_seeds`. Treat its output as leads to verify, not truth.

## Step 2 — Build the framing portfolio (no single hypothesis)

This is grounded-theory discipline applied to agents: you cannot start truly blank (even which sources you open is a prior), so instead of one hypothesis, hold a *portfolio* provisionally and let the evidence kill framings. "No hypothesis" operationally means "no commitment."

Emit **4-6 competing framings** of the field, deliberately spanning the space — not variations on one theme. Always include:
- the **mainstream/consensus** framing (so you can test it, not serve it),
- at least one **minority/heterodox** framing ("the experts are wrong because ..."),
- at least one **practitioner/field-report** framing (what people who actually tried it report),
- at least one **orthogonal/reframe** ("this is really a question about Y, not X").

For each framing record: `id`, `statement`, `who_holds_it`, `what_would_confirm`, `what_would_disconfirm`, `where_it_would_hide` (which un-laundered channel would reveal it if true). Hold all provisionally; none is the working hypothesis.

## Step 2.5 — Select channels by relevance (not all of them)

More channels is not more rigor. Firing every channel on every topic adds noise, token cost, and fake diversity. Pick a **small, well-matched set** using `channel-retrieval/channels.json` -> `selection_guidance`:

- Match the topic type (e.g. Stack Exchange + GitHub for software; OpenAlex + Europe PMC for medicine; Google Books + Gutenberg for history). Stack Exchange is high-signal for technical/how-to questions and near-useless for humanities/policy — choose accordingly.
- Always cover three roles regardless of topic: one **independent web** index (Brave/Marginalia), one **primary source** (papers/repos/docs), one **un-laundered** channel (Reddit/forums/HN) where a wrong consensus would show.
- Prefer depth over breadth of shallow channels: 3 well-chosen channels read deeply beat 10 skimmed. Deep reading is the `read.py` / `youtube.py` step in `channel-retrieval`.

## Step 3 — Derive non-overlapping subagent specs

Cross framings with channels so each subagent points a **different direction**. Scope separation, not headcount, is the control surface. Each spec:

```json
{
  "id": "s1",
  "framing_id": "f3",
  "channel": "openalex",
  "direction": "one-sentence, distinct hunt objective",
  "persona": "role that induces a different search trajectory (sets SCOPE only, not credibility)",
  "queries": ["author-scoped or entity-scoped queries, not bare keywords"],
  "must_return": "compressed findings + normalized source records (see channel-retrieval); NOT raw dumps",
  "stop_when": "coverage/steady-state condition"
}
```

Rules:
- No two specs share the same (framing x channel) direction.
- At least one spec is explicitly tasked to find **disconfirming** evidence for the current-leading framing.
- Spread across `index_group`s (see `channel-retrieval/channels.json`) — do not fill the roster with three Google-index channels.
- A persona changes *what a subagent hunts*, never *whose answer wins*.
- **Order channels primary-first** (papers/repos/official docs before expert-summary and community channels), per the orchestrator's research ladder — so the base is built from primaries, not from the laundered consensus.

## Step 4 — Confirm scope with the user

Present the portfolio + the spec roster and ask the user to adjust before fan-out. This is the one place not to improvise. If the user is absent, proceed but state the framings explicitly in `scope.md` so the assumptions are auditable.

## Output

Write `runs/<run>/scope.md` containing: the resolved entities, the framing portfolio, and the subagent spec roster. This file is the contract the orchestrator fans out from.
