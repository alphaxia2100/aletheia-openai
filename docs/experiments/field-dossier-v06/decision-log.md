# Field-dossier experiment decision log

## 2026-07-27 — preserve production before experimentation

- Pinned the clean `addfaf6` checkpoint as production.
- Kept the candidate on `codex/exp-field-dossier-v06`; no production code is edited.
- Baseline suite: 156/156 tests passed.

## 2026-07-27 — choose the output cliff as the isolated first mechanism

Observed a 72-line/4.6 KB brief paired with a 9,077-line/950.9 KB bundle. Code inspection showed that
the bundle inlines raw reads, puts the answer last, and omits material trace artifacts. This is a
direct implementation defect and a cleanly isolatable mechanism.

Alternatives deferred to separate branches: semantic read-identity gate, claim/evidence ledger,
adaptive question DAG, origin ontology, multi-signal stopping, and runtime event sourcing. Combining
them here would make an A/B uninterpretable.

## 2026-07-27 — reject “more hierarchy” as the design rule

The initial idea was a recursive tree of summaries. The interface research found direct 2026 agent
evidence that a second always-loaded routing layer often reduced accuracy, with task-specific
counterexamples. The candidate therefore uses one bounded map that links to arbitrarily deep
evidence; depth is available but not preloaded.

## 2026-07-27 — preserve by reference, not by context injection

Adopted the invariant “lossless on durable storage, selective and reversible in context.” HiAgent's
trajectory-retrieval ablation and the existing Aletheia file tree both support retaining raw artifacts
while assembling smaller views. The manifest hashes every artifact so omission is inspectable.

Rejected: silently truncating reads, returning only a shorter summary, or deleting raw worker state.

## 2026-07-27 — make agent handoff the default on this branch

The requester defined Aletheia primarily as an agent tool. `treestate.py init` therefore defaults to
`verbosity=agent`; explicit `--verbosity user` remains available. The inline bundle remains a
transport fallback for harnesses without shared artifact access.

## Pending decisions

- Promotion or rejection after objective follow-up A/Bs.
- Whether transport should become a first-class `shared|inline|archive` parameter in a later branch.
- Whether the dossier should expose generated claim cards or only link to an independent claim ledger.

## 2026-07-27 — first diagnostic passes; promotion withheld

Static same-run checks passed on one narrow and one broad run: every artifact hash, branch synthesis,
and local link resolved; the entry artifact shrank 96.97% and 98.45% without inlining a full read.
On a seven-item downstream lookup diagnostic, the flat bundle scored 6/7 and the dossier tree 7/7.
The difference was the exact rejected-path rationale: production omitted `decisions.jsonl`, while the
dossier exposed it. No speed claim is made because elapsed/tool counts were not instrumented equally.

The adversary branch simultaneously ranked output navigation behind six epistemic/runtime
bottlenecks. Therefore the mechanism remains experimental even though its local invariant and lookup
tests passed. The next separate branch should address semantic read identity; promotion of this branch
awaits the multi-topic repeated protocol in `eval-protocol.md`.
