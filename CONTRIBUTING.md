# Contributing to Kotlin Digest

This is a community project. The pipeline, sources, and topic definitions are all open. PRs are the primary contribution mechanism.

---

## Adding a source

Open `sources/sources.yml` and add an entry:

```yaml
- id: your-source-id          # unique, kebab-case
  name: "Human-readable name"
  url: "https://example.com/"
  rss: "https://example.com/feed/"    # optional but strongly preferred
  type: blog                  # blog | news | conference | changelog | slack-mirror
  language: en                # ISO 639-1 code
  cadence_days: 7             # how often this source typically publishes
  topics: [kotlin, compose]   # editorial hints (not exclusive)
```

Open a PR. Include a brief note on why this source adds value.

### Source quality bar

- Must publish original content (not just link roundups of other roundups)
- Must have identifiable publication dates on articles
- Must be actively maintained (published within the last 90 days)
- Language must be declared accurately

---

## Adding or editing topics

Open `topics/topics.yml`. Topics can be added to the seeded list or to a cluster. PRs to reorganize clusters are welcome too.

Auto-emerged topics (flagged `needs_review: true` in `state/bible.json`) can be formalized here once someone verifies they're meaningful.

---

## Translations

The site is English-first. To add a translated edition:

1. Add a language entry to `sources/sources.yml` with `language: xx`
2. Open `site/i18n/xx.json` with translated UI strings (copy from `en.json`)
3. The assembler will group non-English articles into a separate language section

Translation of AI-generated summaries is on the roadmap but not yet implemented.

---

## Opening a PR for a dead source

If you notice a source hasn't published in a long time, open a PR removing it from `sources/sources.yml`. Include the last known article URL and date in the PR description.

---

## Code contributions

The pipeline lives in `pipeline/`. Each stage is a self-contained Python module. Tests live in `pipeline/tests/`. All contributions must pass CI (lint + tests) before merge.

Dependencies are pinned in `pipeline/requirements.txt`.
