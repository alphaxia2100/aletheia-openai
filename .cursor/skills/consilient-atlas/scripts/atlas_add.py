#!/usr/bin/env python3
"""Append a completed survey to the Consilient Atlas.

Creates atlas/surveys/<date>-<slug>.md (optionally embedding a run's synthesis /
defensibility) and inserts a row into atlas/index.md so surveys compound.

Usage:
  atlas_add.py --title "State of X" [--slug state-of-x] [--date 2026-07-01] \
               [--spiky-pov "..."] [--defensibility "defensible (3.5/4)"] \
               [--synthesis runs/<run>/synthesis.md] [--defensibility-file runs/<run>/defensibility.md] \
               [--atlas-dir atlas]

Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from typing import List, Optional


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "survey"


def _read(path: Optional[str]) -> str:
    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError as e:
        sys.stderr.write("warning: could not read %s: %s\n" % (path, e))
        return ""


def build_survey_md(title: str, date: str, spiky: str, defensibility: str,
                    synthesis: str, defensibility_body: str) -> str:
    parts = [
        "---",
        "title: %s" % title,
        "date: %s" % date,
        "spiky_pov: %s" % (spiky or ""),
        "defensibility: %s" % (defensibility or ""),
        "---",
        "",
        "# %s" % title,
        "",
    ]
    if spiky:
        parts += ["## Spiky POV", spiky, ""]
    parts += ["## Survey", synthesis or "_(paste synthesis.md here)_", ""]
    if defensibility_body:
        parts += ["## Defensibility", defensibility_body, ""]
    return "\n".join(parts)


def update_index(index_path: str, date: str, title: str, spiky: str,
                 defensibility: str, rel: str) -> str:
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    else:
        lines = ["# Consilient Atlas — index", "",
                 "| Date | Survey | Spiky POV (if any) | Defensibility | File |",
                 "|------|--------|--------------------|---------------|------|"]

    if any(rel in ln for ln in lines):
        sys.stderr.write("note: %s already in index; not duplicating\n" % rel)
        return index_path

    spiky_cell = (spiky[:60] + "...") if len(spiky) > 63 else spiky
    row = "| %s | %s | %s | %s | [%s](%s) |" % (
        date, title, spiky_cell or "", defensibility or "", os.path.basename(rel), rel)

    # drop placeholder, insert after the last table row
    lines = [ln for ln in lines if "_(none yet)_" not in ln]
    last_tbl = -1
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("|"):
            last_tbl = i
    if last_tbl == -1:
        lines += ["", "| Date | Survey | Spiky POV (if any) | Defensibility | File |",
                  "|------|--------|--------------------|---------------|------|", row]
    else:
        lines.insert(last_tbl + 1, row)

    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return index_path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Append a survey to the Consilient Atlas.")
    ap.add_argument("--title", required=True)
    ap.add_argument("--slug")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--spiky-pov", default="")
    ap.add_argument("--defensibility", default="")
    ap.add_argument("--synthesis", help="path to synthesis.md to embed")
    ap.add_argument("--defensibility-file", help="path to defensibility.md to embed")
    ap.add_argument("--atlas-dir", default=os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "..", "atlas"))
    args = ap.parse_args(argv)

    # sanitize inputs used to build filenames (no path traversal / injection)
    slug = slugify(args.slug or args.title)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        ap.error("--date must be YYYY-MM-DD")
    atlas_dir = os.path.abspath(args.atlas_dir)
    surveys_dir = os.path.join(atlas_dir, "surveys")
    os.makedirs(surveys_dir, exist_ok=True)

    fname = "%s-%s.md" % (args.date, slug)
    fpath = os.path.join(surveys_dir, fname)
    body = build_survey_md(
        args.title, args.date, args.spiky_pov, args.defensibility,
        _read(args.synthesis), _read(args.defensibility_file))
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(body + "\n")

    rel = os.path.join("surveys", fname)
    update_index(os.path.join(atlas_dir, "index.md"), args.date, args.title,
                 args.spiky_pov, args.defensibility, rel)

    sys.stdout.write("wrote %s\nindexed in %s\n" % (fpath, os.path.join(atlas_dir, "index.md")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
