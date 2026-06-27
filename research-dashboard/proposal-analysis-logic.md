# Proposal Analysis — Logic Reference

The proposal analyzer takes free-text (a proposal draft, abstract, thesis direction, or project idea) and scores it against the DRC research corpus to produce seven analysis outputs. Everything is deterministic — no LLM is involved. All scoring is keyword overlap, token frequency, and category matching.

---

## Dual implementation

The logic runs in two places that mirror each other:

| Environment | File | When used |
|---|---|---|
| Browser (client-side) | `dashboard/index.html` (inline JS) | Interactive dashboard — runs instantly on the loaded CSV + JSON |
| Python (CLI / backend) | `scripts/analyze_proposal.py` | Command-line use, server-side cache pre-warming |

The Python version also writes results to `proposal_analysis_cache.json` keyed by SHA-256 hash of the proposal text. The browser version re-runs on every call (no persistent cache).

---

## Stage 1 — Proposal profile

The proposal text is transformed into a **profile** before any matching begins.

### Tokenization

The text is lowercased and split on non-alphanumeric characters. Stop words (common English words plus domain-generic terms like "research", "design", "build") are removed. Remaining tokens are counted by frequency.

### Salient tokens

The top 16 most-frequent non-stopword tokens become the **salient token list**. These are the signal the rest of the analysis uses for overlap scoring.

### Category scoring

The text is scored against four DRC research categories using two signals:

| Signal | Weight |
|---|---|
| Keyword presence in raw text (exact match) | 0.65 |
| Token overlap with category keyword set | 0.35 |

The combined score is clamped to [0, 1] and normalized by keyword set size. Categories scoring ≥ 0.16 are included. If nothing clears the threshold, the single highest-scoring category is used as a fallback.

| Category | Example keywords |
|---|---|
| `ideation` | ideation, brainstorm, concept, divergent, sketch, creativity |
| `optimization` | optimization, topology, surrogate, neural, parametric, simulation |
| `grammar` | grammar, rule, sequence, heuristic, constraint, hmm, markov |
| `decision_making` | decision, tradeoff, preference, uncertainty, trust, evaluation |

---

## Stage 2 — Analysis outputs

### 1. Research space summary

Reports which DRC category (or categories) the proposal occupies, and names the nearest prior paper as an anchor. This section sets context for everything that follows.

### 2. DRC Niche Momentum *(new)*

