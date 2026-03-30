"""
1_fetch_and_classify.py

Fetches papers from two HuggingFace datasets, classifies them with the
OpenAlex BERT topic model (title+abstract), maps OpenAlex topics to keywords
and to the four CCM categories, then writes data/papers.csv.

Usage:
    python scripts/1_fetch_and_classify.py

Optional (faster test runs):
    MAX_PAPERS=500 python scripts/1_fetch_and_classify.py
"""

from __future__ import annotations

import os
import re
from typing import Any

import pandas as pd
from datasets import load_dataset
from tqdm import tqdm
from transformers import pipeline

# ── Config ────────────────────────────────────────────────────────────────────

DATASETS = [
    {"hf_id": "ccm/publications", "data_source": "CCM Lab publications"},
    {"hf_id": "ccm/cmu-engineering-publications", "data_source": "CMU Engineering publications"},
]

MODEL_ID = (
    "OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract"
)

# Single label per paper; spelling matches project convention ("optimmization").
CATEGORIES = ["ideation", "optimmization", "grammar", "decision_making"]

# Substrings (lowercase) in title + abstract + BERT topic labels — weighted toward primary contribution.
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

# Tie-break order when scores tie (first wins).
CATEGORY_TIE_ORDER = ["ideation", "optimmization", "grammar", "decision_making"]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.csv")

# Inference batch size (pipeline accepts lists)
CLASSIFY_BATCH = 8
TOP_K_TOPICS = 8


def _s(x: Any) -> str:
    """Safe string for HF dataset fields that may be None."""
    if x is None:
        return ""
    return str(x).strip()


