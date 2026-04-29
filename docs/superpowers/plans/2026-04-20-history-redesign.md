# Price History Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the /history/ page with a reusable design system, stat cards for all 14 price metrics, and ApexCharts interactive charting.

**Architecture:** Create a standalone `design-system.css` with CSS custom properties and component classes that extend Bootstrap 5. Rewrite `price_history.html` to use these components plus ApexCharts (replacing Chart.js). One-line edit to `_base.html` to load the design system globally.

**Tech Stack:** Bootstrap 5.3.3, ApexCharts (CDN), CSS custom properties, vanilla JavaScript, Jinja2 templates

**Spec:** `docs/superpowers/specs/2026-04-20-history-redesign-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `modules/routes/web/static/design-system.css` | Create | CSS tokens + reusable component classes |
| `modules/routes/web/templates/components/_base.html` | Edit (line 24) | Add design-system.css link |
| `modules/routes/web/templates/market/price_history.html` | Rewrite | New layout, stats zone, ApexCharts |

---

### Task 1: Create design-system.css

**Files:**
- Create: `modules/routes/web/static/design-system.css`

This task is independent and can run in parallel with Task 3's HTML structure planning.

- [ ] **Step 1: Create the design system CSS file**

Create `modules/routes/web/static/design-system.css` with the following complete content:

```css
/* WynnVentory Design System
 * Reusable tokens and component classes built on Bootstrap 5.
 * Import after style.css in _base.html. */

/* ── Dark theme tokens (default) ── */
[data-bs-theme="dark"] {
    --wv-surface-1: #1e2023;
    --wv-surface-2: #25282c;
    --wv-surface-3: #2b2e33;
    --wv-border: rgba(255, 255, 255, 0.1);
    --wv-border-hover: rgba(255, 255, 255, 0.2);
    --wv-text-primary: #e0e0e0;
    --wv-text-secondary: #9ca3af;
    --wv-text-muted: #6b7280;
    --wv-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
    --wv-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
    --wv-chart-grid: rgba(255, 255, 255, 0.06);
    --wv-chart-text: #9ca3af;
    --wv-skeleton-base: #25282c;
    --wv-skeleton-shine: #2f3338;
}

/* ── Light theme tokens ── */
[data-bs-theme="light"] {
    --wv-surface-1: #ffffff;
    --wv-surface-2: #f8f9fa;
    --wv-surface-3: #e9ecef;
    --wv-border: rgba(0, 0, 0, 0.1);
    --wv-border-hover: rgba(0, 0, 0, 0.2);
    --wv-text-primary: #212529;
    --wv-text-secondary: #6b7280;
    --wv-text-muted: #9ca3af;
    --wv-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
    --wv-shadow-md: 0 4px 12px rgba(0, 0, 0, 0.12);
    --wv-chart-grid: rgba(0, 0, 0, 0.06);
    --wv-chart-text: #6b7280;
    --wv-skeleton-base: #e9ecef;
    --wv-skeleton-shine: #f8f9fa;
}

/* ── Shared tokens (theme-independent) ── */
:root {
    --wv-accent: #4facfe;
    --wv-accent-hover: #3a9aed;
    --wv-accent-muted: rgba(79, 172, 254, 0.3);
    --wv-positive: #00e396;
    --wv-negative: #ff4560;
    --wv-neutral: #6c757d;
    --wv-space-xs: 0.25rem;
    --wv-space-sm: 0.5rem;
    --wv-space-md: 1rem;
    --wv-space-lg: 1.5rem;
    --wv-space-xl: 2rem;
    --wv-radius-sm: 0.375rem;
    --wv-radius-md: 0.5rem;
    --wv-radius-lg: 0.75rem;
}

/* ── Card ── */
.wv-card {
    background: var(--wv-surface-1);
    border: 1px solid var(--wv-border);
    border-radius: var(--wv-radius-lg);
    box-shadow: var(--wv-shadow-sm);
    padding: var(--wv-space-lg);
}

/* ── Stat Card ── */
.wv-stat-card {
    background: var(--wv-surface-1);
    border: 1px solid var(--wv-border);
    border-radius: var(--wv-radius-md);
    padding: var(--wv-space-md) var(--wv-space-lg);
    display: flex;
    flex-direction: column;
    gap: var(--wv-space-xs);
    transition: border-color 0.2s, box-shadow 0.2s;
}

.wv-stat-card:hover {
    border-color: var(--wv-border-hover);
    box-shadow: var(--wv-shadow-sm);
}

