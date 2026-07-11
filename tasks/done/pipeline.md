# Pipeline: Replace hardcoded site with dynamic weekly content

Replace the hardcoded article arrays in `site/index.html` with a real pipeline
that scouts sources, scores topics, summarizes articles, and assembles the page.

---

## Step 1 — Scout (`pipeline/scout.py`)

**Inputs:** `sources/sources.yml`, `state/source_health.json`, `state/articles.json`
**Outputs:** `state/articles.json` (appended), `state/source_health.json` (updated)

### Per-source loop

- [x] Load `last_article_date` from health file — default to 7 days ago on first run
- [x] Fetch: try `rss`/`atom` field via `feedparser` first; fall back to scraping `url` with `httpx` + `BeautifulSoup`
- [x] Detect article dates in priority order:
  1. RSS `<pubDate>` / `<dc:date>`
  2. OpenGraph `article:published_time`
  3. JSON-LD `datePublished`
  4. HTML `<time datetime="...">` tag
  5. URL date pattern (e.g. `/2026/07/03/title`)
  6. Flag `date_uncertain: true` if nothing found
- [x] Filter: keep only articles newer than `last_article_date` and not already in `articles.json` (URL dedup — strip query params + trailing slash)
- [x] Store each new article: `{id, title, url, date, source_id, excerpt, date_uncertain, summarized: false}`
- [x] Update source health: compute `days_since_last`, derive state, increment `consecutive_empty_cycles` if zero new articles

### Health state rule (from `cadence_days` per source)

```
active   → days_since_last <= cadence_days * 1.5
slowing  → <= cadence_days * 3
stale    → <= cadence_days * 6
dead     → beyond → open GitHub Issue automatically
```

### Source-type strategies

| Type | Strategy |
|---|---|
| `blog` with RSS/Atom | feedparser, straightforward |
| `changelog` (GitHub releases) | Atom feed — always has clean dates and version tags |
| `discussion` (Reddit) | RSS, but keyword-filter titles to cut noise before storing |
| `slack-mirror` | Scrape public archive for the past 7 days on Sunday — topic signal only, not stored as articles |
| `conference` | Stub in v1 — scraping schedule pages is complex, add later |

**JetBrains blog** — filter at ingest: only keep posts whose title or tags contain Kotlin/Android/KMP keywords (the feed covers all JetBrains products)

### After the loop

- [x] Prune `articles.json` to 90-day rolling window
- [x] Write both state files atomically (write to `.tmp` then rename)
- [x] Print summary: `N new articles from X sources, Y slowing, Z dead`

**Libraries:** `feedparser`, `httpx`, `PyYAML`, `beautifulsoup4`

---

## Step 2 — Bible (`pipeline/bible.py`)

**Inputs:** `state/articles.json` (new articles), `topics/topics.yml`, `state/bible.json`
**Outputs:** `state/bible.json` (updated scores + history appended)

- [x] Read new articles from this run's cycle
- [x] For each article: match title + excerpt against topic keywords, boost matched topic scores by source weight
  - Source weights: `conference 3.0 · changelog 2.5 · blog 2.0 · discussion 1.5 · slack-mirror 1.0`
- [x] Apply daily decay to all topics: `score = score * 0.92`
- [x] Auto-emerge: if an AI-extracted term appears in ≥3 articles this cycle and isn't in the bible, add it (flagged `unvetted: true`)
- [x] Append today's entry `{date, mentions, score}` to each topic's history — **never prune, full history kept permanently**
- [x] Write updated `bible.json`

---

## Step 3 — Summarize (`pipeline/summarize.py`)

**Inputs:** `state/articles.json` (unsummarized), `ANTHROPIC_API_KEY`
**Outputs:** `state/articles.json` (summary + tags + optional snippet written back)

- [x] Read articles where `summarized: false`
- [x] For each: fetch full article content (or use RSS description if ≥300 words)
- [x] Call Claude with:
  - Summary: 2–3 sentences, max ~50 words, no marketing language, focus on what's new and why it matters
  - Topic tags: match against top-N bible topics (semantic, not keyword-only)
  - Code snippet: extract only if the article has a concrete API change expressible in ≤10 lines of Kotlin/Swift — otherwise omit
- [x] Mark `summarized: true`, store `{summary, topics, code_snippet, snippet_label}`
- [x] Write updated `articles.json`

---

## Step 4 — Assemble (`pipeline/assemble.py`)

**Inputs:** `--edition 2026-W27`, `state/bible.json`, `state/articles.json`
**Outputs:** `site/index.html`

- [x] Derive 7-day date range from `--edition` (ISO week → Mon–Sun dates)
- [x] Filter `articles.json` to articles within that date window
- [x] Look up bible scores **point-in-time**: use each topic's score from the last day of the target week in the history array — not the current score (enables accurate historical runs)
- [x] Recompute `placement_score` per article at assembly time using those point-in-time bible scores: `sum(bible_score for matched_topics)`
- [x] Cluster articles into chapters by topic cluster, order chapters by aggregate placement score
- [x] Assign column width within each chapter by score rank:
  - Rank 1 in chapter → `c12` (full-width flagship)
  - Rank 2–3 → `c8`
  - Rank 4–6 → `c6`
  - Rank 7+ → `c4`
- [x] Render `site/index.html` — replace hardcoded JS data arrays with real content
- [x] Set edition label, week number, and date range in masthead and page title

---

## Step 5 — GitHub Actions: daily scout

- [x] Wire `scout.yml` to run steps 1–2 on schedule (06:00 UTC daily) — summarize is agent-driven, not automated
- [x] Commit updated state files to repo after each run

## Step 6 — GitHub Actions: publish

- [x] Wire `publish.yml` to run step 4 on `workflow_dispatch`
- [x] `edition_label` input (e.g. `2026-W27`) passed to assemble — enables historical week runs
- [x] Commit updated `site/index.html`
- [x] Trigger GitHub Pages deploy

---

## Editorial decisions (locked)

- **Publication window**: 7 days per edition (assemble filters to that week only)
- **Storage window**: 90 days in `articles.json` (articles are bulk); `bible.json` history is permanent and never pruned
- **Cadence**: scout runs daily, publish runs Sunday evening for Monday morning
- **Summary cap**: ~50 words, 2–3 sentences, no marketing language
- **Snippet criteria**: yes if article has a concrete API change expressible in ≤10 lines of Kotlin/Swift

---

## Decisions needed before writing code

- [x] Column-width rule: rank 1→c12, rank 2-3→c8, rank 4-6→c6, rank 7+→c4
