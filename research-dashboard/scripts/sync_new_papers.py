"""
sync_new_papers.py

Incremental sync: fetches both HuggingFace datasets, finds papers not already
in papers.csv (matched by normalized title), runs BERT only on the new ones,
appends them to papers.csv, regenerates all JSON analysis artifacts, and clears
the proposal analysis cache.

Writes new_count=<n> to $GITHUB_OUTPUT so the GitHub Action can decide whether
to commit.

Usage:
    python scripts/sync_new_papers.py
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from datasets import load_dataset
from transformers import pipeline as hf_pipeline

from author_profiles import load_records_from_csv, write_analysis_outputs
from category_classifier import (
    classify_categories,
    primary_category_from_multi,
    strip_topic_id,
)

# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CSV_PATH = DATA_DIR / "papers.csv"
PAPERS_ENRICHED_PATH = DATA_DIR / "papers_enriched.json"
AUTHOR_PROFILES_PATH = DATA_DIR / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = DATA_DIR / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = DATA_DIR / "whitespace_matches.json"
PROPOSAL_ANALYSIS_CACHE_PATH = DATA_DIR / "proposal_analysis_cache.json"

HF_DATASETS = [
    {"hf_id": "ccm/publications", "data_source": "CCM Lab publications"},
    {"hf_id": "ccm/cmu-engineering-publications", "data_source": "CMU Engineering publications"},
]

MODEL_ID = (
    "OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract"
)
TOP_K_TOPICS = 8
CLASSIFY_BATCH = 8

# ── helpers (mirrors of 1_fetch_and_classify.py) ──────────────────────────────

def _s(x: Any) -> str:
    return "" if x is None else str(x).strip()


def extract_url_from_bibtex(bib: str) -> str:
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
    s = _s(s)
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/"):
        return "https://scholar.google.com" + s
    return s


def extract_bib_fields(row: dict[str, Any], ds_meta: dict[str, str]) -> dict[str, Any]:
    data_source = ds_meta["data_source"]
    hf_id = ds_meta["hf_id"]
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
            "hf_dataset": hf_id,
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
        "hf_dataset": hf_id,
        "data_source": data_source,
        "department": _s(row.get("department")),
        "bibtex": "",
        "citedby_url": "",
        "url_related_articles": "",
    }


def format_openalex_input(title: str, abstract: str) -> str:
    t = (title or "").strip()
    a = (abstract or "").strip()
    if not t and not a:
        return " "
    if not a:
        return f" {t}"
    if not t:
        return f" NONE\n {a}"
    return f" {t}\n {a}"


def topics_to_keywords(topic_results: list[dict[str, Any]], max_items: int = 5) -> str:
    parts = []
    for item in topic_results[:max_items]:
        name = strip_topic_id(item.get("label", ""))
        if not name:
            continue
        parts.append(name[:90] if len(name) > 90 else name)
    return " | ".join(parts)


def serialize_bert_topics(topic_results: list[dict[str, Any]]) -> str:
    return "; ".join(
        f'{item["label"]} ({float(item["score"]):.4f})' for item in topic_results[:TOP_K_TOPICS]
    )

# ── core logic ────────────────────────────────────────────────────────────────

def normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def load_existing_titles() -> set[str]:
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        return {
            normalize_title(row["title"])
            for row in csv.DictReader(f)
            if row.get("title")
        }


def csv_columns() -> list[str]:
    """Return the column order of the existing CSV, or a sensible default."""
    if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
        with CSV_PATH.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                return next(reader)
            except StopIteration:
                pass
    return [
        "title", "authors", "year", "categories", "keywords",
        "hf_dataset", "data_source", "bert_topics", "journal", "citations",
        "url", "citedby_url", "url_related_articles", "abstract", "bibtex", "department",
    ]


def fetch_hf_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ds_meta in HF_DATASETS:
        print(f"Fetching {ds_meta['hf_id']} …")
        try:
            ds = load_dataset(ds_meta["hf_id"], split="train")
            print(f"  → {len(ds)} rows")
            for row in ds:
                record = extract_bib_fields(dict(row), ds_meta)
                if record["title"]:
                    rows.append(record)
        except Exception as exc:
            print(f"  ✗ Failed: {exc}", file=sys.stderr)
    return rows


def classify_records(records: list[dict[str, Any]], clf: Any) -> list[dict[str, Any]]:
    for i in range(0, len(records), CLASSIFY_BATCH):
        batch = records[i : i + CLASSIFY_BATCH]
        texts = [format_openalex_input(p["title"], p.get("abstract", "")) for p in batch]
        raw = clf(texts)
        if raw and isinstance(raw[0], dict):
            raw = [raw]
        for j, record in enumerate(batch):
            topics = raw[j] if j < len(raw) else []
            record["keywords"] = topics_to_keywords(topics)
            record["bert_topics"] = serialize_bert_topics(topics)
            multi_cats = classify_categories(topics, record["title"], record.get("abstract", ""))
            record["primary_category"] = primary_category_from_multi(multi_cats)
            record["categories"] = "|".join(multi_cats)
    return records


def append_to_csv(records: list[dict[str, Any]], cols: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for record in records:
            writer.writerow({col: record.get(col, "") for col in cols})


def set_github_output(key: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{key}={value}\n")


def main() -> None:
    existing_titles = load_existing_titles()
    print(f"Existing papers in CSV: {len(existing_titles)}")

    all_hf_rows = fetch_hf_rows()
    print(f"Total papers in HuggingFace datasets: {len(all_hf_rows)}")

    new_rows = [
        row for row in all_hf_rows
        if normalize_title(row["title"]) not in existing_titles
    ]
    print(f"New papers to process: {len(new_rows)}")

    if not new_rows:
        print("Nothing to do.")
        set_github_output("new_count", "0")
        return

    print(f"Loading BERT classifier …")
    clf = hf_pipeline(
        "text-classification",
        model=MODEL_ID,
        top_k=TOP_K_TOPICS,
        truncation=True,
        max_length=512,
    )

    classified = classify_records(new_rows, clf)
    cols = csv_columns()
    append_to_csv(classified, cols)
    print(f"Appended {len(classified)} new rows to {CSV_PATH.name}")

    print("Regenerating analysis artifacts …")
    records = load_records_from_csv(CSV_PATH)
    write_analysis_outputs(
        records,
        papers_enriched_path=PAPERS_ENRICHED_PATH,
        author_profiles_path=AUTHOR_PROFILES_PATH,
        whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
        whitespace_matches_path=WHITESPACE_MATCHES_PATH,
    )
    PROPOSAL_ANALYSIS_CACHE_PATH.write_text("[]", encoding="utf-8")
    print("Done. Proposal analysis cache cleared.")

    set_github_output("new_count", str(len(classified)))


if __name__ == "__main__":
    main()