.wv-stat-card .wv-stat-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--wv-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.wv-stat-card .wv-stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--wv-text-primary);
    line-height: 1.2;
}

.wv-stat-card .wv-stat-sub {
    font-size: 0.8rem;
    color: var(--wv-text-muted);
}

/* ── Inputs ── */
.wv-input {
    background: var(--wv-surface-3);
    border: 1px solid var(--wv-border);
    border-radius: var(--wv-radius-md);
    color: var(--wv-text-primary);
    padding: 0.625rem 1rem;
    font-size: 0.95rem;
    transition: border-color 0.2s, box-shadow 0.2s;
    width: 100%;
}

.wv-input:focus {
    outline: none;
    border-color: var(--wv-accent);
    box-shadow: 0 0 0 3px var(--wv-accent-muted);
}

.wv-input::placeholder {
    color: var(--wv-text-muted);
}

/* ── Search wrapper (icon inside input) ── */
.wv-search-wrapper {
    position: relative;
}

.wv-search-wrapper .wv-search-icon {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--wv-text-muted);
    pointer-events: none;
    font-size: 1rem;
}

.wv-search-wrapper .wv-input {
    padding-left: 2.5rem;
}

/* ── Buttons ── */
.wv-btn-primary {
    background: var(--wv-accent);
    color: #fff;
    border: 1px solid var(--wv-accent);
    border-radius: var(--wv-radius-md);
    padding: 0.5rem 1.25rem;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s, box-shadow 0.2s;
}

.wv-btn-primary:hover {
    background: var(--wv-accent-hover);
    box-shadow: var(--wv-shadow-sm);
}

.wv-btn-outline {
    background: transparent;
    color: var(--wv-text-primary);
    border: 1px solid var(--wv-border);
    border-radius: var(--wv-radius-md);
    padding: 0.5rem 1.25rem;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}

.wv-btn-outline:hover {
    border-color: var(--wv-accent);
    color: var(--wv-accent);
}

/* ── Pill toggle buttons ── */
.wv-pill-group {
    display: flex;
    flex-wrap: wrap;
    gap: var(--wv-space-xs);
}

.wv-btn-pill {
    background: transparent;
    color: var(--wv-text-secondary);
    border: 1px solid var(--wv-border);
    border-radius: 9999px;
    padding: 0.375rem 1rem;
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.wv-btn-pill:hover {
    border-color: var(--wv-accent);
    color: var(--wv-accent);
}

.wv-btn-pill.active {
    background: var(--wv-accent);
    color: #fff;
    border-color: var(--wv-accent);
}

/* ── Section header ── */
.wv-section-header {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--wv-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding-bottom: var(--wv-space-sm);
    margin-top: var(--wv-space-lg);
    margin-bottom: var(--wv-space-md);
    border-bottom: 1px solid var(--wv-border);
}

/* ── Badge ── */
.wv-badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 9999px;
    background: var(--wv-accent-muted);
    color: var(--wv-accent);
}

/* ── Responsive grids ── */
.wv-grid-2col {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--wv-space-md);
}

.wv-grid-3col {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--wv-space-md);
}

.wv-grid-4col {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--wv-space-md);
}

@media (max-width: 992px) {
    .wv-grid-4col { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 768px) {
    .wv-grid-3col { grid-template-columns: repeat(2, 1fr); }
    .wv-grid-4col { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 480px) {
    .wv-grid-2col { grid-template-columns: 1fr; }
    .wv-grid-3col { grid-template-columns: 1fr; }
    .wv-grid-4col { grid-template-columns: 1fr; }
}

/* ── Skeleton loading ── */
.wv-skeleton {
    background: linear-gradient(
        90deg,
        var(--wv-skeleton-base) 25%,
        var(--wv-skeleton-shine) 50%,
        var(--wv-skeleton-base) 75%
    );
    background-size: 200% 100%;
    animation: wv-shimmer 1.5s infinite;
    border-radius: var(--wv-radius-sm);
}

@keyframes wv-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

/* ── Empty state ── */
.wv-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--wv-space-xl) var(--wv-space-md);
    color: var(--wv-text-muted);
    text-align: center;
}

.wv-empty-state i {
    font-size: 2.5rem;
    margin-bottom: var(--wv-space-md);
    opacity: 0.5;
}

.wv-empty-state p {
    font-size: 1rem;
    margin: 0;
}

