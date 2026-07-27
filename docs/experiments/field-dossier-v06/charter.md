# Field-dossier v0.6 experiment charter

Date: 2026-07-27  
Production baseline: `addfaf6`, tagged `aletheia-prod-v0.5.0-openai.1`  
Experiment branch: `codex/exp-field-dossier-v06`  
Candidate version: `aletheia-research 0.6.0-dossier.1`

## Objective

Improve Aletheia's output as an agent-to-agent research object. Preserve the full research record
while letting a caller start from a field map, inspect self-contained branch syntheses, traverse to
claim/decision evidence, and open full reads only when the downstream task needs them.

This branch isolates the handoff mechanism. Retrieval, routing, budgets, source selection,
independence, synthesis authorship, and verification remain the production implementation so a result
can be attributed and rolled back.

## Mechanism hypothesis

The production handoff creates a compression cliff: a short `brief.md` or a flat bundle that injects
every raw read. A shallow, content-addressed dossier should retain all recoverable nuance while
improving orientation, branch coverage, caveat/gap recovery, trace access, and context efficiency.

The candidate has four levels:

1. L0: the exact verified brief;
2. L1: a one-page survey map plus every self-contained branch synthesis;
3. L2: structured claim verdicts and material decision/rejected-path previews;
4. L3: content-addressed evidence, source indexes, reads, telemetry, and execution state.

Logical evidence depth may be arbitrarily rich. Always-loaded routing depth stays shallow.

## Main falsifiers

- A fresh agent answers branch/caveat/gap/evidence follow-ups no better than from the flat bundle.
- The dossier silently omits a node, branch synthesis, claim, decision trace, or raw artifact.
- Links or hashes do not resolve after regeneration or from a caller outside the run directory.
- The smaller default context causes agents to skip decisive L3 evidence when the task requires it.
- An extra routing layer reduces answer accuracy, as the strongest direct long-context-agent study
  found in several settings ([He et al. 2026](https://arxiv.org/pdf/2607.17598v1)).
- Benefits disappear when presentation length, access to underlying artifacts, and evaluation tasks
  are controlled.

## Promotion gate

Promotion requires all of the following:

1. Every durable artifact is represented by path, role, byte count, and SHA-256 in the manifest.
2. Every nonempty node synthesis is reachable from the map and embedded in the dossier.
3. The brief appears before branch/raw material; raw reads are not injected by default.
4. Objective follow-up tasks test answer, disagreement, gap, decision, and exact-evidence recovery.
5. A/B presentation names and order are blinded; both conditions receive the same underlying run.
6. At least one narrow and one broad/contested run pass link/hash and comprehension checks.
7. No production research behavior or baseline branch is modified.

Smaller size, more Markdown, passing unit tests, or a generic style preference are not promotion
evidence.

## Evidence basis and limits

- Shneiderman's overview/zoom/filter/details/history pattern motivates overview-to-detail navigation,
  but it is HCI guidance rather than an agent evaluation.
- Pirolli and Card distinguish raw sources, an evidence file, schemas, hypotheses, and presentation;
  this supports typed layers, not this exact file schema.
- HiAgent found that hierarchical summaries plus on-demand trajectory retrieval outperformed
  summary-only memory; its tasks are long-horizon action environments, not research surveys
  ([ACL 2025](https://aclanthology.org/2025.acl-long.1575.pdf)).
- He et al. directly show that progressive disclosure is harness/task/scale dependent and that a
  deeper always-loaded route can harm accuracy. This is why the candidate uses one map, not a
  recursively preloaded routing tree.
- No primary study validates the integrated dossier on agentic field surveys. The mechanism remains
  experimental until the targeted A/B is complete.

