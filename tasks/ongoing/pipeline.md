# Pipeline: Replace hardcoded site with dynamic weekly content

Replace the hardcoded article arrays in `site/index.html` with a real pipeline
that scouts sources, scores topics, summarizes articles, and assembles the page.

---

## Step 1 — Scout (`pipeline/scout.py`)

- [ ] Read `sources/sources.yml`, fetch each RSS feed / scrape each URL
- [ ] Detect articles published since last run (date-based dedup)
- [ ] Append new articles to `state/articles.json`
- [ ] Update per-source health in `state/source_health.json` (active / slowing / stale / dead)

## Step 2 — Bible (`pipeline/bible.py`)

- [ ] Read new articles + `topics/topics.yml`
- [ ] Boost topic scores for keyword matches in title/content
- [ ] Apply daily decay to all scores
- [ ] Write updated scores + 90-day history to `state/bible.json`

## Step 3 — Summarize (`pipeline/summarize.py`)

- [ ] Read unsummarized articles from `state/articles.json`
- [ ] Call Claude per article: 2–3 sentence summary, topic tags, optional code snippet
- [ ] Decide snippet criteria: does the article's core point fit in ≤10 lines of Kotlin/Swift?
- [ ] Write results back into `state/articles.json`

## Step 4 — Assemble (`pipeline/assemble.py`)

- [ ] Accept `--edition` flag (e.g. `2026-W27`) and derive the 7-day date range from it
- [ ] Read `state/bible.json` + `state/articles.json`, filter to articles within that 7-day window
- [ ] Cluster articles into chapters ordered by topic score
- [ ] Assign column width per article (c12 / c8 / c6 / c4) based on score rank within chapter
- [ ] Render `site/index.html` — replace hardcoded JS data arrays with real content
- [ ] Update edition label in page title and masthead from `--edition`

## Step 5 — GitHub Actions: daily scout

- [ ] Wire `scout.yml` to run steps 1–3 on schedule (06:00 UTC daily)
- [ ] Commit updated state files to repo after each run

## Step 6 — GitHub Actions: publish

- [ ] Wire `publish.yml` to run step 4 on `workflow_dispatch`
- [ ] `edition_label` input (e.g. `2026-W27`) passed to assemble — enables historical week runs
- [ ] Commit updated `site/index.html`
- [ ] Trigger GitHub Pages deploy

---

## Editorial decisions (locked)

- **Publication window**: 7 days per edition (assemble filters to that week only)
- **Storage window**: 90 days in `articles.json` — enables re-running any past week
- **Cadence**: scout runs daily, publish runs Sunday evening for Monday morning

---

## Decisions needed before writing code

- [ ] Column-width rule: what score threshold earns c12 vs c8 vs c6 vs c4?
- [ ] Summary length cap to pass to Claude (target: ~50 words)
- [ ] Snippet criteria finalized (tentative: yes if article has a concrete API change expressible in ≤10 lines)