/* ── Alert ── */
.wv-alert-error {
    background: rgba(255, 69, 96, 0.1);
    border: 1px solid rgba(255, 69, 96, 0.3);
    border-radius: var(--wv-radius-md);
    padding: var(--wv-space-sm) var(--wv-space-md);
    color: var(--wv-negative);
    font-size: 0.9rem;
    display: none;
}
```

- [ ] **Step 2: Verify file was created correctly**

Run: `wc -l modules/routes/web/static/design-system.css`
Expected: approximately 240 lines

- [ ] **Step 3: Commit**

```bash
git add modules/routes/web/static/design-system.css
git commit -m "feat: add WynnVentory design system CSS with reusable tokens and components"
```

---

### Task 2: Add design-system.css to _base.html

**Files:**
- Modify: `modules/routes/web/templates/components/_base.html:24`

Depends on: Task 1

- [ ] **Step 1: Add the CSS link after style.css**

In `modules/routes/web/templates/components/_base.html`, find line 24:

```html
    <link rel="stylesheet" href="{{ url_for('web.static', filename='style.css') }}"/>
```

Add immediately after it:

```html
    <link rel="stylesheet" href="{{ url_for('web.static', filename='design-system.css') }}"/>
```

- [ ] **Step 2: Verify the edit**

Run: `grep -n "design-system" modules/routes/web/templates/components/_base.html`
Expected: one line showing the new link tag at approximately line 25

- [ ] **Step 3: Commit**

```bash
git add modules/routes/web/templates/components/_base.html
git commit -m "feat: load design-system.css globally via _base.html"
```

---

### Task 3: Rewrite price_history.html

**Files:**
- Rewrite: `modules/routes/web/templates/market/price_history.html`

Depends on: Task 1 (uses `.wv-*` classes)

This is the largest task. The template is a complete rewrite — replace the entire file contents.

- [ ] **Step 1: Replace price_history.html with the new template**

Replace the entire contents of `modules/routes/web/templates/market/price_history.html` with:

```html
{% extends '/components/_base.html' %}
{% block title %}Price History{% endblock %}
{% block content %}

    <!-- Header -->
    <h1 id="pageTitle">Price History</h1>

    <!-- Search bar -->
    <div class="wv-search-wrapper mb-3">
        <i class="bi bi-search wv-search-icon"></i>
        <input type="text" class="wv-input" id="itemSearch"
               placeholder="Search item: Hero, Dernic Ingot 3 ...">
    </div>

    <!-- Error alert (hidden by default) -->
    <div id="errorAlert" class="wv-alert-error mb-3"></div>

    <!-- Timeframe pills -->
    <div class="wv-pill-group mb-3">
        <button class="wv-btn-pill active" id="btn7" onclick="updateTimeframe(7, this)">7d</button>
        <button class="wv-btn-pill" id="btn14" onclick="updateTimeframe(14, this)">14d</button>
        <button class="wv-btn-pill" id="btn30" onclick="updateTimeframe(30, this)">30d</button>
        <button class="wv-btn-pill" id="btn90" onclick="updateTimeframe(90, this)">90d</button>
        <button class="wv-btn-pill" id="btnRange" onclick="activateDateRange(this)">Custom</button>
    </div>

    <!-- Custom date range (hidden until 'Custom' clicked) -->
    <div class="row mb-3" id="dateRangeContainer" style="display: none;">
        <div class="col-md-3 mb-2">
            <label for="startDate" class="form-label" style="font-size:0.85rem;color:var(--wv-text-secondary);">Start Date</label>
            <input type="text" class="wv-input" id="startDate" placeholder="YYYY-MM-DD">
        </div>
        <div class="col-md-3 mb-2">
            <label for="endDate" class="form-label" style="font-size:0.85rem;color:var(--wv-text-secondary);">End Date</label>
            <input type="text" class="wv-input" id="endDate" placeholder="YYYY-MM-DD">
        </div>
        <div class="col-md-3 mb-2 d-flex align-items-end gap-2">
            <button id="applyFilter" class="wv-btn-primary">Apply</button>
            <button id="resetFilter" class="wv-btn-outline">Reset</button>
        </div>
    </div>

    <!-- Stats Zone: Identified (skeleton on load) -->
    <div id="statsIdentified" class="wv-grid-4col mb-3" style="display:none;"></div>

    <!-- Stats Zone: Unidentified (conditional) -->
    <div id="statsUnidentifiedHeader" class="wv-section-header" style="display:none;">Unidentified</div>
    <div id="statsUnidentified" class="wv-grid-4col mb-3" style="display:none;"></div>

    <!-- Skeleton placeholders (visible before data loads) -->
    <div id="statsSkeleton" class="wv-grid-4col mb-3" style="display:none;">
        <div class="wv-stat-card"><div class="wv-skeleton" style="height:14px;width:60%;margin-bottom:8px;"></div><div class="wv-skeleton" style="height:24px;width:80%;"></div></div>
        <div class="wv-stat-card"><div class="wv-skeleton" style="height:14px;width:60%;margin-bottom:8px;"></div><div class="wv-skeleton" style="height:24px;width:80%;"></div></div>
        <div class="wv-stat-card"><div class="wv-skeleton" style="height:14px;width:60%;margin-bottom:8px;"></div><div class="wv-skeleton" style="height:24px;width:80%;"></div></div>
        <div class="wv-stat-card"><div class="wv-skeleton" style="height:14px;width:60%;margin-bottom:8px;"></div><div class="wv-skeleton" style="height:24px;width:80%;"></div></div>
    </div>

    <!-- Price Chart -->
    <div class="wv-card mb-3">
        <div id="priceChart" style="min-height:400px;"></div>
        <div id="priceChartEmpty" class="wv-empty-state" style="display:none;min-height:400px;">
            <i class="bi bi-graph-up"></i>
            <p>No price data found for this item</p>
        </div>
    </div>

    <!-- Volume Chart -->
    <div class="wv-card mb-3">
        <div id="volumeChart" style="min-height:200px;"></div>
    </div>

    <!-- ApexCharts CDN -->
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

    <script>
        /* ── State ── */
        let priceChart = null;
        let volumeChart = null;
        let currentTimeframe = 7;
        const DEFAULT_LAG_DAYS = 1;
        const MS_PER_DAY = 24 * 60 * 60 * 1000;

        /* ── Helpers ── */
        function capitalizeWords(str) {
            const smallWords = ['of'];
            return str.split(' ').map((word, index) => {
                if (index === 0 || !smallWords.includes(word.toLowerCase())) {
                    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                }
                return word.toLowerCase();
            }).join(' ');
        }

        function convertEmeraldsToGameFormat(emeralds) {
            if (emeralds == null || isNaN(emeralds)) return '—';
            emeralds = Math.round(emeralds);
            const stx = Math.floor(emeralds / (64 * 64 * 64));
            let rem = emeralds % (64 * 64 * 64);
            const le = Math.floor(rem / (64 * 64));
            rem %= (64 * 64);
            const eb = Math.floor(rem / 64);
            const e = rem % 64;
            if (stx > 0) {
                let dec = le + eb / 64 + e / (64 * 64);
                dec = Math.round(dec * 100) / 100;
                const display = Number.isInteger(dec) ? dec.toString() : dec.toFixed(2);
                return stx + 'stx' + (display !== '0' ? ' ' + display + 'le' : '');
            }
            let result = '';
            if (le > 0) result += le + 'le ';
            if (eb > 0) result += eb + 'eb ';
            if (e > 0) result += e + 'e';
            return result.trim() || '0e';
        }

        function formatPrice(val) {
            if (val == null || isNaN(val) || val === 0) return '—';
            return convertEmeraldsToGameFormat(val);
        }

        function formatPriceWithRaw(val) {
            if (val == null || isNaN(val) || val === 0) return '—';
            return Math.round(val).toLocaleString() + 'e';
        }

        /* ── Get current theme for ApexCharts ── */
        function getChartTheme() {
            const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
            const style = getComputedStyle(document.documentElement);
            return {
                mode: isDark ? 'dark' : 'light',
                background: 'transparent',
                foreColor: style.getPropertyValue('--wv-chart-text').trim() || '#9ca3af',
                gridColor: style.getPropertyValue('--wv-chart-grid').trim() || 'rgba(255,255,255,0.06)'
            };
        }

        /* ── Stat cards ── */
        function buildStatCard(label, value) {
            const card = document.createElement('div');
            card.className = 'wv-stat-card';
            card.innerHTML =
                '<span class="wv-stat-label">' + label + '</span>' +
                '<span class="wv-stat-value">' + formatPrice(value) + '</span>' +
                '<span class="wv-stat-sub">' + formatPriceWithRaw(value) + '</span>';
            return card;
        }

        function buildCountCard(label, value) {
            const card = document.createElement('div');
            card.className = 'wv-stat-card';
            card.innerHTML =
                '<span class="wv-stat-label">' + label + '</span>' +
                '<span class="wv-stat-value">' + (value != null ? Math.round(value).toLocaleString() : '—') + '</span>';
            return card;
        }

        function renderStats(data) {
            const latest = data[data.length - 1];
            const idEl = document.getElementById('statsIdentified');
            const unidEl = document.getElementById('statsUnidentified');
            const unidHeader = document.getElementById('statsUnidentifiedHeader');

            // Identified stats
            idEl.innerHTML = '';
            idEl.appendChild(buildStatCard('Average Price', latest.average_price));
            idEl.appendChild(buildStatCard('80% Average', latest.average_mid_80_percent_price));
            idEl.appendChild(buildStatCard('Median (P50)', latest.p50_price));
            idEl.appendChild(buildStatCard('P50 EMA (7d)', latest.average_p50_ema_price));
            idEl.appendChild(buildStatCard('Lowest Price', latest.lowest_price));
            idEl.appendChild(buildStatCard('Highest Price', latest.highest_price));
            idEl.appendChild(buildCountCard('Listings', latest.total_count));
            idEl.style.display = '';

            // Unidentified stats (show only if any value > 0)
            const hasUnid = (latest.unidentified_average_price > 0) ||
                            (latest.unidentified_average_mid_80_percent_price > 0) ||
                            (latest.unidentified_p50_price > 0) ||
                            (latest.unidentified_average_p50_ema_price > 0) ||
                            (latest.unidentified_lowest_price > 0) ||
                            (latest.unidentified_highest_price > 0) ||
                            (latest.unidentified_count > 0);

            if (hasUnid) {
                unidEl.innerHTML = '';
                unidEl.appendChild(buildStatCard('Unid Average', latest.unidentified_average_price));
                unidEl.appendChild(buildStatCard('Unid 80% Avg', latest.unidentified_average_mid_80_percent_price));
                unidEl.appendChild(buildStatCard('Unid Median', latest.unidentified_p50_price));
                unidEl.appendChild(buildStatCard('Unid P50 EMA', latest.unidentified_average_p50_ema_price));
                unidEl.appendChild(buildStatCard('Unid Lowest', latest.unidentified_lowest_price));
                unidEl.appendChild(buildStatCard('Unid Highest', latest.unidentified_highest_price));
                unidEl.appendChild(buildCountCard('Unid Listings', latest.unidentified_count));
                unidEl.style.display = '';
                unidHeader.style.display = '';
            } else {
                unidEl.style.display = 'none';
                unidHeader.style.display = 'none';
            }
        }

        /* ── Charts ── */
        function makeSeries(name, data, visible) {
            return { name: name, data: data, visible: visible !== false };
        }

        function renderCharts(data) {
            const theme = getChartTheme();
            const timestamps = data.map(d => new Date(d.timestamp).getTime());

            // Destroy previous charts
            if (priceChart) { priceChart.destroy(); priceChart = null; }
            if (volumeChart) { volumeChart.destroy(); volumeChart = null; }

            // Build price series
            const priceSeries = [
                makeSeries('P50 (Median)',  data.map((d,i) => [timestamps[i], d.p50_price]),           true),
                makeSeries('P50 EMA (7d)',  data.map((d,i) => [timestamps[i], d.average_p50_ema_price]), true),
                makeSeries('Average',       data.map((d,i) => [timestamps[i], d.average_price]),        false),
                makeSeries('80% Average',   data.map((d,i) => [timestamps[i], d.average_mid_80_percent_price]), false),
                makeSeries('Lowest',        data.map((d,i) => [timestamps[i], d.lowest_price]),         true),
                makeSeries('Highest',       data.map((d,i) => [timestamps[i], d.highest_price]),        true),
                makeSeries('Unid P50',      data.map((d,i) => [timestamps[i], d.unidentified_p50_price]),             false),
                makeSeries('Unid P50 EMA',  data.map((d,i) => [timestamps[i], d.unidentified_average_p50_ema_price]), false),
                makeSeries('Unid Average',  data.map((d,i) => [timestamps[i], d.unidentified_average_price]),         false),
                makeSeries('Unid 80% Avg',  data.map((d,i) => [timestamps[i], d.unidentified_average_mid_80_percent_price]), false),
                makeSeries('Unid Lowest',   data.map((d,i) => [timestamps[i], d.unidentified_lowest_price]),          false),
                makeSeries('Unid Highest',  data.map((d,i) => [timestamps[i], d.unidentified_highest_price]),         false),
            ];

            const priceColors = [
                '#4facfe', '#00d4ff', '#4bc0c0', '#358686', '#36a2eb', '#ff6384',
                '#b77aff', '#9b59b6', '#6a5d9e', '#453586', '#7e57c2', '#e040fb'
            ];

            // Determine which series should be hidden initially
            const hiddenSeries = priceSeries
                .map((s, i) => s.visible ? null : i)
                .filter(i => i !== null);

            priceChart = new ApexCharts(document.getElementById('priceChart'), {
                chart: {
                    type: 'line',
                    height: 400,
                    background: theme.background,
                    foreColor: theme.foreColor,
                    toolbar: { show: true, tools: { download: true, selection: true, zoom: true, zoomin: true, zoomout: true, pan: true, reset: true } },
                    zoom: { enabled: true },
                    animations: { enabled: true, easing: 'easeinout', speed: 400 }
                },
                series: priceSeries.map(s => ({ name: s.name, data: s.data })),
                colors: priceColors,
                stroke: { width: 2, curve: 'smooth' },
                xaxis: {
                    type: 'datetime',
                    labels: { datetimeUTC: false },
                    axisBorder: { show: false },
                    axisTicks: { show: false }
                },
                yaxis: {
                    title: { text: 'Price (emeralds)' },
                    labels: {
                        formatter: function(val) { return val != null ? convertEmeraldsToGameFormat(val) : ''; }
                    }
                },
                tooltip: {
                    shared: true,
                    intersect: false,
                    x: { format: 'dd MMM yyyy' },
                    y: {
                        formatter: function(val) {
                            if (val == null) return '—';
                            return Math.round(val).toLocaleString() + 'e (' + convertEmeraldsToGameFormat(val) + ')';
                        }
                    }
                },
                grid: {
                    borderColor: theme.gridColor,
                    strokeDashArray: 3
                },
                legend: {
                    position: 'top',
                    horizontalAlign: 'left',
                    fontSize: '12px',
                    itemMargin: { horizontal: 8, vertical: 4 }
                },
                theme: { mode: theme.mode }
            });

            priceChart.render().then(function() {
                // Hide series that should not be visible by default
                hiddenSeries.forEach(function(idx) {
                    priceChart.toggleSeries(priceSeries[idx].name);
                });
            });

            // Volume chart
            const volumeSeries = [
                { name: 'Total Listings', data: data.map((d,i) => [timestamps[i], d.total_count]) },
                { name: 'Unid Listings',  data: data.map((d,i) => [timestamps[i], d.unidentified_count]) }
            ];

            volumeChart = new ApexCharts(document.getElementById('volumeChart'), {
                chart: {
                    type: 'area',
                    height: 200,
                    background: theme.background,
                    foreColor: theme.foreColor,
                    toolbar: { show: false },
                    zoom: { enabled: false },
                    animations: { enabled: true, easing: 'easeinout', speed: 400 }
                },
                series: volumeSeries,
                colors: ['rgba(75, 192, 192, 0.8)', 'rgba(54, 162, 235, 0.8)'],
                fill: { type: 'solid', opacity: [0.3, 0.3] },
                stroke: { width: 2, curve: 'smooth' },
                xaxis: {
                    type: 'datetime',
                    labels: { datetimeUTC: false },
                    axisBorder: { show: false },
                    axisTicks: { show: false }
                },
                yaxis: {
                    title: { text: 'Listings' },
                    labels: { formatter: function(val) { return val != null ? Math.round(val).toString() : ''; } }
                },
                tooltip: {
                    shared: true,
                    intersect: false,
                    x: { format: 'dd MMM yyyy' }
                },
                grid: {
                    borderColor: theme.gridColor,
                    strokeDashArray: 3
                },
                legend: {
                    position: 'top',
                    horizontalAlign: 'left',
                    fontSize: '12px'
                },
                theme: { mode: theme.mode }
            });

            volumeChart.render();
        }

        /* ── UI state helpers ── */
        function showLoading() {
            document.getElementById('statsSkeleton').style.display = '';
            document.getElementById('statsIdentified').style.display = 'none';
            document.getElementById('statsUnidentified').style.display = 'none';
            document.getElementById('statsUnidentifiedHeader').style.display = 'none';
            document.getElementById('priceChart').style.display = 'none';
            document.getElementById('priceChartEmpty').style.display = 'none';
            document.getElementById('volumeChart').style.display = 'none';
            document.getElementById('errorAlert').style.display = 'none';
        }

        function showEmpty() {
            document.getElementById('statsSkeleton').style.display = 'none';
            document.getElementById('statsIdentified').style.display = 'none';
            document.getElementById('statsUnidentified').style.display = 'none';
            document.getElementById('statsUnidentifiedHeader').style.display = 'none';
            document.getElementById('priceChart').style.display = 'none';
            document.getElementById('priceChartEmpty').style.display = '';
            document.getElementById('volumeChart').style.display = 'none';
            if (priceChart) { priceChart.destroy(); priceChart = null; }
            if (volumeChart) { volumeChart.destroy(); volumeChart = null; }
        }

        function showError(msg) {
            const el = document.getElementById('errorAlert');
            el.textContent = msg;
            el.style.display = '';
            document.getElementById('statsSkeleton').style.display = 'none';
        }

        function showData() {
            document.getElementById('statsSkeleton').style.display = 'none';
            document.getElementById('priceChart').style.display = '';
            document.getElementById('priceChartEmpty').style.display = 'none';
            document.getElementById('volumeChart').style.display = '';
            document.getElementById('errorAlert').style.display = 'none';
        }

        /* ── Data fetching ── */
        async function fetchPriceData(itemName) {
            showLoading();
            try {
                const params = new URLSearchParams(window.location.search);
                const tierParam = params.get('tier');
                const match = itemName.match(/^(.*?)(\d+)$/);
                let base = itemName, tier = tierParam;

                if (!tier && match) {
                    base = match[1].trim();
                    tier = match[2].trim();
                }

                const startVal = document.getElementById('startDate').value || params.get('start_date') || '';
                const endVal = document.getElementById('endDate').value || params.get('end_date') || '';
                document.getElementById('startDate').value = startVal;
                document.getElementById('endDate').value = endVal;

                let s = startVal, e = endVal;
                if (!s && !e) {
                    const now = new Date();
                    const lag = new Date(now.getTime() - DEFAULT_LAG_DAYS * MS_PER_DAY);
                    e = lag.toISOString().split('T')[0];
                    const begin = new Date(lag.getTime() - currentTimeframe * MS_PER_DAY);
                    s = begin.toISOString().split('T')[0];
                }

                const q = new URLSearchParams({ start_date: s, end_date: e });
                if (tier) q.append('tier', tier);
                const url = '/api/trademarket/history/' + encodeURIComponent(base) + '?' + q;
                const res = await fetch(url);

                if (!res.ok) {
                    showError('Failed to load price data (HTTP ' + res.status + ')');
                    return;
                }

                const data = await res.json();
                if (!Array.isArray(data) || data.length === 0) {
                    showEmpty();
                    return;
                }

                showData();
                renderStats(data);
                renderCharts(data);
            } catch (err) {
                console.error(err);
                showError('Failed to load price data');
            }
        }

        /* ── Search & navigation ── */
        function handleSearch(item) {
            if (!item) { showEmpty(); return; }
            const name = capitalizeWords(item);
            document.getElementById('itemSearch').value = name;
            document.getElementById('pageTitle').textContent = 'Price History \u2014 ' + name;
            const baseUrl = '/history/' + encodeURIComponent(name);
            history.replaceState(null, '', baseUrl + window.location.search);
            fetchPriceData(name);
        }

        function updateTimeframe(days, btn) {
            history.replaceState(null, '', location.pathname);
            document.getElementById('dateRangeContainer').style.display = 'none';
            document.getElementById('startDate').value = '';
            document.getElementById('endDate').value = '';
            currentTimeframe = days;
            document.querySelectorAll('.wv-pill-group .wv-btn-pill').forEach(function(b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            const nm = document.getElementById('itemSearch').value.trim();
            if (nm) handleSearch(nm);
        }

        function activateDateRange(btn) {
            document.querySelectorAll('.wv-pill-group .wv-btn-pill').forEach(function(b) {
                b.classList.remove('active');
            });
            btn.classList.add('active');
            document.getElementById('dateRangeContainer').style.display = 'flex';
        }

        /* ── Theme change listener ── */
        const observer = new MutationObserver(function() {
            const nm = document.getElementById('itemSearch').value.trim();
            if (nm && priceChart) {
                // Re-fetch to rebuild charts with new theme colors
                fetchPriceData(nm);
            }
        });
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });

        /* ── Init ── */
        window.onload = function() {
            $('#startDate,#endDate').datepicker({
                format: 'yyyy-mm-dd',
                autoclose: true,
                todayHighlight: true
            });

            document.getElementById('itemSearch').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') handleSearch(e.target.value.trim());
            });
            document.getElementById('applyFilter').onclick = function() {
                handleSearch(document.getElementById('itemSearch').value.trim());
            };
            document.getElementById('resetFilter').onclick = function() {
                document.getElementById('startDate').value = '';
                document.getElementById('endDate').value = '';
                history.replaceState(null, '', location.pathname);
            };

            // Restore state from URL
            const initItem = '{{ item_name }}';
            const urlParams = new URLSearchParams(window.location.search);
            const sParam = urlParams.get('start_date');
            const eParam = urlParams.get('end_date');
            const presets = [7, 14, 30, 90];

            if (sParam || eParam) {
                if (sParam && eParam) {
                    const sDate = new Date(sParam);
                    const eDate = new Date(eParam);
                    const diffDays = (eDate - sDate) / MS_PER_DAY;
                    const today = new Date();
                    const lagged = new Date(today.getTime() - DEFAULT_LAG_DAYS * MS_PER_DAY);
                    const lagISO = lagged.toISOString().split('T')[0];
                    let matched = false;
                    presets.forEach(function(d) {
                        if (!matched &&
                            Math.abs(diffDays - d) < 0.1 &&
                            eParam === lagISO &&
                            sParam === new Date(lagged.getTime() - d * MS_PER_DAY).toISOString().split('T')[0]
                        ) {
                            updateTimeframe(d, document.getElementById('btn' + d));
                            matched = true;
                        }
                    });
                    if (!matched) {
                        activateDateRange(document.getElementById('btnRange'));
                        document.getElementById('startDate').value = sParam;
                        document.getElementById('endDate').value = eParam;
                    }
                } else {
                    activateDateRange(document.getElementById('btnRange'));
                    if (sParam) document.getElementById('startDate').value = sParam;
                    if (eParam) document.getElementById('endDate').value = eParam;
                }
            } else {
                document.getElementById('btn7').click();
            }

            if (initItem && initItem !== 'None') {
                document.getElementById('itemSearch').value = capitalizeWords(initItem);
                handleSearch(initItem);
            }
        };
    </script>
{% endblock %}
```

- [ ] **Step 2: Verify the rewrite**

Run: `grep -c "apexcharts\|ApexCharts\|wv-stat-card\|wv-card\|wv-pill" modules/routes/web/templates/market/price_history.html`
Expected: at least 10 matches, confirming ApexCharts and design system classes are present

Run: `grep -c "Chart.js\|chart.js\|new Chart" modules/routes/web/templates/market/price_history.html`
Expected: 0 (Chart.js fully removed)

- [ ] **Step 3: Commit**

```bash
git add modules/routes/web/templates/market/price_history.html
git commit -m "feat: rewrite price history page with ApexCharts, stat cards, and all 14 metrics"
```

---

### Task 4: Visual verification and integration test

**Files:** (no changes — verification only)

Depends on: Tasks 1, 2, 3

- [ ] **Step 1: Verify all files exist and are consistent**

Run these checks:

```bash
# design-system.css exists and has content
wc -l modules/routes/web/static/design-system.css

