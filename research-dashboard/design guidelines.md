# DRC Research Dashboard — Design Guidelines

**Research Whitespace Explorer · v2.0**  
Source of truth: `research-dashboard/dashboard/index.html`  
Update this file whenever tokens, type styles, spacing, or components change.

---

## 1. Design Principles

| Principle | In practice |
|---|---|
| **Data forward** | Research content is the product. Chrome frames it; it never competes. |
| **Dark & quiet** | Deep surfaces, high-contrast text. Color reserved for meaning only. |
| **Consistent hierarchy** | Spacing, weight, and contrast do the hierarchical work — not color. |
| **16px floor** | No text smaller than 16px anywhere, ever. |
| **Reuse before extending** | Always reach for an existing variable before introducing anything new. |

---

## 2. Color System

### 2.1 Surface Tokens

Use these in order to create depth. Never skip a level when layering panels inside panels.

| Token | Value | Role |
|---|---|---|
| `--bg` | `#080810` | Page background only |
| `--surface` | `#111118` | Cards, primary panels |
| `--surface2` | `#18181f` | Nested cards, secondary panels |
| `--surface3` | `#1f202a` | Inputs, chip fills, hover backgrounds |
| `--border` | `#252530` | All structural borders — always 1px |

### 2.2 Text Tokens

Three levels only. Never use `--muted` for any readable content.

| Token | Value | Role |
|---|---|---|
| `--text` | `#dddde8` | Primary content, all headings |
| `--text-soft` | `#b6b7c9` | Descriptions, metadata, labels, support copy |
| `--muted` | `#5a5a70` | Placeholder text, disabled states, UI hints only |
| `--white` | `#f0f0f8` | Emphasis moments within dark surfaces |

### 2.3 Accent Tokens

Accents encode **category meaning** — they are not decorative. Apply them consistently to every chip, tag, counter, and highlight. Do not introduce a fifth accent without updating the full category map below.

| Token | Value | Assigned Category |
|---|---|---|
| `--accent1` | `#7c6af7` | Ideation |
| `--accent2` | `#f7796a` | Optimization |
| `--accent3` | `#5af7c0` | Grammar |
| `--accent4` | `#f7c55a` | Decision Making |

### 2.4 Accent Construction Rules

Accents are **never used at full opacity as fills**. They appear at:

- **Chip / tag background:** 8% opacity (`rgba(accent, 0.08)`)
- **Chip / tag border:** 30% opacity (`rgba(accent, 0.30)`)
- **Chip / tag text:** 100% opacity (full accent color)
- **Numeric highlights / scores:** 100% opacity, `--accent3` only
- **Top-edge card accent bar:** 100%, 3px height
- **Hover emphasis borders:** 40% opacity

Never use an accent as a card background or large fill — it overpowers the layout and makes other categories hard to read.

---

## 3. Typography

### 3.1 Font Families

Three families. Each has a specific role. Do not substitute or mix beyond what is described.

| Family | CSS Value | Role |
|---|---|---|
| **DM Mono** | `'DM Mono', monospace` | Body text, card descriptions, sidebar copy, metadata, all data-dense reading |
| **DM Sans** | `'DM Sans', Arial, Helvetica, sans-serif` | Navigation, tabs, buttons, filter labels, section headings, form controls |
| **Syne** | `'Syne', sans-serif` | Page/dashboard title, numeric highlights, score displays |

**Rule:** If it's being *read* (paragraphs, descriptions, author bios, whitespace opportunity text), use **DM Mono**. If it's being *acted on* (tabs, buttons, nav, filters), use **DM Sans**. If it's a *number or title on display*, use **Syne**.

---

### 3.2 Complete Type Scale

Every text element in the product maps to exactly one of these styles. Do not invent intermediate sizes.

---

#### Style 1 — Dashboard Title

Used for the main page heading only. One per view.

```
Font:         Syne
Weight:       700
Size:         clamp(23px, 2.6vw, 34px)
Line height:  0.98
Letter spacing: -0.02em
Color:        --text
Transform:    none
```

---

#### Style 2 — Section Heading

Top-level section labels within a page (e.g. "Whitespace Opportunities", "Author Overview").

```
Font:         DM Sans
Weight:       600
Size:         18px
Line height:  1.3
Letter spacing: 0
Color:        --text
Transform:    none
```

---

#### Style 3 — Card Title

The primary title inside a paper card, whitespace card, or author card.

