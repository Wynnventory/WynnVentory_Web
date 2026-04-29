# Price History Page Redesign + Design System

**Date:** 2026-04-20
**Status:** Approved
**Approach:** Design System CSS + ApexCharts rebuild (Approach A)

## Overview

Redesign the `/history/` page to be modern and user-friendly, display all 14 available price metrics, and establish a reusable design system that other pages can adopt.

## Scope

- Create `design-system.css` with reusable tokens and component classes
- Rebuild `price_history.html` with ApexCharts, stat cards, and improved layout
- Add `design-system.css` to `_base.html` (1 line)
- No API changes. No new Python files. No new routes.

---

## 1. Design System (`design-system.css`)

### 1.1 CSS Custom Properties

Extend the existing `:root` and `[data-bs-theme]` selectors with new tokens:

**Surface colors (dark / light):**
- `--wv-surface-1`: Card backgrounds (`#1e2023` / `#ffffff`)
- `--wv-surface-2`: Elevated card backgrounds (`#25282c` / `#f8f9fa`)
- `--wv-surface-3`: Input wells / recessed areas (`#2b2e33` / `#e9ecef`)

**Accent colors:**
- `--wv-accent`: Primary action color (`#4facfe`)
- `--wv-accent-hover`: Hover state (`#3a9aed`)
- `--wv-accent-muted`: Disabled / subtle state (`rgba(79, 172, 254, 0.3)`)

**Semantic colors:**
- `--wv-positive`: Price up / good (`#00e396`)
- `--wv-negative`: Price down / bad (`#ff4560`)
- `--wv-neutral`: Unchanged / muted (`#6c757d`)

**Spacing scale:**
- `--wv-space-xs`: `0.25rem`
- `--wv-space-sm`: `0.5rem`
- `--wv-space-md`: `1rem`
- `--wv-space-lg`: `1.5rem`
- `--wv-space-xl`: `2rem`

**Border radius:**
- `--wv-radius-sm`: `0.375rem`
- `--wv-radius-md`: `0.5rem`
- `--wv-radius-lg`: `0.75rem`

**Shadows (dark / light):**
- `--wv-shadow-sm`: Subtle card shadow
- `--wv-shadow-md`: Elevated card shadow

### 1.2 Reusable Component Classes

| Class | Purpose |
|-------|---------|
| `.wv-card` | Rounded card with `--wv-surface-1` background, subtle border, `--wv-shadow-sm` |
| `.wv-stat-card` | Compact card: label (small muted text) + value (large) + optional sub-value |
| `.wv-input` | Styled text input with `--wv-surface-3` background |
| `.wv-btn-primary` | Primary button using `--wv-accent` |
| `.wv-btn-outline` | Outline variant, accent border |
| `.wv-btn-pill` | Pill-shaped toggle button (for timeframe selectors) |
| `.wv-badge` | Small label badge |
| `.wv-section-header` | Section title + optional subtitle |
| `.wv-grid-2col` | 2-column responsive grid (`grid-template-columns`) |
| `.wv-grid-3col` | 3-column responsive grid |
| `.wv-grid-4col` | 4-column responsive grid (wraps to 2 on mobile) |
| `.wv-skeleton` | Loading placeholder with shimmer animation |
| `.wv-empty-state` | Centered message with muted icon for no-data states |

All classes are additive to Bootstrap 5. Existing pages are unaffected.

---

## 2. Price History Page Layout

### 2.1 Header Zone

- Page title: "Price History" (appends "-- {item_name}" when an item is loaded)
- Search bar: full-width `.wv-input` with embedded search icon, placeholder "Search item: Hero, Dernic Ingot 3...", enter-to-search + search button
- Timeframe pills: `.wv-btn-pill` group — 7d, 14d, 30d, 90d, Custom
- Custom date range: collapsible row with start/end date pickers and Apply/Reset buttons (same behavior as current, restyled)

### 2.2 Stats Zone

Displays the **latest snapshot** values (last element of the API response array).

**Identified row (always shown) — `.wv-grid-4col`:**

| Stat Card | API Field | Display |
|-----------|-----------|---------|
| Average Price | `average_price` | Raw + game format |
| 80% Average | `average_mid_80_percent_price` | Raw + game format |
| Median (P50) | `p50_price` | Raw + game format |
| P50 EMA (7d) | `average_p50_ema_price` | Raw + game format |
| Lowest Price | `lowest_price` | Raw + game format |
| Highest Price | `highest_price` | Raw + game format |
| Listings | `total_count` | Count |

