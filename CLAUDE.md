# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

One repo holding **three unrelated deliverables**, all shipped as standalone HTML files that are opened directly from GitHub via `raw.githack.com` (QR codes are handed out to users, and the pages are installable as PWAs). There is no server, no test suite, and no linter.

| Deliverable | Source | What ships |
|---|---|---|
| 焼肉ロス管理アプリ (Buffet Log) | `src/` (React + Vite) | `dist/app.html` → copied to `index.html` and `yakiniku.html` |
| ほおばりハムスター モグモグ大冒険 (game) | `hamster.html` | `hamster.html` itself |
| 店舗管理Master v16.9 (retired) | `legacy/susukino-v16.9.html` | not served |

`.nojekyll`, `manifest.webmanifest`, and `icon-*.png` exist so GitHub Pages / the PWA install flow work. **The manifest and icons belong to the hamster game**, not to the buffet app.

## Commands

```bash
npm install
npm run dev      # Vite dev server for the React app (entry: app.html → src/main.jsx)
npm run build    # vite build && cp dist/app.html index.html && cp dist/app.html yakiniku.html
npm run preview
```

There are **no tests and no lint config**. `hamster.html` and `legacy/` are not part of the Vite build at all — open them directly in a browser.

## The build overwrites tracked files — do not hand-edit them

`vite.config.js` uses `viteSingleFile` and sets `rollupOptions.input = 'app.html'` so the built page inlines all JS/CSS into a single file that works from any URL (`base: './'`).

- **`app.html` is the source entry** (a 20-line shell with `<div id="root">`). Edit this.
- **`index.html`, `yakiniku.html`, and `dist/app.html` are generated** — three identical ~215 KB copies of the build output. Never edit them by hand; run `npm run build`.
- `dist/` is **deliberately committed** (see the comment in `.gitignore`) because `raw.githack.com` serves it. `yakiniku.html` exists purely as a cache-busting alias.

## React app (`src/App.jsx`)

One ~856-line component; no router, no state library, no backend. All state is `useState` in `App`, persisted to `localStorage` via `useEffect`.

**Per-day storage keys.** A "day" is an ISO date string, and each day is stored under its own set of keys, read back by `readDay(date)`:

- `bl_rec_{date}` — the records map, keyed by item id
- `bl_daily_{date}` — 本日だけメニュー (one-off items added for that day)
- `bl_flavors_{date}` — 本日の味メモ
- `bl_closed_{date}` — `'1'` once the day is closed
- `bl_menu` / `bl_menu_ver` — the menu table (shared across days)
- `bl_pool` — a reuse pool of past one-off items

Saving is keyed off `day.date`, not "today", so viewing and editing a past day writes to the right place.

**Record model and cost math.** Each record is `{ supply, refills: [{id, time, qty}], remained }`:

- `supply` = 開店時の出し, `refills` = 営業中の補充 (each stamped with `HH:MM`), `remained` = 残り
- `totalOut = supply + Σrefills`
- `consumed = max(0, totalOut - remained)` → `consumedYen = consumed × cost`
- **`wasteYen = remained × cost`** — every unit left over is currently counted as waste. There is no notion of carrying stock over to the next day or reusing it, so a high-value item that was saved rather than binned still scores as loss.
- `lossRate = remained / totalOut × 100`

**`MENU_VERSION` is a reset gate.** On load, `bl_menu_ver` is compared against `MENU_VERSION` (currently `4`); on mismatch the stored menu is **discarded and replaced with `INITIAL_MENU_DATA`**. Bumping it pushes a new menu to every client but wipes user menu edits — decide deliberately when changing menu defaults.

**Other things worth knowing.** Two views (`input` / `report`) toggled by `view`. Admin/edit mode is gated by `ADMIN_PW = '1234'` hardcoded in the file (cosmetic, not security). `UNIT_CONFIG` drives per-unit keypad step sizes, quick-add chips, and the roller picker. CSV export builds its own escaping and prepends a BOM.

## Hamster game (`hamster.html`)

Single file, no build, plain `<script>` (not a module) with `"use strict"`. Canvas is a fixed **960×540** internal resolution scaled by CSS.

**The file is ~2.6 MB but only ~1,400 lines** — one line near the top is a base64 MP3 (`const BGM_DATA = "..."`, ~2.57 M characters). Never read or rewrite that line; use targeted edits and avoid whole-file rewrites.

**Beware trailing whitespace.** Many original lines end with two trailing spaces. Exact-match edits must include them, or anchor on a substring that avoids line ends.

**Shape of the code.** A `game` object holds the state machine (`title` / `play` / `next` / `over` / `clear`) plus `mode`, `stage`, `sel`. `STAGES` defines the 4 story stages (theme colors, platforms, enemy spawns, optional `boss`). `BOSS_TYPES` defines 4 bosses. `BOSS_RUSH` is built from `STAGES` themes + `RUSH_ORDER` to give each boss its own short arena. **`stageList` is the indirection that matters**: it points at either `STAGES` or `BOSS_RUSH`, and `loadStage`, `draw`, `drawHUD`, and `drawNext` all read through it — reference `stageList`, not `STAGES`, in anything stage-driven.

**Progress is saved** under `hamster_record_v1` as `{best, bestRush, stage, clears, rushClears, plays}`. `record.stage` (max story stage reached) unlocks stage select; `record.clears > 0` unlocks boss rush. Story and rush high scores are kept separate so they can't contaminate each other.

**Title-screen input is coordinate-based.** The on-screen D-pad (`#ui`) is hidden unless `body.playing`, so the title/over/clear screens handle taps by converting client coords to canvas coords (`toCanvasXY`) and hit-testing `SEL_L` / `SEL_R` / `BACK_Y`. If you move that UI, move the rects with it.

**Verifying changes.** There is no test runner, but the script can be syntax-checked and driven headlessly:

```bash
# 構文チェック: <script> を抜き出して node に通す
python3 -c "import re,io; s=io.open('hamster.html',encoding='utf-8').read(); \
m=re.search(r'<script>\s*\"use strict\";(.*?)</script>', s, re.S); \
io.open('/tmp/game.js','w',encoding='utf-8').write('\"use strict\";'+m.group(1))"
node --check /tmp/game.js
```

For behavior, drive it with Playwright against the preinstalled browser at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (do **not** run `playwright install`). Top-level `let`/`const` are reachable from `page.evaluate`, so `game`, `record`, `player`, `boss`, and functions like `startOrRetry()` / `defeatBoss()` can be poked directly. When simulating a stage transition, wait for `game.state` to actually become `'next'` before forcing `game.banner = 1` — the goal handler resets `banner` to 150 after you set it.

## Conventions

- **All UI text and code comments are in Japanese.** Match that when editing user-facing strings, and write commit messages in Japanese to match the history.
- Buffet app styling is Tailwind utility classes; the game draws everything to canvas by hand.
- PWA/icon URLs inside `hamster.html` and `manifest.webmanifest` are **absolute `raw.githack.com` links**, so they 404 when the file is opened locally. That is expected — don't "fix" them to relative paths without checking how the page is distributed.

## Git workflow

Active development branch: `claude/claude-md-docs-L6qxO`. Commit and push completed work there; do not push to `main` without explicit permission.