```
Font:         DM Sans
Weight:       600
Size:         16px
Line height:  1.35
Letter spacing: 0
Color:        --text
Transform:    none
Max lines:    2 (truncate with ellipsis on overflow)
```

---

#### Style 4 — Body / Description Text

All descriptive paragraph text inside cards, sidebars, and expanded views. The most-used style in the dashboard.

```
Font:         DM Mono
Weight:       400
Size:         16px
Line height:  1.7
Letter spacing: 0
Color:        --text-soft
Transform:    none
```

**Do not reduce to 14px or 13px even in compact cards.** The 16px floor is non-negotiable.

---

#### Style 5 — Metadata / Support Text

Author names, publication years, citation counts, paper IDs, and other secondary data points within cards.

```
Font:         DM Mono
Weight:       400
Size:         16px
Line height:  1.6
Letter spacing: 0
Color:        --text-soft
Transform:    none
```

Note: metadata uses the same size as body (16px) but typically sits in the chip row or below the card title, separated by spacing rather than font-size reduction.

---

#### Style 6 — Numeric Highlight / Score

Whitespace opportunity scores, paper counts in headers, and other prominent single numbers.

```
Font:         Syne
Weight:       700
Size:         20px
Line height:  1.0
Letter spacing: -0.01em
Color:        --accent3   (scores)  OR  --text  (neutral counts)
Transform:    none
```

Use `--accent3` for scored/ranked numbers (whitespace priority score, relevance). Use `--text` for neutral counts (total papers, author count).

---

#### Style 7 — Section Label / Utility Heading

Small uppercase labels used to introduce sidebar sections, filter groups, and card sub-sections (e.g. "Filter by Category", "Opportunity", "Co-authors").

```
Font:         DM Sans
Weight:       600
Size:         11px  —  the only allowed exception to the 16px floor
              (utility labels only — never for reading text)
Line height:  1.4
Letter spacing: 0.10em – 0.14em
Color:        --muted
Transform:    uppercase
```

**This is the only style permitted below 16px.** It exists solely for non-reading utility labels. Never use it for descriptions, card content, or any text the user needs to read. Maximum 3 words per label.

---

#### Style 8 — Tab / Navigation Label

Horizontal tab labels and primary nav items.

```
Font:         DM Sans
Weight:       500
Size:         16px
Line height:  1.0
Letter spacing: 0
Color:        --text-soft  (inactive)
              --text       (active)
Transform:    none
```

Active tab gets `--text` color plus the accent underline. No bold shift on active — weight stays at 500.

---

#### Style 9 — Button / Filter Control

Primary action buttons, filter dropdowns, select controls, search input placeholder text.

```
Font:         DM Sans
Weight:       500
Size:         16px
Line height:  1.0
Letter spacing: 0
Color:        --text-soft  (default state)
              --text       (hover / focus state)
Transform:    none
```

---

#### Style 10 — Chip / Pill Label

Category chips, year pills, author tags, and topic chips.

```
Font:         DM Sans
Weight:       500
Size:         12px
Line height:  1.0
Letter spacing: 0
Color:        [accent color]   (category chips)
              --muted          (neutral/filter chips)
Transform:    none
Padding:      3px 9px
Border radius: 999px
```

Chips are the **only other exception** to the 16px floor. They are decorative-functional labels in a tightly constrained pill shape, not reading text.

---

### 3.3 Type Pairing Logic

When a card has both a title and description, the contrast between them comes from **font family + weight + color**, not size:

```
Card Title:      DM Sans   600   16px   --text
Card Description: DM Mono   400   16px   --text-soft
```

The visual separation is achieved entirely by family and color. This is intentional — reducing the description font size to create hierarchy would violate the 16px floor and make dense research content harder to read.

---

### 3.4 Line Height Reference

| Context | Line height |
|---|---|
| Dashboard title | `0.98` |
| Section heading | `1.3` |
| Card title (2 lines) | `1.35` |
| Body / description | `1.7` |
| Metadata / support | `1.6` |
| Tab / button | `1.0` |
| Chip / pill | `1.0` |

---

### 3.5 Letter Spacing Reference

| Context | Letter spacing |
|---|---|
| Dashboard title | `-0.02em` |
| Numeric highlight | `-0.01em` |
| All other headings | `0` |
| All body text | `0` |
| Section labels (uppercase) | `0.10em – 0.14em` |

**Never track body text or card titles.** Tight tracking on monospaced text (DM Mono) in particular creates unreadable dense blocks.

