# DRC Research Dashboard Design Guidelines

This document is the UI rule book for the Research Whitespace Explorer. It is based on the current implementation in [`/Users/mana/Documents/Work/Design Research Collective/DesignResearchCollective/research-dashboard/dashboard/index.html`](/Users/mana/Documents/Work/Design Research Collective/DesignResearchCollective/research-dashboard/dashboard/index.html).

## Purpose

Use this guide to keep the dashboard visually consistent as new features, tabs, cards, filters, and data views are added.

Core goals:
- Preserve the current dark, research-oriented visual identity.
- Keep all text readable.
- Maintain compact, professional spacing.
- Reuse the existing color and typography system before introducing anything new.

## Design Principles

- Keep the interface dark, quiet, and data-forward.
- Use color mainly for category meaning, status emphasis, and subtle hierarchy.
- Prefer clear structure over decorative styling.
- Maintain a minimum readable font size of `16px`.
- Use rounded corners, thin borders, and soft layered surfaces instead of heavy shadows or bright fills.

## Color System

### Base Tokens

- `--bg`: `#080810`
- `--surface`: `#111118`
- `--surface2`: `#18181f`
- `--surface3`: `#1f202a`
- `--border`: `#252530`
- `--text`: `#dddde8`
- `--text-soft`: `#b6b7c9`
- `--muted`: `#5a5a70`
- `--white`: `#f0f0f8`

### Accent Tokens

- `--accent1`: `#7c6af7`
- `--accent2`: `#f7796a`
- `--accent3`: `#5af7c0`
- `--accent4`: `#f7c55a`

### Category Mapping

- `Ideation`: `--accent1`
- `Optimization`: `--accent2`
- `Grammar`: `--accent3`
- `Decision Making`: `--accent4`

### Color Usage Rules

- Use `--bg` for page background.
- Use `--surface`, `--surface2`, and `--surface3` for panels, cards, and layered UI.
- Use `--border` for separators, chip outlines, cards, and control boundaries.
- Use `--text` for primary content.
- Use `--text-soft` for secondary labels, descriptions, metadata, and support text.
- Use `--muted` sparingly for de-emphasized UI hints only.
- Use accent colors for category chips, counters, tags, and hover/emphasis states.
- Do not introduce new brand colors unless the existing four accent colors cannot cover the need.

## Typography

### Font Families

- Primary body / UI mono: `DM Mono, monospace`
- Primary UI sans: `DM Sans, Arial, Helvetica, sans-serif`
- Display / numeric emphasis: `Syne, sans-serif`

### Type Roles

- Body copy: `DM Mono`
- Navigation / buttons / filters: `DM Sans` or `DM Mono` depending on the existing component
- Major heading: `DM Sans`
- Numeric highlights and some display headings: `Syne`

### Font Size Rules

- Minimum font size anywhere in the product: `16px`
- Primary body size: `16px`
- Metadata and support text floor: `16px`
- Section labels and utility labels: `16px`
- Large title: `clamp(23px, 2.6vw, 34px)`
- Prominent counters: `20px`

### Type Style Rules

- Body line height: `1.6`
- Descriptive copy line height: `1.7` to `1.75`
- Large title line height: `0.98`
- Use uppercase labels sparingly for utility headings and section labels.
- Use tighter tracking only for small utility labels, never for long paragraphs.

## Layout

### Main Structure

- Desktop layout uses a two-column grid:
  - sidebar: `236px`
  - content: remaining width
- Header sits above the grid and contains:
  - eyebrow
  - main title
  - header counters
  - data status line

### Spacing Rhythm

- Prefer spacing increments in the `6px` to `28px` range.
- Common gaps:
  - `6px`
  - `8px`
  - `10px`
  - `12px`
  - `14px`
  - `16px`
  - `18px`
  - `20px`
  - `22px`
  - `28px`

### Border Radius

- Small chips / pills: `999px`
- Small panels: `6px` to `8px`
- Standard cards / controls: `10px` to `12px`
- Header counter group: `14px`

## Component Rules

### Header

- Keep the header compact.
- Use a subtle top-to-bottom tint and a thin accent gradient divider.
- Keep the title visually dominant.
- Keep counters inline with the title area when space allows.

### Sidebar

- Sidebar sections should use a label, a divider, and tightly grouped content.
- Sidebar text must remain at least `16px`.
- Use mono text in the sidebar unless a strong reason exists not to.

### Tabs

- Tabs use `DM Sans`.
- Tabs should be readable, compact, and scroll horizontally on small screens.
- Active tab uses the accent underline pattern already established.

### Buttons and Filters

- Keep controls dark with subtle borders.
- Rounded corners should stay soft, not sharp.
- Hover states should increase contrast slightly without glowing.
- Search and select controls should match card surfaces.

### Cards

- Cards use `--surface` background and `--border`.
- Avoid oversized empty space.
- Cards should be content-driven wherever possible.
- Use subtle shadow only to lift cards slightly from the background.

### Author Cards

- Summary cards should be fit-content height.
- Summary card content:
  - author name
  - paper count
  - latest publication year
  - short description
- Expanded author cards may span full row width.
- Keep summary content tight and readable.

### Whitespace Cards

- Use category-colored top edge accents.
- Use restrained emphasis for priority score markers.
- Keep description and opportunity sections clearly separated.

### Chips and Pills

- Use pills for years, tags, categories, and topic-like metadata.
- Maintain rounded pill shape.
- Use accent-backed pills only when meaning is category-based.
- Use neutral outlined pills for filters and non-category metadata.

## Motion and Interaction

- Hover transitions should stay subtle and quick.
- Use short transitions around `0.12s` to `0.15s`.
- Avoid dramatic animations.
- Scale or lift interactions should be restrained.

## Borders, Shadows, and Surfaces

- Default border color: `--border`
- Prefer 1px borders for structure.
- Use layered surface contrast before increasing shadow depth.
- Standard card shadow:
  - `0 12px 32px rgba(0,0,0,0.18)`

## Responsive Rules

- On smaller screens, stack the main layout into one column.
- Sidebar becomes top content instead of a sticky side rail.
- Tabs remain horizontally scrollable.
- Author cards may move from multi-column to two-column, then to one-column layouts.
- Preserve readable text sizing on mobile. Do not reduce below `16px`.

## Accessibility Rules

- Minimum font size: `16px`
- Primary text should always use `--text` or stronger.
- Secondary text should usually use `--text-soft`, not `--muted`.
- Category colors must not be the only signal; pair them with labels and layout.
- Keep interactive targets padded enough to be easily tapped.

## Do

- Reuse existing CSS variables first.
- Reuse existing font families first.
- Keep cards compact and readable.
- Keep hierarchy obvious through spacing, weight, and contrast.
- Keep category colors consistent throughout the product.

## Avoid

- Do not add new colors casually.
- Do not use font sizes below `16px`.
- Do not introduce bright white boxes or light themes inside the dashboard.
- Do not create oversized hero sections or empty card space.
- Do not mix too many different visual patterns for cards or filters.

## Implementation Reference

If the UI evolves, update this file whenever any of these change:
- root color tokens
- font families
- font size scale
- spacing rhythm
- card patterns
- responsive rules
- accessibility constraints

Current source of truth:
- [`/Users/mana/Documents/Work/Design Research Collective/DesignResearchCollective/research-dashboard/dashboard/index.html`](/Users/mana/Documents/Work/Design Research Collective/DesignResearchCollective/research-dashboard/dashboard/index.html)
