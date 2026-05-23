from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from whitespace_catalog import WHITESPACE_OPPORTUNITIES

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "using", "into", "between",
    "through", "based", "study", "paper", "design", "engineering", "system", "systems",
    "analysis", "approach", "framework", "model", "models", "data", "new", "via", "toward",
    "towards", "their", "have", "been", "into", "can", "use", "used", "over", "under",
    "during", "across", "effects", "effect", "understanding", "understand", "role",
}

CATEGORY_LABELS = {
    "ideation": "ideation",
    "optimmization": "optimization",
    "grammar": "grammar",
    "decision_making": "decision making",
}

PRIORITY_WEIGHTS = {
    "current_trends_score": 0.25,
    "drc_interest_score": 0.25,
    "impact_score": 0.20,
    "evidence_strength_score": 0.15,
    "feasibility_readiness_score": 0.15,
}

PRIORITY_THRESHOLDS = {
    "high": 0.70,
    "medium": 0.45,
}

AUTHOR_MATCH_WEIGHTS = {
    "recent_drc_relevance_score": 0.25,
    "category_topic_match_score": 0.35,
    "representative_paper_score": 0.25,
    "bridge_to_gap_score": 0.15,
}

AUTHOR_MATCH_THRESHOLD = 0.42

CORE_DRC_SIGNAL_TOKENS = {
    "design", "grammar", "process", "ideation", "optimization", "decision", "human-ai",
    "trust", "uav", "drone", "manufacturing", "topology", "neural", "operator", "llm",
    "collaboration", "uncertainty", "sustainability", "inclusive", "bias", "empathy",
    "multi-agent", "workflow", "simulation",
}

COLLABORATION_ROLE_RULES = {
    "Theory / Framework Building": {"framework", "theory", "grammar", "conceptual", "strategy", "rule-based"},
    "Methods & Tooling": {"tool", "pipeline", "method", "workflow", "platform", "library", "benchmark"},
    "Evaluation & Validation": {"evaluation", "validation", "benchmark", "assessment", "metrics", "testing"},
    "Human Studies": {"trust", "team", "collaboration", "empathy", "bias", "participation", "human"},
    "Systems / Infrastructure": {"system", "infrastructure", "platform", "network", "process", "deployment"},
    "AI & ML": {"ai", "ml", "llm", "neural", "learning", "agentic", "multi-agent"},
    "Visualization": {"visual", "visualization", "mapping", "dashboard", "graph", "explorer"},
    "Simulation": {"simulation", "surrogate", "modeling", "operator", "digital", "scenario"},
    "Decision Support": {"decision", "tradeoff", "uncertainty", "recommend", "support", "optimization"},
    "Sustainability": {"sustainability", "carbon", "renewable", "recyclability", "climate", "lifecycle"},
    "Cross-disciplinary Bridge": {"cross-domain", "interdisciplinary", "bridge", "hybrid", "human-ai"},
}

METHOD_ACCESS_RULES = {
    "Has datasets": {"dataset", "benchmark", "repository", "corpus", "data"},
    "Simulation-heavy": {"simulation", "surrogate", "operator", "modeling", "topology"},
    "AI/ML methods": {"ai", "ml", "llm", "neural", "learning", "agentic"},
    "Experimental methods": {"experiment", "prototype", "lab", "fabrication", "testing"},
    "Design studies": {"design study", "concept generation", "ideation", "workflow", "design teams"},
    "Field studies": {"field", "longitudinal", "deployment", "stakeholder", "real-world"},
    "Review/meta-analysis": {"review", "survey", "meta", "analysis", "bibliometric"},
}


def split_categories(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split("|") if part.strip()]


def normalize_category_token(raw: str) -> str:
    token = str(raw or "").strip().lower().replace(" ", "_")
    if token == "optimization":
        return "optimmization"
    return token


def tokenize_text(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z][a-z0-9\-]{2,}", (text or "").lower())
        if token not in STOPWORDS
    ]


