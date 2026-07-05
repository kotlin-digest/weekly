# Android Digest

An open-source, AI-assembled magazine for Android, Kotlin, and KMP developers.

Scouts the community, scores what the world is talking about, and assembles readable editions — hosted on GitHub Pages, personalized by cookies.

---

## What it does

1. **Scouts** registered sources — blogs, conference talks, Kotlin Slack — using article publication dates (not HTML diffs) to detect what's new
2. **Tracks source health** — knows each source's typical cadence, flags stale or dead sources
3. **Builds a Topic Bible** — a living graph of terms the Kotlin world is actively discussing, scored by daily mention volume and decayed over time so trending topics rise and old ones fade
4. **Assembles editions** — AI-summarized articles tagged to bible topics, structured into chapters positioned by topic weight
5. **Publishes to GitHub Pages** — static site, reader preferences stored in cookies (filters, keywords, topic types), gracefully degraded if cookies are absent

---

## Core goals

- **Open content pipeline** — community can open PRs to add or remove sources via `sources/sources.yml`
- **Transparent topic scoring** — the bible is versioned; you can see how scores evolved over time
- **No server required** — GitHub Actions runs the daily scout; a manual trigger publishes editions
- **Reader sovereignty** — cookie preferences are simple checkboxes; losing your cookies doesn't break anything
- **Language-first English, community-extended** — content starts in English, translation PRs welcome as it grows
- **Editorial keyword control** — readers can set keywords to always include or always exclude

---

## Repository layout

```
android-digest/
├── sources/
│   └── sources.yml          # Registered sources — PRs welcome
├── topics/
│   └── topics.yml           # Curated baseline topic list
├── pipeline/                # Python pipeline (scout → score → assemble)
│   ├── scout.py             # Source freshness check + article ingestion
│   ├── bible.py             # Topic scoring and decay engine
│   ├── summarize.py         # AI summarization + topic tagging
│   └── assemble.py          # Chapter builder + edition renderer
├── site/                    # GitHub Pages output (committed by Actions)
│   └── index.html
├── docs/
│   ├── architecture.md      # Full system design
│   ├── pipeline.md          # Pipeline stage detail
│   ├── topic-bible.md       # Scoring and decay model
│   └── sources.md           # Source health tracking model
├── .github/
│   └── workflows/
│       ├── scout.yml        # Daily scheduled pipeline run
│       └── publish.yml      # Manual edition publish trigger
└── CONTRIBUTING.md          # How to add sources, topics, translations
```

---

## Architecture at a glance

```
[sources.yml + topics.yml]
         ↓
    [Scout Engine]
    • fetch articles newer than last-seen date
    • record source cadence + health
         ↓
    [Topic Bible]
    • score ++ per article mention
    • daily decay on all scores
    • historical volume graph per topic
         ↓
    [AI Aggregator]
    • summarize each article
    • tag with matching bible topics
    • score-weighted placement signal
         ↓
    [Chapter Assembler]
    • group stories by chapter (topic clusters)
    • position chapters by current bible weight
    • apply reader keyword filters
         ↓
    [GitHub Pages]
    • static HTML edition
    • cookie-stored reader prefs
    • keyword include/exclude filters
```

---

## Tech stack

| Layer | Tool |
|---|---|
| Pipeline language | Python 3.12 |
| RSS parsing | `feedparser` |
| HTML scraping | `httpx` + `BeautifulSoup` |
| AI summarization | Claude API (`claude-sonnet-4-6`) |
| Scheduling | GitHub Actions (cron) |
| Topic state | `bible.json` committed to repo |
| Site rendering | Jinja2 → static HTML |
| Hosting | GitHub Pages |
| Reader preferences | Browser cookies (no server) |
| Configuration | YAML |

---

## Roadmap

- [ ] v0.1 — source scout + staleness detection
- [ ] v0.2 — topic bible scoring + decay
- [ ] v0.3 — AI summarization + tagging
- [ ] v0.4 — chapter assembly + first edition
- [ ] v0.5 — GitHub Pages site + cookie preferences
- [ ] v1.0 — community PRs, keyword filters, multi-language scaffold
