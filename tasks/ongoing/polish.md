# Polish: Logo, About Page, Bundle

---

## Task 1 — Logo

Create an SVG logo mark for Kotlin Digest that lives in the masthead of both
`site/template.html` and `site/about.html`. Must work in light and night modes.
Should fit the existing design system: cream paper, ink, orange accent (#E06020),
JetBrains Mono + Playfair Display.

- [ ] Design the mark (SVG, inline-safe, no external deps)
- [ ] Replace the plain text wordmark in `site/template.html` masthead with logo
- [ ] Replace the plain text wordmark in `site/about.html` masthead with logo

---

## Task 2 — About page

`site/about.html` currently fetches `./README.md` at runtime via `fetch()`.
This breaks in the bundled file and offline. Rewrite it as a fully static page
with the README content baked in as HTML. No JavaScript fetch, no loading state.

- [ ] Bake README content into `about.html` as static HTML
- [ ] Remove `fetch()` / loading spinner
- [ ] Page must look great: editorial layout, same design tokens as index

---

## Task 3 — Bundle

After Tasks 1–2 are done, rebuild the portable file.

- [ ] `make assemble EDITION=2026-W28` (picks up logo changes from template)
- [ ] `make bundle EDITION=2026-W28`
- [ ] Verify `dist/kotlin-digest-2026-W28.html` opens standalone with no external deps

---

## Backlog (not in this task)

- Fix styling-android duplicate IDs in articles.json
- Fix john-oreilly articles with `date: None`
- Add missing bible topics: android-studio, koog, gemini, mcp, foldables, firebase, etc.
- Patch masthead article/source count (still hardcoded "27 articles · 8 sources")
