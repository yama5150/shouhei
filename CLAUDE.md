# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-file restaurant/buffet inventory tracking app ("店舗管理Master" / "Susukino MASTER"). Staff record stock counts, refills, and waste per dish; managers review a daily cost/waste summary and edit the menu. The entire application — markup, styles, and logic — lives in `index.html`. There is no build step, package manager, test suite, or backend code in this repo.

## Running / developing

- **Run it**: open `index.html` directly in a browser, or serve it statically (`python3 -m http.server` then visit `index.html`). All dependencies load from CDNs (Tailwind, qrcodejs, Firebase 11.6.1 ESM), so an internet connection is required.
- **No build, lint, or test commands exist.** Edit `index.html` and reload the browser. Because logic is inline ES module code, there is no transpilation — syntax must be browser-native.
- **Reset app state during testing**: the Settings tab has a "Critical Reset" button (`localStorage.clear()`), or clear `localStorage` keys prefixed `tracker_menu_`, `daily_logs_`, `sales_`, and `staff_name` in devtools.

## Architecture

Everything is driven by one global `state` object and a set of `window.*` functions invoked directly from inline `onclick`/`oninput` handlers in the HTML. There is no framework and no module bundling — rendering is manual `innerHTML` string assembly into fixed container IDs (`refill-buttons-container`, `summary-list`, `log-list`, `menu-manager-list`, etc.).

**Dual persistence with automatic fallback.** `initApp()` tries to initialize Firebase from a `__firebase_config` global (injected by the host environment — this app is built to run inside a Canvas/Gemini-style sandbox that provides `__firebase_config`, `__app_id`, and `__initial_auth_token`). If that global is absent or init fails, `fallbackToLocal()` switches to `localStorage`. Every read/write path branches on `state.isFirebaseMode`:
- Firestore paths: `artifacts/{appId}/public/data/{menu_config_v16_9 | logs_v16_9 | sales_v16_9}`. Logs use `onSnapshot` listeners (one filtered by today's `date`, one ordered by `timestamp` limit 20).
- localStorage equivalents: `tracker_menu_v16_9`, `daily_logs_v16_9` (array, capped at 2000 entries), `sales_v16_9` (map keyed by date string).

**`MASTER_CONFIG` is the source of truth for the menu, and it is version-gated.** It defines `pages` (4 tabs, each mapping to category keys) and `categories` (each with label, color, icon, and a `dishes` array of `{name, unit, defaultQuantity, cost}`). `ensureMenuState(data)` compares the stored config's `version` against `MASTER_CONFIG.version`; on mismatch (or missing data) it **discards the stored menu and force-resets to `MASTER_CONFIG`**. Consequence: bumping the version string is an intentional way to push a new menu to all clients, but it wipes any user-edited menu customizations. When you change the menu defaults, also decide whether to bump the version.

**Log model and cost math.** Each log entry is `{dish, quantity, unit, type, timestamp, date, staffName}`. `type` is one of `start` (朝在庫 / morning stock), `end` (夜在庫 / night stock), `refill` (補充), `waste` (廃棄). The daily summary (`updateSummaryView`) computes consumption as `(start + refill) - end` when start/end stock was recorded, otherwise just `refill`; food cost = consumption × dish `cost`, waste loss = waste × `cost`.

**Admin gate.** The Stats and Settings tabs are PIN-protected. The PIN (`1129`) is hardcoded in `inputPin()`. This is cosmetic access control, not security.

**Render flow.** `renderUI()` calls `renderPageNav()` + `renderCategories()` + `renderDishButtons()`. Page/category/search state lives in `state.currentPage`, `state.activeCategory`, `state.searchQuery`; changing any re-renders from `state.currentMenu`. Menu edits go through `openEditDish`/`saveEditDish`/`deleteEditDish`, which mutate `state.currentMenu` then call `saveMenu()` to persist.

## Conventions

- **UI text and comments are in Japanese**; match that when editing user-facing strings.
- **Styling is Tailwind utility classes inline.** Custom theme colors (`primary`, `waste`, `start`, `end`, plus per-category colors like `crab`, `sashimi`, `mutton`) are defined in the `tailwind.config` block in the `<head>`. Category `color` values in `MASTER_CONFIG` (e.g. `bg-hokkaido`) must correspond to a defined color or a real Tailwind class, or buttons render colorless.
- **Functions called from HTML must be assigned to `window`** (e.g. `window.recordLog = ...`), since handlers are global inline attributes.
- **The version string appears in multiple places** (`MASTER_CONFIG.version`, the `<title>`, the header badge, localStorage/Firestore key suffixes `_v16_9`). Keep them consistent when bumping.

## Git workflow

Active development branch: `claude/claude-md-docs-L6qxO`. Commit and push completed work there; do not push to `main` without explicit permission.