**Unidentified row (conditionally shown) — `.wv-grid-4col`:**

Only rendered if ANY of the unidentified metrics are > 0.

| Stat Card | API Field |
|-----------|-----------|
| Unid Average | `unidentified_average_price` |
| Unid 80% Avg | `unidentified_average_mid_80_percent_price` |
| Unid Median | `unidentified_p50_price` |
| Unid P50 EMA | `unidentified_average_p50_ema_price` |
| Unid Lowest | `unidentified_lowest_price` |
| Unid Highest | `unidentified_highest_price` |
| Unid Listings | `unidentified_count` |

Separated from identified row by a `.wv-section-header` labeled "Unidentified".

### 2.3 Chart Zone

**Two ApexCharts** replacing the current 3 Chart.js charts.

**Shared configuration:**
- X-axis: time (daily)
- Zoom & pan enabled
- Responsive, fills available width
- Users toggle series on/off via ApexCharts' built-in legend click

**Chart 1 — Price History** (min-height ~400px):
- Y-axis: Price in emeralds
- Tooltip: shows value in both raw and game format (using `convertEmeraldsToGameFormat`)

| Group | Series | Color | Default Visible |
|-------|--------|-------|-----------------|
| Identified | P50 (Median) | `#4facfe` | Yes |
| Identified | P50 EMA (7d) | `#00d4ff` | Yes |
| Identified | Average Price | `#4bc0c0` | No |
| Identified | 80% Average | `#358686` | No |
| Identified | Lowest Price | `#36a2eb` | Yes |
| Identified | Highest Price | `#ff6384` | Yes |
| Unidentified | Unid P50 | `#b77aff` | No |
| Unidentified | Unid P50 EMA | `#9b59b6` | No |
| Unidentified | Unid Average | `#6a5d9e` | No |
| Unidentified | Unid 80% Avg | `#453586` | No |
| Unidentified | Unid Lowest | `#7e57c2` | No |
| Unidentified | Unid Highest | `#e040fb` | No |

**Chart 2 — Market Volume** (min-height ~200px):
- Y-axis: Listing count
- Rendered as area chart with semi-transparent fill

| Series | Color | Default Visible |
|--------|-------|-----------------|
| Total Listings | `rgba(75, 192, 192, 0.5)` | Yes |
| Unid Listings | `rgba(54, 162, 235, 0.5)` | Yes |

### 2.4 Dark/Light Mode

ApexCharts theme config reads from CSS variables so it automatically adapts when the dark mode toggle is used. The design system variables already define both themes.

---

## 3. Data Flow

```
User visits /history/Hero
  -> Flask renders price_history.html with item_name="Hero"
  -> JS on page load calls fetchPriceData("Hero")
  -> GET /api/trademarket/history/Hero?start_date=...&end_date=...
  -> API returns array of archive documents (all 14 fields per doc)
  -> JS extracts latest snapshot -> populates stat cards
  -> JS maps all 14 fields into ApexCharts series -> renders chart
```

No API changes needed. The endpoint already returns all fields.

### 3.1 States

| State | Behavior |
|-------|----------|
| **Loading** | `.wv-skeleton` placeholders in stat cards + chart area |
| **Empty** | `.wv-empty-state` centered: "No price data found" with muted icon |
| **Error** | Inline alert below search bar: "Failed to load price data" |
| **Loaded** | Stat cards + chart populated |

---

## 4. File Changes

| File | Change |
|------|--------|
| `modules/routes/web/static/design-system.css` | **New** — Reusable design tokens + component classes |
| `modules/routes/web/templates/market/price_history.html` | **Rewrite** — New layout with ApexCharts |
| `modules/routes/web/templates/components/_base.html` | **Edit** — Add `<link>` for `design-system.css` |

### 4.1 External Dependencies Added

| Library | CDN | Purpose |
|---------|-----|---------|
| ApexCharts | `cdn.jsdelivr.net/npm/apexcharts` | Interactive charting |

Chart.js and its date adapter are removed from this page (not used elsewhere).

---

## 5. Constraints

- Must work with both dark and light mode
- Must be responsive (mobile-first, wrapping grids)
- Must preserve existing URL behavior (`/history/<item_name>`, query params `start_date`, `end_date`, `tier`, `shiny`)
- Must preserve `convertEmeraldsToGameFormat` for tooltip/stat display
- Design system must not break existing pages (additive only)
