# Changelog Release Collapse + Synthesized Rollup — Design

**Date:** 2026-07-11
**Status:** Approved (pending spec review)

## Problem

Editions show near-duplicate noise from high-frequency changelog sources. In
W28, the Compose Multiplatform source emitted **nine** GitHub release tags in one
week (`v1.12.10-alpha01+dev4438/4434/4419/4413/4443/4403`, plus the
`v1.12.0-beta02+dev4432/4414/4402` train). Each has a unique URL, so the pipeline's
only dedup dimension — normalized-URL identity (`scout.py:53-60`) — treats every
nightly as a distinct story. Each got its own AI summary, producing a wall of
near-identical "incremental improvements" cards.

This is **not** a dedup bug. The URLs are legitimately distinct. The gap is that
"unique URL" ≠ "distinct story worth its own card." Changelog sources are a
firehose of real-but-noisy nightlies.

(Separately, a Reddit repost — the gesture-launcher story submitted twice under
different comment IDs — is content-similarity duplication. **Out of scope** for
this spec; tracked as a follow-up.)

## Goal

For each changelog source, render only its **single newest release** as a card,
and fold the older in-window releases into that card as a **synthesized digest
paragraph** ("Across N builds this week, the ... trains landed ...") plus a
compact, honest list of every collapsed build. Nothing is dropped from the reader's
view — it is *consolidated* into one card. `state/articles.json` is never
mutated; every ingested release stays in state (full git audit trail preserved).

"Newest" = the single most recent tag per source (decided: single newest tag,
not per-release-train). For W28 Compose MP this surfaces
`v1.12.10-alpha01+dev4443` (10 Jul) as the survivor; the `beta02` train and all
older dev builds are folded into its rollup.

## Constraints / Operating Model

- **Scout runs on GitHub Actions** (daily cron, `scout.yml`) — pure deterministic
  fetching, no agent required. Unchanged by this work.
- **Summarize → rollup synthesis → assemble run locally**, agent-in-the-loop,
  because they need an agent to write the summary/digest text. Results are
  committed to `state/` and `site/`. `publish.yml` only deploys the rendered
  `site/`.
- **No in-code Claude calls anywhere.** Every AI step is a *queue → agent →
  apply* cycle (see `summarize.py`). The rollup synthesis MUST follow this same
  pattern — it introduces one more queue file, not an API client.

## Architecture

### New module: `pipeline/rollup.py`

Owns release grouping, the rollup identity, the synthesis queue, and apply.
Keeps `assemble.py` focused on rendering. Well-bounded, unit-testable in
isolation.

- `natural_version_key(title: str) -> tuple`
  Numeric-aware sort key so same-day builds order deterministically:
  `dev4443 > dev4438`, and `1.12.10 > 1.12.9` for semver-tagged sources.
  Extracts runs of digits and compares them as ints, non-digits as text.

- `group_releases(week_articles, source_type_map) -> list[ReleaseGroup]`
  For each source whose `type == "changelog"`, group its in-window articles by
  `source_id`. Within a group, the **survivor** is the max by
  `(date, natural_version_key(title))`; the rest are the **collapsed** set.
  A group with a single release yields survivor + empty collapsed set (no
  rollup). Non-changelog articles are not grouped. Returns the groups; callers
  derive both the kept-article list and the collapse metadata from it. This is
  the single source of grouping truth, shared by assemble and the queue
  generator so they can never disagree.

- `rollup_id(build_ids: Iterable[str]) -> str`
  SHA1 (truncated) of the **sorted set** of collapsed build IDs. Content-keyed:
  stable across re-runs and independent of edition boundaries or input order.
  Same collapsed set → same id → cache hit.

- `--apply <file>` CLI
  Reads agent output `[{rollup_id, summary}, ...]` and writes/updates
  **`state/rollups.json`**:
  `{rollup_id: {summary, source_id, build_ids, generated}}`. Git-audited, so the
  synthesized text is reviewable in history and re-used on re-runs.

### New state file: `state/rollups.json`

Cache of synthesized rollup paragraphs, keyed by `rollup_id`. Committed to the
repo like the other state files.

### Two-pass assemble (mirrors summarize's existing two-pass)

`assemble.py`, after `filter_articles` and before `score_articles`:

1. Call `group_releases`. Build the kept-article list = survivors +
   non-changelog articles. Attach collapse metadata to each survivor that has a
   non-empty collapsed set: the list of collapsed builds `{title, date, url}` and
   the group's `rollup_id`.
2. For each survivor with collapsed builds, look up `rollup_id` in
   `state/rollups.json`:
   - **Hit** → attach the synthesized `rollup_summary` to the survivor.
   - **Miss** → accumulate into `state/rollup-queue.json`; log
     `N rollups need synthesis`. Assemble still completes and renders, using a
     **graceful fallback**: the collapsed build list with no synthesized prose.
3. If a queue was written, print the operator instruction (same shape as
   summarize): run the agent on `rollup-queue.json`, then
   `python3.11 pipeline/rollup.py --apply <file>`, then re-run assemble.

Second assemble pass → cache hits → survivor cards render the synthesized digest.

### Rendering (`_assemble/render.py` + `site/template.html`)

The survivor card renders its normal headline + summary, plus a **"This week's
builds"** block when it has collapsed builds:
- the synthesized `rollup_summary` paragraph when present;
- a compact list of every collapsed build (tag + date + link), shown **either
  way**, so the full run is always visible and nothing is silently hidden.

`build_data_block` carries `rollup_summary` and `collapsed_builds` per article
into the data block; the template renders the block conditionally.

## Queue formats

`state/rollup-queue.json` (assemble → agent):
```json
[{ "rollup_id": "…", "source_id": "lib-compose-multiplatform",
   "survivor": {"title": "…", "date": "…", "url": "…"},
   "builds": [{"title": "…", "date": "…", "url": "…", "summary": "…", "excerpt": "…"}] }]
```

Agent output (→ `--apply`):
```json
[{ "rollup_id": "…", "summary": "Across 9 dev builds this week, …" }]
```

## Scope boundaries

- Applies to **all 21 `changelog` sources**, not just Compose MP. A run of
  Ktor/Coil/etc. releases in one week collapses the same way.
- `state/articles.json` is never mutated — collapse and rollup are
  assemble-time / synthesis-time only.
- Reddit repost / content-similarity dedup is **out of scope** (follow-up).
- Scout / GitHub Actions are unchanged.

## Testing

Unit (`pipeline/rollup.py`):
- `group_releases`: newest-per-source survivor; same-day tiebreak picks higher
  dev number via `natural_version_key`; semver tiebreak (`1.12.10 > 1.12.9`);
  non-changelog (blog) articles untouched; singleton group → empty collapsed set.
- `rollup_id`: order-independent, set-based; different sets → different ids.
- `--apply`: writes and updates `state/rollups.json` by id.

Integration:
- assemble with a pre-populated `rollups.json` attaches `rollup_summary` to the
  survivor card.
- assemble with a missing rollup writes `rollup-queue.json` and renders the
  fallback build list.

End-to-end: regenerate W28 and confirm Compose MP shows one survivor card with
the rollup, and the nightly flood is gone from the render.
