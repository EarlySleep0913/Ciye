# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

词页 (CiYe) — A literary-styled English vocabulary learning web app with spaced repetition, Ebbinghaus forgetting curve, bookshelf UI, and ECDICT dictionary integration.

## Build & Run Commands

```bash
# Install frontend dependencies
npm install

# Build frontend (outputs to public/)
npm run build

# Start server (Python backend serves both API and static files)
python run.py
# → http://127.0.0.1:8765

# Dev mode (Vite dev server with proxy to backend)
npm run dev
# → http://127.0.0.1:5173 (proxies /api to :8765)
```

No test suite exists. No linter configured.

## Architecture

### Backend (Python, zero dependencies beyond stdlib)

`run.py` → `server/app.py` → starts `ThreadingHTTPServer` on port 8765.

All API routes are in `server/app.py` (`CiYeHandler` class). The server handles both API endpoints (`/api/*`) and static file serving (from `public/`).

Key modules:
- `server/db.py` — SQLite connection pool (thread-local), schema, migrations, settings CRUD. Uses WAL mode.
- `server/auth.py` — Login/register/token management. Passwords hashed with SHA256 + salt. Sessions stored in `sessions` table.
- `server/ebbinghaus.py` — Forgetting curve math: `R = e^(-t/S)`. Memory strength updates on each review.
- `server/dict.py` — ECDICT (local SQLite) + Free Dictionary API lookups.
- `server/pexels.py` — Pexels image search with 5-minute status cache.

### Frontend (Vue 3 + Composition API)

Entry: `src/main.js` → `src/App.vue`. All components use `<script setup>`.

Key composables:
- `src/composables/useApi.js` — Fetch wrapper with auto-retry (3 attempts), 15s timeout, Bearer token injection, 401 auto-logout.
- `src/composables/useAudio.js` — Pronunciation playback (API audio → browser TTS fallback).

Component structure:
- `App.vue` — Auth gate (shows LoginPage if no token), top-level routing via `activeSection` ref
- `StudyCard.vue` — Main learning interface with queue, feedback buttons, retention display
- `BookShelf.vue` — Bookshelf UI with 3D books, preview/edit/delete, CSV import with AI button
- `BookPreview.vue` — Paginated word list editor for a single book
- `EbbinghausPanel.vue` — Forgetting curve visualization and review queue
- `SettingsPanel.vue` — Date simulation, resets, Pexels/AI config, user management
- `StatsPanel.vue` — Charts (bar, pie, line) via Chart.js + heatmap

### Database (SQLite)

Tables: `users`, `sessions`, `books`, `words`, `progress`, `daily_session`, `events`, `settings`, `pdf_words`, `pdf_word_marks`.

All user data tables include `user_id` for complete data isolation between users.

`progress` table tracks per-word learning state:
- `status`: new → learning → mastered
- `familiarity`: 0–10 (legacy)
- `memory_strength`: float, used by Ebbinghaus formula (default 1.0)
- `due_date`: next review date, calculated from memory_strength

`daily_session` persists the daily word queue per user per date. Studied words tracked in `studied_ids` JSON column.

### Key Design Decisions

- **Thread-local SQLite connections** — Each HTTP handler thread gets its own connection. The old shared connection caused `SQLITE_MISUSE` errors under concurrent access.
- **Date isolation** — Each virtual date (from date_offset setting) has its own `daily_session`. Studying on "tomorrow" doesn't affect "today's" queue.
- **Ebbinghaus-based scheduling** — Review threshold is R < 60%. Both `/api/today` and `/api/ebbinghaus/review` use the same logic.
- **No background enrichment on startup** — Was causing JSON corruption from concurrent DB access. Enrichment now happens lazily on word lookup.
- **Template example filtering** — CSV data contains "I need to remember the word X" placeholders. These are filtered out by `_clean_example()` so only real examples from Free Dictionary API are stored.

## Authentication

Token-based (Bearer header). 4 preset accounts seeded on first run:
- `earlysleep0913` / `200413` (admin)
- `bing` / `jbjzhkpku200595` (admin)
- `lbw` / `200413` (user)
- `jbj` / `jbjzhkpku200595` (user, has 90 days of demo learning data)

Admin-only: settings page, user management, AI config, public book creation.

## External APIs

| Service | Auth | Used For |
|---------|------|----------|
| Free Dictionary API | None | Phonetics, pronunciation audio, English definitions, examples |
| ECDICT (local) | None | Chinese translations (810MB SQLite in `data/ecdict.db`) |
| Pexels API | API Key (settings) | Memory images for words |
| SiliconFlow / OpenAI-compatible | API Key (settings) | AI-powered CSV generation for word import |

## CSS Design System

Defined in `src/styles/main.css`. Key variables:
- `--paper: #f4efe4` (background), `--ink: #223b32` (text), `--red: #8b3a3a` (accent), `--gold: #af8744` (highlights)
- Fonts: ZCOOL XiaoWei (Chinese display), Cormorant Garamond (English display), Noto Serif SC (body)
- Paper texture via SVG noise filter applied as `::after` pseudo-element on cards

## Important Patterns

- All API responses go through `_json_response()` which handles UTF-8 encoding.
- The `enrich_word()` function chains: ECDICT → Free Dictionary → Pexels, filling missing fields progressively.
- `parse_import_text()` handles CSV, TSV, and plain text with auto-delimiter detection.
- Vue reactivity: queue items wrapped with `reactive()` so direct property mutations (like `is_favorite`) trigger UI updates.