---

### 3.6 Font Weight Reference

| Weight | Used for |
|---|---|
| `400` | All DM Mono body, metadata, descriptions |
| `500` | DM Sans navigation, tabs, buttons, chips |
| `600` | DM Sans section headings, card titles, utility labels |
| `700` | Syne dashboard title, numeric scores |

No other weights. Do not use `300` (too light on dark backgrounds), `800`, or `900`.

---

### 3.7 What Not To Do — Typography

- **Never** reduce any reading text below `16px`, regardless of card compactness.
- **Never** apply `DM Mono` to buttons, tabs, or navigation items.
- **Never** apply `Syne` to body text, descriptions, or labels.
- **Never** use `DM Sans` for descriptive paragraphs — it reads as marketing copy.
- **Never** use letter spacing on body or heading text (only utility labels).
- **Never** use a font weight outside the four defined above.
- **Never** set dashboard title to a fixed px value — always use `clamp(23px, 2.6vw, 34px)`.

---

## 4. Layout & Spacing

### 4.1 Main Grid

- Desktop: two-column — `236px` fixed sidebar + fluid content area.
- Mobile: single column — sidebar stacks above content. Tabs scroll horizontally.
- Header spans full width above the grid: contains eyebrow, title, counters, and data status line.

### 4.2 Spacing Scale

Always pick from these values. Do not use arbitrary pixel values.

| Value | Use |
|---|---|
| `6px` | Icon-to-text gap, tight chip padding |
| `8px` | Chip internal horizontal padding |
| `10px` | Between metadata items in a row |
| `12px` | Between elements within a card |
| `14px` | Sidebar list item gaps |
| `16px` | Card side padding, standard control height gap |
| `18px` | Between card rows in a grid |
| `20px` | Sidebar section gap, header element spacing |
| `22px` | Between card title and description |
| `28px` | Section-to-section gap |

### 4.3 Border Radius

| Value | Use |
|---|---|
| `999px` | All chips and pills |
| `6px – 8px` | Small utility panels, input controls |
| `10px – 12px` | Standard cards, filter controls |
| `14px` | Header counter group |

### 4.4 Borders

- Always `1px solid var(--border)`.
- Never use 2px or heavier structural borders.
- Use `--border` at rest. On hover, shift to `--surface3` as the border color.
- Card accent bar (whitespace cards): `3px` top edge, accent color at 100%.

### 4.5 Shadows

Standard card shadow only:

```
box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
```

Do not increase depth beyond this. Prefer layered surface contrast over shadow depth.

---

## 5. Component Rules

### 5.1 Header

- Keep compact. One tint gradient (top to bottom, subtle) plus a thin accent divider below.
- Title (Style 1) visually dominant.
- Counters inline with title area using Style 6 numerics.
- Data status line below title using Style 5 metadata text.

### 5.2 Sidebar

- Section introduced with Style 7 label + `1px solid var(--border)` divider.
- Content in DM Mono (Style 4 or Style 5).
- All text ≥ 16px.
- Sticky rail on desktop; stacks above content on mobile.

### 5.3 Tabs

- Use Style 8 (DM Sans 500 16px).
- Horizontal scroll on small screens — never wrap to second row.
- Active state: `--text` color + 2px bottom accent line using category or primary accent.
- Inactive: `--text-soft`, no underline.

### 5.4 Buttons & Filter Controls

- Style 9 (DM Sans 500 16px).
- Background: `--surface3`. Border: `1px solid var(--border)`.
- Hover: border shifts to `rgba(accent, 0.4)`, background lightens to `--surface2` edge.
- No glow, no box-shadow change, no scale transform on hover.
- Border radius: `8px` for buttons, `10px` for large filter controls.
- Minimum height: 36px (accessibility tap target).

### 5.5 Paper Cards

```
Background:   --surface
Border:       1px solid var(--border)
Radius:       10px
Padding:      14px 16px

Layout (top to bottom):
  1. [Card Title — Style 3]     [Score — Style 6, right-aligned]
  2. [Category chip] [Year pill] [Author pill]
  3. [Description — Style 4]

Score: Syne 700 18px, --accent3
Title max-width: subtract score width + 10px gap
```

### 5.6 Whitespace Opportunity Cards

