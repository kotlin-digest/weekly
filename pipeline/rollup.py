#!/usr/bin/env python3.11
"""
Changelog release collapse + synthesized rollup.

High-frequency changelog sources (GitHub release feeds) emit many near-identical
nightly/dev builds in a single week. Each has a unique URL, so URL dedup treats
every one as a distinct story — producing a wall of near-identical cards.

This module collapses each changelog source to its single newest *renderable*
release and folds the rest into that survivor card as a rollup: a compact list of
the collapsed builds plus an agent-synthesized digest paragraph.

The synthesis follows the same agent-driven pattern as summarize.py — no in-code
API calls. assemble emits a queue (state/rollup-queue.json), an agent writes the
paragraphs, and `--apply` caches them in state/rollups.json keyed by rollup_id.

Usage:
  python3.11 pipeline/rollup.py --apply state/rollup-summaries.json
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
ROLLUPS_FILE = ROOT / "state" / "rollups.json"
QUEUE_FILE = ROOT / "state" / "rollup-queue.json"


# ── version ordering ──────────────────────────────────────────────────────────

def natural_version_key(title: str):
    """Numeric-aware sort key so same-day builds order deterministically.

    Splits the title into runs of digits and non-digits; digit runs compare as
    ints, text runs as strings. `dev4443 > dev4438` and `1.12.10 > 1.12.9`.
    The (0/1) type tag keeps ints and strings from being compared directly.
    """
    tokens = re.findall(r"\d+|\D+", title or "")
    return tuple((1, int(t)) if t.isdigit() else (0, t) for t in tokens)


def _renderable(article: dict) -> bool:
    """An article that would survive cluster_articles — i.e. has topics.

    Unsummarized builds (topics is None/empty) are not shown in the edition, so
    they must never be chosen as the survivor (that would blank out the card).
    """
    return bool(article.get("topics"))


def _release_sort_key(article: dict):
    return (article.get("date", ""), natural_version_key(article.get("title", "")))


# ── grouping ──────────────────────────────────────────────────────────────────

def group_releases(articles: list, source_type_map: dict) -> list:
    """Group renderable changelog releases per source.

    Returns a list of {source_id, survivor, collapsed} — one per changelog source
    that has at least one renderable release in the given (already window-filtered)
    article list. The survivor is the newest by (date, natural_version_key); the
    rest are the collapsed set. Non-changelog articles are ignored. The result is
    sorted by source_id for determinism.
    """
    by_source: dict = {}
    for a in articles:
        if source_type_map.get(a.get("source_id"), "blog") != "changelog":
            continue
        if not _renderable(a):
            continue
        by_source.setdefault(a["source_id"], []).append(a)

    groups = []
    for source_id, arts in by_source.items():
        ordered = sorted(arts, key=_release_sort_key, reverse=True)
        groups.append({
            "source_id": source_id,
            "survivor": ordered[0],
            "collapsed": ordered[1:],
        })
    return sorted(groups, key=lambda g: g["source_id"])


def rollup_id(build_ids) -> str:
    """Stable, order-independent id for a set of build ids (content-keyed cache)."""
    key = "|".join(sorted(set(build_ids)))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def _build_ref(article: dict) -> dict:
    return {
        "title": article.get("title", ""),
        "date": article.get("date", ""),
        "url": article.get("url", ""),
    }


def collapse(articles: list, source_type_map: dict):
    """Collapse changelog sources to their survivor; return (kept, rollups).

    kept    — non-changelog/ungrouped articles untouched, plus one survivor per
              changelog source. A survivor that folded builds gets `collapsed_builds`
              (list of {title,date,url}) and `rollup_id` attached.
    rollups — queue entries for groups that actually collapsed something, each
              {rollup_id, source_id, survivor, builds} where builds carry the
              folded releases' summaries/excerpts for the synthesis agent.
    """
    groups = group_releases(articles, source_type_map)
    grouped_ids = set()
    for g in groups:
        grouped_ids.add(g["survivor"]["id"])
        grouped_ids.update(c["id"] for c in g["collapsed"])

    kept = [a for a in articles if a["id"] not in grouped_ids]

    rollups = []
    for g in groups:
        survivor = dict(g["survivor"])
        if g["collapsed"]:
            rid = rollup_id([survivor["id"]] + [c["id"] for c in g["collapsed"]])
            survivor["collapsed_builds"] = [_build_ref(c) for c in g["collapsed"]]
            survivor["rollup_id"] = rid
            rollups.append({
                "rollup_id": rid,
                "source_id": g["source_id"],
                "survivor": _build_ref(survivor),
                "builds": [
                    {**_build_ref(c),
                     "summary": c.get("summary", ""),
                     "excerpt": c.get("excerpt", "")}
                    for c in g["collapsed"]
                ],
            })
        kept.append(survivor)
    return kept, rollups


# ── cache (state/rollups.json) ────────────────────────────────────────────────

def load_rollups(path: Path = ROLLUPS_FILE) -> dict:
    """Load the synthesized-rollup cache; {} if it doesn't exist yet."""
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, data: object) -> None:
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(path)


def write_queue(entries: list, path: Path = QUEUE_FILE) -> None:
    """Write rollups needing synthesis for the agent to process."""
    _write_atomic(path, entries)


def apply_rollups(entries: list, path: Path = ROLLUPS_FILE) -> int:
    """Merge agent-produced rollup summaries into the cache, keyed by rollup_id."""
    cache = load_rollups(path)
    for e in entries:
        rid = e["rollup_id"]
        cache[rid] = {k: v for k, v in e.items() if k != "rollup_id"}
    _write_atomic(path, cache)
    return len(entries)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--apply":
        src = Path(sys.argv[2])
        if not src.exists():
            print(f"[!] File not found: {src}", file=sys.stderr)
            sys.exit(1)
        n = apply_rollups(json.loads(src.read_text(encoding="utf-8")))
        print(f"  Applied {n} rollup summaries to {ROLLUPS_FILE.name}")
    else:
        print("usage: python3.11 pipeline/rollup.py --apply <summaries.json>", file=sys.stderr)
        sys.exit(2)
