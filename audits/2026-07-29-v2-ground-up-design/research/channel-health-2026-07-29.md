# Channel-health snapshot — 2026-07-29

**Command:** `python3 .cursor/skills/channel-retrieval/scripts/doctor.py`
**Purpose:** record the live-retrieval qualification for the v2 workflow/alternatives investigation.

The command performed one functional request per configured core channel and reported:

| Channel | Status | Note |
|---|---|---|
| arXiv | ok | HTTP 200 |
| DuckDuckGo | ok | 3 results |
| Europe PMC | ok | HTTP 200 |
| GitHub | ok | 3 results; unauthenticated rate limit noted |
| Hacker News | ok | 3 results |
| Marginalia | ok | 2 results |
| OpenAlex | ok | HTTP 200 |
| Open Library | ok | HTTP 200 |
| Jina reader | ok | HTTP 200 |
| Reddit | ok | 3 results |
| Stack Exchange | ok | 3 results |
| Wikipedia | ok | HTTP 200 |
| Brave | warn | no `BRAVE_API_KEY`; independent web index unavailable |

**Result:** 12/13 core channels were live; Brave was degraded. This is a
point-in-time capability check, not a reliability/load test and not evidence of
complete web coverage. The workflow report consequently uses direct official
pages for load-bearing external statements.
