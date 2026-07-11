# Summarization Workflow Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `state/summaries.json` from `state/queue.json` so that `make apply` can write topics + summaries back into `articles.json`, enabling the assembler to cluster real articles into chapters.

**Architecture:** An agent (Claude Code or Codex) reads `state/queue.json`, processes each article in batches, and writes `state/summaries.json`. No API key or LLM call is made from code — the agent running this plan IS the LLM. After `make apply`, articles gain `topics`, `summary`, and optional `code_snippet` fields, and `make assemble EDITION=...` produces a live site.

**Tech Stack:** Python 3.11, `make`, existing `pipeline/summarize.py`

## Global Constraints

- Summary: 2–3 sentences, ≤50 words, no marketing language ("exciting", "powerful", "game-changing"), focus on what's new and why it matters to developers
- Topics: 1–4 IDs from the 59 valid bible topics listed below — semantic match, not keyword-only; omit if no clear match
- Code snippet: only if the article shows a concrete API change expressible in ≤10 lines of Kotlin or Swift; omit otherwise
- Output IDs must match the `id` field in `queue.json` exactly — a mismatch silently drops that article
- Process all articles; do not skip low-quality or short ones — write a minimal summary from the title + excerpt if content is unavailable

**Valid topic IDs (59 total):**
`adaptive-ui`, `android-api`, `android-auto`, `android-developers`, `animation`, `architecture`, `build-logic`, `clean-architecture`, `compose`, `compose-multiplatform`, `context-receivers`, `coroutines`, `datastore`, `droidcon`, `exposed`, `flows`, `google-io`, `gradle`, `gradle-plugin`, `hilt`, `ios-interop`, `jetbrains`, `jetpack`, `k2-compiler`, `kapt`, `kmp`, `kodein`, `koin`, `kotlin`, `kotlin-backend`, `kotlin-js`, `kotlin-scripting`, `kotlin-stdlib`, `kotlinconf`, `ksp`, `ktor`, `ktor-server`, `material3`, `media3`, `mvi`, `mvvm`, `navigation`, `okhttp`, `paparazzi`, `r8-proguard`, `retrofit`, `room`, `sealed-classes`, `shot`, `spring-kotlin`, `swift-export`, `testing`, `turbine`, `value-classes`, `version-catalog`, `viewmodel`, `wasm`, `wear-os`, `workmanager`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `state/queue.json` | Read | Fetched article content, produced by `make fetch` |
| `state/summaries.json` | Create | Agent-produced summaries, consumed by `make apply` |
| `state/articles.json` | Modified by make apply | Gets topics + summaries written back |
| `site/index.html` | Modified by make assemble | Final rendered output |

---

## Task 1: Produce state/queue.json

**Files:**
- Writes: `state/queue.json`

- [ ] **Step 1: Run fetch**

```bash
python3.11 pipeline/summarize.py > state/queue.json
```

Watch stderr for progress. Expect ~187 articles. If a URL fails, the content field will say `[fetch error: ...]` — that's fine, use the title + excerpt for those.

Expected output on stderr:
```
Fetching content for 187 articles...
  [1/187] Introducing the Kotlin Benchmark for AI Coding Agents
  [2/187] ...
```

- [ ] **Step 2: Verify the file**

```bash
python3.11 -c "
import json; data = json.load(open('state/queue.json'))
print(f'{len(data)} articles in queue')
print('First:', data[0]['id'], '-', data[0]['title'][:60])
"
```

Expected: `187 articles in queue`

---

## Task 2: Summarize each article and produce state/summaries.json

**Files:**
- Reads: `state/queue.json`
- Creates: `state/summaries.json`

Each item in queue.json has:
```json
{
  "id": "3c654d42e44bf872",
  "title": "Introducing the Kotlin Benchmark for AI Coding Agents",
  "url": "https://...",
  "date": "2026-07-08",
  "source_id": "kotlin-blog",
  "excerpt": "Agentic coding benchmarks...",
  "content": "...full article text (up to 6000 chars)..."
}
```

Each item you produce in summaries.json must be:
```json
{
  "id": "3c654d42e44bf872",
  "summary": "JetBrains released a new benchmark...",
  "topics": ["kotlin", "k2-compiler"],
  "code_snippet": "fun main() {\n  ...\n}",
  "snippet_label": "BENCHMARK SETUP"
}
```

`code_snippet` and `snippet_label` are optional — omit the keys entirely if no snippet applies.

**Decision rules:**