See [Stage 3 — DRC Niche Momentum](#stage-3--drc-niche-momentum) below.

### 3. Nearest prior papers

All corpus papers are scored against the proposal profile. The score is a weighted sum:

| Signal | Weight |
|---|---|
| Salient-token overlap with paper title | 0.25 (JS) / 0.25 (Py) |
| Salient-token overlap with abstract | 0.25 / 0.25 |
| Salient-token overlap with keywords | 0.18 / 0.18 |
| Salient-token overlap with BERT topics | 0.14 / 0.14 |
| Category overlap (shared DRC categories) | 0.12 / 0.12 |
| Recency (linear scale over 12-year window) | 0.06–0.08 |

Papers scoring above 0.08 are kept. The top 6 by score (tie-broken by year descending) are returned.

**Overlap score formula** — for a query token list Q and candidate token set C:

```
overlap_score = min(|{t ∈ Q : t ∈ C}|, 12) / min(|Q|, 12)
```

Capped at 12 to prevent very long abstracts from dominating.

### 4. What is distinct

The union of all tokens from the nearest 6 papers forms a "nearby token set." Tokens in the proposal's salient list that appear in the nearby set = **shared foundation**. Tokens that do not appear = **distinct terms**. The section reports both and explains what the proposal overlaps with and where it diverges.

### 5. DRC capabilities it builds on

Eight capability labels are scored against the proposal. Each rule has a `categories` set and a `keywords` set.

| Signal | Weight |
|---|---|
| Category overlap between rule and proposal categories | 0.45–0.55 |
| Keyword hits in proposal text / salient tokens | 0.35–0.45 |

Capabilities scoring above 0 are ranked and the top 5 returned.

| Capability label | Categories | Example keywords |
|---|---|---|
| Design ideation | ideation | ideation, concept, brainstorm, fixation |
| Optimization workflows | optimization | optimization, surrogate, topology, workflow |
| Design grammars | grammar | grammar, rule, sequence, heuristic |
| Human-AI collaboration | ideation + decision | human-ai, interactive, feedback, copilot |
| Decision support | decision | decision, uncertainty, tradeoff, selection |
| Simulation / evaluation | optimization + decision | simulation, benchmark, experiment, validation |
| Visualization | decision + ideation | visualization, interface, dashboard, explainability |
| Computational design methods | grammar + optimization | computational, generative, algorithmic, parametric |

### 6. Likely collaborators

All authors in `author_profiles.json` are scored. The score for each author is:

| Signal | Weight |
|---|---|
| Recent DRC relevance (recency + affiliation boost) | 0.25 |
| Category and topic match to proposal | 0.35 |
| Best representative paper score | 0.25 |
| Bridge-to-gap score (whitespace opportunity overlap) | 0.15 |

**Recent DRC relevance** combines publication recency (linear over 10-year window) and affiliation (DRC = 1.0, Both = 0.85–0.9, External = 0.65).

**Bridge-to-gap score** measures how much the author's whitespace opportunity titles and collaboration roles overlap with the proposal's salient tokens — specifically looking for authors who sit at the edge of a gap the proposal could fill.

Authors scoring ≥ 0.18 are included. Top 4–5 returned.

### 7. Missing evidence / biggest risks

Rule-based checklist. A risk flag fires if any of the following are true:

| Condition | Risk message |
|---|---|
| No category signal detected | Proposal doesn't anchor to a DRC category |
| Nearest paper score < 0.16–0.18 | Weak connection to existing corpus |
| No method/evaluation terms in text | No clear evaluation path described |
| No dataset/benchmark terms + proposal mentions AI | No data source identified |
| No strong collaborator fit (top score < 0.24–0.25) | Poor fit to current DRC author set |
| Salient tokens < 6 | Proposal too brief to score confidently |
| More than 3 categories simultaneously | Scope may be too broad |

Method terms: `dataset`, `benchmark`, `evaluation`, `experiment`, `study`, `simulation`, `user study`, `protocol`, `metric`.

Dataset terms: `dataset`, `corpus`, `benchmark`, `archive`, `log data`, `telemetry`, `repository`, `sensor`.

---

## Stage 3 — DRC Niche Momentum

This stage answers: **is DRC actively publishing in this specific niche, and in which direction?**

It operates only on DRC papers (`hf_dataset = ccm/publications`), not the full corpus.

### Algorithm

1. Score every DRC paper against the proposal profile using the same overlap formula as nearest prior papers (threshold: match score > 0.04 — lower than the corpus threshold to capture the niche broadly).
2. Split matched papers into **recent** (last 2 calendar years from the most recent DRC publication) and **historical** (everything before).
3. Compute annualized rates: `recent_per_year = recent_count / 2`, `historical_per_year = historical_count / historical_years`.
4. Derive **trend direction**:

| Condition | Trend |
|---|---|
| No historical papers, some recent | Emerging |
| `recent_per_year / historical_per_year ≥ 2.0` | Accelerating |
| `ratio ≥ 1.2` | Growing |
| `ratio ≤ 0.5` | Declining |
| Otherwise | Steady |
| No DRC papers in niche at all | Gap |

5. **Rising topics**: for each topic appearing in recent DRC niche papers, compute `(recent_count / 2) - (historical_count / historical_years)`. Positive delta = rising. Top 4 returned.

6. Return the 3 most recent DRC niche papers (by year, then match score) as examples.

### Output fields

| Field | Description |
|---|---|
| `gap` | `true` if no DRC papers found in this niche |
| `total_niche_papers` | Total DRC papers scoring above threshold |
| `recent_count` | DRC papers in last 2 years |
| `historical_count` | DRC papers before the 2-year window |
| `recent_cutoff_year` | First year of the recent window |
| `max_year` | Most recent year in DRC corpus |
| `trend_direction` | One of: accelerating / growing / steady / declining / emerging / gap |
| `rising_topics` | Up to 4 topic strings with positive per-year delta |
| `recent_papers` | Up to 3 recent DRC papers with title, year, authors, match score |

### Threshold rationale

The 0.04 threshold (vs 0.08 for nearest papers) is intentionally permissive. The goal is to detect whether DRC is working *anywhere near* this space — not just papers with high overlap. A gap finding at 0.04 is a stronger signal than a gap finding at a higher threshold.

---

## Caching (Python backend only)

`proposal_analysis_cache.json` stores results keyed by `SHA-256(proposal_text.strip())`. On a cache hit the full analysis dict is returned without re-running. The cache is invalidated (reset to `[]`) whenever:
- A new paper is uploaded via `upload_server.py`
- The daily GitHub Action syncs new papers via `sync_new_papers.py`

The browser implementation does not cache — it re-runs scoring on every click, which is fast enough given the corpus size.

---

## Data sources

| Artifact | Contents | Used by |
|---|---|---|
| `data/papers.csv` | All corpus papers (DRC + CMU Engineering) with BERT topics, categories | Browser (loaded via PapaParse) |
| `data/papers_enriched.json` | Same papers in structured JSON with `year_num`, `tokens`, enriched fields | Python backend |
| `data/author_profiles.json` | Per-author aggregates: categories, recurring topics, whitespace opportunities, collaboration roles | Both |
| `data/whitespace_opportunities.json` | 12 scored whitespace items with priority factors | Both |
| `data/proposal_analysis_cache.json` | SHA-256 → analysis result cache | Python backend only |
