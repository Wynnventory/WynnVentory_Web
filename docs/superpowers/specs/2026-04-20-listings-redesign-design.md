# Listings Page Redesign

**Date:** 2026-04-20
**Status:** Approved

## Overview

Rework the `/listings/` page to use the design system, replacing the right-side filter sidebar with top controls, restyling item cards, and improving pagination. Goal: better readability, mobile-friendliness, and visual consistency with the redesigned price history page.

## Scope

- Rewrite `listings.html` with top controls layout and restyled cards
- Remove old sidebar/collapse CSS from `style.css`
- No API changes. No new Python files. No new routes.

---

## 1. Top Controls Bar

A `.wv-card` section at the top of the page containing all filters.

### 1.1 Search Row

- Full-width `.wv-input` with embedded search icon (same pattern as price history)
- Placeholder: "Search item name..."
- Form submits on Enter or via a Search button

### 1.2 Filter Row

Responsive flex row (`.d-flex flex-wrap gap-2`) of styled `<select>` dropdowns:

| Filter | Options | Default |
|--------|---------|---------|
| Type | All, Gear, Materials, Ingredients, Powders, Runes, Dungeon Keys | All |
| Sub Type | Dynamic based on Type (same JS logic as current) | All |
| Rarity | All, Mythic, Fabled, Legendary, Rare, Unique, Normal | All |
| Shiny | Both, Yes, No | Both |
| Unidentified | Both, Yes, No | Both |
| Tier | All, 1-9 | All |
| Sort | All existing sort options | Timestamp Desc |

Each select uses `.form-select` with a compact width (`min-width: 120px; flex: 0 1 auto`).

An "Apply Filters" button (`.wv-btn-primary`) at the end of the row.

### 1.3 Active Filters Display

Below the filter row, show small `.wv-badge` pills for each active (non-default) filter. Each pill shows the filter name and value (e.g., "Rarity: Mythic") with an `x` link that removes that param and resubmits. A "Clear All" link resets to the default URL.

Only displayed when at least one filter is active.

---

## 2. Item Cards

Each item card uses `.wv-card` as the base container.

### 2.1 Card Structure

```
+-------------------------------------------+
| [Icon]  Item Name  [Shiny badge] [Unid]   |
|          [Overall Roll %]                  |
+-------------------------------------------+
| Identification rolls (existing macro)      |
| ...                                        |
+-------------------------------------------+
| Rarity [reroll count]                      |
+-------------------------------------------+
| Price: 2stx 14.5le          Amount: 1     |
| 84.2% of avg (green/red colored)          |
| Recorded 2h ago                            |
+-------------------------------------------+
```

### 2.2 Styling Details

- Card background: `var(--wv-surface-1)` with `var(--wv-shadow-sm)`
- Card border: `1px solid var(--wv-border)`, with rarity-colored left border (4px)
- Name: keeps existing rarity color class (`.mythic`, `.fabled`, etc.)
- Shiny indicator: `.wv-badge` with a gold/yellow accent
- Unidentified indicator: `.wv-badge` with muted styling
- Price: large font weight, game format as primary, raw emerald count as secondary small text
- Percentage of average: colored using `var(--wv-positive)` (below 100%) / `var(--wv-negative)` (above 100%)
- Timestamp: small muted text at bottom

### 2.3 Grid Layout

```css
.listings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--wv-space-md);
}
```

This replaces the Bootstrap `row-cols-*` classes with a more fluid auto-fill grid.

---

## 3. Pagination

Centered at the bottom in a flex row:

```
[Page size: 10|25|50]    < 1 2 3 ... 10 >    Page X of Y
```

- Page size: small `.form-select` inline
- Page numbers: `.wv-btn-pill` style buttons, current page gets `.active`
- Show up to 5 page numbers with ellipsis for large page counts
- Prev/Next arrows at the edges

---

## 4. Removed Code

### 4.1 From `style.css`

Remove the following CSS blocks that are no longer needed:
- `#filter-sidebar` and all its variants
- `#items-container` and its `.expanded`/`.dtog` variants
- `#collapse-button` and its positioning
- `.items-handle` width rules
- Related media queries for sidebar/container width toggling

### 4.2 From `listings.html`

- Remove the `filter-sidebar` div and `collapse-button`
- Remove the `removeClass()` JS function call
- Keep the subtype rebuild JS logic (still needed for dynamic subtypes)
- Keep the color gradient JS for stat percentages

---

## 5. Preserved Behavior

- Server-side filtering via GET query params (no API changes)
- All existing filter options and sort options
- Dynamic sub-type dropdown based on selected type
- Gradient coloring for identification roll percentages
- Overall roll percentage coloring
- Rarity-based card styling
- Price ratio coloring (red above average, green below)
- URL state: all filters reflected in URL for bookmarking/sharing
- Pagination preserves all current filter params

---

## 6. Constraints

- Must work with both dark and light mode
- Must be responsive (cards reflow on mobile)
- Must use existing design-system.css classes where possible
- Must not break other pages (listings-specific CSS only)
- Preserve the `_identification_macro.html` import and usage unchanged