| Field | Rule |
|---|---|
| summary | 2-3 sentences, ≤50 words. Focus: what changed, why it matters for Android/KMP/Kotlin devs. Never say "this article", "the author", "exciting". |
| topics | Match semantically: a Kotlin 2.x features article → `["kotlin", "k2-compiler"]`. A Compose animation deep-dive → `["compose", "animation"]`. Max 4 topics. If genuinely unclassifiable, use `[]`. |
| code_snippet | Only if article shows a ≤10-line concrete API change. Kotlin or Swift only. Strip imports. |
| snippet_label | Short ALL-CAPS label describing what the snippet shows, e.g. `"NEW API"`, `"MIGRATION"`, `"CONFIG"`. |

- [ ] **Step 1: Read queue.json**

```bash
python3.11 -c "
import json
data = json.load(open('state/queue.json'))
for i, a in enumerate(data):
    print(f'[{i}] {a[\"id\"]} | {a[\"date\"]} | {a[\"title\"][:70]}')
"
```

This gives you the index, id, date, and title for every article at a glance.

- [ ] **Step 2: Write state/summaries.json**

Process all articles. Write the file as a single JSON array. Example with 2 articles:

```json
[
  {
    "id": "3c654d42e44bf872",
    "summary": "JetBrains launched a Kotlin-specific benchmark suite to evaluate AI coding agents on real-world tasks like refactoring and API migration. It targets models and agents used in IntelliJ and standalone tools.",
    "topics": ["kotlin", "jetbrains"]
  },
  {
    "id": "a1b2c3d4e5f6g7h8",
    "summary": "Compose 1.8 adds a new `OverscrollEffect` API that replaces the internal glowEffect, giving developers control over stretch and glow behaviors per-platform.",
    "topics": ["compose"],
    "code_snippet": "val effect = rememberOverscrollEffect()\nLazyColumn(overscrollEffect = effect) { ... }",
    "snippet_label": "NEW API"
  }
]
```

Write to `state/summaries.json`. Cover all 187 articles — batching across multiple responses is fine, collect into one final file.

- [ ] **Step 3: Verify coverage**

```bash
python3.11 -c "
import json
queue = json.load(open('state/queue.json'))
summaries = json.load(open('state/summaries.json'))
q_ids = {a['id'] for a in queue}
s_ids = {s['id'] for s in summaries}
missing = q_ids - s_ids
print(f'Queue: {len(q_ids)}, Summaries: {len(s_ids)}, Missing: {len(missing)}')
if missing:
    print('Missing IDs:', list(missing)[:5])
"
```

Expected: `Missing: 0`

---

## Task 3: Apply summaries and assemble

**Files:**
- Modifies: `state/articles.json` (via make apply)
- Writes: `site/index.html` (via make assemble)

- [ ] **Step 1: Apply summaries**

```bash
python3.11 pipeline/summarize.py --apply state/summaries.json
```

Expected:
```
  Applied 187 summaries to articles.json
```

- [ ] **Step 2: Verify articles have topics**

```bash
python3.11 -c "
import json
articles = json.load(open('state/articles.json'))
with_topics = [a for a in articles if a.get('topics')]
summarized = [a for a in articles if a.get('summarized')]
print(f'Summarized: {len(summarized)}, With topics: {len(with_topics)}')
"
```

Expected: both counts ≥ 180.

- [ ] **Step 3: Assemble the edition**

```bash
python3.11 pipeline/assemble.py --edition 2026-W28
```

Expected (example):
```
  Edition 2026-W28: 2026-07-06 → 2026-07-12
  139 articles in window
  8 chapters, 112 placed articles
  Written → site/index.html
```

`placed articles` < `in window` is normal — articles with no matching topics are dropped.

- [ ] **Step 4: Review the output**

Open `site/index.html` in a browser. Verify:
- Chapters appear with real article titles
- Ticker shows real topic names and scores
- Edition label in masthead reads `2026·W28`
- At least one article has a code snippet card

- [ ] **Step 5: Move task to done**

```bash
mv tasks/ongoing/pipeline.md tasks/done/pipeline.md
```

---

## Self-Review

**Spec coverage:**
- ✅ Queue production (Task 1)
- ✅ Agent summarization with all quality rules (Task 2)
- ✅ Output format (Task 2, Step 2 example)
- ✅ Topic ID validation list (Global Constraints)
- ✅ Apply + assemble + browser review (Task 3)
- ✅ Missing-ID detection (Task 2, Step 3)

**Placeholder scan:** None found.

**Type consistency:** `id` is a string throughout. `topics` is always a list of strings. `code_snippet` + `snippet_label` always travel as a pair or are both absent.