```
Background:   --surface2
Border:       1px solid var(--border)
Radius:       10px
Top accent:   3px solid [category accent]
Padding:      14px 16px  (below accent bar)

Layout (top to bottom):
  1. [Category chip — left]     [Score — right]
  2. [Card Title — Style 3]
  3. [Description — Style 4]
  4. [Section label: "OPPORTUNITY" — Style 7]
  5. [Opportunity text — Style 4]

Sections 3 and 5 use the same Style 4 but are separated by the Style 7 label.
```

### 5.7 Author Cards (Summary)

```
Background:   --surface2
Border:       1px solid var(--border)
Radius:       10px
Padding:      14px 16px
Height:       fit-content

Content:
  - Author name (Style 3, --text)
  - Paper count (Style 6 numeric, --text)
  - Latest year (Style 5, --text-soft)
  - Short description (Style 4, --text-soft, max 2 lines)
```

Expanded author cards span full row width and may include full bio, co-author network, and year distribution.

### 5.8 Chips & Pills

```
Category chip:   DM Sans 500 12px · accent color text · 8% accent fill · 30% accent border · 999px radius · 3px 9px padding
Year pill:       DM Sans 500 12px · --muted text · --surface3 fill · --border border · 999px radius · 3px 9px padding
Filter chip:     DM Sans 500 12px · --muted text · --surface3 fill · --border border · 999px radius · 3px 9px padding
```

Never mix chip styles within the same row — category chips and neutral chips have distinct visual weight.

---

## 6. Motion & Interaction

| Property | Value |
|---|---|
| Hover transition duration | `0.12s ease` |
| Filter / expand transition | `0.15s ease` |
| Hover border treatment | Shift from `--border` to `rgba(accent, 0.4)` |
| Hover fill treatment | Background lightens by one surface step |
| Scale on hover | Never |
| Glow / neon on hover | Never |
| Box-shadow change on hover | Never |

Hover states signal interactivity through **border and background color shift only** — no shadows, no rings, no lifts. These effects read as error states in dark UIs.

---

## 7. Accessibility

| Requirement | Value |
|---|---|
| Minimum font size | `16px` (utility labels and chips are the only exceptions) |
| Primary text contrast | `--text` on `--surface` ≥ 7:1 |
| Secondary text contrast | `--text-soft` on `--surface` ≥ 4.5:1 |
| Category color rule | Always paired with a text label — never color alone |
| Interactive target minimum | `36px` tall |
| `--muted` text use | Placeholders and hints only — never for readable content |
| Responsive font floor | Never reduce below `16px` on mobile |

---

## 8. Do & Don't

### Do

- Reuse existing CSS variables before introducing anything new.
- Use `1px solid var(--border)` for all structural borders.
- Keep category accent colors consistent across every chip, tag, and highlight.
- Use `--text-soft` for descriptions, metadata, and secondary labels.
- Keep cards content-driven and compact — no oversized empty space.
- Apply accent colors at 8% opacity for chip fills.
- Always pair category color with its text label.
- Update this document whenever any token, type style, or component pattern changes.

### Don't

- Add new colors without updating the full category mapping.
- Use any font size below `16px` for reading text.
- Use `--muted` for any text the user needs to read.
- Introduce a light-mode surface inside the dark dashboard.
- Use full-opacity accent fills as card or panel backgrounds.
- Use box-shadow deeper than `0 12px 32px rgba(0,0,0,0.18)`.
- Create hero sections or oversized empty card space.
- Mix too many card pattern variants — new card types need to justify themselves against the existing two (paper card, whitespace card).
- Apply `DM Mono` to navigation, buttons, or tabs.
- Apply `Syne` to body or description text.
- Use font weights outside `400 / 500 / 600 / 700`.
- Use letter spacing on body text or card titles.

---

## 9. Quick Token Reference

```css
/* Surfaces */
--bg:        #080810;
--surface:   #111118;
--surface2:  #18181f;
--surface3:  #1f202a;
--border:    #252530;

/* Text */
--text:       #dddde8;
--text-soft:  #b6b7c9;
--muted:      #5a5a70;
--white:      #f0f0f8;

/* Accents */
--accent1: #7c6af7;   /* Ideation */
--accent2: #f7796a;   /* Optimization */
--accent3: #5af7c0;   /* Grammar */
--accent4: #f7c55a;   /* Decision Making */

/* Fonts */
--font-mono: 'DM Mono', monospace;
--font-sans: 'DM Sans', Arial, Helvetica, sans-serif;
--font-display: 'Syne', sans-serif;
```

---

*DRC Research Dashboard · Design Guidelines v2.0*  
*Last updated: April 2026*