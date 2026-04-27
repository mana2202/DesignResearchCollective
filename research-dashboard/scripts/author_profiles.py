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


def split_categories(raw: str) -> list[str]:
    return [part.strip() for part in str(raw or "").split("|") if part.strip()]


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


def build_author_profiles(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    author_papers: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in records:
        paper_categories = split_categories(row.get("categories")) or split_categories(row.get("primary_category"))
        paper_topics = parse_keyword_labels(row.get("keywords")) + parse_topic_labels(row.get("bert_topics"))
        paper = {
            "title": str(row.get("title", "")).strip(),
            "year": str(row.get("year", "")).strip(),
            "categories": paper_categories,
            "topics": list(dict.fromkeys(topic for topic in paper_topics if topic))[:8],
            "abstract": str(row.get("abstract", "")).strip(),
            "journal": str(row.get("journal", "")).strip(),
            "hf_dataset": str(row.get("hf_dataset", "")).strip(),
        }
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
        last_published = normalize_year_label(sorted_papers[0]["year"]) if sorted_papers else ""
        profiles.append({
            "author_name": author_name,
            "paper_count": len(papers),
            "last_published": last_published,
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
        })

    whitespace_matches = match_authors_to_whitespace(profiles)
    author_map = {profile["author_name"]: profile for profile in profiles}
    total_match_count = 0
    for whitespace in whitespace_matches:
        total_match_count += len(whitespace["matched_authors"])
        for match in whitespace["matched_authors"]:
            profile = author_map[match["author_name"]]
            profile["recommended_topics_to_participate_in"].append(whitespace["title"])
            profile["related_whitespace_opportunities"].append({
                "title": whitespace["title"],
                "match_score": match["match_score"],
                "reason": match["reason"],
            })

    for profile in profiles:
        profile["recommended_topics_to_participate_in"] = list(dict.fromkeys(profile["recommended_topics_to_participate_in"]))[:6]
        profile["related_whitespace_opportunities"] = sorted(
            profile["related_whitespace_opportunities"],
            key=lambda item: item["match_score"],
            reverse=True,
        )[:5]
        profile.pop("_topic_tokens", None)

    return profiles, whitespace_matches


def match_authors_to_whitespace(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    whitespace_matches: list[dict[str, Any]] = []

    for whitespace in WHITESPACE_OPPORTUNITIES:
        ws_tokens = tokenize_text(" ".join(whitespace["keywords"] + [whitespace["title"], whitespace["description"]]))
        matched_authors: list[dict[str, Any]] = []

        for profile in profiles:
            author_topics = set(profile.get("_topic_tokens", []))
            category_overlap = set(profile["dominant_categories"]) & set(whitespace["related_categories"])
            keyword_overlap = author_topics & set(ws_tokens)
            repeated_interest_overlap = set(tokenize_text(" ".join(profile["inferred_interests"]))) & set(ws_tokens)

            # Explainable deterministic score:
            # - category overlap is weighted most strongly
            # - topic overlap contributes steadily
            # - inferred-interest overlap adds an extra boost
            raw_score = (
                len(category_overlap) * 0.32
                + min(len(keyword_overlap), 4) * 0.12
                + min(len(repeated_interest_overlap), 3) * 0.08
            )
            match_score = min(round(raw_score, 2), 0.99)

            if match_score >= 0.38:
                reasons: list[str] = []
                if category_overlap:
                    reasons.append("category overlap in " + ", ".join(cat.replace("_", " ") for cat in sorted(category_overlap)))
                if keyword_overlap:
                    reasons.append("topic overlap in " + ", ".join(sorted(keyword_overlap)[:4]))
                if repeated_interest_overlap:
                    reasons.append("recurring interest overlap in " + ", ".join(sorted(repeated_interest_overlap)[:3]))
                matched_authors.append({
                    "author_name": profile["author_name"],
                    "match_score": match_score,
                    "reason": "; ".join(reasons),
                })

        whitespace_matches.append({
            "title": whitespace["title"],
            "description": whitespace["description"],
            "related_categories": whitespace["related_categories"],
            "matched_authors": sorted(
                matched_authors,
                key=lambda item: (-item["match_score"], item["author_name"].lower()),
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
