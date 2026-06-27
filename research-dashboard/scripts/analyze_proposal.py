from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from author_profiles import (
    CATEGORY_LABELS,
    load_records_from_csv,
    normalize_category_token,
    tokenize_text,
    write_analysis_outputs,
)


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PAPERS_CSV_PATH = DATA_DIR / "papers.csv"
PAPERS_ENRICHED_PATH = DATA_DIR / "papers_enriched.json"
AUTHOR_PROFILES_PATH = DATA_DIR / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = DATA_DIR / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = DATA_DIR / "whitespace_matches.json"
PROPOSAL_ANALYSIS_CACHE_PATH = DATA_DIR / "proposal_analysis_cache.json"

CATEGORY_KEYWORDS = {
    "ideation": {
        "ideation", "brainstorm", "brainstorming", "concept", "concepts", "creative",
        "creativity", "co-creation", "co-creative", "exploration", "fixation", "divergent",
        "sketch", "sketching", "inspiration",
    },
    "optimmization": {
        "optimization", "optimmization", "topology", "surrogate", "surrogates", "simulation",
        "neural", "operator", "lattice", "performance", "fabrication", "manufacturing",
        "parametric", "parameterized",
    },
    "grammar": {
        "grammar", "grammars", "rule", "rules", "sequence", "sequences", "state",
        "heuristic", "heuristics", "protocol", "constraint", "constrained", "hmm", "markov",
    },
    "decision_making": {
        "decision", "decisions", "decision-making", "decision_making", "tradeoff",
        "tradeoffs", "trade-off", "trade-offs", "preference", "preferences", "trust",
        "evaluation", "assessment", "uncertainty", "selection", "risk",
    },
}

CAPABILITY_RULES = [
    {"label": "design ideation", "categories": {"ideation"}, "keywords": {"ideation", "concept", "brainstorm", "creative", "fixation"}},
    {"label": "optimization workflows", "categories": {"optimmization"}, "keywords": {"optimization", "surrogate", "topology", "workflow", "performance", "simulation"}},
    {"label": "design grammars", "categories": {"grammar"}, "keywords": {"grammar", "rule", "sequence", "heuristic", "constraint"}},
    {"label": "human-AI collaboration", "categories": {"ideation", "decision_making"}, "keywords": {"human-ai", "interactive", "ai-assisted", "collaboration", "feedback", "trust"}},
    {"label": "decision support", "categories": {"decision_making"}, "keywords": {"decision", "uncertainty", "tradeoff", "preference", "selection"}},
    {"label": "simulation/evaluation", "categories": {"optimmization", "decision_making"}, "keywords": {"simulation", "evaluation", "experiment", "validation", "benchmark"}},
    {"label": "visualization", "categories": {"decision_making", "ideation"}, "keywords": {"visualization", "interface", "dashboard", "mapping", "explainability"}},
    {"label": "computational design methods", "categories": {"grammar", "optimmization"}, "keywords": {"computational", "generative", "parametric", "algorithmic", "operator"}},
]

METHOD_TERMS = {"dataset", "datasets", "benchmark", "evaluation", "evaluate", "validation", "validated", "experiment", "experiments", "study", "studies", "simulation", "protocol", "metric", "metrics"}
DATASET_TERMS = {"dataset", "datasets", "corpus", "benchmark", "repository", "repositories", "archive", "telemetry", "log", "logs"}
LOW_SIGNAL_THRESHOLD = 0.16


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def display_category(category: str) -> str:
    return CATEGORY_LABELS.get(normalize_category_token(category), str(category).replace("_", " "))


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_analysis_artifacts() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not PAPERS_ENRICHED_PATH.exists() or not AUTHOR_PROFILES_PATH.exists() or not WHITESPACE_OPPORTUNITIES_PATH.exists():
        records = load_records_from_csv(PAPERS_CSV_PATH)
        write_analysis_outputs(
            records,
            papers_enriched_path=PAPERS_ENRICHED_PATH,
            author_profiles_path=AUTHOR_PROFILES_PATH,
            whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
            whitespace_matches_path=WHITESPACE_MATCHES_PATH,
        )
    if not PROPOSAL_ANALYSIS_CACHE_PATH.exists():
        PROPOSAL_ANALYSIS_CACHE_PATH.write_text("[]\n", encoding="utf-8")

    return (
        load_json(PAPERS_ENRICHED_PATH, []),
        load_json(AUTHOR_PROFILES_PATH, []),
        load_json(WHITESPACE_OPPORTUNITIES_PATH, []),
    )


