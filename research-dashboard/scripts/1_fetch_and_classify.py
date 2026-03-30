"""
1_fetch_and_classify.py

Fetches papers from two HuggingFace datasets, classifies them with the
OpenAlex BERT topic model (title+abstract), maps OpenAlex topics to keywords
and to the four CCM categories, then writes data/papers.csv.

Usage:
    python scripts/1_fetch_and_classify.py
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
    {
        "hf_id": "ccm/publications",
        "source": "CCM Lab",
        "data_source": "CCM Lab publications",
    },
    {
        "hf_id": "ccm/cmu-engineering-publications",
        "source": "CMU Engineering",
        "data_source": "CMU Engineering publications",
    },
]

MODEL_ID = (
    "OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract"
)

CATEGORIES = ["ideation", "optimization", "grammar", "decision_making"]

# Substrings matched (lowercase) against topic labels + title + abstract
CAT_PATTERNS: dict[str, list[str]] = {
    "ideation": [
        "ideation",
        "creativity",
        "creative",
        "conceptual",
        "concept generation",
        "brainstorm",
        "design exploration",
        "innovation",
        "generative",
        "idea",
        "concept design",
        "co-design",
        "user-centered",
        "design thinking",
        "early design",
    ],
    "optimization": [
        "optimization",
        "optimisation",
        "machine learning",
        "neural",
        "evolutionary",
        "surrogate",
        "metamodel",
        "topology optimization",
        "multiobjective",
        "computational",
        "algorithm",
        "deep learning",
        "cfd",
        "finite element",
        "parametric design",
    ],
    "grammar": [
        "grammar",
        "shape grammar",
        "rule-based",
        "formal language",
        "syntax",
        "representation",
        "schema",
        "symbolic",
        "graph grammar",
        "formal grammar",
    ],
    "decision_making": [
        "decision",
        "human factors",
        "team",
        "collaborative",
        "behavior",
        "cognitive",
        "strategy",
        "social",
        "agent-based",
        "game theory",
        "preference",
        "trust",
    ],
}

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.csv")

# Inference batch size (pipeline accepts lists)
CLASSIFY_BATCH = 8
TOP_K_TOPICS = 8


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


def map_to_categories(
    topic_results: list[dict[str, Any]],
    title: str,
    abstract: str,
) -> str:
    """Map OpenAlex topic labels + text to the four CCM categories."""
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

    # Weight higher-confidence topics more
    for i, item in enumerate(topic_results[:5]):
        w = float(item.get("score", 0)) * (1.2 - i * 0.08)
        label = strip_topic_id(item.get("label", "")).lower()
        for cat, patterns in CAT_PATTERNS.items():
            for p in patterns:
                if p in label:
                    scores[cat] += 2.0 * w

    ordered = sorted(CATEGORIES, key=lambda c: scores[c], reverse=True)
    chosen = [c for c in ordered if scores[c] > 0]

    if not chosen:
        b = blob
        if any(x in b for x in ("design", "engineering design", "product development")):
            chosen = ["ideation"]
        elif "optim" in b or "machine learning" in b or "neural" in b:
            chosen = ["optimization"]
        elif "grammar" in b or " rule" in b or "formal" in b:
            chosen = ["grammar"]
        elif "decision" in b or "team" in b or "human" in b:
            chosen = ["decision_making"]
        else:
            chosen = ["ideation"]

    return ", ".join(chosen)


def extract_bib_fields(row: dict, ds_meta: dict) -> dict:
    """Pull title, authors, year, abstract from a dataset row."""
    source = ds_meta["source"]
    data_source = ds_meta["data_source"]
    hf_dataset = ds_meta["hf_id"]

    if "bib_dict" in row and isinstance(row["bib_dict"], dict):
        bd = row["bib_dict"]
        return {
            "title": bd.get("title", "").strip(),
            "authors": bd.get("author", "").strip(),
            "year": bd.get("pub_year") or "",
            "abstract": bd.get("abstract", "").strip(),
            "journal": (bd.get("journal") or bd.get("conference") or "").strip(),
            "url": row.get("pub_url", "") or "",
            "citations": row.get("num_citations", 0) or 0,
            "source": source,
            "hf_dataset": hf_dataset,
            "data_source": data_source,
            "department": "",
        }

    return {
        "title": str(row.get("title", "")).strip(),
        "authors": str(row.get("faculty", "")).strip(),
        "year": str(row.get("pub_year", "")).strip()[:4],
        "abstract": "",
        "journal": str(row.get("citation", "")).strip(),
        "url": "",
        "citations": int(row.get("num_citations", 0) or 0),
        "source": source,
        "hf_dataset": hf_dataset,
        "data_source": data_source,
        "department": str(row.get("department", "")).strip(),
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
            record["categories"] = map_to_categories(
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

    # Stable column order for CSV consumers
    preferred = [
        "title",
        "authors",
        "year",
        "categories",
        "keywords",
        "hf_dataset",
        "data_source",
        "source",
        "bert_topics",
        "journal",
        "citations",
        "url",
        "abstract",
        "department",
    ]
    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
    df = df[cols]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\n💾  Saved {len(df)} rows → {OUTPUT_PATH}")
    print(df[["title", "year", "hf_dataset", "categories"]].head(5).to_string())


if __name__ == "__main__":
    main()
