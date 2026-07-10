# Runtime-ledger experiment

Branch: `codex/exp-runtime-ledger-v06`  
Base: `52aaca9`

## Factor isolated

Decouple source reads from the tree scrutiny unit, honor `candidates --reads`, make an explicitly
uncapped browser reread truly uncapped, and reserve search/read work atomically before network I/O.
The high-accuracy configuration can now express the user's ceilings directly:

```text
--reads-per-round 40 --max-read-attempts 640 --max-seconds 3600
```

Failed or crashed reserved reads still count. Parallel workers serialize reservations through the
run-local ledger lock, so the read ceiling fails closed. Denied work is recorded in
`runtime-events.jsonl` and never reaches network I/O.

## Result

- 160/160 repository tests pass on Python 3.12.
- Added regressions prove the reasoning unit remains 4 while the read ceiling is 40, the run-wide
  reservation refuses 2 additional reads after 2/3 slots are consumed, the agent candidate path
  preserves an explicit read count of 7, and browser `max_chars=0` reaches the browser backend as 0.
- This removes two confirmed defects and makes engine-managed caps executable rather than advisory.

## Interpretation and limits

This is plumbing, not evidence of higher answer accuracy. It should be retained as an observability
and experiment-integrity prerequisite, but it must not be credited as a quality win. Direct/manual
artifacts are still detected only by the scorer rather than reserved before acquisition, and a single
network call can finish after the wall-clock threshold because the check occurs immediately before
I/O. Those limitations must be closed before calling the wall clock a strict kill deadline.

