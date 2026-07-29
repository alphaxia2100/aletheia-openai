# Skeptical validation of critical findings

Validated against current `cbed4789a1c4b283189ec62742eb6ae1ea40f087`.  A scoped
`git diff --quiet bd5e1a50a491ee7c5ebe1382ace35c21f7909de5 HEAD` over every file
referenced below was clean, so these are also findings against the frozen `bd5`
candidate.  The probes below used monkeypatches and temporary directories only;
none made a network request.

## Confirmed at material integrity severity

- **Length-only / wrong-body read success — confirmed; High.**
  `investigate.py:376-410` accepts a generic body solely at 1,500 characters,
  and `:590-609` persists/counts it as `_read_ok`; neither proves document
  identity. `read.py:50-56,73-91` also provides no resolved-body identity.
  A hermetic unrelated 2,200-character body for
  `https://expected.example/paper` produced `reads_ok=1`, `_read_ok=true`, and
  `resolved_url=https://expected.example/paper`. This demonstrates the
  acceptance rule, not a live bad upstream response. The consequence is still
  high: the wrong body joins the evidence basis as a successful read.

- **Stale split replay — confirmed; High/P1 integrity risk.**
  `treestate.py:303-367` neither requires a pending parent nor makes a split
  one-shot; `:381-388` leaves `proposal.json` reusable. Old child directories
  remain, while `synthesize.py:71-76,139-156` enumerates directories rather
  than the parent status manifest. Replaying `a,b` then `c,d` left status
  `['c','d']`, disk children `['a','b','c','d']`, and four synthesis children,
  including an old findings marker. A retry/materialization duplicate is enough;
  no malformed filesystem input is required.

## Confirmed behavior, with scope or severity qualification

- **QID gate bypass — confirmed logic bug; Medium–High protocol-control risk.**
  `treestate.py:439-463` records an answer for any QID and sets state
  `answered`; `synthesize.py:62-68` treats any nonblank answer row as resolution.
  A bogus QID plus an empty body left the real question `answered=false` but
  returned no unresolved child and gate exit 0. It is correctly a bypass of the
  advertised gate, but it is not a sandbox/security boundary (and root findings
  can be written without invoking the gate), so describe the severity as an
  enforcement/protocol failure rather than an autonomous privilege escalation.

- **Concurrent source/index/node-cap race — confirmed under concurrent writers;
  Medium–High conditional risk.** `treestate.py:126-143,164-172` uses unlocked
  read/modify/write; `:267-289,303-367` has a check-then-act cap; `:391-414`
  reads then appends the global index; and `:439-463` derives QIDs from line
  count. Barrier probes produced duplicate `q1`, two equal global-index rows
  (both callers returned one add), and seven nodes after two splits each saw a
  `max_nodes=5` run. The defect is real, but loss/corruption requires duplicate
  scheduling or another concurrent writer; no naturally occurring live race was
  demonstrated.

- **Preflight marker/manifest bypass — confirmed; Medium tamper-evidence issue.**
  `scripts/preflight.py:68-90` excludes `.aletheia-install.json` from manifest
  rows, while `:163-171` lets that marker alone decide portability and
  `:220-232` skips verification otherwise. After mutating a manifest-listed
  file and changing the marker mode, `check()` returned `ok=true`,
  `manifest=not-applicable`, and no errors. This defeats the copied-runtime
  corruption check, but a party able to do this already writes the runtime (and
  the manifest is not a signature); it is not an elevation or cross-user attack.

- **Direct connector capability bypass — confirmed; Medium design-contract issue.**
  `_http.py:349-370` gates only the CLI wrapper, while `openalex.py:39-77`
  calls the network helper directly. With `require_enabled` replaced by a
  raising stub, `openalex.search()` still completed through a stubbed HTTP call.
  `investigate.py:523-533` does gate its own production route, so the finding is
  a callable/API boundary bypass, not a bypass of that engine path or proof that
  arbitrary local Python is sandboxed.

- **Stale browser extraction — confirmed for the opt-in browser reader; Medium
  (High within that feature).** `_agentreach.py:116-121` discards subprocess
  status, and `:217-254` ignores the open result before extracting from the
  fixed `aletheia` session. A failed/empty mocked open followed by an extract
  returned `STALE-PAGE` as success. `read.py:80-91` accepts that nonempty body.
  It is a genuine provenance failure when `read.py --browser` is used, but the
  normal Aletheia engine and verifier call `read_url(..., False)`
  (`investigate.py:402`; `verify.py:95`), so it is not a default full-read path.

- **Router specialist cancellation — confirmed core logic; Medium quality risk.**
  `router.py:157-195` unions every selected domain's exclusions before filtering
  all candidate picks. For the dual-domain medical-ML probe, it selected
  `biomed,cs_software` and excluded `arxiv,europepmc,github,stackexchange`.
  That drops each domain's named specialist(s), as shown by the domain lists at
  `:39-57`. The stronger wording that *all* specialists disappear is too broad:
  default configuration retains generic OpenAlex (and, when enabled,
  Semantic Scholar); the impact is systematic coverage loss, not a total outage.

- **Completion-order alias selection — confirmed; Medium reproducibility/quality
  risk.** `investigate.py:320-359` appends results in `as_completed()` order;
  `:238-285` retains the first duplicate, and `:538-546` deduplicates before
  ranking. Switching only two stub delays switched the survivor between a mirror
  and its arXiv alias. This proves latency controls representative choice; it
  does not prove every discarded later alias is lower quality, so P1-style
  evidence harm should be stated conditionally.

- **No primary quota — confirmed for deterministic selection; Medium contract
  mismatch.** `rank.py:103-128` gives `primary` only a 1.05 score multiplier and
  `:137-191` selects by class, never by `primary`, despite the claim at `:10-11`.
  Three higher-scoring non-primary evidence rows plus a lead selected no eligible
  primary. The normal agent-triage path delegates the choice to the agent
  (`investigate.py:708-760`); the deterministic fallback calls this selector
  (`:660-670`). Thus this is not proof that agent-driven runs never read a
  primary, but it disproves an unconditional primary-read guarantee.

## Rejected claims

None of the ten named behavior claims was rejected. The qualifications above are
about threat model, triggering conditions, and severity—not a failure to reproduce
the underlying code paths.
