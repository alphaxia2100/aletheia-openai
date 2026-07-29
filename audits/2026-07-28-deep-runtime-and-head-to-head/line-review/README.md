# Literal runtime-source coverage

This is a source review, not a test-coverage claim. Each listed executable-runtime line at frozen
candidate `bd5e1a50a491ee7c5ebe1382ace35c21f7909de5` was displayed with line numbers and assigned to
one reviewer. The candidate files are byte-identical at audit commit `cbed4789a1c4b283189ec62742eb6ae1ea40f087`.

| Area | Files | Executable lines | Record |
|---|---:|---:|---|
| Leaf engine — `investigate`, `router`, `rank` | 3 | 1,335 | [engine.md](engine.md), [engine-coverage.json](engine-coverage.json) |
| State, report, verification, synthesis | 4 | 1,573 | [control-plane.md](control-plane.md), [control-plane-coverage.json](control-plane-coverage.json) |
| Channel/provenance clients, installer, preflight | 29 | 4,316 | [boundary.md](boundary.md), [boundary-coverage.json](boundary-coverage.json) |
| Closure executables added during review — Claude installer and sandbox wrapper | 2 | 134 | [boundary.md](boundary.md), [boundary-coverage.json](boundary-coverage.json) |
| **All executable runtime source** | **38** | **7,358** | **All three manifests** |

The boundary review also inspected 120 behavior-changing, non-Python/shell lines: the container
Dockerfile (36), channel configuration (80), and agent manifest (4). That brings the literal
runtime-and-policy asset review to 7,478 lines. The public Aletheia `SKILL.md` contract was read in
full separately; it is cited where its promises differ from code.

The manifests contain contiguous, exhaustive line ranges. A local validation parsed each JSON
manifest and confirmed all ranges union exactly to `1..line_count` for every file:

```text
engine-coverage.json          3 files / 1,335 lines / full coverage
control-plane-coverage.json   4 files / 1,573 lines / full coverage
boundary-coverage.json       34 files / 4,570 lines / full coverage
```

The 4,570 boundary lines include the 4,316 original executable assignment, the two additional
executables, and the three policy/config assets. “No separate finding” records an inspected range
with no additional issue at the stated severity; it is not a statement that the range is bug-free.

The standard suite passed 186/186 tests. That is regression evidence only: it is neither a line
coverage measurement nor proof of live connector, host-agent, concurrency, or output-quality behavior.
