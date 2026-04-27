from __future__ import annotations

import re
from typing import Any

# Category spellings are intentionally preserved for downstream compatibility.
CATEGORIES = ["ideation", "optimmization", "grammar", "decision_making"]
CATEGORY_TIE_ORDER = ["ideation", "optimmization", "grammar", "decision_making"]

# These thresholds keep the classifier deterministic while still allowing overlap.
RELATIVE_SCORE_THRESHOLD = 0.55
MIN_SECONDARY_SCORE = 2.2
STRONG_SCORE_THRESHOLD = 4.0

# Substrings (lowercase) in title + abstract + BERT topic labels.
CAT_PATTERNS: dict[str, list[str]] = {
    "ideation": [
        "ideation",
        "concept generation",
        "conceptual design",
        "creative",
        "creativity",
        "brainstorm",
        "design exploration",
        "exploratory",
        "novel framework",
        "proposing",
        "new concept",
        "design directions",
        "innovation",
        "idea generation",
        "user-centered design",
        "design thinking",
        "co-design",
        "early design",
        "generative design",
    ],
    "optimmization": [
        "optimization",
        "optimisation",
        "optimal",
        "minimize",
        "maximize",
        "efficiency",
        "performance improvement",
        "computational cost",
        "resource use",
        "best solution",
        "topology optimization",
        "multiobjective",
        "surrogate model",
        "evolutionary algorithm",
        "machine learning for",
        "deep learning",
        "cfd",
        "finite element",
        "accuracy",
        "faster",
        "reduce cost",
    ],
    "grammar": [
        "shape grammar",
        "graph grammar",
        "design grammar",
        "rule-based generation",
        "formal grammar",
        "parametric rule",
        "syntax",
        "formal language",
        "generative rules",
        "rule-based",
        "representation system",
        "formal structure",
        "grammar",
    ],
    "decision_making": [
        "decision support",
        "decision-making",
        "tradeoff",
        "trade-off",
        "tradeoffs",
        "recommendation system",
        "evaluation framework",
        "choose between",
        "alternative selection",
        "multi-criteria",
        "ranking",
        "human-ai",
        "decision making",
        "preference",
        "game theory",
        "strategy",
    ],
}


def strip_topic_id(label: str) -> str:
    return re.sub(r"^\d+\s*:\s*", "", (label or "").strip()).strip()


def _empty_evidence() -> dict[str, dict[str, float]]:
    return {
        cat: {
            "score": 0.0,
            "blob_hits": 0.0,
            "title_hits": 0.0,
            "abstract_hits": 0.0,
            "topic_hits": 0.0,
        }
        for cat in CATEGORIES
    }


def score_categories(
    topic_results: list[dict[str, Any]],
    title: str,
    abstract: str,
) -> dict[str, dict[str, float]]:
    title_l = (title or "").lower()
    abstract_l = (abstract or "").lower()
    topic_labels = [strip_topic_id(item.get("label", "")).lower() for item in topic_results]
    raw_topic_labels = [(item.get("label") or "").lower() for item in topic_results]
    blob = " ".join(topic_labels + raw_topic_labels + [title_l, abstract_l])

    evidence = _empty_evidence()

    for cat, patterns in CAT_PATTERNS.items():
        for pattern in patterns:
            weight = float(len(pattern)) ** 0.5
            if pattern in blob:
                evidence[cat]["score"] += weight
                evidence[cat]["blob_hits"] += 1
            if pattern in title_l:
                evidence[cat]["score"] += 1.8
                evidence[cat]["title_hits"] += 1
            if pattern in abstract_l:
                evidence[cat]["score"] += 1.0
                evidence[cat]["abstract_hits"] += 1

    for i, item in enumerate(topic_results[:5]):
        topic_weight = float(item.get("score", 0)) * (1.2 - i * 0.08)
        label = strip_topic_id(item.get("label", "")).lower()
        for cat, patterns in CAT_PATTERNS.items():
            for pattern in patterns:
                if pattern in label:
                    evidence[cat]["score"] += 2.0 * topic_weight
                    evidence[cat]["topic_hits"] += 1

    return evidence


def _primary_from_scores(scores: dict[str, float]) -> str:
    best = max(scores.values())
    for cat in CATEGORY_TIE_ORDER:
        if scores[cat] == best:
            return cat
    return "ideation"


def heuristic_fallback(blob: str) -> str | None:
    if any(
        x in blob
        for x in (
            "tradeoff",
            "trade-off",
            "recommendation",
            "decision support",
            "evaluation framework",
            "choose between",
            "alternatives",
            "ranking",
            "multi-criteria",
        )
    ):
        return "decision_making"
    if any(
        x in blob
        for x in (
            "shape grammar",
            "rule-based",
            "formal grammar",
            "syntax",
            "parametric rule",
            "representation system",
        )
    ):
        return "grammar"
    if any(
        x in blob
        for x in (
            "optimization",
            "optimisation",
            "efficiency",
            "optimal",
            "minimize",
            "maximize",
            "topology optimization",
            "surrogate",
            "performance",
        )
    ):
        return "optimmization"
    return None


def classify_categories(
    topic_results: list[dict[str, Any]],
    title: str,
    abstract: str,
) -> list[str]:
    """
    Return overlapping categories when evidence is meaningful.

    Rules:
    - always include the top-scoring category when any score is present
    - include additional categories when they are close to the top score
      and have direct pattern evidence
    - include categories with especially strong explicit evidence even if
      they are not close to the top score
    - use ideation only as the final fallback when some paper text exists
    - return ["Misc"] only when no evidence and effectively no useful text exist
    """

    evidence = score_categories(topic_results, title, abstract)
    scores = {cat: details["score"] for cat, details in evidence.items()}
    max_score = max(scores.values())

    if max_score > 0:
        primary = _primary_from_scores(scores)
        selected = [primary]
        for cat in CATEGORY_TIE_ORDER:
            if cat == primary:
                continue
            details = evidence[cat]
            direct_hits = details["title_hits"] + details["abstract_hits"] + details["topic_hits"]
            close_to_primary = scores[cat] >= max_score * RELATIVE_SCORE_THRESHOLD
            strong_explicit = (
                (details["title_hits"] > 0 or details["topic_hits"] > 0)
                and scores[cat] >= STRONG_SCORE_THRESHOLD
            )
            if (
                close_to_primary
                and scores[cat] >= MIN_SECONDARY_SCORE
                and direct_hits > 0
            ) or strong_explicit:
                selected.append(cat)
        return selected

    blob = " ".join(
        [strip_topic_id(item.get("label", "")).lower() for item in topic_results]
        + [(title or "").lower(), (abstract or "").lower()]
    ).strip()
    heuristic = heuristic_fallback(blob)
    if heuristic:
        return [heuristic]
    if (title or "").strip() or (abstract or "").strip():
        return ["ideation"]
    return ["Misc"]


def primary_category_from_multi(categories: list[str]) -> str:
    if not categories:
        return "Misc"
    if categories[0] in CATEGORIES:
        return categories[0]
    for cat in CATEGORY_TIE_ORDER:
        if cat in categories:
            return cat
    return categories[0]