def proposal_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def top_tokens(tokens: list[str], limit: int = 16) -> list[str]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return [
        token
        for token, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def overlap_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    candidate_set = set(candidate_tokens)
    overlap = sum(1 for token in query_tokens if token in candidate_set)
    return clamp01(overlap / min(len(query_tokens), 12))


def matched_terms(query_tokens: list[str], candidate_tokens: list[str], limit: int = 4) -> list[str]:
    candidate_set = set(candidate_tokens)
    return [token for token in query_tokens if token in candidate_set][:limit]


def build_proposal_profile(proposal_text: str) -> dict[str, Any]:
    normalized_text = proposal_text.strip()
    raw_lower = normalized_text.lower()
    tokens = tokenize_text(normalized_text)
    salient_tokens = top_tokens(tokens)
    category_scores: dict[str, float] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        keyword_hits = sum(1 for keyword in keywords if keyword in raw_lower)
        token_hits = sum(1 for token in salient_tokens if token in keywords)
        category_scores[category] = round(clamp01((keyword_hits * 0.65 + token_hits * 0.35) / 3.0), 3)

    categories = [
        category
        for category, score in sorted(category_scores.items(), key=lambda item: (-item[1], item[0]))
        if score >= LOW_SIGNAL_THRESHOLD
    ]
    if not categories:
        strongest = max(category_scores.items(), key=lambda item: item[1])
        if strongest[1] > 0:
            categories = [strongest[0]]

    return {
        "text": normalized_text,
        "raw_lower": raw_lower,
        "tokens": tokens,
        "salient_tokens": salient_tokens,
        "category_scores": category_scores,
        "categories": categories,
    }


def score_paper_match(profile: dict[str, Any], paper: dict[str, Any]) -> dict[str, Any]:
    title_tokens = tokenize_text(paper.get("title", ""))
    abstract_tokens = tokenize_text(paper.get("abstract", ""))
    keyword_tokens = tokenize_text(" ".join(paper.get("keywords", [])))
    topic_tokens = tokenize_text(" ".join(paper.get("topics", [])))
    all_tokens = unique(title_tokens + abstract_tokens + keyword_tokens + topic_tokens)
    proposal_categories = set(profile["categories"])
    paper_categories = {normalize_category_token(category) for category in paper.get("categories", [])}
    category_overlap = proposal_categories & paper_categories
    current_year = paper.get("year_num", 0) or 0
    recency_score = clamp01((paper.get("year_num", 0) - max(current_year - 12, 0)) / 12) if paper.get("year_num") else 0.0
    match_score = round(
        overlap_score(profile["salient_tokens"], title_tokens) * 0.25
        + overlap_score(profile["salient_tokens"], abstract_tokens) * 0.25
        + overlap_score(profile["salient_tokens"], keyword_tokens) * 0.18
        + overlap_score(profile["salient_tokens"], topic_tokens) * 0.14
        + clamp01(len(category_overlap) / max(len(proposal_categories), 1)) * 0.12
        + recency_score * 0.06,
        3,
    )
    overlap_terms = matched_terms(profile["salient_tokens"], all_tokens)
    reason_parts = []
    if category_overlap:
        reason_parts.append(f"aligns with {', '.join(display_category(cat) for cat in sorted(category_overlap))}")
    if overlap_terms:
        reason_parts.append(f"shares terms like {', '.join(overlap_terms)}")
    if paper.get("year"):
        reason_parts.append(f"published in {paper['year']}")
    return {
        "title": paper.get("title", ""),
        "year": paper.get("year", ""),
        "authors": paper.get("authors", []),
        "categories": sorted(paper_categories),
        "topics": paper.get("topics", [])[:5],
        "abstract": paper.get("abstract", ""),
        "match_score": match_score,
        "reason": "; ".join(reason_parts) if reason_parts else "Weak but detectable topical overlap.",
        "_tokens": all_tokens,
    }


def nearest_prior_papers(profile: dict[str, Any], papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [score_paper_match(profile, paper) for paper in papers]
    return [
        paper for paper in sorted(scored, key=lambda item: (-item["match_score"], str(item["year"])), reverse=False)
        if paper["match_score"] >= 0.08
    ][:6]


def score_author_match(profile: dict[str, Any], author: dict[str, Any], paper_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    recurring_tokens = tokenize_text(" ".join(author.get("recurring_topics", [])))
    interest_tokens = tokenize_text(" ".join(author.get("inferred_interests", [])))
    proposal_categories = set(profile["categories"])
    author_categories = {normalize_category_token(category) for category in author.get("research_categories", [])}
    category_topic_match = clamp01(
        overlap_score(profile["salient_tokens"], unique(recurring_tokens + interest_tokens)) * 0.65
        + (len(proposal_categories & author_categories) / max(len(proposal_categories), 1) if proposal_categories else 0.0) * 0.35
    )

    representative_papers = []
    for paper in author.get("papers", []):
        title = paper.get("title", "")
        scored_paper = score_paper_match(profile, {
            "title": title,
            "abstract": "",
            "keywords": [],
            "topics": paper.get("topics", []),
            "categories": paper.get("categories", []),
            "year": paper.get("year", ""),
            "year_num": int(str(paper.get("year", "0") or 0)) if str(paper.get("year", "")).isdigit() else 0,
            "authors": [author.get("author_name", "")],
        })
        if title in paper_lookup:
            scored_paper["match_score"] = round((scored_paper["match_score"] * 0.7) + (paper_lookup[title]["match_score"] * 0.3), 3)
            if paper_lookup[title]["reason"]:
                scored_paper["reason"] = paper_lookup[title]["reason"]
        if scored_paper["match_score"] >= 0.08:
            representative_papers.append({
                "title": title,
                "year": paper.get("year", ""),
                "categories": paper.get("categories", []),
                "topics": paper.get("topics", [])[:4],
                "reason": scored_paper["reason"],
                "_score": scored_paper["match_score"],
            })

    representative_papers = sorted(representative_papers, key=lambda item: (-item["_score"], str(item["year"])))[:3]
    representative_paper_score = representative_papers[0]["_score"] if representative_papers else 0.0
    recent_year = int(author.get("last_published_year") or 0)
    recency_score = clamp01((recent_year - (max(recent_year, 2026) - 10)) / 10) if recent_year else 0.0
    affiliation = author.get("affiliation_bucket", "")
    affiliation_score = 1.0 if affiliation == "DRC Researchers" else 0.85 if affiliation == "Both" else 0.65
    recent_drc_relevance = clamp01(recency_score * 0.7 + affiliation_score * 0.3)
    whitespace_tokens = tokenize_text(" ".join(item.get("title", "") for item in author.get("related_whitespace_opportunities", [])))
    bridge_to_gap_score = clamp01(overlap_score(profile["salient_tokens"], whitespace_tokens) * 0.6 + overlap_score(profile["salient_tokens"], recurring_tokens + interest_tokens) * 0.4)
    total_score = round(
        recent_drc_relevance * 0.25
        + category_topic_match * 0.35
        + representative_paper_score * 0.25
        + bridge_to_gap_score * 0.15,
        3,
    )
    matched = matched_terms(profile["salient_tokens"], unique(recurring_tokens + interest_tokens), 3)
    bridge_reason = (
        f"Connects through {'/'.join(matched)} and adjacent whitespace overlap."
        if matched
        else "Connects primarily through adjacent category and whitespace overlap."
    )
    return {
        "author_name": author.get("author_name", ""),
        "author_whitespace_match_score": total_score,
        "match_factors": {
            "recent_drc_relevance_score": round(recent_drc_relevance, 3),
            "category_topic_match_score": round(category_topic_match, 3),
            "representative_paper_score": round(representative_paper_score, 3),
            "bridge_to_gap_score": round(bridge_to_gap_score, 3),
        },
        "representative_papers": [
            {key: value for key, value in paper.items() if not key.startswith("_")}
            for paper in representative_papers
        ],
        "bridge_reason": bridge_reason,
        "reason": (
            f"Relevant through {', '.join(display_category(cat) for cat in sorted(proposal_categories & author_categories))}."
            if proposal_categories & author_categories
            else "Relevant through adjacent topics and recent work."
        ),
    }


def likely_collaborators(profile: dict[str, Any], authors: list[dict[str, Any]], nearest_papers_for_lookup: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paper_lookup = {paper["title"]: paper for paper in nearest_papers_for_lookup}
    scored = [score_author_match(profile, author, paper_lookup) for author in authors]
    return [
        author for author in sorted(scored, key=lambda item: (-item["author_whitespace_match_score"], item["author_name"].lower()))
        if author["author_whitespace_match_score"] >= 0.18
    ][:5]


def research_space_summary(profile: dict[str, Any], nearby_papers: list[dict[str, Any]]) -> dict[str, Any]:
    category_labels = [display_category(category) for category in profile["categories"]]
    if category_labels:
        broad_space = ", ".join(category_labels)
    else:
        broad_space = "an interdisciplinary space without a strong category signal"
    summary = f"This proposal sits in {broad_space}."
    if nearby_papers:
        summary += f' The closest prior anchor is "{nearby_papers[0]["title"]}" ({nearby_papers[0]["year"] or "n.d."}).'
    return {
        "broad_research_space": broad_space,
        "categories": profile["categories"],
        "category_scores": profile["category_scores"],
        "summary": summary,
    }


def distinctiveness_summary(profile: dict[str, Any], nearby_papers: list[dict[str, Any]]) -> dict[str, Any]:
    nearby_tokens = unique([token for paper in nearby_papers for token in paper.get("_tokens", [])])
    shared = matched_terms(profile["salient_tokens"], nearby_tokens, 6)
    distinct = [token for token in profile["salient_tokens"] if token not in set(nearby_tokens)][:6]
    return {
        "shared_foundation": shared,
        "distinct_terms": distinct,
        "summary": (
            f"Nearby work already covers {', '.join(shared)}. "
            f"The proposal appears most distinct where it emphasizes {', '.join(distinct)}."
            if shared and distinct
            else "The proposal is either very close to existing work or too underspecified to isolate a distinct angle clearly."
        ),
    }


def infer_capabilities(profile: dict[str, Any]) -> list[dict[str, Any]]:
    proposal_categories = set(profile["categories"])
    results: list[dict[str, Any]] = []
    for rule in CAPABILITY_RULES:
        category_hits = len(rule["categories"] & proposal_categories)
        keyword_hits = len(rule["keywords"] & set(profile["salient_tokens"]))
        score = category_hits * 0.55 + keyword_hits * 0.45
        if score <= 0:
            continue
        results.append({
            "capability": rule["label"],
            "score": round(score, 3),
            "reason": (
                f"Supported by category overlap in {', '.join(display_category(cat) for cat in sorted(rule['categories'] & proposal_categories))}"
                if category_hits
                else f"Supported by proposal language around {', '.join(sorted(rule['keywords'] & set(profile['salient_tokens']))[:3])}"
            ),
        })
    return sorted(results, key=lambda item: (-item["score"], item["capability"]))[:5]


def infer_risks(profile: dict[str, Any], nearby_papers: list[dict[str, Any]], collaborators: list[dict[str, Any]]) -> list[str]:
    risks: list[str] = []
    if not profile["categories"]:
        risks.append("The proposal does not yet anchor clearly to ideation, optimmization, grammar, or decision_making.")
    if not nearby_papers or nearby_papers[0]["match_score"] < 0.16:
        risks.append("The connection to the current corpus is still weak, which makes the occupied research space harder to justify.")
    if not any(term in profile["raw_lower"] for term in METHOD_TERMS):
        risks.append("The proposal does not yet describe a clear method or evaluation path.")
    if not any(term in profile["raw_lower"] for term in DATASET_TERMS):
        risks.append("The proposal does not yet show a concrete dataset, benchmark, or evidence source.")
    if not collaborators or collaborators[0]["author_whitespace_match_score"] < 0.24:
        risks.append("There is not yet a strong collaborator fit in the current DRC profile set.")
    if len(profile["salient_tokens"]) < 6:
        risks.append("The proposal is still too brief to score confidently; adding domain, method, and outcome detail would help.")
    return risks or ["The biggest remaining risk is making the evaluation plan explicit enough for others to judge feasibility."]


def strip_private_fields(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in paper.items() if not key.startswith("_")} for paper in papers]


DRC_HF_DATASET = "ccm/publications"
NICHE_SCORE_THRESHOLD = 0.04
NICHE_RECENT_WINDOW = 2


def niche_momentum(profile: dict[str, Any], papers: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute DRC-only publication trend in the proposal's specific niche.

    Filters to ccm/publications papers, scores each against the proposal
    profile, then splits into recent (last NICHE_RECENT_WINDOW years) and
    historical to derive a trend direction and rising topic signals.
    """
    drc_papers = [p for p in papers if p.get("hf_dataset") == DRC_HF_DATASET and p.get("year_num")]
    if not drc_papers:
        return {"gap": True}

    max_year = max(p["year_num"] for p in drc_papers)
    recent_cutoff = max_year - NICHE_RECENT_WINDOW + 1

    scored: list[dict[str, Any]] = []
    for paper in drc_papers:
        match = score_paper_match(profile, paper)
        if match["match_score"] > NICHE_SCORE_THRESHOLD:
            scored.append({**paper, "match_score": match["match_score"]})

    if not scored:
        return {"gap": True, "max_year": max_year}

    recent = [p for p in scored if p["year_num"] >= recent_cutoff]
    historical = [p for p in scored if p["year_num"] < recent_cutoff]

    min_scored_year = min(p["year_num"] for p in scored)
    historical_years = max(recent_cutoff - min_scored_year, 1)
    recent_per_year = len(recent) / NICHE_RECENT_WINDOW
    historical_per_year = len(historical) / historical_years

    if not historical:
        trend = "emerging" if recent else "gap"
    else:
        ratio = recent_per_year / max(historical_per_year, 0.5)
        if ratio >= 2.0:
            trend = "accelerating"
        elif ratio >= 1.2:
            trend = "growing"
        elif ratio <= 0.5:
            trend = "declining"
        else:
            trend = "steady"

    recent_topics: dict[str, int] = {}
    historical_topics: dict[str, int] = {}
    for p in recent:
        for topic in (p.get("topics") or [])[:4]:
            recent_topics[topic] = recent_topics.get(topic, 0) + 1
    for p in historical:
        for topic in (p.get("topics") or [])[:4]:
            historical_topics[topic] = historical_topics.get(topic, 0) + 1

    rising_topics = sorted(
        recent_topics.items(),
        key=lambda kv: -(kv[1] / NICHE_RECENT_WINDOW - historical_topics.get(kv[0], 0) / historical_years),
    )[:4]

    recent_papers_out = sorted(recent, key=lambda p: (-p["year_num"], -p["match_score"]))[:3]

    return {
        "gap": False,
        "total_niche_papers": len(scored),
        "recent_count": len(recent),
        "historical_count": len(historical),
        "recent_cutoff_year": recent_cutoff,
        "max_year": max_year,
        "trend_direction": trend,
        "rising_topics": [t for t, _ in rising_topics],
        "recent_papers": [
            {
                "title": p["title"],
                "year": p["year_num"],
                "authors": p.get("authors", []),
                "match_score": round(p["match_score"], 3),
            }
            for p in recent_papers_out
        ],
    }


def analyze_proposal(proposal_text: str, *, use_cache: bool = True) -> dict[str, Any]:
    proposal_text = proposal_text.strip()
    if not proposal_text:
        raise ValueError("proposal_text must not be empty")

    papers, authors, whitespace = ensure_analysis_artifacts()
    cache_entries = load_json(PROPOSAL_ANALYSIS_CACHE_PATH, [])
    cache_key = proposal_hash(proposal_text)

    if use_cache:
        for entry in cache_entries:
            if entry.get("proposal_hash") == cache_key:
                return entry["analysis"]

    profile = build_proposal_profile(proposal_text)
    nearby_papers = nearest_prior_papers(profile, papers)
    collaborators = likely_collaborators(profile, authors, nearby_papers)
    capabilities = infer_capabilities(profile)
    distinct = distinctiveness_summary(profile, nearby_papers)
    risks = infer_risks(profile, nearby_papers, collaborators)
    momentum = niche_momentum(profile, papers)

    proposal_tokens = set(profile["salient_tokens"])
    whitespace_hits = [
        {
            "title": item.get("title", ""),
            "priority_label": item.get("priority_label", item.get("priority", "")),
            "match_score": round(
                overlap_score(profile["salient_tokens"], tokenize_text(" ".join(
                    [item.get("title", ""), item.get("description", ""), item.get("opportunity", ""), " ".join(item.get("keywords", []))]
                ))),
                3,
            ),
        }
        for item in whitespace
    ]
    whitespace_hits = [item for item in whitespace_hits if item["match_score"] >= 0.10]
    whitespace_hits.sort(key=lambda item: (-item["match_score"], item["title"].lower()))

    analysis = {
        "proposal_text": proposal_text,
        "research_space_summary": research_space_summary(profile, nearby_papers),
        "drc_niche_momentum": momentum,
        "nearest_prior_papers": strip_private_fields(nearby_papers),
        "what_is_distinct": distinct,
        "drc_capability_it_builds_on": capabilities,
        "likely_collaborators": collaborators,
        "missing_evidence_or_biggest_risk": risks,
        "related_whitespace_opportunities": whitespace_hits[:5],
        "analysis_metadata": {
            "approach": "deterministic metadata scoring",
            "signals_used": [
                "keyword overlap",
                "topic overlap",
                "category overlap",
                "paper recency",
                "author representative papers",
                "author recent DRC relevance",
                "bridge-to-gap overlap",
                "drc niche momentum (last 2 years)",
            ],
            "salient_tokens": sorted(proposal_tokens),
        },
    }

    if use_cache:
        cache_entries = [entry for entry in cache_entries if entry.get("proposal_hash") != cache_key]
        cache_entries.append({"proposal_hash": cache_key, "analysis": analysis})
        PROPOSAL_ANALYSIS_CACHE_PATH.write_text(json.dumps(cache_entries, indent=2, ensure_ascii=False), encoding="utf-8")

    return analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a research proposal against the DRC corpus.")
    parser.add_argument("proposal", nargs="?", help="Proposal text. If omitted, stdin is used.")
    parser.add_argument("--file", type=Path, help="Path to a text file containing the proposal.")
    parser.add_argument("--no-cache", action="store_true", help="Bypass and do not update proposal_analysis_cache.json.")
    args = parser.parse_args()

    if args.file:
        proposal_text = args.file.read_text(encoding="utf-8")
    elif args.proposal:
        proposal_text = args.proposal
    else:
        proposal_text = input("Paste proposal text: ").strip()

    analysis = analyze_proposal(proposal_text, use_cache=not args.no_cache)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
