# Topic Bible — Design

The Topic Bible is the system's pulse. It answers: **what is the Kotlin world actually talking about right now?**

---

## Lifecycle of a topic

```
[curated seed] OR [auto-emerged from articles]
       ↓
  receives daily mention boosts from ingested articles
       ↓
  decays daily without new mentions
       ↓
  history graph accumulates → visible in the site UI
```

---

## Scoring model (per daily cycle)

```
new_score = (old_score * DECAY) + (mentions_today * source_weight)
```

Constants:
- `DECAY = 0.92` — score halves in ~8 days with zero new mentions
- `source_weight` by type:
  - `conference` → 3.0 (KotlinConf talk title = strong signal)
  - `blog` → 2.0 (editorial intent = considered mention)
  - `news` → 1.5
  - `slack-mirror` → 1.0 (high volume, lower signal per mention)

---

## Seeded baseline (`topics/topics.yml`)

```yaml
topics:
  # Language core
  - id: kotlin
  - id: coroutines
  - id: flows
  - id: k2-compiler
  - id: kotlin-scripting

  # UI
  - id: compose
  - id: compose-multiplatform
  - id: navigation
  - id: animation

  # Multiplatform
  - id: kmp
  - id: ios-interop
  - id: wasm
  - id: kotlin-js

  # DI
  - id: hilt
  - id: koin
  - id: kodein

  # Networking
  - id: ktor
  - id: retrofit
  - id: okhttp

  # Build
  - id: gradle
  - id: gradle-plugin
  - id: version-catalog
  - id: ksp
  - id: kapt

  # Android platform
  - id: android-api
  - id: jetpack
  - id: room
  - id: datastore
  - id: wear-os
  - id: android-auto

  # Backend
  - id: ktor-server
  - id: spring-kotlin
  - id: exposed

  # Community
  - id: droidcon
  - id: kotlinconf
  - id: google-io
  - id: android-developers
```

---

## Auto-emergence

If the AI pipeline surfaces a term not in the bible that appears in ≥3 distinct articles in one cycle, it is added to the bible automatically with:

```json
{
  "auto_emerged": true,
  "first_seen": "2026-07-05",
  "needs_review": true
}
```

Contributors can PR `topics.yml` to formalize or remove it.

---

## Historical graph

`state/bible.json` keeps rolling 90-day history per topic. The site renders this as inline sparklines (7-day bars) next to article topic tags — so the reader can see at a glance whether a topic is accelerating, stable, or fading.

---

## Topic clusters (for chapter grouping)

Topics are grouped into clusters for chapter assembly. Clusters are defined in `topics/topics.yml`:

```yaml
clusters:
  - id: language-core
    label: "Kotlin Core"
    topics: [kotlin, coroutines, flows, k2-compiler]
  - id: ui
    label: "Compose & UI"
    topics: [compose, compose-multiplatform, navigation, animation]
  - id: multiplatform
    label: "KMP"
    topics: [kmp, ios-interop, wasm, kotlin-js]
  - id: di
    label: "Dependency Injection"
    topics: [hilt, koin, kodein]
  - id: networking
    label: "Networking"
    topics: [ktor, retrofit, okhttp]
  - id: build
    label: "Build & Tooling"
    topics: [gradle, ksp, kapt, version-catalog]
  - id: platform
    label: "Android Platform"
    topics: [android-api, jetpack, room, datastore]
  - id: community
    label: "Community"
    topics: [droidcon, kotlinconf, google-io]
```

Chapter order in an edition = clusters sorted by sum of their topic scores on that day.
