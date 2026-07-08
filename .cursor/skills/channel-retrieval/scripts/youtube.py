#!/usr/bin/env python3
"""YouTube transcripts (no key) -> normalized records (JSONL) + full transcript files.

Depth channel. Works on a residential machine without any API key:
  1. captions via `youtube-transcript-api` (primary; sidesteps yt-dlp's PO-token gate)
  2. fallback: audio via `yt-dlp` + local `faster-whisper` (only with --whisper, if installed)
Search uses `yt-dlp` ytsearch; titles via oEmbed (no key).

Class = color: a spoken claim is not evidence. The transcript is written IN FULL to
--outdir for real depth; the record carries an excerpt + the file path. Extract claims
and corroborate on an evidence channel before citing.

Deps (pip install --user): youtube-transcript-api ; yt-dlp ; (optional) faster-whisper
Usage:
  youtube.py VIDEO_URL_OR_ID [VIDEO2 ...] [--outdir DIR]
  youtube.py --search "query" --limit 5 [--outdir DIR]
  youtube.py VIDEO --whisper        # transcribe audio locally if no captions
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def video_id(s: str) -> str:
    s = s.strip()
    if "youtu.be/" in s:
        return s.split("youtu.be/")[1].split("?")[0][:11]
    if "v=" in s:
        qs = urllib.parse.urlparse(s).query
        v = urllib.parse.parse_qs(qs).get("v", [""])[0]
        if v:
            return v[:11]
    return s[:11] if re.fullmatch(r"[A-Za-z0-9_-]{11}", s[:11]) else s


def oembed(vid: str, timeout: float) -> Tuple[str, str]:
    try:
        j = _http.get_json(
            "https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=" + vid,
            timeout)
        return j.get("title", ""), j.get("author_name", "")
    except Exception:  # noqa: BLE001
        return "", ""


def captions(vid: str) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except Exception:
        return ""
    # v1.x: instance.fetch(); v0.x: classmethod get_transcript()
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            ft = api.fetch(vid)
            return " ".join(getattr(s, "text", "") for s in ft).strip()
    except Exception:  # noqa: BLE001
        pass
    try:
        t = YouTubeTranscriptApi.get_transcript(vid)  # type: ignore[attr-defined]
        return " ".join(x.get("text", "") for x in t).strip()
    except Exception:  # noqa: BLE001
        return ""


def whisper_fallback(vid: str, outdir: str, timeout: float) -> str:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        sys.stderr.write("whisper fallback unavailable: pip install --user faster-whisper\n")
        return ""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", vid)[:64] or "video"  # no path traversal
    audio_stub = os.path.join(outdir, safe)
    try:
        subprocess.run(
            [sys.executable, "-m", "yt_dlp", "-x", "--audio-format", "mp3",
             "-o", audio_stub + ".%(ext)s", "https://www.youtube.com/watch?v=" + vid],
            capture_output=True, timeout=timeout, check=True)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("audio download failed: %s\n" % e)
        return ""
    mp3 = audio_stub + ".mp3"
    if not os.path.exists(mp3):
        return ""
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(mp3)
    text = " ".join(s.text for s in segments).strip()
    try:
        os.remove(mp3)
    except OSError:
        pass
    return text


def yt_search(query: str, n: int, timeout: float, latest: bool = False) -> List[str]:
    # ytsearchdate = newest-first (latest videos); ytsearch = relevance
    prefix = "ytsearchdate" if latest else "ytsearch"
    try:
        r = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--dump-json", "--flat-playlist",
             "%s%d:%s" % (prefix, n, query)],
            capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write("yt-dlp search failed: %s\n" % e)
        return []
    ids = []
    for line in r.stdout.splitlines():
        try:
            ids.append(json.loads(line)["id"])
        except Exception:  # noqa: BLE001
            pass
    return ids


def process(vid: str, outdir: str, use_whisper: bool, timeout: float) -> Optional[Dict[str, Any]]:
    title, author = oembed(vid, timeout)
    text = captions(vid)
    method = "captions"
    if not text and use_whisper:
        text = whisper_fallback(vid, outdir, max(timeout, 120))
        method = "whisper"
    if not text:
        sys.stderr.write("no transcript for %s (captions gated; try --whisper)\n" % vid)
        return None
    os.makedirs(outdir, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", vid)[:64] or "video"  # no path traversal
    path = os.path.join(outdir, safe + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    words = len(text.split())
    return _http.rec(
        "youtube", url="https://www.youtube.com/watch?v=" + vid,
        title=title or vid, authors=[{"name": author}] if author else [],
        primary=False,
        snippet="[%s, %d words, full=%s] %s" % (method, words, path, text[:300]),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube transcripts (no key) -> records")
    ap.add_argument("videos", nargs="*", help="video URLs or IDs")
    ap.add_argument("--search", help="search query (uses yt-dlp ytsearch)")
    ap.add_argument("--latest", action="store_true", help="sort search by upload date (newest first)")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--outdir", default="runs/transcripts")
    ap.add_argument("--whisper", action="store_true", help="audio+faster-whisper fallback if no captions")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args()

    vids = [video_id(v) for v in args.videos]
    if args.search:
        vids += yt_search(args.search, args.limit, max(args.timeout, 60), args.latest)
    if not vids:
        ap.error("provide video URLs/IDs or --search")

    recs = []
    for vid in vids[: args.limit if args.search else len(vids)]:
        rec = process(vid, args.outdir, args.whisper, args.timeout)
        if rec:
            recs.append(rec)
    _http.emit(recs)
    return 0 if recs else 1


if __name__ == "__main__":
    raise SystemExit(main())