# _base.html loads design-system.css
grep "design-system.css" modules/routes/web/templates/components/_base.html

# price_history.html uses design system classes
grep -c "wv-" modules/routes/web/templates/market/price_history.html

# No Chart.js references remain in price_history.html
grep -c "chart.js\|Chart(" modules/routes/web/templates/market/price_history.html

# ApexCharts is loaded
grep "apexcharts" modules/routes/web/templates/market/price_history.html
```

Expected:
- design-system.css: ~240 lines
- _base.html: 1 match for design-system.css
- price_history.html: 20+ matches for `wv-` classes
- price_history.html: 0 matches for Chart.js
- price_history.html: 1 match for apexcharts CDN

- [ ] **Step 2: Verify dark/light theme token consistency**

Run:

```bash
# All dark theme tokens should have light counterparts
grep "^\-\-wv-" modules/routes/web/static/design-system.css | sed 's/:.*//' | sort | uniq -c | sort -rn | head -20
```

Expected: each token name appears exactly 2 times (once in dark, once in light)

- [ ] **Step 3: Check that existing pages are unaffected**

Run:

```bash
# design-system.css should not override any existing style.css selectors
grep -E "^(body|h1|img|a|\.footer|\.sidebar|\.content|\.navbar)" modules/routes/web/static/design-system.css
```

Expected: 0 matches — the design system only defines `.wv-*` prefixed classes and CSS variables

- [ ] **Step 4: Final commit with all files**

If any fixups were needed in steps 1-3, commit them:

```bash
git add -A
git status
# Only commit if there are changes
git diff --cached --quiet || git commit -m "fix: integration fixes for price history redesign"
```

---

## Execution Dependencies

```
Task 1 (design-system.css)  ──┐
                               ├──> Task 4 (verification)
Task 2 (_base.html edit)    ──┤
                               │
Task 3 (price_history.html) ──┘

Tasks 1 and 3 can run in parallel.
Task 2 depends on Task 1.
Task 4 depends on all others.
```
