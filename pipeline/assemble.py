#!/usr/bin/env python3.11
"""
Step 4 — Assemble: cluster articles into chapters, render site/index.html.

Usage:
  python3.11 pipeline/assemble.py --edition 2026-W28
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
ARTICLES_FILE = ROOT / "state" / "articles.json"
BIBLE_FILE = ROOT / "state" / "bible.json"
SOURCES_FILE = ROOT / "sources" / "sources.yml"
TOPICS_FILE = ROOT / "topics" / "topics.yml"
TEMPLATE_FILE = ROOT / "site" / "template.html"
OUTPUT_FILE = ROOT / "site" / "index.html"

sys.path.insert(0, str(ROOT))

from pipeline._assemble.dates import edition_to_dates
from pipeline._assemble.scores import lookup_scores_at
from pipeline._assemble.articles import filter_articles, score_articles, cluster_articles
from pipeline._assemble.render import build_data_block, inject_data


def write_atomic(path: Path, text: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", required=True, help="e.g. 2026-W28")
    args = parser.parse_args()

    start, end = edition_to_dates(args.edition)
    print(f"  Edition {args.edition}: {start} → {end}")

    articles = json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    bible = json.loads(BIBLE_FILE.read_text(encoding="utf-8"))
    topics_config = yaml.safe_load(TOPICS_FILE.read_text(encoding="utf-8"))
    sources_config = yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))
    template = TEMPLATE_FILE.read_text(encoding="utf-8")

    clusters = topics_config.get("clusters", [])
    source_type_map = {s["id"]: s.get("type", "blog") for s in sources_config.get("sources", [])}

    scores = lookup_scores_at(bible, end)

    week_articles = filter_articles(articles, start, end)
    week_articles = score_articles(week_articles, scores)
    print(f"  {len(week_articles)} articles in window")

    chapters = cluster_articles(week_articles, clusters)
    total_arts = sum(len(ch["articles"]) for ch in chapters)
    print(f"  {len(chapters)} chapters, {total_arts} placed articles")

    data_block = build_data_block(
        edition=args.edition,
        start=start,
        end=end,
        chapters=chapters,
        bible=bible,
        source_type_map=source_type_map,
        clusters=clusters,
    )
    html = inject_data(template, data_block)

    # Patch masthead edition label and title
    edition_display = args.edition.replace("-W", "·W")
    html = html.replace("2026·W27", edition_display)
    html = html.replace("Kotlin Digest — 2026·W27", f"Kotlin Digest — {edition_display}")

    write_atomic(OUTPUT_FILE, html)
    print(f"  Written → site/index.html")


if __name__ == "__main__":
    main()
