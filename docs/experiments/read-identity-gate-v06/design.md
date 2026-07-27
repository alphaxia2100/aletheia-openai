# Semantic read-identity gate v0.6 — experiment design

Status: experimental branch, derived directly from `prod` (`060387b`)  
Branch: `codex/exp-read-identity-gate-v06`  
Mechanism under test: expected-versus-observed identity and content state for fetched bodies

## Trigger and provenance

The Aletheia self-survey on 2026-07-27 produced two direct failures:

1. manifest DOI `10.1145/3772318.3791101` / *PaperTrail* persisted the body of GRADE 2011,
   DOI `10.1016/j.jclinepi.2011.03.017`, with `_read_ok=true`;
2. manifest DOI `10.1145/3742413.3789079` / *From Toil to Thought* persisted the body of GRADE
   2023, DOI `10.1016/j.jclinepi.2023.03.003`, with `_read_ok=true`.

The preserved run artifacts are under
`runs/aletheia-research/2026-07-27-101249-aletheia-output-quality-20260727/tree/root/children/interface/`.
The failure is not hypothetical: the browser/resolver returned a long, coherent, wrong document and
the production predicate accepted length as success.

## Hypothesis

A typed gate can catch both observed wrong bodies and preserve valid difficult pages without using
topic relevance as an identity proxy. A successful read must have both usable content and either:

- a matching strong identifier in trusted front matter; or
- a high-confidence normalized title match.

The gate must distinguish:

- `verified_identifier`;
- `verified_title`;
- `unverified_identity` (persist, retry/inspect, exclude from synthesis);
- `mismatch` (persist, never count as evidence);

and independently record `complete|truncated|blocked|shell|image_only|unreadable` content state.

## Falsifiers

The mechanism fails this diagnostic if any of the following occurs:

- either exact observed wrong body remains `_read_ok=true`;
- a mismatch artifact is deleted or overwritten by a retry;
- a valid DOI, exact title, abbreviated title, matching title with multiple cited DOIs, or direct
  YouTube-caption object is rejected;
- a no-metadata page is falsely called a mismatch rather than honestly unverified;
- an expected DOI appearing only in a wrong document's reference list overrides a conflicting title;
- telemetry cannot distinguish content success from evidence-identity success.

## Comparison

The deterministic A/B applies the production effective predicate (`len(body) >= 1500` after the
reader returns) and the candidate gate to the same 11 portable cases. It includes the two observed
failures, three mismatch/unverified negatives, content-state negatives, and five difficult positive
controls. This is an executable mechanism test, not a proxy essay score or a release benchmark.

## Deliberate scope

This branch does not change retrieval queries, source ranking, the dossier, claim schemas, or
orchestration. It does not yet implement a full resolver chain. An identity failure remains available
for the agent to inspect and retry through DOI, repository, HTML, PDF, OCR, or a direct browser, but
automatic resolution policy belongs in a later isolated experiment.

## Known risks

- Publisher title markup is irregular; conservative parsing can turn some valid reads into
  `unverified_identity`.
- A matching title does not prove version, retraction state, or completeness.
- A matching identifier in trusted front matter can still accompany a malformed or partial body;
  content state remains separate for this reason.
- Heuristic title thresholds require broader real-run calibration before promotion.
- Generic browser extraction is not a trusted direct-object method. YouTube captions and Reddit
  thread reads can use their stable object IDs because those adapters directly address the object.
