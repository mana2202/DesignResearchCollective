# Research Paper Categorization

This project classifies papers into one or more overlapping categories:

- `ideation`
  Papers about generating ideas, exploring design spaces, proposing new frameworks, brainstorming, creativity, concept generation, or opening new design possibilities.

- `optimmization`
  Papers about improving outcomes, performance, efficiency, accuracy, or resource use. This includes topology optimization, surrogate models, deep learning used to improve results, and methods for finding better solutions.

- `grammar`
  Papers about rule-based or formal structure in design. This includes shape grammars, graph grammars, design grammars, syntax, formal languages, parametric rules, and rule-driven generation.

- `decision_making`
  Papers about choosing between alternatives, evaluating tradeoffs, ranking options, recommendation systems, preference modeling, strategy, and decision support.

## How the classifier decides

The multi-label classifier lives in [`scripts/category_classifier.py`](/Users/mana/Documents/Work/Design Research Collective/DesignResearchCollective/research-dashboard/scripts/category_classifier.py).

It uses three sources of evidence:

- title text
- abstract text
- top OpenAlex BERT topic labels

For each category, it scores keyword and phrase matches from those sources.

## Multi-label rules

A paper can receive more than one category.

- The highest-scoring category is always included when any score is present.
- Additional categories are included when they are close enough to the top score and have direct pattern evidence.
- Categories with especially strong explicit evidence from the title or top topic labels can also be included, even if they are not very close to the top score.
- `ideation` is used as a fallback only when no stronger category is detected but the paper still has usable text.
- `Misc` is returned only when there is effectively no category evidence at all.

## CSV output

The pipeline writes:

- `primary_category`
  The single primary category, used for backward compatibility.

- `categories`
  A pipe-separated multi-label field, for example:
  `ideation|grammar`
  `optimmization|decision_making`
  `ideation|optimmization|decision_making`

The dashboard reads the multi-label `categories` field first and falls back to `primary_category` when needed.
