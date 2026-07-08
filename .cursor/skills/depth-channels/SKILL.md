---
name: depth-channels
description: Pulls transcripts from YouTube videos and podcasts (the wealth of information ordinary agents cannot reach), using a robust fallback chain, and handles them as color/lead-gen that must be corroborated before citing. Use when an Aletheia survey needs video or audio sources, or when the user asks about YouTube transcripts, podcasts, or spoken-word content.
disable-model-invocation: true
---

# depth-channels

The channels most agents can't touch — YouTube transcripts, podcasts. High value for practitioner/field-report framings, but epistemically **color**: a confident spoken claim is not evidence. Extract the claim, then route it back through `channel-retrieval` to find primary corroboration before it appears in synthesis. All records here are `primary: false`; set `derives_from` when the speaker is citing a paper/source you can name.

These channels are paid / toggle-on; if the keys are absent, skip them — the free core stands without them.

## YouTube

Two hard facts (design around them):
- **YouTube Data API v3 cannot return transcripts** for videos you don't own (`captions.download` needs OAuth + ownership → 403). Use it for metadata/search only (`YOUTUBE_API_KEY`, 10k units/day).
- **Datacenter/cloud IPs are blocked.** Every self-hosted extractor hits "confirm you're not a bot" from AWS/GCP/Azure. Only residential/rotating proxies (or a managed service that owns the proxy problem) defeat it. Cookies/PO-tokens do not.

Fallback chain (implement all three tiers):
1. **Existing captions** → `youtube-transcript-api` (Python) or `yt-dlp --write-auto-subs --skip-download`. Cheapest, most "primary" (YouTube's own captions). From a residential IP, or via a rotating residential proxy on cloud.
2. **If IP-blocked / no proxy ops** → managed extractor: **Supadata** `GET https://api.supadata.ai/v1/transcript?url=<video>` header `x-api-key: $SUPADATA_API_KEY`, mode `native` (captions) or `auto` (captions→whisper). MCP: `supadata`. It owns the proxy + whisper for you.
3. **If no captions exist** → download audio (`yt-dlp -x --audio-format mp3`) → transcribe with **faster-whisper** (self-host) or Deepgram/AssemblyAI (managed). Supadata `mode=auto` collapses tiers 1+3 into one call.

**Bundled no-key client: `channel-retrieval/scripts/youtube.py`** — on a residential machine this works with zero keys: captions via `youtube-transcript-api` (primary; it uses the timedtext endpoint and sidesteps the 2026 PO-token gate that now blocks `yt-dlp` *subtitle* downloads), `yt-dlp` for search + audio, and `faster-whisper` for the no-captions fallback (`--whisper`). It writes the FULL transcript to a file. Deps: `pip install --user youtube-transcript-api yt-dlp` (+ `faster-whisper` for whisper).

**Discovery (how to find videos, no key):**
- `python3 ~/.cursor/skills/channel-retrieval/scripts/youtube.py --search "topic"` -> relevance (yt-dlp `ytsearch`), or add `--latest` -> **newest-first** (yt-dlp `ytsearchdate`). Verified working no-key.
- Follow specific creators for the latest uploads via channel RSS: `https://www.youtube.com/feeds/videos.xml?channel_id=<ID>` (no key) — pair with `survey-scope`'s entity resolution to resolve a field's key channels first.
- Broader reach (X/Bilibili/etc.): use **agent-reach** as the access layer.

Minimal robust design: `youtube.py` (captions) on a residential IP → **Supadata `auto`** as the managed catch-all when you're on cloud/blocked → `yt-dlp + faster-whisper` as the self-hosted escape hatch for videos with no captions.

## Podcasts

Invert the priority — podcast audio is openly downloadable from the RSS `<enclosure>`, so a whisper pipeline is low legal/IP risk and universal.
1. **Taddy** (best transcript API) — GraphQL `https://api.taddy.org` with headers `X-USER-ID: $TADDY_USER_ID`, `X-API-KEY: $TADDY_API_KEY`; generates transcripts when the podcaster didn't provide one; grants storage/caching rights. Free 500 req/mo.
2. **Fallback** — resolve the show via PodcastIndex / Listen Notes, take the `<enclosure>` audio URL from the RSS feed → faster-whisper / Deepgram / AssemblyAI.

## Discipline

- **class = color.** Never cite a video/podcast as fact. Extract the claim, tag the record `channel_class: color`, `primary: false`, and (if the speaker cites something nameable) `derives_from`/`refs` to it.
- **Corroborate before use.** A claim worth keeping gets a `channel-retrieval` pass on an evidence-class channel; only the corroborating primary is cited.
- **Provenance still applies.** Feed the records into `provenance-audit` like any other — a claim echoed across ten videos and one blog is still one narrative, not eleven sources.
- **Recency note:** the YouTube datacenter-IP block and pay-per-use X pricing are 2026-current; verify extractor/library health at build time (see `channel-retrieval/reference.md`).