def extract_url_from_bibtex(bib: str) -> str:
    """Best-effort `url = {...}` from a BibTeX string when pub_url is absent."""
    if not bib:
        return ""
    m = re.search(r"url\s*=\s*\{([^}]*)\}", bib, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r'url\s*=\s*"([^"]+)"', bib, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def normalize_scholar_href(s: str) -> str:
    """HF sometimes stores Google Scholar paths without a host."""
    s = _s(s)
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/"):
        return "https://scholar.google.com" + s
    return s


def format_openalex_input(title: str, abstract: str) -> str:
    """Match OpenAlex training format: title+abstract, title-only, or abstract-only."""
    t = (title or "").strip()
    a = (abstract or "").strip()
    if not t and not a:
        return " "
    if not a:
        return f" {t}"
    if not t:
        return f" NONE\n {a}"
    return f" {t}\n {a}"


def strip_topic_id(label: str) -> str:
    return re.sub(r"^\d+\s*:\s*", "", (label or "").strip()).strip()


def topics_to_keywords(topic_results: list[dict[str, Any]], max_items: int = 5) -> str:
    parts: list[str] = []
    for item in topic_results[:max_items]:
        name = strip_topic_id(item.get("label", ""))
        if not name:
            continue
        if len(name) > 90:
            name = name[:87] + "..."
        parts.append(name)
    return " | ".join(parts)


def serialize_bert_topics(topic_results: list[dict[str, Any]]) -> str:
    return "; ".join(
        f'{item["label"]} ({float(item["score"]):.4f})' for item in topic_results[:TOP_K_TOPICS]
    )


def primary_category(
    topic_results: list[dict[str, Any]],
    title: str,
    abstract: str,
) -> str:
    """Exactly one label: ideation | optimmization | grammar | decision_making."""
    blobs: list[str] = []
    for item in topic_results[:TOP_K_TOPICS]:
        blobs.append(strip_topic_id(item.get("label", "")).lower())
        blobs.append((item.get("label") or "").lower())
    blobs.append((title or "").lower())
    blobs.append((abstract or "").lower())
    blob = " ".join(blobs)

    scores: dict[str, float] = {c: 0.0 for c in CATEGORIES}
    for cat, patterns in CAT_PATTERNS.items():
        for p in patterns:
            if p in blob:
                scores[cat] += float(len(p)) ** 0.5

    for i, item in enumerate(topic_results[:5]):
        w = float(item.get("score", 0)) * (1.2 - i * 0.08)
        label = strip_topic_id(item.get("label", "")).lower()
        for cat, patterns in CAT_PATTERNS.items():
            for p in patterns:
                if p in label:
                    scores[cat] += 2.0 * w

    best = max(scores.values())
    if best > 0:
        for c in CATEGORY_TIE_ORDER:
            if scores[c] == best:
                return c

    # Fallback when no pattern matched — heuristic aligned with user rules
    b = blob
    if any(
        x in b
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
        x in b
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
        x in b
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
    return "ideation"


def extract_bib_fields(row: dict, ds_meta: dict) -> dict:
    """Pull title, authors, year, abstract from a dataset row."""
    data_source = ds_meta["data_source"]
    hf_dataset = ds_meta["hf_id"]

    if "bib_dict" in row and isinstance(row["bib_dict"], dict):
        bd = row["bib_dict"]
        bibtex_raw = _s(row.get("bibtex"))
        pub = _s(row.get("pub_url"))
        url = pub or extract_url_from_bibtex(bibtex_raw)
        return {
            "title": _s(bd.get("title")),
            "authors": _s(bd.get("author")),
            "year": bd.get("pub_year") or "",
            "abstract": _s(bd.get("abstract")),
            "journal": _s(bd.get("journal") or bd.get("conference")),
            "url": url,
            "citations": row.get("num_citations", 0) or 0,
            "hf_dataset": hf_dataset,
            "data_source": data_source,
            "department": "",
            "bibtex": bibtex_raw,
            "citedby_url": normalize_scholar_href(_s(row.get("citedby_url"))),
            "url_related_articles": normalize_scholar_href(_s(row.get("url_related_articles"))),
        }

    return {
        "title": _s(row.get("title")),
        "authors": _s(row.get("faculty")),
        "year": _s(row.get("pub_year"))[:4],
        "abstract": "",
        "journal": _s(row.get("citation")),
        "url": "",
        "citations": int(row.get("num_citations", 0) or 0),
        "hf_dataset": hf_dataset,
        "data_source": data_source,
        "department": _s(row.get("department")),
        "bibtex": "",
        "citedby_url": "",
        "url_related_articles": "",
    }


def main() -> None:
    print(f"Loading classifier: {MODEL_ID} …")
    clf = pipeline(
        "text-classification",
        model=MODEL_ID,
        top_k=TOP_K_TOPICS,
        truncation=True,
        max_length=512,
    )

    all_rows: list[dict] = []

    for ds_config in DATASETS:
        print(f"\n📥  Loading {ds_config['hf_id']} …")
        try:
            ds = load_dataset(ds_config["hf_id"], split="train")
            print(f"    → {len(ds)} rows")
            for row in ds:
                record = extract_bib_fields(dict(row), ds_config)
                if record["title"]:
                    all_rows.append(record)
        except Exception as e:
            print(f"    ✗ Failed to load: {e}")

    print(f"\n✅  Loaded {len(all_rows)} papers total")

    max_papers = os.environ.get("MAX_PAPERS")
    if max_papers:
        try:
            n = int(max_papers)
            if n > 0 and len(all_rows) > n:
                print(f"\n⚙️  MAX_PAPERS={n}: classifying first {n} of {len(all_rows)} rows …")
                all_rows = all_rows[:n]
        except ValueError:
            print(f"\n⚠️  Ignoring invalid MAX_PAPERS={max_papers!r}")

    print(f"\n🤖  Classifying with OpenAlex BERT (batch size={CLASSIFY_BATCH}) …")
    for i in tqdm(range(0, len(all_rows), CLASSIFY_BATCH)):
        batch = all_rows[i : i + CLASSIFY_BATCH]
        texts = [format_openalex_input(p["title"], p.get("abstract", "")) for p in batch]
        raw = clf(texts)
        # Batch returns list[list[dict]]; single-item edge case
        if raw and isinstance(raw[0], dict):
            raw = [raw]

        for j, record in enumerate(batch):
            topic_results = raw[j] if j < len(raw) else []
            record["keywords"] = topics_to_keywords(topic_results)
            record["bert_topics"] = serialize_bert_topics(topic_results)
            record["categories"] = primary_category(
                topic_results,
                record["title"],
                record.get("abstract", ""),
            )

    df = pd.DataFrame(all_rows)

    def parse_year(y: object) -> int | None:
        try:
            return int(str(y)[:4])
        except Exception:
            return None

    df["year"] = df["year"].apply(parse_year)
    df = df.sort_values("year", ascending=False, na_position="last")

    output_cols = [
        "title",
        "authors",
        "year",
        "categories",
        "keywords",
        "hf_dataset",
        "data_source",
        "bert_topics",
        "journal",
        "citations",
        "url",
        "citedby_url",
        "url_related_articles",
        "abstract",
        "bibtex",
        "department",
    ]
    df = df[[c for c in output_cols if c in df.columns]]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\n💾  Saved {len(df)} rows → {OUTPUT_PATH}")
    print(df[["title", "year", "hf_dataset", "categories"]].head(5).to_string())


if __name__ == "__main__":
    main()