def parse_topic_labels(raw: str) -> list[str]:
    labels: list[str] = []
    for chunk in str(raw or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        label = re.sub(r"^\d+\s*:\s*", "", chunk)
        label = re.sub(r"\s*\([^)]*\)\s*$", "", label).strip()
        if label:
            labels.append(label)
    return labels


def parse_keyword_labels(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split("|") if part.strip()]


def normalize_year_label(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text


def normalize_author_name(name: str) -> str:
    name = re.sub(r"\s+", " ", str(name or "").strip())
    return name.strip(" ,;")


def split_authors(raw: str) -> list[str]:
    text = normalize_author_name(raw)
    if not text:
        return []
    if " and " in text:
        parts = re.split(r"\s+and\s+", text)
    elif ";" in text:
        parts = text.split(";")
    elif text.count(",") >= 2:
        parts = text.split(",")
    else:
        parts = [text]
    return [normalize_author_name(part) for part in parts if normalize_author_name(part)]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def collect_text_tokens(*parts: str) -> set[str]:
    return set(tokenize_text(" ".join(part for part in parts if part)))


def year_weight(year_num: int, recent_year_cutoff: int) -> float:
    if not year_num:
        return 0.15
    if year_num >= recent_year_cutoff:
        return 1.0
    if year_num >= recent_year_cutoff - 3:
        return 0.75
    if year_num >= recent_year_cutoff - 8:
        return 0.45
    return 0.2


def extract_author_topics(papers: list[dict[str, Any]]) -> list[str]:
    topic_counter: Counter[str] = Counter()
    token_counter: Counter[str] = Counter()

    for paper in papers:
        for keyword in paper["topics"]:
            topic_counter[keyword] += 2
            for token in tokenize_text(keyword):
                token_counter[token] += 1
        for category in paper["categories"]:
            token_counter[CATEGORY_LABELS.get(category, category)] += 2
        for token in tokenize_text(paper["title"]):
            token_counter[token] += 1
        for token in tokenize_text(paper.get("abstract", "")):
            token_counter[token] += 0.3

    recurring_topics = [topic for topic, _ in topic_counter.most_common(8)]
    if len(recurring_topics) < 8:
        for token, _ in token_counter.most_common(16):
            if token not in recurring_topics:
                recurring_topics.append(token)
            if len(recurring_topics) >= 8:
                break
    return recurring_topics[:8]


def infer_author_interests(
    dominant_categories: list[str],
    recurring_topics: list[str],
) -> list[str]:
    interests: list[str] = []
    for topic in recurring_topics:
        readable = topic.replace("_", " ")
        if readable not in interests:
            interests.append(readable)
        if len(interests) >= 6:
            break

    for category in dominant_categories:
        readable = CATEGORY_LABELS.get(category, category).replace("_", " ")
        phrase = f"{readable} research"
        if phrase not in interests:
            interests.append(phrase)
        if len(interests) >= 6:
            break
    return interests[:6]


def build_author_summary(
    dominant_categories: list[str],
    recurring_topics: list[str],
    paper_count: int,
) -> str:
    cat_labels = [CATEGORY_LABELS.get(cat, cat).replace("_", " ") for cat in dominant_categories[:2]]
    topic_labels = [topic.replace("_", " ") for topic in recurring_topics[:2]]
    summary_bits: list[str] = []
    if cat_labels:
        if len(cat_labels) == 1:
            summary_bits.append(cat_labels[0])
        else:
            summary_bits.append(f"{cat_labels[0]} and {cat_labels[1]}")
    if topic_labels:
        summary_bits.append("recurring work in " + " and ".join(topic_labels))
    if summary_bits:
        summary = "Publishes across " + " with ".join(summary_bits)
    else:
        summary = "Researcher with a broad publication profile"
    if paper_count == 1:
        summary += " across 1 paper."
    else:
        summary += f" across {paper_count} papers."
    return summary


def record_to_paper(row: dict[str, Any]) -> dict[str, Any]:
    paper_categories = split_categories(row.get("categories")) or split_categories(row.get("primary_category"))
    paper_categories = [normalize_category_token(cat) for cat in paper_categories if normalize_category_token(cat)]
    paper_topics = parse_keyword_labels(row.get("keywords")) + parse_topic_labels(row.get("bert_topics"))
    year_text = normalize_year_label(row.get("year"))
    year_num = int(year_text) if year_text.isdigit() else 0
    text_blob = " ".join(
        [
            str(row.get("title", "")).strip(),
            str(row.get("abstract", "")).strip(),
            " ".join(paper_topics),
            str(row.get("keywords", "")).strip().replace("|", " "),
            " ".join(CATEGORY_LABELS.get(category, category) for category in paper_categories),
        ]
    )
    return {
        "title": str(row.get("title", "")).strip(),
        "year": year_text,
        "year_num": year_num,
        "categories": paper_categories,
        "topics": list(dict.fromkeys(topic for topic in paper_topics if topic))[:8],
        "abstract": str(row.get("abstract", "")).strip(),
        "journal": str(row.get("journal", "")).strip(),
        "hf_dataset": str(row.get("hf_dataset", "")).strip(),
        "data_source": str(row.get("data_source", "")).strip(),
        "tokens": tokenize_text(text_blob),
    }


def derive_affiliation_bucket(papers: list[dict[str, Any]]) -> str:
    sources = {paper.get("hf_dataset", "") for paper in papers}
    has_drc = "ccm/publications" in sources
    has_engineering = "ccm/cmu-engineering-publications" in sources
    if has_drc and has_engineering:
        return "Both"
    if has_drc:
        return "DRC Researchers"
    if has_engineering:
        return "External Engineering Researchers"
    return "Both"


def derive_whitespace_relevance_bucket(related_whitespace_opportunities: list[dict[str, Any]]) -> str:
    top_score = max((item.get("author_whitespace_match_score", item.get("match_score", 0)) for item in related_whitespace_opportunities), default=0)
    if top_score >= 0.75:
        return "Strong whitespace match"
    if top_score >= 0.58:
        return "Medium whitespace match"
    if top_score >= 0.42:
        return "Emerging relevance"
    return "No whitespace connection"


def derive_activity_tags(last_published: str, paper_count: int, papers: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    year_num = int(last_published) if str(last_published).isdigit() else 0
    max_year = max((paper["year_num"] for paper in papers), default=0)
    if year_num and max_year - year_num <= 1:
        tags.append("Active in last 1 year")
    if year_num and max_year - year_num <= 3:
        tags.append("Active in last 3 years")
    if paper_count >= 8 or len({paper["year_num"] for paper in papers if paper["year_num"]}) >= 6:
        tags.append("Established researcher")
    if paper_count <= 5 and year_num and max_year - year_num <= 3:
        tags.append("Emerging researcher")
    return tags or ["Established researcher"]


def derive_breadth_tags(dominant_categories: list[str], papers: list[dict[str, Any]]) -> list[str]:
    all_categories = {category for paper in papers for category in paper["categories"]}
    tags: list[str] = []
    if len(all_categories) <= 1:
        tags.append("Specialist")
    if len(all_categories) >= 2:
        tags.append("Interdisciplinary")
    if len(all_categories) >= 3 or len(dominant_categories) >= 3:
        tags.append("Cross-category bridge researcher")
    return tags or ["Specialist"]


def derive_rule_tags(source_tokens: set[str], rules: dict[str, set[str]]) -> list[str]:
    return [label for label, rule_tokens in rules.items() if source_tokens & rule_tokens]


def build_corpus_stats(papers: list[dict[str, Any]], profiles: list[dict[str, Any]]) -> dict[str, Any]:
    topic_counter: Counter[str] = Counter()
    token_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    recent_token_counter: Counter[str] = Counter()
    recent_year_cutoff = max((paper["year_num"] for paper in papers), default=0) - 4
    recent_paper_count = 0

    for paper in papers:
        category_counter.update(paper["categories"])
        for topic in paper["topics"]:
            topic_counter[topic] += 1
        token_counter.update(paper["tokens"])
        if paper["year_num"] and paper["year_num"] >= recent_year_cutoff:
            recent_paper_count += 1
            recent_token_counter.update(paper["tokens"])

    author_interest_tokens: Counter[str] = Counter()
    for profile in profiles:
        author_interest_tokens.update(tokenize_text(" ".join(profile["recurring_topics"] + profile["inferred_interests"])))

    return {
        "paper_count": len(papers),
        "recent_paper_count": recent_paper_count,
        "recent_year_cutoff": recent_year_cutoff,
        "topic_counter": topic_counter,
        "token_counter": token_counter,
        "category_counter": category_counter,
        "recent_token_counter": recent_token_counter,
        "author_interest_tokens": author_interest_tokens,
    }


def build_whitespace_tokens(whitespace: dict[str, Any]) -> set[str]:
    return set(
        tokenize_text(
            " ".join(
                whitespace["keywords"]
                + whitespace["impact_signals"]
                + whitespace["drc_focus_signals"]
                + whitespace["feasibility_signals"]
                + [whitespace["title"], whitespace["description"], whitespace["opportunity"]]
            )
        )
    )


def whitespace_supporting_papers(
    whitespace: dict[str, Any],
    papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    keyword_tokens = build_whitespace_tokens(whitespace)
    related_categories = set(whitespace["related_categories"])
    supporting: list[dict[str, Any]] = []

    for paper in papers:
        token_overlap = keyword_tokens & set(paper["tokens"])
        category_overlap = related_categories & set(paper["categories"])
        support_strength = len(token_overlap) * 0.18 + len(category_overlap) * 0.32
        if support_strength >= 0.36:
            supporting.append(
                {
                    "title": paper["title"],
                    "year_num": paper["year_num"],
                    "year": paper["year"],
                    "categories": paper["categories"],
                    "topics": paper["topics"],
                    "token_overlap": sorted(token_overlap),
                    "category_overlap": sorted(category_overlap),
                    "support_strength": support_strength,
                }
            )

    return supporting


def author_representative_papers(
    whitespace: dict[str, Any],
    profile: dict[str, Any],
    recent_year_cutoff: int,
) -> list[dict[str, Any]]:
    whitespace_tokens = build_whitespace_tokens(whitespace)
    related_categories = set(whitespace["related_categories"])
    representatives: list[dict[str, Any]] = []

    for paper in profile.get("_papers_full", []):
        topic_tokens = set(tokenize_text(" ".join(paper["topics"])))
        paper_tokens = set(paper["tokens"])
        category_overlap = related_categories & set(paper["categories"])
        topic_overlap = whitespace_tokens & (paper_tokens | topic_tokens)
        recency = year_weight(paper["year_num"], recent_year_cutoff)

        # Representative papers favor direct overlap plus recency, without rewarding sheer volume.
        direct_match_score = (
            len(category_overlap) * 0.34
            + min(len(topic_overlap), 6) * 0.08
            + recency * 0.18
        )
        if direct_match_score < 0.42:
            continue

        reasons: list[str] = []
        if category_overlap:
            reasons.append("category overlap in " + ", ".join(CATEGORY_LABELS.get(cat, cat) for cat in sorted(category_overlap)))
        if topic_overlap:
            reasons.append("topic overlap in " + ", ".join(sorted(topic_overlap)[:4]))
        if recency >= 0.75:
            reasons.append(f"recent contribution in {paper['year'] or 'recent work'}")

        representatives.append(
            {
                "title": paper["title"],
                "year": paper["year"],
                "reason": "; ".join(reasons) if reasons else "Directly supports this whitespace opportunity.",
                "_score": round(direct_match_score, 3),
                "_category_overlap": len(category_overlap),
                "_topic_overlap": len(topic_overlap),
            }
        )

    representatives.sort(
        key=lambda item: (-item["_score"], -(item["_category_overlap"] + item["_topic_overlap"]), item["title"].lower())
    )
    return representatives[:3]


def compute_recent_drc_relevance_score(
    profile: dict[str, Any],
    whitespace: dict[str, Any],
    recent_year_cutoff: int,
) -> float:
    whitespace_tokens = build_whitespace_tokens(whitespace)
    related_categories = set(whitespace["related_categories"])
    weighted_scores: list[float] = []

    for paper in profile.get("_papers_full", []):
        token_overlap = whitespace_tokens & set(paper["tokens"])
        category_overlap = related_categories & set(paper["categories"])
        if not token_overlap and not category_overlap:
            continue
        recency = year_weight(paper["year_num"], recent_year_cutoff)
        overlap_score = clamp01(len(token_overlap) / 6 + len(category_overlap) / 3)
        weighted_scores.append(clamp01(0.55 * recency + 0.45 * overlap_score))

    if not weighted_scores:
        return 0.0
    return round(clamp01(sum(weighted_scores[:5]) / min(len(weighted_scores), 5)), 3)


def compute_category_topic_match_score(
    profile: dict[str, Any],
    whitespace: dict[str, Any],
) -> float:
    related_categories = set(whitespace["related_categories"])
    whitespace_tokens = build_whitespace_tokens(whitespace)
    dominant_categories = set(profile.get("dominant_categories", []))
    recurring_topics = set(tokenize_text(" ".join(profile.get("recurring_topics", []) + profile.get("inferred_interests", []))))
    category_overlap_score = clamp01(len(related_categories & dominant_categories) / max(len(related_categories), 1))
    topic_overlap_score = clamp01(len(whitespace_tokens & recurring_topics) / 6)
    return round(clamp01(0.6 * category_overlap_score + 0.4 * topic_overlap_score), 3)


def compute_representative_paper_score(representative_papers: list[dict[str, Any]]) -> float:
    if not representative_papers:
        return 0.0
    base = average([paper["_score"] for paper in representative_papers[:3]])
    count_bonus = 0.08 if len(representative_papers) >= 2 else 0.0
    return round(clamp01(base + count_bonus), 3)


def compute_bridge_to_gap_score(
    profile: dict[str, Any],
    whitespace: dict[str, Any],
    representative_papers: list[dict[str, Any]],
) -> tuple[float, str]:
    whitespace_tokens = build_whitespace_tokens(whitespace)
    recurring_topics = set(tokenize_text(" ".join(profile.get("recurring_topics", []))))
    inferred_interests = set(tokenize_text(" ".join(profile.get("inferred_interests", []))))
    related_categories = set(whitespace["related_categories"])
    dominant_categories = set(profile.get("dominant_categories", []))

    direct_overlap = whitespace_tokens & recurring_topics
    adjacent_overlap = whitespace_tokens & inferred_interests
    category_bridge = related_categories & dominant_categories

    score = clamp01(
        0.45 * clamp01(len(direct_overlap) / 4)
        + 0.30 * clamp01(len(adjacent_overlap) / 4)
        + 0.25 * clamp01(len(category_bridge) / max(len(related_categories), 1))
    )

    if representative_papers:
        reason = (
            f"This author bridges {', '.join(sorted(category_bridge)[:2]).replace('_', ' ') or 'adjacent DRC themes'} "
            f"with whitespace-relevant topics such as {', '.join(sorted((direct_overlap or adjacent_overlap))[:3]) or 'the target gap'}, "
            "making them a plausible contributor to this opportunity."
        )
    else:
        reason = "This author has only limited adjacent overlap with the whitespace opportunity."
    return round(score, 3), reason


def compute_author_whitespace_match(
    profile: dict[str, Any],
    whitespace: dict[str, Any],
    recent_year_cutoff: int,
) -> dict[str, Any] | None:
    representative_papers = author_representative_papers(whitespace, profile, recent_year_cutoff)
    match_factors = {
        "recent_drc_relevance_score": compute_recent_drc_relevance_score(profile, whitespace, recent_year_cutoff),
        "category_topic_match_score": compute_category_topic_match_score(profile, whitespace),
        "representative_paper_score": compute_representative_paper_score(representative_papers),
    }
    bridge_score, bridge_reason = compute_bridge_to_gap_score(profile, whitespace, representative_papers)
    match_factors["bridge_to_gap_score"] = bridge_score

    # Deterministic author-to-whitespace scoring that stays independent from whitespace priority.
    author_whitespace_match_score = round(
        sum(match_factors[key] * AUTHOR_MATCH_WEIGHTS[key] for key in AUTHOR_MATCH_WEIGHTS),
        3,
    )
    if author_whitespace_match_score < AUTHOR_MATCH_THRESHOLD:
        return None

    concise_reason_parts: list[str] = []
    if match_factors["category_topic_match_score"] >= 0.6:
        concise_reason_parts.append("strong category/topic overlap")
    if match_factors["recent_drc_relevance_score"] >= 0.6:
        concise_reason_parts.append("recent DRC-relevant work")
    if representative_papers:
        concise_reason_parts.append(f"{len(representative_papers)} representative paper{'s' if len(representative_papers) != 1 else ''}")
    concise_reason = ", ".join(concise_reason_parts) if concise_reason_parts else "adjacent expertise aligned to this gap"

    return {
        "author_name": profile["author_name"],
        "author_whitespace_match_score": author_whitespace_match_score,
        "match_score": author_whitespace_match_score,
        "match_factors": match_factors,
        "representative_papers": [
            {
                "title": paper["title"],
                "year": paper["year"],
                "reason": paper["reason"],
            }
            for paper in representative_papers
        ],
        "bridge_reason": bridge_reason,
        "reason": concise_reason,
    }


def compute_current_trends_score(
    whitespace: dict[str, Any],
    supporting_papers: list[dict[str, Any]],
    corpus_stats: dict[str, Any],
) -> float:
    keyword_tokens = set(tokenize_text(" ".join(whitespace["keywords"])))
    if not keyword_tokens:
        return 0.0
    recent_cutoff = corpus_stats["recent_year_cutoff"]
    recent_support = [paper for paper in supporting_papers if paper["year_num"] and paper["year_num"] >= recent_cutoff]
    recent_ratio = len(recent_support) / max(len(supporting_papers), 1)
    coverage_ratio = clamp01(len(supporting_papers) / 14)
    recent_mentions = sum(corpus_stats["recent_token_counter"].get(token, 0) for token in keyword_tokens)
    total_mentions = sum(corpus_stats["token_counter"].get(token, 0) for token in keyword_tokens)
    recency_signal = recent_mentions / max(total_mentions, 1)
    return round(clamp01(0.45 * recent_ratio + 0.30 * coverage_ratio + 0.25 * recency_signal), 3)


def compute_drc_interest_score(
    whitespace: dict[str, Any],
    supporting_papers: list[dict[str, Any]],
    matched_authors: list[dict[str, Any]],
    corpus_stats: dict[str, Any],
) -> float:
    related_categories = whitespace["related_categories"]
    category_presence = average(
        [
            clamp01(corpus_stats["category_counter"].get(category, 0) / max(corpus_stats["paper_count"] * 0.18, 1))
            for category in related_categories
        ]
    )
    author_alignment = average([item["match_score"] for item in matched_authors[:5]])
    focus_tokens = set(tokenize_text(" ".join(whitespace["drc_focus_signals"] + whitespace["keywords"])))
    drc_signal_overlap = sum(corpus_stats["author_interest_tokens"].get(token, 0) for token in focus_tokens if token in CORE_DRC_SIGNAL_TOKENS)
    drc_signal_score = clamp01(drc_signal_overlap / 24)
    support_density = clamp01(len(supporting_papers) / 10)
    return round(clamp01(0.35 * category_presence + 0.30 * author_alignment + 0.20 * drc_signal_score + 0.15 * support_density), 3)


def compute_impact_score(whitespace: dict[str, Any]) -> float:
    impact_tokens = set(tokenize_text(" ".join(whitespace["impact_signals"] + whitespace["keywords"] + [whitespace["title"], whitespace["description"], whitespace["opportunity"]])))
    impact_keywords = {
        "sustainability", "climate", "human-ai", "decision", "evaluation", "workflow",
        "scalable", "methods", "uncertainty", "collaboration", "inclusive", "equity",
        "renewable", "trust", "optimization", "design", "teams", "project",
    }
    token_score = clamp01(len(impact_tokens & impact_keywords) / 6)
    breadth_score = clamp01(len(set(whitespace["related_categories"])) / 3)
    domain_bonus = 0.12 if whitespace["card_category"] in {"cc", "cx"} else 0.0
    return round(clamp01(0.55 * token_score + 0.30 * breadth_score + domain_bonus), 3)


def compute_evidence_strength_score(
    whitespace: dict[str, Any],
    supporting_papers: list[dict[str, Any]],
    matched_authors: list[dict[str, Any]],
) -> float:
    support_count_score = clamp01(len(supporting_papers) / 8)
    author_count_score = clamp01(len(matched_authors) / 8)
    category_convergence = clamp01(
        len(
            set(
                category
                for paper in supporting_papers
                for category in paper["category_overlap"]
            )
        ) / max(len(set(whitespace["related_categories"])), 1)
    )
    repeated_topic_signal = clamp01(
        len(
            set(
                token
                for paper in supporting_papers
                for token in paper["token_overlap"]
            )
        ) / 6
    )
    return round(clamp01(0.35 * support_count_score + 0.25 * author_count_score + 0.20 * category_convergence + 0.20 * repeated_topic_signal), 3)


def compute_feasibility_readiness_score(
    whitespace: dict[str, Any],
    matched_authors: list[dict[str, Any]],
    supporting_papers: list[dict[str, Any]],
) -> float:
    author_path_score = average([item["match_score"] for item in matched_authors[:5]])
    support_path_score = clamp01(len(supporting_papers) / 8)
    feasibility_tokens = set(tokenize_text(" ".join(whitespace["feasibility_signals"] + whitespace["keywords"] + [whitespace["opportunity"]])))
    method_tokens = {"dataset", "project", "study", "methods", "simulation", "authors", "student", "pipeline", "optimization", "bayesian"}
    method_signal = clamp01(len(feasibility_tokens & method_tokens) / 5)
    return round(clamp01(0.45 * author_path_score + 0.30 * support_path_score + 0.25 * method_signal), 3)


def compute_priority_label(overall_priority_score: float) -> str:
    if overall_priority_score >= PRIORITY_THRESHOLDS["high"]:
        return "High"
    if overall_priority_score >= PRIORITY_THRESHOLDS["medium"]:
        return "Medium"
    return "Low"


def build_priority_reason(
    priority_label: str,
    factors: dict[str, float],
) -> str:
    label_text = priority_label.lower()
    ordered = sorted(factors.items(), key=lambda item: item[1], reverse=True)
    strongest = [name.replace("_score", "").replace("_", " ") for name, _ in ordered[:2]]
    weakest = [name.replace("_score", "").replace("_", " ") for name, _ in ordered[-1:]]
    return (
        f"{priority_label} priority because {strongest[0]} and {strongest[1]} are strong, "
        f"while {weakest[0]} remains the main limiting factor."
        if len(strongest) > 1
        else f"{priority_label} priority because {strongest[0]} is the strongest signal."
    )


def build_scored_whitespace_entries(
    papers: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
    whitespace_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    corpus_stats = build_corpus_stats(papers, profiles)
    match_map = {item["title"]: item for item in whitespace_matches}
    scored_entries: list[dict[str, Any]] = []

    for whitespace in WHITESPACE_OPPORTUNITIES:
        matched_authors = match_map.get(whitespace["title"], {}).get("matched_authors", [])
        supporting_papers = whitespace_supporting_papers(whitespace, papers)
        factors = {
            "current_trends_score": compute_current_trends_score(whitespace, supporting_papers, corpus_stats),
            "drc_interest_score": compute_drc_interest_score(whitespace, supporting_papers, matched_authors, corpus_stats),
            "impact_score": compute_impact_score(whitespace),
            "evidence_strength_score": compute_evidence_strength_score(whitespace, supporting_papers, matched_authors),
            "feasibility_readiness_score": compute_feasibility_readiness_score(whitespace, matched_authors, supporting_papers),
        }
        # Weighted average keeps the priority label deterministic and easy to tune.
        overall_priority_score = round(
            sum(factors[key] * PRIORITY_WEIGHTS[key] for key in PRIORITY_WEIGHTS),
            3,
        )
        priority_label = compute_priority_label(overall_priority_score)
        scored_entries.append(
            {
                **whitespace,
                "priority": priority_label,
                "priority_label": priority_label,
                "overall_priority_score": overall_priority_score,
                "priority_factors": factors,
                "priority_reason": build_priority_reason(priority_label, factors),
                "supporting_paper_count": len(supporting_papers),
                "supporting_author_count": len(matched_authors),
                "matched_authors": matched_authors,
            }
        )

    scored_entries.sort(
        key=lambda item: (
            -item["overall_priority_score"],
            item["title"].lower(),
        )
    )

    tier_counts = Counter(item["priority_label"] for item in scored_entries)
    tier_order = defaultdict(int)
    for entry in scored_entries:
        tier_order[entry["priority_label"]] += 1
        rank = tier_order[entry["priority_label"]]
        prefix = entry["priority_label"][0].upper()
        entry["priority_rank"] = rank
        entry["score"] = f"{prefix}{rank}"
        entry["tagLabel"] = f'{entry["card_label"]} · {entry["priority_label"]}'
        entry["sc"] = {
            "High": "sh",
            "Medium": "sm",
            "Low": "sl",
        }[entry["priority_label"]]
        # Legacy aliases keep the frontend compatible with older card field names.
        entry["cat"] = entry["card_category"]
        entry["tag"] = entry["card_tag"]
        entry["desc"] = entry["description"]
        entry["opp"] = entry["opportunity"]
        entry["matched_authors"] = entry["matched_authors"][:8]

    print(
        "Whitespace priority summary: "
        f'High={tier_counts.get("High", 0)}, '
        f'Medium={tier_counts.get("Medium", 0)}, '
        f'Low={tier_counts.get("Low", 0)}'
    )
    return scored_entries


def build_author_profiles(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    author_papers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    papers: list[dict[str, Any]] = []

    for row in records:
        paper = record_to_paper(row)
        papers.append(paper)
        for author in split_authors(row.get("authors", "")):
            author_papers[author].append(paper)

    profiles: list[dict[str, Any]] = []
    for author_name, papers in sorted(author_papers.items(), key=lambda item: item[0].lower()):
        category_counter = Counter()
        for paper in papers:
            category_counter.update(paper["categories"])
        dominant_categories = [cat for cat, _ in category_counter.most_common(3)]
        recurring_topics = extract_author_topics(papers)
        inferred_interests = infer_author_interests(dominant_categories, recurring_topics)
        sorted_papers = sorted(
            papers,
            key=lambda p: float(str(p["year"]).strip() or 0),
            reverse=True,
        )
        publication_years = sorted({paper["year_num"] for paper in sorted_papers if paper["year_num"]})
        first_published_year = publication_years[0] if publication_years else 0
        last_published_year = publication_years[-1] if publication_years else 0
        last_published = normalize_year_label(sorted_papers[0]["year"]) if sorted_papers else ""
        profiles.append({
            "author_name": author_name,
            "paper_count": len(papers),
            "first_published": str(first_published_year) if first_published_year else "",
            "first_published_year": first_published_year or None,
            "last_published": last_published,
            "last_published_year": last_published_year or None,
            "short_description": build_author_summary(dominant_categories, recurring_topics, len(papers)),
            "papers": [
                {
                    "title": paper["title"],
                    "year": normalize_year_label(paper["year"]),
                    "categories": paper["categories"],
                    "topics": paper["topics"][:4],
                }
                for paper in sorted_papers
            ],
            "dominant_categories": dominant_categories,
            "recurring_topics": recurring_topics[:6],
            "inferred_interests": inferred_interests,
            "recommended_topics_to_participate_in": [],
            "related_whitespace_opportunities": [],
            "_topic_tokens": tokenize_text(" ".join(recurring_topics + inferred_interests)),
            "_papers_full": sorted_papers,
        })

    whitespace_matches = match_authors_to_whitespace(profiles)
    scored_whitespace = build_scored_whitespace_entries(papers, profiles, whitespace_matches)
    author_map = {profile["author_name"]: profile for profile in profiles}
    total_match_count = 0
    for whitespace in scored_whitespace:
        total_match_count += len(whitespace["matched_authors"])
        for match in whitespace["matched_authors"]:
            profile = author_map[match["author_name"]]
            profile["recommended_topics_to_participate_in"].append(whitespace["title"])
            profile["related_whitespace_opportunities"].append({
                "title": whitespace["title"],
                "priority_label": whitespace["priority_label"],
                "author_whitespace_match_score": match["author_whitespace_match_score"],
                "match_score": match["match_score"],
                "reason": match["reason"],
                "bridge_reason": match.get("bridge_reason", ""),
                "representative_papers": match.get("representative_papers", []),
                "match_factors": match.get("match_factors", {}),
            })

    for profile in profiles:
        profile["recommended_topics_to_participate_in"] = list(dict.fromkeys(profile["recommended_topics_to_participate_in"]))[:6]
        profile["related_whitespace_opportunities"] = sorted(
            profile["related_whitespace_opportunities"],
            key=lambda item: item["author_whitespace_match_score"],
            reverse=True,
        )[:5]
        papers_full = profile.get("_papers_full", [])
        source_tokens = collect_text_tokens(
            " ".join(profile.get("recurring_topics", [])),
            " ".join(profile.get("inferred_interests", [])),
            " ".join(paper["title"] for paper in papers_full),
            " ".join(paper.get("abstract", "") for paper in papers_full),
            " ".join(topic for paper in papers_full for topic in paper.get("topics", [])),
        )
        all_categories = sorted({category for paper in papers_full for category in paper["categories"]})
        profile["affiliation_bucket"] = derive_affiliation_bucket(papers_full)
        profile["research_categories"] = all_categories
        profile["whitespace_relevance_bucket"] = derive_whitespace_relevance_bucket(profile["related_whitespace_opportunities"])
        profile["activity_tags"] = derive_activity_tags(profile["last_published"], profile["paper_count"], papers_full)
        profile["breadth_tags"] = derive_breadth_tags(profile["dominant_categories"], papers_full)
        collaboration_roles = derive_rule_tags(source_tokens, COLLABORATION_ROLE_RULES)
        method_access_tags = derive_rule_tags(source_tokens, METHOD_ACCESS_RULES)
        profile["collaboration_roles"] = collaboration_roles or ["Methods & Tooling"]
        profile["method_access_tags"] = method_access_tags or ["Design studies"]
        profile.pop("_topic_tokens", None)
        profile.pop("_papers_full", None)

    return profiles, scored_whitespace


def match_authors_to_whitespace(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    whitespace_matches: list[dict[str, Any]] = []
    recent_year_cutoff = max(
        (
            paper["year_num"]
            for profile in profiles
            for paper in profile.get("_papers_full", [])
        ),
        default=0,
    ) - 4

    for whitespace in WHITESPACE_OPPORTUNITIES:
        matched_authors: list[dict[str, Any]] = []

        for profile in profiles:
            match = compute_author_whitespace_match(profile, whitespace, recent_year_cutoff)
            if match:
                matched_authors.append(match)

        whitespace_matches.append({
            "title": whitespace["title"],
            "description": whitespace["description"],
            "related_categories": whitespace["related_categories"],
            "matched_authors": sorted(
                matched_authors,
                key=lambda item: (-item["author_whitespace_match_score"], item["author_name"].lower()),
            )[:8],
        })

    return whitespace_matches


def write_author_outputs(
    records: list[dict[str, Any]],
    author_profiles_path: str | Path,
    whitespace_matches_path: str | Path,
) -> tuple[int, float, int]:
    profiles, whitespace_matches = build_author_profiles(records)
    author_profiles_path = Path(author_profiles_path)
    whitespace_matches_path = Path(whitespace_matches_path)
    author_profiles_path.parent.mkdir(parents=True, exist_ok=True)

    with author_profiles_path.open("w", encoding="utf-8") as fh:
        json.dump(profiles, fh, indent=2, ensure_ascii=False)
    with whitespace_matches_path.open("w", encoding="utf-8") as fh:
        json.dump(whitespace_matches, fh, indent=2, ensure_ascii=False)

    profile_count = len(profiles)
    avg_papers = round(sum(profile["paper_count"] for profile in profiles) / profile_count, 2) if profile_count else 0.0
    match_count = sum(len(item["matched_authors"]) for item in whitespace_matches)
    return profile_count, avg_papers, match_count


def load_records_from_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
