# Field-dossier A/B protocol

## Factor under test

- **A — production:** `report.py bundle --reads`, one flat inline Markdown artifact.
- **B — candidate:** `report.py handoff`, a dossier entry point plus the content-addressed run tree.

Both conditions are generated from the exact same completed run. Research quality and retrieval luck
are therefore held constant; this is an interface/handoff ablation, not an end-to-end efficacy test.

## Static gates

For each narrow and broad run:

1. count bytes/lines in the entry artifact and full durable record;
2. verify that the entry's first substantive research product is the final brief;
3. verify every nonempty node `findings.md` is embedded or explicitly linked;
4. verify every run file (excluding generated handoff files) has a manifest row and correct SHA-256;
5. resolve every local Markdown link;
6. count decision/question/answer artifacts exposed by each condition;
7. verify no full-read body appears in the candidate dossier;
8. regenerate twice and compare semantic inventory (timestamps may differ; artifact paths/hashes may not).

## Objective downstream tasks

A fresh-context agent receives one blinded entry point and must:

1. state the top-level conclusion and confidence/caveat;
2. identify the strongest branch-level disagreement;
3. recover one named boundary condition omitted by a simplistic summary;
4. identify an unresolved gap and the branch that owns it;
5. explain one rejected source/path and its recorded reason;
6. locate the exact primary-read artifact supporting a named claim;
7. say whether the requested conclusion is supported, contradicted, single-origin, or unknown.

The answer key is frozen from the run before either condition is generated. Score exact content and
artifact path, not prose style. Record commands/files opened and elapsed time when the harness exposes
them.

## Controls

- Use paired A/B and B/A presentation labels; evaluator must not know which is the candidate.
- The evaluator may follow links supplied by its condition but may not independently search the web.
- Give both conditions the same task list and time ceiling.
- Separate “could not find” from “artifact lacks the information.”
- Run at least one strong filesystem navigator and one weaker/no-search reader if available; direct
  evidence says progressive-disclosure benefit is harness dependent.
- Do not use report length, source count, or a generic holistic LLM preference as the primary metric.

## Interpretation

A win establishes only that the handoff exposes the existing record better. It does not prove better
retrieval, truth, source independence, stopping, or synthesis. Those mechanisms remain separate
branches and require end-to-end matched-cost tests.

