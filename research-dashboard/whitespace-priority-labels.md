# Whitespace Priority Labels

This note explains how whitespace priority labels are now generated for the **White Spaces** tab.

Source of truth:
- `research-dashboard/scripts/whitespace_catalog.py`
- `research-dashboard/scripts/author_profiles.py`
- Generated output: `research-dashboard/data/whitespace_matches.json`

## What the labels mean

Each whitespace opportunity now receives:

- `priority_label`: `High`, `Medium`, or `Low`
- `overall_priority_score`: a deterministic `0.00–1.00` score
- `priority_factors`: five factor scores on the same `0.00–1.00` scale
- `priority_reason`: a short explanation string

For backward compatibility, each item also keeps:

- `priority`: same value as `priority_label`
- `score`: ranked shorthand such as `H1`, `M2`, `L3`

Examples:

- `High` means `overall_priority_score >= 0.70`
- `Medium` means `0.45 <= overall_priority_score < 0.70`
- `Low` means `overall_priority_score < 0.45`

The compact shorthand still works like this:

- `H1` = top-ranked `High` opportunity
- `M1` = top-ranked `Medium` opportunity
- `L1` = top-ranked `Low` opportunity

## Priority formula

The overall priority score is a weighted average of five explainable factors:

```text
priority =
  current_trends_score      * 0.25 +
  drc_interest_score        * 0.25 +
  impact_score              * 0.20 +
  evidence_strength_score   * 0.15 +
  feasibility_readiness_score * 0.15
```

Current weights:

- `current_trends_score`: `0.25`
- `drc_interest_score`: `0.25`
- `impact_score`: `0.20`
- `evidence_strength_score`: `0.15`
- `feasibility_readiness_score`: `0.15`

Thresholds are intentionally centralized in `author_profiles.py` so they are easy to tune.

## What each factor measures

### 1. Current trends

This estimates whether the whitespace is active or rising in the broader paper corpus.

Signals used:

- how many supporting papers match the whitespace
- how many of those supporting papers are recent
- how often the whitespace keywords appear in recent papers relative to all matching mentions

Interpretation:

- higher score = more recent and repeated evidence that the topic is active now

### 2. DRC interest

This estimates how closely the whitespace aligns with DRC strengths and ongoing themes.

Signals used:

- presence of the whitespace categories in the DRC paper corpus
- strength of author matches from the author-profile pipeline
- overlap between whitespace focus signals and recurring DRC author/topic tokens
- density of supporting papers inside the DRC-related corpus

Interpretation:

- higher score = stronger fit with what DRC already works on or can plausibly extend

### 3. Impact

This estimates how meaningful the whitespace could be if explored.

Signals used:

- impact-oriented keywords such as sustainability, evaluation, workflow, human-AI, uncertainty, or real-world application
- breadth across multiple categories
- bonus for cross-category or domain-gap opportunities when they indicate broader strategic value

Interpretation:

- higher score = the gap appears more consequential for design research or practice

### 4. Evidence strength

This estimates how clearly the corpus supports the existence of the gap.

Signals used:

- number of supporting papers
- number of matched authors
- convergence across related categories
- repeated overlap in topic/keyword signals across supporting papers

Interpretation:

- higher score = the whitespace is supported by repeated evidence, not just one weak signal

### 5. Feasibility / readiness

This estimates whether there is a plausible near-term path to work on the whitespace.

Signals used:

- strength of matched authors
- number of supporting papers
- feasibility signals such as methods, datasets, simulation, project paths, or student-scope work

Interpretation:

- higher score = the topic looks more actionable with current DRC people, methods, and data

## Where the inputs come from

### Static whitespace definitions

`whitespace_catalog.py` defines each whitespace opportunity with:

- title
- description
- opportunity text
- related categories
- keywords
- card display metadata
- impact signals
- DRC focus signals
- feasibility signals

These are curated inputs, but the **priority labels themselves are no longer manually assigned**.

### Dynamic evidence from the corpus

`author_profiles.py` computes scores using:

- paper titles
- abstracts
- category labels
- keywords
- parsed topic labels
- matched authors from the author-to-whitespace alignment pipeline

## Output fields

Each generated whitespace item now includes fields like:

```json
{
  "priority_label": "High",
  "priority": "High",
  "score": "H1",
  "overall_priority_score": 0.712,
  "priority_factors": {
    "current_trends_score": 0.764,
    "drc_interest_score": 0.659,
    "impact_score": 0.787,
    "evidence_strength_score": 0.515,
    "feasibility_readiness_score": 0.808
  },
  "priority_reason": "High priority because feasibility readiness and impact are strong, while evidence strength remains the main limiting factor."
}
```

## How ranking within a tier works

After all overall scores are computed:

1. whitespace opportunities are sorted by descending `overall_priority_score`
2. each item is mapped to `High`, `Medium`, or `Low`
3. each item gets a within-tier rank:
   - `H1`, `H2`, ...
   - `M1`, `M2`, ...
   - `L1`, `L2`, ...

That means the dashboard keeps a compact priority shorthand while still using evidence-based labels underneath.

## What is now deterministic

The new system is:

- deterministic
- explainable
- threshold-based
- weight-based
- tunable from one place

It does **not** use random scoring or opaque model inference for the final priority label.
