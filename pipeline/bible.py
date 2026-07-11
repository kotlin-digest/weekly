#!/usr/bin/env python3.11
"""
Step 2 — Bible: boost topic scores from new articles, apply decay, surface emergence candidates.

Inputs:  state/articles.json, topics/topics.yml, state/bible.json
Outputs: state/bible.json (updated scores + history), state/candidates.json (for interactive review)
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import nltk
import yaml

nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords as nltk_corpus

ROOT = Path(__file__).parent.parent
ARTICLES_FILE = ROOT / "state" / "articles.json"
BIBLE_FILE = ROOT / "state" / "bible.json"
CANDIDATES_FILE = ROOT / "state" / "candidates.json"
TOPICS_FILE = ROOT / "topics" / "topics.yml"
SOURCES_FILE = ROOT / "sources" / "sources.yml"

TODAY = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

# NLTK English stopwords + domain-specific extras that NLTK doesn't cover
STOPS = set(nltk_corpus.words("english")) | {
    "alpha", "beta", "stable", "preview", "release", "update", "version",
    "build", "series", "part", "detail", "details", "article", "blog",
    "guide", "post", "week", "month", "year",
    "january", "february", "march", "april", "june", "july", "august",
    "september", "october", "november", "december",
    "development", "apps", "complete", "studio", "introducing", "library",
    "platform", "support", "feature", "features", "change", "changes",
    # Already in bible as seeds — skip as candidates
    "android", "kotlin", "code",
}


# ── Topic matching ────────────────────────────────────────────────────────────

def build_matchers(topics):
    """topic_id → set of lowercase match terms."""
    matchers = {}
    for t in topics:
        tid = t["id"]
        label = t.get("label", "")
        terms = {tid.lower(), label.lower()}
        parts = tid.split("-")
        if len(parts) > 1:
            for part in parts:
                if len(part) > 4 and part.lower() not in STOPS:
                    terms.add(part.lower())
        for word in re.findall(r"[a-zA-Z][a-zA-Z0-9]{3,}", label):
            w = word.lower()
            if w not in STOPS:
                terms.add(w)
        matchers[tid] = terms
    return matchers


def article_text(article):
    return (article.get("title", "") + " " + article.get("excerpt", "")).lower()


def match_topics(text, matchers):
    return [tid for tid, terms in matchers.items() if any(t in text for t in terms)]


# ── Bible term reverse map ────────────────────────────────────────────────────

def build_bible_term_map(bible):
    """Maps lowercase term/label/id-part → bible_id for spaCy → known topic lookup."""
    term_to_id = {}
    for tid, entry in bible.items():
        if tid.startswith("_"):
            continue
        term_to_id[tid.lower()] = tid
        label = entry.get("label", "").lower()
        if label:
            term_to_id[label] = tid
        for part in tid.split("-"):
            pl = part.lower()
            if len(pl) >= 4 and pl not in term_to_id:
                term_to_id[pl] = tid
    return term_to_id


# ── Atomic write ──────────────────────────────────────────────────────────────

def write_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.rename(path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    with open(TOPICS_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    scoring = config.get("scoring", {})
    decay = scoring.get("decay_factor", 0.92)
    raw_weights = scoring.get("source_weights", {})
    source_weights = dict(raw_weights)
    source_weights.setdefault("discussion", raw_weights.get("news", 1.5))
    source_weights.setdefault("blog", 2.0)
    emergence_threshold = scoring.get("emergence_threshold", 3)
    seed_topics = config.get("topics", [])

    articles = json.loads(ARTICLES_FILE.read_text(encoding="utf-8")) if ARTICLES_FILE.exists() else []

    is_initial = not BIBLE_FILE.exists()
    bible = json.loads(BIBLE_FILE.read_text(encoding="utf-8")) if BIBLE_FILE.exists() else {}

    for t in seed_topics:
        if t["id"] not in bible:
            bible[t["id"]] = {
                "score": 0.0,
                "label": t.get("label", t["id"]),
                "history": [],
            }

    last_run = None if is_initial else (bible.get("_meta") or {}).get("last_run")
    new_articles = articles if not last_run else [
        a for a in articles if a.get("date") and a["date"] > last_run
    ]

    source_type_map = {}
    if SOURCES_FILE.exists():
        with open(SOURCES_FILE, encoding="utf-8") as f:
            sc = yaml.safe_load(f)
        for s in sc.get("sources", []):
            source_type_map[s["id"]] = s.get("type", "blog")

    matchers = build_matchers(seed_topics)
    bible_term_map = build_bible_term_map(bible)

    # Load spaCy — graceful fallback to keyword-only if model missing
    nlp = None
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        print("  [!] spaCy unavailable — run: python -m spacy download en_core_web_sm")

    topic_mentions = Counter()
    topic_boost = {}
    candidate_articles = defaultdict(set)  # term → set of article_ids

    for article in new_articles:
        text = article_text(article)
        src_type = source_type_map.get(article.get("source_id", ""), "blog")
        weight = source_weights.get(src_type, source_weights["blog"])

        # Keyword matches
        matched = set(match_topics(text, matchers))

        # spaCy: PROPN + NER on title → boost known topics or queue candidates
        if nlp:
            doc = nlp(article.get("title", ""))
            spacy_terms = set()

            for ent in doc.ents:
                term = ent.text.strip().lower()
                if len(term) >= 3 and term not in STOPS:
                    spacy_terms.add(term)
            for token in doc:
                if token.pos_ == "PROPN" and not token.is_stop and len(token.text) >= 4:
                    term = token.text.lower()
                    if term not in STOPS:
                        spacy_terms.add(term)

            for term in spacy_terms:
                if term in bible_term_map:
                    matched.add(bible_term_map[term])  # reinforce known topic
                else:
                    candidate_articles[term].add(article["id"])  # new candidate

        for tid in matched:
            topic_mentions[tid] += 1
            topic_boost[tid] = topic_boost.get(tid, 0.0) + weight

    # Apply decay + boost; append history
    for tid, entry in bible.items():
        if tid.startswith("_"):
            continue
        old_score = entry.get("score", 0.0)
        new_score = old_score * decay + topic_boost.get(tid, 0.0)
        entry["score"] = round(new_score, 4)
        entry.setdefault("history", []).append({
            "date": TODAY,
            "mentions": topic_mentions.get(tid, 0),
            "score": round(new_score, 4),
        })

    # Surface emergence candidates — filtered by STOPS + threshold + not-in-bible
    known_terms = set(bible_term_map.keys())
    raw_candidates = sorted(
        [
            (term, len(ids))
            for term, ids in candidate_articles.items()
            if len(ids) >= emergence_threshold
            and term not in known_terms
            and term not in STOPS
            and len(term) >= 4
            and not re.search(r"\d", term)  # drop version strings and years
        ],
        key=lambda x: -x[1],
    )

    # Save candidates with article context for interactive curation
    candidates_out = []
    for term, count in raw_candidates:
        ids = candidate_articles[term]
        titles = [a["title"] for a in new_articles if a["id"] in ids][:3]
        candidates_out.append({"term": term, "count": count, "seen_in": titles})

    if candidates_out:
        write_atomic(CANDIDATES_FILE, candidates_out)

    bible["_meta"] = {"last_run": TODAY}
    write_atomic(BIBLE_FILE, bible)

    # ── Summary ───────────────────────────────────────────────────────────────
    boosted = sum(1 for tid in topic_mentions if topic_mentions[tid] > 0)
    top = sorted(
        [
            (tid, e["score"])
            for tid, e in bible.items()
            if not tid.startswith("_") and not e.get("auto_emerged")
        ],
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    print(f"  {len(new_articles)} articles  |  {boosted} topics boosted  |  {len(raw_candidates)} emergence candidates")

    if raw_candidates:
        print(f"\n  Emergence candidates (state/candidates.json):")
        for term, count in raw_candidates:
            print(f"    {term:<30} {count}x")

    print(f"\n  Top topics:")
    for tid, score in top:
        label = bible[tid].get("label", tid)
        print(f"    {label:<35} {score:>7.1f}")


if __name__ == "__main__":
    main()
